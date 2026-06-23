"""
防飞单模块 Pydantic 模型
- 扫描请求
- 预警记录（基于 table_sessions 的 is_anomaly + anomaly_reason）
- 5 规则明细
- 统计汇总
"""
import uuid
from pydantic import BaseModel, field_validator
from datetime import date as DateType


# ==================== 5 规则明细 ====================

class RuleDetail(BaseModel):
    """单条规则的打分明细"""
    rule_name: str           # cancellation / account_diff / amount_deviation / time_gap / employee_deviation
    rule_label: str          # 作废异常 / 账差 / 金额偏离 / 时间裂隙 / 员工偏差
    score: float             # 0-20
    max_score: float = 20.0
    detail: str              # 触发原因说明
    raw_data: dict | None = None  # 原始数据快照


class SessionRisk(BaseModel):
    """单个开台会话的风险评分结果"""
    session_id: uuid.UUID
    store_id: uuid.UUID
    table_no: str
    employee_id: uuid.UUID
    employee_name: str = ""
    opened_at: str
    closed_at: str | None = None
    guest_count: int
    crmeb_order_count: int
    crmeb_total_amount: float
    wework_pay_count: int
    wework_pay_amount: float
    risk_score: float           # 0-100
    risk_level: str             # low / medium / high / critical
    rules: list[RuleDetail]     # 5 条规则明细
    is_anomaly: bool
    anomaly_reason: str | None = None
    status: str                 # open / closed


class ScanRequest(BaseModel):
    """手动触发扫描"""
    date: str = ""              # YYYY-MM-DD, 空=昨天
    store_id: uuid.UUID | None = None # None = 当前门店

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        if not v:
            return v
        import re
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", v):
            raise ValueError("date 格式必须为 YYYY-MM-DD")
        return v


class ScanResponse(BaseModel):
    """扫描结果汇总"""
    date: str
    store_id: uuid.UUID
    total_sessions: int
    anomaly_count: int
    anomaly_rate: float       # 异常率百分比
    high_risk_count: int      # risk_score > 50
    critical_count: int       # risk_score > 80
    sessions: list[SessionRisk]


# ==================== 预警查询 ====================

class AlertFilter(BaseModel):
    """预警列表筛选"""
    date_from: str | None = None
    date_to: str | None = None
    risk_level: str | None = None   # low / medium / high / critical
    employee_id: uuid.UUID | None = None
    status: str | None = None       # open / closed
    page: int = 1
    page_size: int = 20


class AlertListItem(BaseModel):
    """预警列表项（精简）"""
    session_id: uuid.UUID
    table_no: str
    employee_id: uuid.UUID
    employee_name: str
    risk_score: float
    risk_level: str
    anomaly_reason: str | None
    opened_at: str
    closed_at: str | None
    status: str
    is_anomaly: bool


class AlertDetail(SessionRisk):
    """预警详情 = 完整 SessionRisk"""


# ==================== 统计 ====================

class AntiFraudStats(BaseModel):
    """防飞单统计"""
    store_id: uuid.UUID
    date_from: str
    date_to: str
    total_sessions: int
    anomaly_sessions: int
    anomaly_rate: float
    avg_risk_score: float
    by_employee: list[dict]         # [{employee_id, name, anomaly_count, avg_risk}]
    by_rule: list[dict]             # [{rule_name, rule_label, avg_score, trigger_count}]
    daily_trend: list[dict]         # [{date, total, anomaly_count, anomaly_rate}]
