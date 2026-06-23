"""
小C AI 助手 Pydantic Schemas
"""
from pydantic import BaseModel


# ==================== 聊天 ====================

class ChatRequest(BaseModel):
    """用户发送的消息"""
    message: str
    conversation_id: str | None = None  # 用于多轮对话上下文


class ChatResponse(BaseModel):
    """AI 回复"""
    reply: str
    conversation_id: str
    sql: str | None = None           # 后端生成的 SQL（调试用，前端不展示）


# ==================== AI 配置 ====================

class AIConfigUpdate(BaseModel):
    """管理端更新 AI 配置"""
    ai_api_url: str | None = None
    ai_api_key: str | None = None     # 明文传入，后端 AES 加密存储
    ai_model: str | None = None
    ai_temperature: float | None = None


class AIConfigResponse(BaseModel):
    """返回 AI 配置（key 脱敏）"""
    ai_api_url: str | None = None
    ai_api_key_masked: str | None = None   # "sk-****1234"
    ai_model: str | None = None
    ai_temperature: float = 0.7

    model_config = {"from_attributes": True}


# ==================== 通用分析 / 检测 ====================

class AIAnalyzeRequest(BaseModel):
    """通用 AI 分析请求（m-004 fix: Pydantic schema replaces manual JSON parse）"""
    prompt: str = ""
    context: str = ""


class AIDetectRequest(BaseModel):
    """防飞单 AI 检测请求"""
    prompt: str = "分析以下开台数据是否存在飞单风险"
    context: dict | None = None
