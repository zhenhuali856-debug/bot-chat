import os
from typing import Dict, List, Any
from dotenv import load_dotenv

# 加载 backend 目录下的 .env 环境变量
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
load_dotenv(dotenv_path=dotenv_path)

# API 密钥与配置
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com").strip()
DEEPSEEK_DEFAULT_MODEL = os.environ.get("DEEPSEEK_DEFAULT_MODEL", "deepseek-chat").strip()

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "0f6f01354df2471f85f72fb5e09a1fd4.xzLpaJkW2VvG7bQe").strip()
ZHIPU_BASE_URL = os.environ.get("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4/").strip()
ZHIPU_DEFAULT_MODEL = os.environ.get("ZHIPU_DEFAULT_MODEL", "glm-4-flash").strip()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_BASE_URL = os.environ.get(
    "GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/"
).strip()
GEMINI_DEFAULT_MODEL = os.environ.get("GEMINI_DEFAULT_MODEL", "gemini-3.8-flash").strip()

PORT = int(os.environ.get("PORT", 8000))

# 数据库存储路径
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "chat_memory.db")

AVAILABLE_MODELS: List[Dict[str, Any]] = [
    {
        "id": "deepseek-chat",
        "name": "DeepSeek V3 (通用对话)",
        "description": "适合多轮日常对话、编码与通用文本创作，响应敏捷",
    },
    {
        "id": "deepseek-reasoner",
        "name": "DeepSeek R1 (深度思考 / 推理)",
        "description": "具备慢思考能力，展示完整思维链推理过程，擅长数学与复杂逻辑",
    },
    {
        "id": "glm-4-flash",
        "name": "智谱 GLM-4-Flash (免费开源/极速)",
        "description": "智谱官方永久免费大模型，毫秒级响应，适合日常聊天、快速问答与代码辅助",
    },
    {
        "id": "glm-4-plus",
        "name": "智谱 GLM-4-Plus (旗舰模型)",
        "description": "智谱新一代高智能旗舰模型，擅长复杂推理、长文本理解与高阶任务",
    },
    {
        "id": "gemini-3.8-flash",
        "name": "Gemini 3.8 Flash (均衡旗舰 / 1M上下文)",
        "description": "Google 最新均衡性能模型，支持 1M 超长上下文，适合长篇创作、设定梳理与多轮构思",
    },
    {
        "id": "gemini-3.1-pro-preview",
        "name": "Gemini 3.1 Pro (深度推理 / 旗舰)",
        "description": "Google 高阶推理模型，擅长复杂剧情推演、逻辑设计及长篇结构打磨",
    },
    {
        "id": "gemini-3.5-flash-lite",
        "name": "Gemini 3.5 Flash-Lite (极速轻量)",
        "description": "响应极快、性价比高，适合日常灵感发散与快速润色",
    },
]

