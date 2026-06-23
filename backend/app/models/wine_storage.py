import uuid
from datetime import date, datetime
from sqlalchemy import String, Integer, Text, Date, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class WineStorage(TimestampMixin, Base):
    __tablename__ = "wine_stored_bottles"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(
        "wine_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_stores.store_id")
    )
    customer_name: Mapped[str] = mapped_column(String(50))
    phone: Mapped[str] = mapped_column(String(20))
    wine_name: Mapped[str] = mapped_column(String(100))
    bottle_label: Mapped[str | None] = mapped_column(String(50))
    date_stored: Mapped[date] = mapped_column(Date)
    initial_ml: Mapped[int | None] = mapped_column(Integer, default=0)
    remaining_ml: Mapped[int | None] = mapped_column(Integer)
    cabinet_no: Mapped[str | None] = mapped_column(String(20))
    table_no: Mapped[str | None] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(20), default="stored")
    expiry_date: Mapped[date | None] = mapped_column(Date)
    retrieved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    retrieved_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("shared_employees.employee_id")
    )
    notes: Mapped[str | None] = mapped_column(Text)
