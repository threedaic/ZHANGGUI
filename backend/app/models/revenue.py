"""
门店日营收数据模型

fin_daily_revenue: 门店日营收汇总表（从 crmeb/POS 系统同步）

字段说明:
  - date: 营收日期（Date类型）
  - 金额字段统一使用 Numeric(12,2)
  - details: 原始数据（JSONB类型）
"""
import uuid
from datetime import date, datetime
from sqlalchemy import String, Numeric, Date, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base


class DailyRevenue(Base):
    __tablename__ = "fin_daily_revenue"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column("revenue_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    date: Mapped[date] = mapped_column(Date)
    pos_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    wecom_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    cash_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    member_revenue: Mapped[float] = mapped_column(Numeric(12, 2), default=0)
    avg_spend: Mapped[float | None] = mapped_column(Numeric(12, 2), default=0)
    details: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    @property
    def total_revenue(self) -> float:
        """总营收 = POS + 企微 + 现金 + 会员"""
        return float(self.pos_revenue or 0) + float(self.wecom_revenue or 0) + \
               float(self.cash_revenue or 0) + float(self.member_revenue or 0)
