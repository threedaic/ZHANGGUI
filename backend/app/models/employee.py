"""员工模型（已迁移到 SPEC 2.0 新表）

Employee → shared_employees（UUID主键）

技巧：保持 Python 类名和属性名不变，只改 __tablename__ 和主键类型。
wework_userid 属性映射到 wecom_user_id 列（DB列名变更，Python属性名保持兼容）。
"""
import uuid
from datetime import date
from sqlalchemy import String, Integer, Date, Text, ForeignKey, Boolean, Numeric, ARRAY
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Employee(TimestampMixin, Base):
    """员工表（shared_employees）"""
    __tablename__ = "shared_employees"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 Employee.id，DB 列是 employee_id
    id: Mapped[uuid.UUID] = mapped_column("employee_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shared_stores.store_id", ondelete="CASCADE"))
    employee_code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(64))
    phone: Mapped[str | None] = mapped_column(String(32))
    role: Mapped[str] = mapped_column(String(32))
    base_salary: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)  # SPEC: NUMERIC(12,2)
    hire_date: Mapped[date] = mapped_column(Date)  # 类型注解改为 date
    status: Mapped[str] = mapped_column(String(16), default="active")
    # wework_userid 属性映射到 wecom_user_id 列（DB列名变更）
    wework_userid: Mapped[str | None] = mapped_column("wecom_user_id", String(100))
    department: Mapped[str | None] = mapped_column(String(32))
    skill_tags: Mapped[str | None] = mapped_column(ARRAY(Text))
    is_first_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    is_second_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    is_third_manager: Mapped[bool] = mapped_column(Boolean, default=False)
    shift_group: Mapped[str | None] = mapped_column(String(10), nullable=True, comment="排班组: day=白班组, night=夜班组")
    notes: Mapped[str | None] = mapped_column(Text)
