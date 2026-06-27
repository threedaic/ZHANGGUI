from pydantic_settings import BaseSettings
from pydantic import field_validator, model_validator
from functools import lru_cache
import os
import sys
from typing import Any


class Settings(BaseSettings):
    # Environment
    APP_ENV: str = "development"  # development / staging / production

    # Application
    APP_NAME: str = "Crush掌柜"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = False

    # Database
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_USER: str = "crush"
    POSTGRES_PASSWORD: str = "crush"
    POSTGRES_DB: str = "crush_zhanggui"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
            f"?ssl=disable"
        )

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @property
    def REDIS_URL(self) -> str:
        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    # JWT
    JWT_SECRET: str = "change-me-to-a-random-secret-key"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8小时，覆盖整个班次
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # 数据加密密钥（用于加密存储 API Key 等敏感字段，与 JWT 密钥分离）
    # 留空时回退到 JWT_SECRET 派生（向后兼容），生产环境强烈建议设置独立值。
    # 生成方法: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    ENCRYPT_KEY: str = ""

    # Security (I-001)
    MAX_LOGIN_ATTEMPTS: int = 5  # Max failed attempts before account lockout
    LOGIN_LOCKOUT_MINUTES: int = 30  # Lockout duration after max attempts
    MIN_PASSWORD_LENGTH: int = 8  # Minimum password length

    # CORS (supports comma-separated env var)
    CORS_ORIGINS: list[str] = [
        "https://crushserver.cloud",
        "http://localhost:5173",
        "http://localhost:3000",
    ]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            return [o.strip() for o in v.split(",") if o.strip()]
        return v

    # First boss account seed
    SEED_BOSS_USERNAME: str = "admin"
    SEED_BOSS_PASSWORD: str = "admin123"

    # ============================================================
    # 角色白名单配置 (连锁品牌四级权限体系, 参见 SPEC §0)
    # ============================================================
    # 系统管理员: 全品牌管理员, 不绑定门店, 能管全部门店
    # 规则: 企微「Crush 管理」部门成员 = system_admin (不可遗忘!)
    # 典型: 周鹏飞/卡西/王柏霄 (管理群成员)
    # 能力: 进总店网页/建新门店/全局看板/切换任意门店
    SYSTEM_ADMIN_USERIDS: str = ""

    # 单店老板: 管一家店, 绑定到具体 store_id
    # 通常由门店部门负责人自动识别, 或手动指定
    BOSS_WEWORK_USERIDS: str = ""

    # WeCom global config (all stores share the same corp account)
    WECOM_CORP_ID: str = ""
    WECOM_AGENT_ID: str = ""
    WECOM_SECRET: str = ""

    # WeCom contact change callback (通讯录变更回调)
    # 企微后台"接收事件"配置的 Token 和 EncodingAESKey
    WECOM_CALLBACK_TOKEN: str = ""
    WECOM_CALLBACK_AES_KEY: str = ""

    # External service base URLs (configurable for env switching / proxies)
    WECOM_API_BASE: str = "https://qyapi.weixin.qq.com/cgi-bin"
    FRONTEND_BASE_URL: str = "https://zhanggui.crushserver.cloud"
    UPLOAD_DIR: str = "./uploads"

    # Tencent Cloud SMS
    SMS_SECRET_ID: str = ""
    SMS_SECRET_KEY: str = ""
    SMS_SDK_APP_ID: str = ""
    SMS_SIGN_NAME: str = "Crush酒吧"
    SMS_TEMPLATE_ID_STORED: str = ""   # 存酒通知模板 ID
    SMS_TEMPLATE_ID_RETRIEVED: str = ""  # 取酒通知模板 ID

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        """Refuse to start in production with default JWT_SECRET."""
        if self.APP_ENV in ("production", "staging"):
            if self.JWT_SECRET == "change-me-to-a-random-secret-key":
                print(
                    "FATAL: JWT_SECRET is still the default value. "
                    "Set JWT_SECRET in .env or environment before starting in production/staging.",
                    file=sys.stderr,
                )
                sys.exit(1)
            if self.SEED_BOSS_PASSWORD == "admin123" and self.SEED_BOSS_USERNAME == "admin":
                print(
                    "WARNING: SEED_BOSS_PASSWORD is still the default value 'admin123'. "
                    "This is insecure for production. Set SEED_BOSS_PASSWORD in .env.",
                    file=sys.stderr,
                )
        return self

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache()
def get_settings() -> Settings:
    env = os.getenv("APP_ENV", "development")
    env_file = f".env.{env}" if env != "development" else ".env"
    return Settings(_env_file=env_file if os.path.exists(env_file) else ".env")
