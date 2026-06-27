"""
小C AI 助手 API 路由
前缀: /api/v1/ai

端点:
- POST /chat     → 对话（自然语言查数据）
- GET  /config   → 获取 AI 配置（key 脱敏）
- PUT  /config   → 更新 AI 配置
- POST /detect   → 防飞单检测（由 antifraud 模块调用）
- POST /analyze  → 通用分析（排班建议等）
"""
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.ai import ChatRequest, ChatResponse, AIConfigUpdate, AIConfigResponse, AIAnalyzeRequest, AIDetectRequest
from app.services.ai_engine import (
    process_chat,
    get_ai_config_masked,
    update_ai_config,
    ai_analyze,
)
from app.utils.exceptions import ForbiddenError
from app.utils.deps import get_store_id, make_response

router = APIRouter()


def _ensure_admin(request: Request) -> None:
    """仅管理员角色可修改 AI 配置。"""
    role = getattr(request.state, "role", None)
    if role not in ("boss", "system_admin", "admin"):
        raise ForbiddenError("仅管理员可操作 AI 配置")


# ==================== 对话 ====================

@router.post("/chat")
async def chat(
    body: ChatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    小C AI 助手对话入口。

    用户输入自然语言问题，系统自动:
    1. 判断是否为知识库问题（操作指引/规则说明）→ 直接回复
    2. 否则 → LLM 生成 SQL → 安全执行 → LLM 格式化为自然语言回复

    示例:
    - "赵先生的存酒还在吗"
    - "今天谁晚班"
    - "A1桌有人吗"
    - "今天营业额多少"
    - "存酒怎么操作"
    """
    store_id = get_store_id(request)
    result = await process_chat(
        db=db,
        store_id=store_id,
        user_message=body.message,
        conversation_id=body.conversation_id,
    )
    return make_response(data=ChatResponse(
        reply=result["reply"],
        conversation_id=result["conversation_id"],
        sql=result.get("sql"),
    ).model_dump(), request=request)


# ==================== AI 配置 ====================

@router.get("/config")
async def get_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    获取当前门店的 AI 配置（API Key 脱敏展示）。
    仅 boss 角色可访问。
    """
    _ensure_admin(request)
    store_id = get_store_id(request)
    config = await get_ai_config_masked(db, store_id)
    return make_response(data=AIConfigResponse(**config).model_dump(), request=request)


@router.put("/config")
async def update_config(
    body: AIConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    更新 AI 配置。API Key 明文传入，后端 AES 加密存储。
    仅 boss 角色可操作。
    修改后实时生效，无需重启。
    """
    _ensure_admin(request)
    store_id = get_store_id(request)
    settings = await update_ai_config(
        db=db,
        store_id=store_id,
        ai_api_url=body.ai_api_url,
        ai_api_key=body.ai_api_key,
        ai_model=body.ai_model,
        ai_temperature=body.ai_temperature,
    )
    return make_response(message="AI 配置已更新", data={
        "ai_api_url": settings.ai_api_url,
        "ai_api_key_masked": "已保存" if settings.ai_api_key else None,
        "ai_model": settings.ai_model,
        "ai_temperature": settings.ai_temperature,
    }, request=request)


# ==================== 通用 AI 调用（供其他模块使用） ====================

@router.post("/analyze")
async def analyze(
    body: AIAnalyzeRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    通用 AI 分析入口。供排班建议等模块调用。
    """
    store_id = get_store_id(request)
    result = await ai_analyze(db, store_id, body.prompt, body.context)
    return make_response(data={"result": result}, request=request)


@router.post("/detect")
async def detect(
    body: AIDetectRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    防飞单 AI 检测入口。供 antifraud 模块调用。
    """
    import json as _json

    store_id = get_store_id(request)
    context_str = _json.dumps(body.context, ensure_ascii=False) if body.context else ""
    result = await ai_analyze(db, store_id, body.prompt, context_str)
    return make_response(data={"result": result}, request=request)
