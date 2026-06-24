from app.models.base import Base, TimestampMixin
from app.models.store import Store, StoreSettings
from app.models.employee import Employee
from app.models.user import User
from app.models.schedule import Schedule, ScheduleSnapshot, ScheduleRule, ShiftSwapRequest
from app.models.attendance import AttendanceRecord, ShiftConfig
from app.models.kpi import KPITemplate, KPIScore, KPIResult, KPIAppeal
from app.models.payroll import PayrollRecord, PayrollRecordItem
from app.models.payroll_config import PayrollItemConfig, SalaryRule
from app.models.period import Period
from app.models.performance import EmployeeMonthlyPerformance
from app.models.wework_payment import WeworkPaymentSync
from app.models.ranking import EmployeeRanking
from app.models.revenue import DailyRevenue
from app.models.rating import GuestRating
from app.models.booking import Booking, Table
from app.models.wine_storage import WineStorage
from app.models.wine_stocktake import WineStocktake, WineStocktakeItem
from app.models.table_session import TableSession
from app.models.contract import SalaryMatrix, Contract
from app.models.approval import ApprovalRequest
from app.models.leave_balance import LeaveBalance
from app.models.notification import Notification, NotificationSetting
from app.models.sign_task import SignTask
from app.models.penalty_notice import PenaltyNotice
from app.models.audit import AuditLog
from app.models.butler import (
    ClosingChecklistTemplate,
    ClosingChecklistItem,
    ClosingSession,
    ClosingItemResult,
)

# ---- Crush 2.0 新增模块（依据 SPEC 2.0 §3.4）----
from app.models.shared import (
    Store as SharedStore,
    Franchisee,
    Employee as SharedEmployee,
    Member,
    MemberLevel,
    Category,
    Product,
    Table as SharedTable,
    Device,
    StoreSetting,
)
from app.models.pos import (
    Order,
    OrderItem,
    Payment,
    PaymentMethod,
    TableSession as PosTableSession,
    Refund,
    DiscountApproval,
    MemberTransaction,
    OrderLog,
    DailyReconciliation,
    DeskNote,
)
from app.models.game import (
    GameTemplate,
    GameSession,
    GameParticipant,
    GamePrize,
)
from app.models.sys import (
    SysConfig,
    Printer,
    PrintRoute,
    PrintQueue,
    ModulePrintConfig,
)

__all__ = [
    "Base",
    "TimestampMixin",
    "Store",
    "StoreSettings",
    "Employee",
    "User",
    "Schedule",
    "ScheduleSnapshot",
    "ScheduleRule",
    "ShiftSwapRequest",
    "AttendanceRecord",
    "ShiftConfig",
    "KPITemplate",
    "KPIScore",
    "KPIResult",
    "KPIAppeal",
    "PayrollRecord",
    "PayrollRecordItem",
    "PayrollItemConfig",
    "SalaryRule",
    "Period",
    "EmployeeMonthlyPerformance",
    "WeworkPaymentSync",
    "EmployeeRanking",
    "DailyRevenue",
    "GuestRating",
    "Booking",
    "Table",
    "WineStorage",
    "WineStocktake",
    "WineStocktakeItem",
    "TableSession",
    "SalaryMatrix",
    "Contract",
    "ApprovalRequest",
    "LeaveBalance",
    "Notification",
    "NotificationSetting",
    "SignTask",
    "PenaltyNotice",
    "AuditLog",
    "ClosingChecklistTemplate",
    "ClosingChecklistItem",
    "ClosingSession",
    "ClosingItemResult",
    # ---- Crush 2.0 新增 ----
    "SharedStore",
    "Franchisee",
    "SharedEmployee",
    "Member",
    "MemberLevel",
    "Category",
    "Product",
    "SharedTable",
    "Device",
    "StoreSetting",
    "Order",
    "OrderItem",
    "Payment",
    "PaymentMethod",
    "PosTableSession",
    "Refund",
    "DiscountApproval",
    "MemberTransaction",
    "OrderLog",
    "DailyReconciliation",
    "DeskNote",
    "GameTemplate",
    "GameSession",
    "GameParticipant",
    "GamePrize",
    "SysConfig",
    "Printer",
    "PrintRoute",
    "PrintQueue",
    "ModulePrintConfig",
]
