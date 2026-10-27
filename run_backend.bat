@echo off
chcp 65001 >nul
echo 正在启动 Python 后端服务 (FastAPI)...
cd /d "%~dp0backend"
if not exist ".venv\Scripts\python.exe" (
    echo [错误] 未找到虚拟环境，请先检查 backend/.venv
    pause
    exit /b 1
)
.venv\Scripts\python.exe main.py
pause
