import json
import os
import queue
import subprocess
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# Ensure stdout uses utf-8 on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(PROJECT_DIR, "backend")
FRONTEND_DIR = os.path.join(PROJECT_DIR, "frontend")
HTML_FILE = os.path.join(PROJECT_DIR, "dev_dashboard.html")

PYTHON_EXE = os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe")
if not os.path.exists(PYTHON_EXE):
    PYTHON_EXE = sys.executable

PORT = 3000

# 全局进程状态
frontend_process = None
backend_process = None
lock = threading.Lock()

# SSE 日志订阅队列列表
log_subscribers = []
log_subscribers_lock = threading.Lock()


def broadcast_log(message: str, tag: str = "INFO"):
    """向所有在线的浏览器前端广播日志"""
    payload = json.dumps({"message": message, "tag": tag}, ensure_ascii=False)
    data = f"data: {payload}\n\n"

    with log_subscribers_lock:
        dead_queues = []
        for q in log_subscribers:
            try:
                q.put_nowait(data)
            except Exception:
                dead_queues.append(q)
        for dead in dead_queues:
            if dead in log_subscribers:
                log_subscribers.remove(dead)


def stream_reader(process, tag):
    """异步读取子进程日志并广播"""
    while process and process.poll() is None:
        try:
            line = process.stdout.readline()
            if line:
                broadcast_log(line.rstrip(), tag=tag)
            else:
                time.sleep(0.04)
        except Exception:
            break


def start_frontend():
    global frontend_process
    with lock:
        if frontend_process and frontend_process.poll() is None:
            return True
        try:
            broadcast_log("正在启动前端系统 (npm run dev)...", "FRONTEND")
            frontend_process = subprocess.Popen(
                "npm run dev",
                shell=True,
                cwd=FRONTEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            threading.Thread(
                target=stream_reader,
                args=(frontend_process, "FRONTEND"),
                daemon=True,
            ).start()
            broadcast_log("前端系统启动成功！(http://localhost:5173)", "FRONTEND")
            return True
        except Exception as e:
            broadcast_log(f"前端启动失败: {e}", "ERROR")
            return False


def stop_frontend():
    global frontend_process
    with lock:
        if frontend_process:
            broadcast_log("正在停止前端系统...", "FRONTEND")
            try:
                subprocess.run(
                    f"taskkill /F /T /PID {frontend_process.pid}",
                    shell=True,
                    capture_output=True,
                )
            except Exception:
                pass
            frontend_process = None
            broadcast_log("前端系统已停止。", "FRONTEND")
        return False


def start_backend():
    global backend_process
    with lock:
        if backend_process and backend_process.poll() is None:
            return True
        try:
            broadcast_log("正在启动后端服务器 (FastAPI / Uvicorn)...", "BACKEND")
            backend_process = subprocess.Popen(
                [PYTHON_EXE, "main.py"],
                cwd=BACKEND_DIR,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            threading.Thread(
                target=stream_reader,
                args=(backend_process, "BACKEND"),
                daemon=True,
            ).start()
            broadcast_log("后端服务器启动成功！(http://localhost:8000)", "BACKEND")
            return True
        except Exception as e:
            broadcast_log(f"后端启动失败: {e}", "ERROR")
            return False


def stop_backend():
    global backend_process
    with lock:
        if backend_process:
            broadcast_log("正在停止后端服务器...", "BACKEND")
            try:
                subprocess.run(
                    f"taskkill /F /T /PID {backend_process.pid}",
                    shell=True,
                    capture_output=True,
                )
            except Exception:
                pass
            backend_process = None
            broadcast_log("后端服务器已停止。", "BACKEND")
        return False


class DashboardHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 静默默认控制台输出，不污染终端
        pass

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # 1. 主页面
        if self.path in ("/", "/index.html"):
            if os.path.exists(HTML_FILE):
                with open(HTML_FILE, "r", encoding="utf-8") as f:
                    content = f.read().encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            else:
                self.send_error(404, "dev_dashboard.html not found")
            return

        # 2. 状态查询
        if self.path == "/api/status":
            fe_running = bool(frontend_process and frontend_process.poll() is None)
            be_running = bool(backend_process and backend_process.poll() is None)
            self.send_json({
                "frontend": {"running": fe_running},
                "backend": {"running": be_running},
            })
            return

        # 3. 实时日志流 (SSE)
        if self.path == "/api/logs":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("Connection", "keep-alive")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()

            q = queue.Queue(maxsize=100)
            with log_subscribers_lock:
                log_subscribers.append(q)

            try:
                # 初始连接握手
                init_msg = json.dumps({"message": "已连接到实时日志流", "tag": "INFO"})
                self.wfile.write(f"data: {init_msg}\n\n".encode("utf-8"))
                self.wfile.flush()

                while True:
                    try:
                        msg = q.get(timeout=20)
                        self.wfile.write(msg.encode("utf-8"))
                        self.wfile.flush()
                    except queue.Empty:
                        # 发送心跳防止连接断开
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
            except (ConnectionResetError, BrokenPipeError):
                pass
            finally:
                with log_subscribers_lock:
                    if q in log_subscribers:
                        log_subscribers.remove(q)
            return

        self.send_error(404, "Not Found")

    def do_POST(self):
        if self.path == "/api/start-frontend":
            running = start_frontend()
            self.send_json({"running": running})
            return

        if self.path == "/api/stop-frontend":
            running = stop_frontend()
            self.send_json({"running": running})
            return

        if self.path == "/api/start-backend":
            running = start_backend()
            self.send_json({"running": running})
            return

        if self.path == "/api/stop-backend":
            running = stop_backend()
            self.send_json({"running": running})
            return

        self.send_error(404, "Not Found")


def run_dashboard_server():
    server = ThreadingHTTPServer(("0.0.0.0", PORT), DashboardHandler)
    url = f"http://localhost:{PORT}"
    print(f"\n==========================================")
    print(f"Rabbit AI 网页开发控制台已就绪！")
    print(f"访问地址: {url}")
    print(f"==========================================\n")

    # 延迟 0.5 秒自动弹出系统浏览器
    threading.Timer(0.5, lambda: webbrowser.open(url)).start()

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n正在关闭开发控制台...")
    finally:
        stop_frontend()
        stop_backend()
        server.server_close()


if __name__ == "__main__":
    run_dashboard_server()
