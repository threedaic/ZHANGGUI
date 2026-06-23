import uuid
from sqlalchemy import String, Integer, Numeric, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class LeaveBalance(TimestampMixin, Base):
    __tablename__ = "att_leave_balances"
    __table_args__ = (
        UniqueConstraint("employee_id", "year", "leave_type"),
        {'extend_existing': True},
    )

    id: Mapped[uuid.UUID] = mapped_column("balance_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id"))
    employee_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_employees.employee_id"))
    year: Mapped[int] = mapped_column(Integer)
    leave_type: Mapped[str] = mapped_column(String(20))
    total_days: Mapped[float] = mapped_column(Numeric(5, 1), default=0)
    used_days: Mapped[float] = mapped_column(Numeric(5, 1), default=0)
