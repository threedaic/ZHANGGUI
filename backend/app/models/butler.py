"""
智能管家模块 — 开闭店检查数据模型

四张表：
  butler_checklist_templates    — 清单模板（店长闭店检查单 / 吧台开店检查单 等）
  butler_checklist_items        — 模板明细项
  butler_sessions               — 开店/闭店会话
  butler_item_results           — 每项检查的执行结果
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Text, Boolean, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class ClosingChecklistTemplate(TimestampMixin, Base):
    """开闭店清单模板。每家店可有多套模板（开店/闭店，按角色分组）"""

    __tablename__ = "butler_checklist_templates"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("template_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(50))             # "店长闭店检查单"
    session_type: Mapped[str] = mapped_column(String(10))     # opening / closing
    role_tag: Mapped[str] = mapped_column(String(30), default="all")  # store_manager / bartender / server
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True)


class ClosingChecklistItem(TimestampMixin, Base):
    """模板中的每条检查项"""

    __tablename__ = "butler_checklist_items"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("item_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("butler_checklist_templates.template_id", ondelete="CASCADE"))
    item_name: Mapped[str] = mapped_column(String(100))
    item_type: Mapped[str] = mapped_column(String(20), default="checkbox")  # checkbox / photo
    device_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)   # 预留 IoT
    required_photo: Mapped[bool] = mapped_column(Boolean, default=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    # AI 判定提示词：老板可自定义（如"检查酒水摆放是否整齐，标签朝外"），为空时使用默认提示
    ai_prompt: Mapped[str | None] = mapped_column(String(500), nullable=True)


class ClosingSession(TimestampMixin, Base):
    """每次开店或闭店的执行会话"""

    __tablename__ = "butler_sessions"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("session_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"))
    session_type: Mapped[str] = mapped_column(String(10))           # opening / closing
    operator_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress / completed / abnormal
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_items: Mapped[int] = mapped_column(Integer, default=0)
    completed_items: Mapped[int] = mapped_column(Integer, default=0)


class ClosingItemResult(TimestampMixin, Base):
    """每个检查项的执行结果"""

    __tablename__ = "butler_item_results"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("result_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("butler_sessions.session_id", ondelete="CASCADE"))
    template_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("butler_checklist_templates.template_id", ondelete="SET NULL"), nullable=True)
    item_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("butler_checklist_items.item_id", ondelete="SET NULL"), nullable=True)
    # 临时加项字段（item_id = NULL 时使用）
    item_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    item_type: Mapped[str | None] = mapped_column(String(20), nullable=True)  # checkbox / photo

    completed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_result: Mapped[dict | None] = mapped_column(JSONB, nullable=True)       # {"pass": true, "confidence": 0.92, "reason": "..."}
    review_status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / passed / manual_reviewing / manual_passed / manual_rejected
    review_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("sys_users.user_id"), nullable=True)
    review_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
