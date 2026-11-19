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

ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "").strip()
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

# M3a-2 内置体裁模板字典（大纲骨架 + 创作提示词补充）
GENRE_TEMPLATES: Dict[str, Dict[str, str]] = {
    "三幕式小说": {
        "label": "三幕式小说",
        "outline_template": (
            "第一幕 · 铺垫\n"
            "· 激励事件：主角被卷入核心冲突\n"
            "· 第一转折点：目标被迫改变\n\n"
            "第二幕 · 对抗\n"
            "· 中段尝试与阻碍\n"
            "· 中点反转：真相浮出水面\n"
            "· 最低谷：看似失败\n\n"
            "第三幕 · 结局\n"
            "· 高潮对决\n"
            "· 收束与余韵"
        ),
        "prompt_hint": "遵循三幕结构，注意情节点节奏：铺垫 / 对抗 / 结局各幕转折要清晰。",
    },
    "章节剧（剧本）": {
        "label": "章节剧（剧本）",
        "outline_template": (
            "第一场 · 场景名\n"
            "地点：／时间：／人物：\n"
            "【动作描写】\n"
            "角色A：对白\n"
            "角色B：对白\n\n"
            "第二场 · 场景名\n"
            "地点：／时间：／人物：\n"
            "【动作描写】\n"
            "角色A：对白"
        ),
        "prompt_hint": "按场次结构组织；对话前标注人物名，动作用【】标注，避免大段叙述。",
    },
    "悬疑推理": {
        "label": "悬疑推理",
        "outline_template": (
            "一、谜面：案件与初始表象\n"
            "二、线索：三条以上可验证线索\n"
            "三、反转：推翻读者固有认知\n"
            "四、揭晓：真凶与作案逻辑"
        ),
        "prompt_hint": "设谜面 / 铺线索 / 造反转 / 揭晓四段式，线索必须公平可回溯。",
    },
    "散文随笔": {
        "label": "散文随笔",
        "outline_template": (
            "一、起：意象引入\n"
            "二、承：细节铺陈\n"
            "三、转：情绪或视角转折\n"
            "四、合：回收意象并升华"
        ),
        "prompt_hint": "形散神聚，用一条意象线索贯穿全文，语言克制留白。",
    },
    "营销文案": {
        "label": "营销文案",
        "outline_template": (
            "一、目标人群：是谁\n"
            "二、痛点：他们最在意什么\n"
            "三、卖点：差异化价值\n"
            "四、CTA：希望读者做什么"
        ),
        "prompt_hint": "按目标人群 / 痛点 / 卖点 / CTA 结构组织，标题前置利益点。",
    },
}

