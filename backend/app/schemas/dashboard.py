"""
数据看板 Pydantic 模型
- 今日营收概览 (RevenueBlock)
- 营收构成 (RevenueBreakdown)
- 7天趋势点 (ChartPoint)
- 顾客评分 (RatingSummary + LowScoreAlert)
- 订桌概况 (BookingSummary)
- 完整看板响应 (DashboardResponse)
"""
import uuid
from pydantic import BaseModel


class RevenueBlock(BaseModel):
    """今日营收概览"""
    today_revenue: float = 0.0
    yesterday_revenue: float = 0.0
    growth_rate: float = 0.0          # 环比增长率，如 0.15 表示 +15%
    total_orders: int = 0
    total_guests: int = 0
    avg_order_value: float = 0.0      # 客单价


class RevenueBreakdown(BaseModel):
    """营收构成"""
    bottle_sales: float = 0.0          # 酒水
    card_sales: float = 0.0            # 充值卡
    other_sales: float = 0.0           # 其他（总营收 - 酒水 - 充值卡）
    total: float = 0.0
    bottle_pct: float = 0.0
    card_pct: float = 0.0
    other_pct: float = 0.0


class ChartPoint(BaseModel):
    """7天趋势数据点"""
    date: str                          # 06-07
    weekday: str                       # 周一
    revenue: float = 0.0
    orders: int = 0


class LowScoreAlert(BaseModel):
    """低分预警"""
    id: uuid.UUID
    table_no: str = ""
    overall_score: float = 0.0
    comment: str = ""
    created_at: str = ""


class RatingSummary(BaseModel):
    """顾客评分汇总"""
    avg_score: float = 0.0
    total_ratings: int = 0
    low_score_count: int = 0           # 低分数量 (<3.0)
    alerts: list[LowScoreAlert] = []   # 最近低分列表


class BookingSummary(BaseModel):
    """订桌概况（今日）"""
    confirmed: int = 0                 # 已确认
    total_tables: int = 0              # 总桌数
    available: int = 0                 # 空闲


class AttendanceSummary(BaseModel):
    """今日考勤汇总"""
    scheduled_count: int = 0           # 应出勤人数
    actual_count: int = 0              # 实际出勤人数
    late_count: int = 0                # 迟到人数
    absent_count: int = 0              # 旷工人数
    early_count: int = 0               # 早退人数
    leave_count: int = 0               # 请假人数


class MyPerformance(BaseModel):
    """我的业绩（个人企微收款累计，按发薪月统计）"""
    total_wework_pay: float = 0.0      # 本月累计企微个人收款
    period: str = ""                   # 统计周期，如 "2026-06"


class DashboardResponse(BaseModel):
    """完整看板响应"""
    revenue: RevenueBlock
    breakdown: RevenueBreakdown
    chart: list[ChartPoint] = []
    rating: RatingSummary
    booking: BookingSummary
    attendance: AttendanceSummary
    my_performance: MyPerformance = MyPerformance()
    updated_at: str = ""               # 数据更新时间
