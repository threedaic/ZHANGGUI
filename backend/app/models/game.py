"""game 模块 ORM 模型（模板/会话/参与者/奖品）

依据 SPEC 2.0 §3.4.3
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import String, Integer, Boolean, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class GameTemplate(Base):
    """游戏模板表（game_templates）"""
    __tablename__ = "game_templates"

    template_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    game_type: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    min_participants: Mapped[int] = mapped_column(Integer, default=2)
    max_participants: Mapped[int] = mapped_column(Integer, default=10)
    rules: Mapped[Optional[dict]] = mapped_column(JSONB)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GameSession(Base):
    """游戏会话表（game_sessions）"""
    __tablename__ = "game_sessions"

    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("game_templates.template_id"))
    topic: Mapped[Optional[str]] = mapped_column(String(200))
    status: Mapped[str] = mapped_column(String(20), default="waiting")
    max_participants: Mapped[Optional[int]] = mapped_column(Integer)
    current_participants: Mapped[int] = mapped_column(Integer, default=0)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    winner_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GameParticipant(Base):
    """游戏参与者表（game_participants）"""
    __tablename__ = "game_participants"

    participant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)
    table_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    member_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    device_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    choice: Mapped[Optional[str]] = mapped_column(String(50))
    result: Mapped[Optional[str]] = mapped_column(String(20))
    prize_claimed: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)


class GamePrize(Base):
    """游戏奖品表（game_prizes）"""
    __tablename__ = "game_prizes"

    prize_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("game_sessions.session_id"), nullable=False)
    product_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_products.product_id"), nullable=False)
    product_name: Mapped[Optional[str]] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    claimed_by: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True))
    claimed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
