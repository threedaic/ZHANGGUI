import uuid
from datetime import datetime
from sqlalchemy import String, BigInteger, Text, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class AuditLog(Base):
    __tablename__ = "sys_audit_logs"
    __table_args__ = {'extend_existing': True}

    id: Mapped[int] = mapped_column("log_id", BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    store_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    action: Mapped[str] = mapped_column(String(50))
    entity_type: Mapped[str | None] = mapped_column("resource_type", String(50))
    entity_id: Mapped[uuid.UUID | None] = mapped_column("resource_id", UUID(as_uuid=True), nullable=True)
    old_value: Mapped[str | None] = mapped_column(Text)  # JSONB
    new_value: Mapped[str | None] = mapped_column(Text)  # JSONB
    request_id: Mapped[str | None] = mapped_column(Text)  # UUID
    ip_address: Mapped[str | None] = mapped_column(Text)  # INET
    user_agent: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
