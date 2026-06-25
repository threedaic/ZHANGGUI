"""
考勤与排班一体化 Pydantic 模型
"""
import uuid
from datetime import date
from pydantic import BaseModel, Field, field_validator


# ==================== 排班表 ====================

class ScheduleCell(BaseModel):
    date: str
    scheduled_shift: str | None = None
    status: str = "unknown"
    clock_in: str | None = None
    clock_out: str | None = None
    late_minutes: int = 0
    early_minutes: int = 0


class ScheduleEmployeeRow(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    employee_role: str
    cells: list[ScheduleCell]


class ScheduleShiftInfo(BaseModel):
    shift_code: str
    shift_name: str
    color: str


class ScheduleTableResponse(BaseModel):
    date_from: str
    date_to: str
    shifts: list[ScheduleShiftInfo]
    employees: list[ScheduleEmployeeRow]


class ScheduleBatchItem(BaseModel):
    employee_id: uuid.UUID
    date: str
    scheduled_shift: str


class ScheduleBatchRequest(BaseModel):
    schedules: list[ScheduleBatchItem]


class ScheduleBatchResponse(BaseModel):
    created: int
    updated: int


class MyScheduleResponse(BaseModel):
    employee_id: uuid.UUID
    date_from: str
    date_to: str
    shifts: list[ScheduleShiftInfo]
    cells: list[ScheduleCell]
    stats: dict


# ==================== 班次配置 ====================

class ShiftConfigItem(BaseModel):
    id: uuid.UUID | None = None
    shift_code: str
    shift_name: str
    start_time: str
    end_time: str
    is_overnight: bool = False
    color: str = "#FB0079"
    sort_order: int = 0
    is_active: bool = True

    @field_validator("start_time", "end_time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        import re
        if not re.match(r"^\d{2}:\d{2}$", v):
            raise ValueError("时间格式必须为 HH:MM")
        return v


class ShiftConfigSaveRequest(BaseModel):
    shift_code: str
    shift_name: str
    start_time: str
    end_time: str
    is_overnight: bool = False
    color: str = "#FB0079"
    sort_order: int = 0
    is_active: bool = True


# ==================== 打卡记录 ====================

class AttendanceRecordResponse(BaseModel):
    id: uuid.UUID
    employee_id: uuid.UUID
    store_id: uuid.UUID
    date: str
    scheduled_shift: str | None = None
    clock_in: str | None = None
    clock_out: str | None = None
    status: str
    late_minutes: int = 0
    early_minutes: int = 0
    source: str = "manual"
    note: str | None = None
    employee_name: str = ""
    deduction: float = 0.0
    deduction_reason: str = ""


# ==================== 智能排班生成 ====================

class ScheduleGenerateRequest(BaseModel):
    year: int
    month: int


class ScheduleGenerateItem(BaseModel):
    employee_id: uuid.UUID
    employee_name: str = ""
    date: str
    scheduled_shift: str


class ScheduleGenerateResponse(BaseModel):
    schedules: list[ScheduleGenerateItem]
    stats: dict


class EmployeeRuleItem(BaseModel):
    employee_id: uuid.UUID
    shift_group: str | None = None
    is_first_manager: bool = False
    is_second_manager: bool = False
    is_third_manager: bool = False


class EmployeeRuleUpdateRequest(BaseModel):
    employees: list[EmployeeRuleItem]

    model_config = {"from_attributes": True}


class AttendanceRecordCreate(BaseModel):
    employee_id: uuid.UUID
    date: str
    clock_in: str | None = None
    clock_out: str | None = None
    scheduled_shift: str | None = None


class AttendanceListRequest(BaseModel):
    employee_id: uuid.UUID | None = None
    date_from: str | None = None
    date_to: str | None = None
    status: str | None = None
    page: int = 1
    page_size: int = 20


# ==================== 同步 ====================

class SyncRequest(BaseModel):
    target_date: str | None = None


class SyncResponse(BaseModel):
    synced_count: int
    errors: list[str]


# ==================== 月末汇总 ====================

class MonthlySummaryItem(BaseModel):
    employee_id: uuid.UUID
    employee_name: str
    employee_role: str
    total_days: int = 0
    present_days: int = 0
    late_days: int = 0
    early_days: int = 0
    leave_days: int = 0
    absent_days: int = 0
    makeup_count: int = 0
    total_late_minutes: int = 0


class MonthlySummaryResponse(BaseModel):
    period: str
    store_id: uuid.UUID
    items: list[MonthlySummaryItem]


# ==================== WiFi打卡绑定 ====================

class CheckinWifiItem(BaseModel):
    id: uuid.UUID | None = None
    ssid: str
    bssid: str
    label: str | None = None
    is_active: bool = True

    model_config = {"from_attributes": True}


class CheckinWifiCreateRequest(BaseModel):
    ssid: str = Field(..., min_length=1, max_length=64)
    bssid: str = Field(..., min_length=1, max_length=32)
    label: str | None = None
    is_active: bool = True


class CheckinConfigResponse(BaseModel):
    """打卡配置（前端用于决定打卡流程）"""
    require_wifi: bool = True
    require_photo: bool = True
    grace_minutes: int = 5
    photo_retention_days: int = 90
    time_window_minutes: int = 120
    wifis: list[CheckinWifiItem] = []


class CheckinConfigUpdateRequest(BaseModel):
    require_wifi: bool | None = None
    require_photo: bool | None = None
    grace_minutes: int | None = Field(None, ge=0, le=120)
    photo_retention_days: int | None = Field(None, ge=7, le=365)
    time_window_minutes: int | None = Field(None, ge=30, le=360)


# ==================== 打卡结果 ====================

class CheckinResultResponse(BaseModel):
    """打卡结果"""
    record_id: uuid.UUID
    date: str
    action: str  # clock_in / clock_out
    clock_time: str
    scheduled_shift: str | None = None
    shift_start_time: str | None = None
    shift_end_time: str | None = None
    status: str  # present / late / early / unknown
    late_minutes: int = 0
    early_minutes: int = 0
    matched_by: str  # schedule / time_window
    photo_url: str | None = None
    wifi_ssid: str | None = None


class CheckinStatusResponse(BaseModel):
    """今日打卡状态（前端打卡页展示用）"""
    date: str
    scheduled_shift: str | None = None
    shift_start_time: str | None = None
    shift_end_time: str | None = None
    is_overnight: bool = False
    clock_in: str | None = None
    clock_out: str | None = None
    status: str = "unknown"
    late_minutes: int = 0
    early_minutes: int = 0
    can_checkin: bool = True
    next_action: str = "clock_in"  # clock_in / clock_out / done
