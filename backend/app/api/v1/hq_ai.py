"""
全局 AI 配置 API（系统管理员级别）
前缀: /api/v1/hq/ai-config
"""
from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.global_settings import GlobalSettings
from app.utils.security import encrypt_aes, decrypt_aes
from app.utils.deps import make_response, require_role
from app.utils.exceptions import ForbiddenError
from loguru import logger

router = APIRouter()


def _ensure_system_admin(request: Request):
    role = getattr(request.state, "role", None)
    if role != "system_admin":
        raise ForbiddenError("仅系统管理员可配置全局 AI")


def _mask_key(key: str) -> str:
    if not key or len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


class GlobalAIConfigUpdate(BaseModel):
    # 聊天模型
    chat_api_url: str | None = None
    chat_api_key: str | None = None
    chat_model: str | None = None
    chat_temperature: float | None = None
    # 视觉模型
    vision_api_url: str | None = None
    vision_api_key: str | None = None
    vision_model: str | None = None
    vision_temperature: float | None = None


async def _get_or_create(db: AsyncSession) -> GlobalSettings:
    result = await db.execute(select(GlobalSettings).where(GlobalSettings.id == "global"))
    settings = result.scalar_one_or_none()
    if not settings:
        settings = GlobalSettings(id="global")
        db.add(settings)
        await db.flush()
    return settings


async def get_global_ai_config_decrypted(db: AsyncSession) -> dict:
    """给其他服务调用：返回解密后的全局AI配置"""
    settings = await _get_or_create(db)

    def safe_decrypt(val):
        if not val:
            return None
        try:
            return decrypt_aes(val)
        except Exception:
            return val

    return {
        "chat_api_url": settings.chat_api_url,
        "chat_api_key": safe_decrypt(settings.chat_api_key),
        "chat_model": settings.chat_model,
        "chat_temperature": settings.chat_temperature or 0.7,
        "vision_api_url": settings.vision_api_url,
        "vision_api_key": safe_decrypt(settings.vision_api_key),
        "vision_model": settings.vision_model,
        "vision_temperature": settings.vision_temperature or 0.2,
    }


@router.get("/ai-config")
async def get_ai_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """获取全局 AI 配置（Key 脱敏）"""
    _ensure_system_admin(request)
    settings = await _get_or_create(db)
    return make_response(request=request, data={
        "chat_api_url": settings.chat_api_url,
        "chat_api_key_masked": _mask_key(settings.chat_api_key) if settings.chat_api_key else None,
        "chat_model": settings.chat_model,
        "chat_temperature": settings.chat_temperature or 0.7,
        "vision_api_url": settings.vision_api_url,
        "vision_api_key_masked": _mask_key(settings.vision_api_key) if settings.vision_api_key else None,
        "vision_model": settings.vision_model,
        "vision_temperature": settings.vision_temperature or 0.2,
    })


@router.put("/ai-config")
async def update_ai_config(
    body: GlobalAIConfigUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """更新全局 AI 配置。Key 明文传入，后端 AES 加密存储。"""
    _ensure_system_admin(request)
    settings = await _get_or_create(db)

    if body.chat_api_url is not None:
        settings.chat_api_url = body.chat_api_url
    if body.chat_api_key is not None:
        settings.chat_api_key = encrypt_aes(body.chat_api_key)
    if body.chat_model is not None:
        settings.chat_model = body.chat_model
    if body.chat_temperature is not None:
        settings.chat_temperature = body.chat_temperature

    if body.vision_api_url is not None:
        settings.vision_api_url = body.vision_api_url
    if body.vision_api_key is not None:
        settings.vision_api_key = encrypt_aes(body.vision_api_key)
    if body.vision_model is not None:
        settings.vision_model = body.vision_model
    if body.vision_temperature is not None:
        settings.vision_temperature = body.vision_temperature

    await db.commit()
    logger.info("[全局AI配置] 已更新")
    return make_response(request=request, message="全局 AI 配置已更新", data={
        "chat_api_url": settings.chat_api_url,
        "chat_model": settings.chat_model,
        "vision_api_url": settings.vision_api_url,
        "vision_model": settings.vision_model,
    })
