import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

// 重新导出共享类型，便于视图层从 attendance.ts 统一导入
export type { PageResult }

export interface ShiftConfig {
  id: string
  shift_code: string
  shift_name: string
  start_time: string
  end_time: string
  is_overnight: boolean
  color: string
  sort_order: number
  is_active: boolean
}

export interface ScheduleCell {
  date: string
  scheduled_shift: string | null
  shift_start_time: string | null
  shift_end_time: string | null
  is_overnight: boolean
  clock_in: string | null
  clock_out: string | null
  status: string
  late_minutes: number
  early_minutes: number
}

export interface ScheduleTableData {
  date_from: string
  date_to: string
  days: string[]
  employees: {
    employee_id: string
    employee_name: string
    employee_role: string
    cells: ScheduleCell[]
  }[]
  shifts: {
    shift_code: string
    shift_name: string
    color: string
  }[]
  stats: Record<string, { work: number; rest: number; late: number; absent: number }>
}

export interface MyScheduleData {
  employee_id: string
  date_from: string
  date_to: string
  cells: ScheduleCell[]
  shifts: {
    shift_code: string
    shift_name: string
    color: string
  }[]
  stats: {
    work_days: number
    present_days: number
    late_days: number
    leave_days: number
    absent_days: number
  }
}

/** 排班批量保存结果 */
export interface ScheduleBatchResult {
  created: number
  updated: number
}

/** 智能排班生成结果 */
export interface ScheduleGenerateResult {
  schedules: Array<{
    employee_id: string
    employee_name: string
    date: string
    scheduled_shift: string
  }>
  stats: {
    total_entries: number
    employees: number
    rest_days: number
  }
}

/** 员工排班规则更新结果 */
export interface EmployeeRuleUpdateResult {
  updated: number
}

/** 打卡记录 */
export interface AttendanceRecord {
  id: string
  employee_id: string
  store_id: string
  date: string
  scheduled_shift: string | null
  clock_in: string | null
  clock_out: string | null
  status: string
  late_minutes: number
  early_minutes: number
  source: string
  note: string | null
  employee_name: string
  deduction: number
  deduction_reason: string
}

/** 今日打卡状态条目（复用 AttendanceRecord 结构） */
export type TodayAttendanceItem = AttendanceRecord

/** 指纹机同步结果 */
export interface FingerprintSyncResult {
  synced_count: number
  new_records: number
  updated_records: number
  errors: string[]
}

/** 补卡申请参数 */
export interface MakeupRequestParams {
  employee_id: string
  date: string
  clock_in: string | null
  clock_out: string | null
  reason: string
}

/** 补卡申请结果 */
export interface MakeupResult {
  id: string
  fee: number
  month_count: number
}

/** 请假申请参数 */
export interface LeaveRequestParams {
  employee_id: string
  start_date: string
  end_date: string
  leave_type: string
  reason: string
}

/** 请假记录 */
export interface LeaveResponse {
  id: string
  employee_id: string
  employee_name: string
  start_date: string
  end_date: string
  leave_type: string
  reason: string
  status: string
  created_at: string | null
}

/** 请假记录列表响应 */
export interface LeaveRecordsData {
  items: LeaveResponse[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

/** 月末汇总条目 */
export interface MonthlySummaryItem {
  employee_id: string
  employee_name: string
  employee_role: string
  total_days: number
  present_days: number
  late_days: number
  early_days: number
  leave_days: number
  absent_days: number
  makeup_count: number
  late_fee: number
  makeup_fee: number
  total_deduction: number
}

/** 月末汇总响应 */
export interface MonthlySummaryData {
  period: string
  store_id: string
  items: MonthlySummaryItem[]
  total_deduction: number
}

/** 打卡记录查询参数 */
export interface RecordsQueryParams {
  employee_id?: string
  date_from?: string
  date_to?: string
  status?: string
  page?: number
  page_size?: number
}

export const attendanceAPI = {
  /** 获取全员排班考勤表（管理端） */
  getScheduleTable(params: { date_from: string; date_to: string }) {
    return apiClient.get<ApiResponse<ScheduleTableData>>('/attendance/schedule', { params })
  },

  /** 获取个人排班考勤（员工端） */
  getMySchedule(params: { date_from: string; date_to: string }) {
    return apiClient.get<ApiResponse<MyScheduleData>>('/attendance/schedule/my', { params })
  },

  /** 批量保存排班 */
  batchSaveSchedules(data: { schedules: Array<{ employee_id: string; date: string; scheduled_shift: string }> }) {
    return apiClient.post<ApiResponse<ScheduleBatchResult>>('/attendance/schedule/batch', data)
  },

  /** 智能排班生成 */
  generateSchedule(data: { year: number; month: number }) {
    return apiClient.post<ApiResponse<ScheduleGenerateResult>>('/attendance/schedule/generate', data)
  },

  /** 获取班次配置列表 */
  getShiftConfigs() {
    return apiClient.get<ApiResponse<ShiftConfig[]>>('/attendance/shifts')
  },

  /** 保存班次配置 */
  saveShiftConfig(data: Partial<ShiftConfig> & { shift_code: string; shift_name: string; start_time: string; end_time: string }) {
    return apiClient.post<ApiResponse<ShiftConfig>>('/attendance/shifts', data)
  },

  /** 同步企微打卡 */
  syncCheckin(data?: { target_date?: string }) {
    return apiClient.post<ApiResponse<{ synced_count: number; errors: string[] }>>('/attendance/sync', data || {})
  },

  /** 批量更新员工排班规则 */
  batchUpdateEmployeeRules(data: {
    employees: Array<{
      employee_id: string
      shift_group: string | null
      is_first_manager: boolean
      is_second_manager: boolean
      is_third_manager: boolean
    }>
  }) {
    return apiClient.put<ApiResponse<EmployeeRuleUpdateResult>>('/attendance/employee-rules', data)
  },

  /** 获取今日打卡状态 */
  getToday() {
    return apiClient.get<ApiResponse<TodayAttendanceItem[]>>('/attendance/today')
  },

  /** 同步指纹机打卡 */
  syncFingerprint(date: string) {
    return apiClient.post<ApiResponse<FingerprintSyncResult>>('/attendance/sync/fingerprint', { target_date: date })
  },

  /** 申请补卡 */
  requestMakeup(data: MakeupRequestParams) {
    return apiClient.post<ApiResponse<MakeupResult>>('/attendance/makeup', data)
  },

  /** 申请请假 */
  requestLeave(data: LeaveRequestParams) {
    return apiClient.post<ApiResponse<LeaveResponse>>('/attendance/leave', data)
  },

  /** 获取请假记录列表 */
  getLeaveRecords(params: { status?: string; page?: number; page_size?: number } = {}) {
    return apiClient.get<ApiResponse<LeaveRecordsData>>('/attendance/leave', { params })
  },

  /** 审批请假 */
  approveLeave(recordId: string, data: { action: string; resolution?: string }) {
    return apiClient.put<ApiResponse<LeaveResponse>>(`/attendance/leave/${recordId}/approve`, data)
  },

  /** 获取月度考勤汇总 */
  getMonthlySummary(period: string) {
    return apiClient.get<ApiResponse<MonthlySummaryData>>('/attendance/monthly', {
      params: { period },
    })
  },

  /** 获取打卡记录列表 */
  getRecords(params: RecordsQueryParams) {
    return apiClient.get<ApiResponse<PageResult<AttendanceRecord>>>('/attendance/records', { params })
  },
}
