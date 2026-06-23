"""用户模型（已迁移到 SPEC 2.0 新表）

User → sys_users（UUID主键）

技巧：保持 Python 类名和属性名不变，只改 __tablename__ 和主键类型。
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    """用户表（sys_users）"""
    __tablename__ = "sys_users"

    # 主键：Python 用 User.id，DB 列是 user_id
    id: Mapped[uuid.UUID] = mapped_column("user_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id", ondelete="SET NULL")
    )
    username: Mapped[str] = mapped_column(String(50), unique=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30))
    region: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    must_change_password: Mapped[bool] = mapped_column(Boolean, default=False)
    last_login: Mapped[datetime | None] = mapped_column("last_login_at", DateTime(timezone=True))
