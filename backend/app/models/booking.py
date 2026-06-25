import uuid
from datetime import date

from sqlalchemy import String, Integer, Numeric, Text, Date, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Booking(TimestampMixin, Base):
    __tablename__ = "pos_bookings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "booking_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_tables.table_id")
    )
    customer_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    date: Mapped[date | None] = mapped_column("booking_date", Date)
    start_time: Mapped[str | None] = mapped_column(String(8))
    end_time: Mapped[str | None] = mapped_column(String(8))
    guests_count: Mapped[int] = mapped_column("party_size", Integer, default=1)
    status: Mapped[str] = mapped_column(String(20), default="confirmed")
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    notes: Mapped[str | None] = mapped_column("note", Text)


class Table(TimestampMixin, Base):
    __tablename__ = "shared_tables"
    __table_args__ = (
        UniqueConstraint("store_id", "table_no", name="uq_shared_tables_store_no"),
        {'extend_existing': True},
    )

    id: Mapped[uuid.UUID] = mapped_column(
        "table_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    area: Mapped[str] = mapped_column(String(50), default="大厅")
    table_no: Mapped[str] = mapped_column(String(16))
    capacity: Mapped[int] = mapped_column(Integer, default=4)
    min_spend: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    status: Mapped[str] = mapped_column(String(20), default="active")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
