"""门店模型（已迁移到 SPEC 2.0 新表）

Store → shared_stores（UUID主键，Python属性 id 映射到 store_id 列）
StoreSettings → shared_store_settings（平铺结构，UUID主键）

技巧：保持 Python 类名和属性名不变，只改 __tablename__ 和主键类型，
这样 API/Service/Repository 层代码大部分不需要改。
"""
import uuid
from datetime import date
from sqlalchemy import String, Integer, Text, Boolean, Date, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.models.base import Base, TimestampMixin


class Store(TimestampMixin, Base):
    """门店表（shared_stores）

    旧字段映射：
    - id → store_id (UUID)
    - name → store_name
    - wework_* → wecom_*（DB列名，Python属性名保持 wework_* 兼容旧代码）
    """
    __tablename__ = "shared_stores"
    __table_args__ = {'extend_existing': True}

    # 主键：Python 用 Store.id，DB 列是 store_id
    id: Mapped[uuid.UUID] = mapped_column("store_id", UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # company_id 旧表有，新表用 franchisee_id。保留 company_id 属性指向 franchisee_id 列
    company_id: Mapped[uuid.UUID | None] = mapped_column("franchisee_id", UUID(as_uuid=True), nullable=True)
    # name → store_name
    name: Mapped[str] = mapped_column("store_name", String(64))
    store_code: Mapped[str] = mapped_column(String(32), unique=True)
    address: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column("region", String(32))
    status: Mapped[str] = mapped_column(String(20), default="active")
    daily_booking_limit: Mapped[int | None] = mapped_column(Integer, default=30, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(32))
    opened_at: Mapped[date | None] = mapped_column("opened_at", Date, nullable=True)  # 开业日期
    brand_fee_rate: Mapped[float] = mapped_column(Numeric(5, 4), default=0.05)  # 品牌费率 SPEC §3.4.1
    # 企微配置：Python 属性保持 wework_*，DB 列是 wecom_*
    wework_corp_id: Mapped[str | None] = mapped_column("wecom_corp_id", String(100))
    wework_agent_id: Mapped[str | None] = mapped_column("wecom_agent_id", String(20))
    wework_secret: Mapped[str | None] = mapped_column("wecom_secret", Text)
    wework_department_id: Mapped[int | None] = mapped_column("wecom_department_id", Integer, nullable=True)
    wework_token: Mapped[str | None] = mapped_column(String(100))
    wework_aes_key: Mapped[str | None] = mapped_column(String(100))
    wework_status: Mapped[str | None] = mapped_column(String(20), default="pending", nullable=True)
    # 企微对外收款 Secret（独立于应用 Secret）
    wework_externalpay_secret: Mapped[str | None] = mapped_column("wecom_externalpay_secret", Text)


class StoreSettings(TimestampMixin, Base):
    """门店配置表（shared_store_settings）

    注意：SPEC 2.0 的平铺重建迁移未执行，当前 DB 仍是旧结构。
    模型与实际 DB 列保持一致。
    """
    __tablename__ = "shared_store_settings"
    __table_args__ = {'extend_existing': True}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    store_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True))

    # 排班相关
    rest_days_per_month: Mapped[int] = mapped_column(Integer, default=4)
    rest_allowed_weekdays: Mapped[str | None] = mapped_column(Text, nullable=True)
    rest_forbidden_weekdays: Mapped[str | None] = mapped_column(Text, nullable=True)
    max_same_position_off: Mapped[int] = mapped_column(Integer, default=1)
    min_position_coverage_percent: Mapped[int] = mapped_column(Integer, default=50)
    manager_order_constraint: Mapped[bool] = mapped_column(Boolean, default=True)
    holiday_policy: Mapped[str] = mapped_column(String(20), default="comp_leave")
    auto_schedule_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    schedule_lock_after_publish: Mapped[bool] = mapped_column(Boolean, default=True)

    # 工资/KPI
    payroll_day_of_month: Mapped[int] = mapped_column(Integer, default=5)
    kpi_coefficient_min: Mapped[float] = mapped_column(default=0.60)
    kpi_coefficient_max: Mapped[float] = mapped_column(default=1.50)

    # 合同
    contract_initiator_ids: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_company_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    contract_company_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    contract_company_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    contract_base_salary: Mapped[float] = mapped_column(default=3000.0)
    contract_probation_months: Mapped[int] = mapped_column(Integer, default=6)
    contract_notice_days: Mapped[int] = mapped_column(Integer, default=45)
    contract_duration_years: Mapped[int] = mapped_column(Integer, default=3)

    # AI
    ai_api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_api_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ai_model: Mapped[str | None] = mapped_column(String(100), nullable=True)
    ai_temperature: Mapped[float] = mapped_column(default=0.7)

    # 打印机
    printer_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    label_printer_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    receipt_printer_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    printer_brand: Mapped[str | None] = mapped_column(String(50), nullable=True)
    printer_api_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    printer_sn: Mapped[str | None] = mapped_column(String(100), nullable=True)
    printer_user: Mapped[str | None] = mapped_column(String(100), nullable=True)
    printer_ukey: Mapped[str | None] = mapped_column(Text, nullable=True)
    printer_label_width: Mapped[int] = mapped_column(Integer, default=80)
    printer_label_height: Mapped[int] = mapped_column(Integer, default=50)

    # 企微机器人
    wecom_bot_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    wecom_webhook_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # 打卡配置（WiFi+拍照打卡）
    checkin_require_wifi: Mapped[bool] = mapped_column(Boolean, default=True)
    checkin_require_photo: Mapped[bool] = mapped_column(Boolean, default=True)
    checkin_grace_minutes: Mapped[int] = mapped_column(Integer, default=5)
    checkin_photo_retention_days: Mapped[int] = mapped_column(Integer, default=90)
    # 智能班次归位：时间窗口（分钟），打卡时间在班次开始/结束 ± 此值内才匹配
    checkin_time_window_minutes: Mapped[int] = mapped_column(Integer, default=120)

    # 扩展配置（未来新业务配置放这里，不用改表结构）
    extra_config: Mapped[dict | None] = mapped_column(JSONB, default=dict)
