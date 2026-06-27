import base64
import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
from cryptography.fernet import Fernet
from jose import JWTError, jwt

from app.config import get_settings

settings = get_settings()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def _get_fernet() -> Fernet:
    """获取 Fernet 加密器。

    优先使用独立的 ENCRYPT_KEY（推荐），未配置时回退到 JWT_SECRET 派生（向后兼容）。
    分离密钥的目的：JWT 密钥泄露不能直接解密数据库中的加密字段。
    """
    if settings.ENCRYPT_KEY:
        # 直接使用配置的 Fernet key
        return Fernet(settings.ENCRYPT_KEY.encode("utf-8"))
    # 回退方案：从 JWT_SECRET 派生（向后兼容，已有数据不会失效）
    key_material = settings.JWT_SECRET.encode("utf-8")
    fernet_key = base64.urlsafe_b64encode(key_material.ljust(32, b"\0")[:32])
    return Fernet(fernet_key)


def encrypt_aes(plaintext: str) -> str:
    """AES encrypt a string (used for storing API keys in DB)."""
    return _get_fernet().encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_aes(ciphertext: str) -> str:
    """AES decrypt a string."""
    return _get_fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")


def create_access_token(data: dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_refresh_token(data: dict[str, Any]) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "type": "refresh"})
    return jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError:
        return {}

# ---- Token 黑名单 ----

async def blacklist_token(token: str, ttl: int | None = None):
    """登出时将 token 加入 Redis 黑名单。"""
    from app.utils.redis_client import get_redis
    redis = await get_redis()
    ttl = ttl or settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    await redis.setex(f"blacklist:{token}", ttl, "1")

async def is_token_blacklisted(token: str) -> bool:
    """检查 token 是否已被拉黑。"""
    from app.utils.redis_client import get_redis
    redis = await get_redis()
    return await redis.exists(f"blacklist:{token}") > 0
