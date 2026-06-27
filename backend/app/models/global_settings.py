"""全局配置模型（系统管理员级别，跨门店共享）"""
import uuid
from sqlalchemy import String, Text, Float, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class GlobalSettings(TimestampMixin, Base):
    """全局配置表（单行表，id 固定为 'global'）

    系统管理员在总店设置，全品牌所有门店默认继承。
    """
    __tablename__ = "sys_global_settings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[str] = mapped_column(String(16), primary_key=True, default="global")

    # 聊天模型（老C问答）
    chat_api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # AES 加密
    chat_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    chat_temperature: Mapped[float] = mapped_column(Float, default=0.7)

    # 视觉模型（开闭店照片识别）
    vision_api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    vision_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)  # AES 加密
    vision_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    vision_temperature: Mapped[float] = mapped_column(Float, default=0.2)
