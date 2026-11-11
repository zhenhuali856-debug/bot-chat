import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MessageItem(BaseModel):
    id: Optional[int] = None
    session_id: str
    role: str  # system, user, assistant
    content: str
    reasoning_content: Optional[str] = ""
    created_at: float = Field(default_factory=time.time)


class WorkItem(BaseModel):
    id: str
    title: str
    genre: Optional[str] = None
    summary: Optional[str] = None
    outline: Optional[str] = None
    target_words: int = 0
    status: str = "draft"  # draft / writing / done
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class CreateWorkRequest(BaseModel):
    title: str
    genre: Optional[str] = None
    summary: Optional[str] = None
    outline: Optional[str] = None
    target_words: int = 0


class UpdateWorkRequest(BaseModel):
    title: Optional[str] = None
    genre: Optional[str] = None
    summary: Optional[str] = None
    outline: Optional[str] = None
    target_words: Optional[int] = None
    status: Optional[str] = None


class ChapterItem(BaseModel):
    id: str
    work_id: str
    title: str
    content: str = ""
    word_count: int = 0
    sort_order: int = 0
    source_session_id: Optional[str] = None
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class CreateChapterRequest(BaseModel):
    title: str
    content: str = ""
    source_session_id: Optional[str] = None


class UpdateChapterRequest(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    append_content: Optional[str] = None
    sort_order: Optional[int] = None


class SessionItem(BaseModel):
    id: str
    title: str
    system_prompt: Optional[str] = "你是由 DeepSeek 驱动的高级 AI 助手，回答准确、友好、富有逻辑。"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)
    message_count: int = 0
    work_id: Optional[str] = None


class ChatMessage(BaseModel):
    role: str = Field(..., description="消息角色: system, user, assistant")
    content: str = Field(..., description="消息文本内容")


class CreateSessionRequest(BaseModel):
    title: Optional[str] = "新建对话"
    system_prompt: Optional[str] = None
    work_id: Optional[str] = None


class UpdateSessionRequest(BaseModel):
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    work_id: Optional[str] = None


class BotSettingsRequest(BaseModel):
    bot_nickname: Optional[str] = None
    bot_persona: Optional[str] = None


class ImportSessionRequest(BaseModel):
    format: Optional[str] = "json"  # "json" 或 "markdown"
    title: Optional[str] = None
    system_prompt: Optional[str] = None
    session: Optional[Dict[str, Any]] = None
    messages: Optional[List[Dict[str, Any]]] = None
    markdown_content: Optional[str] = None


class PromptFileItem(BaseModel):
    id: str
    filename: str
    content: str
    scope: str = "session"  # session / work / global
    session_id: Optional[str] = None
    work_id: Optional[str] = None
    enabled: bool = True
    char_count: int = 0
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class CreatePromptFileRequest(BaseModel):
    filename: str
    content: str
    scope: str = "session"  # session / work / global
    session_id: Optional[str] = None
    work_id: Optional[str] = None
    enabled: bool = True


class UpdatePromptFileRequest(BaseModel):
    filename: Optional[str] = None
    content: Optional[str] = None
    scope: Optional[str] = None
    session_id: Optional[str] = None
    work_id: Optional[str] = None
    enabled: Optional[bool] = None


class ChatRequest(BaseModel):
    session_id: Optional[str] = Field(
        None, description="后端会话ID，如果不传将自动创建新会话"
    )
    message: Optional[str] = Field(None, description="用户本次发送的提问内容")
    messages: Optional[List[ChatMessage]] = Field(
        None, description="兼容旧版：直接传递全量消息列表"
    )
    model: Optional[str] = "deepseek-chat"
    temperature: Optional[float] = 0.7
    max_history_rounds: Optional[int] = Field(
        10, description="滑动窗口：传递给大模型的最大历史轮次"
    )
    stream: Optional[bool] = True
    regenerate: Optional[bool] = Field(
        False, description="是否重新生成当前回答 (若为True则不将message再次存入数据库)"
    )

