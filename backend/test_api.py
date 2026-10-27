import os
import sys
from dotenv import load_dotenv
from openai import OpenAI

# Ensure UTF-8 console output on Windows
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# 加载 .env 环境变量
load_dotenv()

api_key = os.environ.get("DEEPSEEK_API_KEY")
base_url = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
model = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat")

print(f"=== DeepSeek API 环境测试 ===")
print(f"Base URL: {base_url}")
print(f"Model: {model}")

if not api_key:
    print("\n[提示] 未检测到 DEEPSEEK_API_KEY！")
    print("请在 backend/.env 文件中填入您的 API Key：")
    print("DEEPSEEK_API_KEY=sk-xxxxxxxx\n")
    sys.exit(1)

masked_key = api_key[:4] + "..." + api_key[-4:] if len(api_key) > 8 else "***"
print(f"API Key: {masked_key} (已配置)")
print("\n正在向 DeepSeek 发送测试流式请求...")

try:
    client = OpenAI(
        api_key=api_key,
        base_url=base_url,
    )

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是一名精通 Vue 3 和 Python 的全栈开发助手。"},
            {"role": "user", "content": "你好，请用一句话打个招呼并确认环境已就绪。"},
        ],
        stream=True
    )

    print("\n[AI 回复]: ", end="", flush=True)
    for chunk in response:
        if chunk.choices and chunk.choices[0].delta.content:
            print(chunk.choices[0].delta.content, end="", flush=True)
    print("\n\n测试成功！环境与 API 接口均正常工作。")

except Exception as e:
    print(f"\n[错误] 调用 API 发生异常: {e}")
    sys.exit(1)
