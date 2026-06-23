import apiClient from './client'
import type { ApiResponse, EmployeeBrief } from './types'

export interface ScheduleItem {
  id: string
  store_id: string
  employee_id: string
  employee_name: string
  date: string
  shift_type: string
  note: string | null
  version: number
}

export interface ScheduleStatsItem {
  date: string
  total_scheduled: number
  day_count: number
  night_count: number
  rest_count: number
}

export interface ScheduleCreatePayload {
  employee_id: string
  date: string
  shift_type: string
  note?: string
}

export interface BatchCreatePayload {
  schedules: ScheduleCreatePayload[]
}

export interface WeekData {
  week: string
  start_date: string
  end_date: string
  schedules: ScheduleItem[]
}

/** 获取日期范围的排班表 */
export function fetchSchedules(startDate: string, endDate: string) {
  return apiClient.get<ApiResponse<ScheduleItem[]>>('/schedules', {
    params: { start_date: startDate, end_date: endDate },
  })
}

/** 按 ISO 周获取排班表 (如 /schedules/weeks/2026-W24) */
export function fetchSchedulesByWeek(week: string) {
  return apiClient.get<ApiResponse<WeekData>>(`/schedules/weeks/${week}`)
}

/** 获取编制统计 */
export function fetchStats(startDate: string, endDate: string) {
  return apiClient.get<ApiResponse<ScheduleStatsItem[]>>('/schedules/stats', {
    params: { start_date: startDate, end_date: endDate },
  })
}

/** 获取可排班员工列表 */
export function fetchEmployees() {
  return apiClient.get<ApiResponse<EmployeeBrief[]>>('/schedules/employees')
}

/** 创建单条排班 */
export function createSchedule(data: ScheduleCreatePayload) {
  return apiClient.post<ApiResponse<ScheduleItem>>('/schedules', data)
}

/** 批量创建排班 */
export function batchCreateSchedules(data: BatchCreatePayload) {
  return apiClient.post<ApiResponse<ScheduleItem[]>>('/schedules/batch', data)
}

/** 更新单条排班 */
export function updateSchedule(id: string, data: { shift_type?: string; note?: string }) {
  return apiClient.put<ApiResponse<ScheduleItem>>(`/schedules/${id}`, data)
}

/** 删除单条排班 */
export function deleteSchedule(id: string) {
  return apiClient.delete<ApiResponse<null>>(`/schedules/${id}`)
}

// ---- 员工个人视图 ----

export interface MyScheduleEntry {
  id: string
  date: string
  shift_type: string
  note: string | null
}

export interface MyScheduleData {
  employee_id: string
  employee_name: string
  start_date: string
  end_date: string
  schedules: MyScheduleEntry[]
}

/** 获取当前员工个人的排班（员工视图，只看自己） */
export function fetchMySchedules(employeeId: string, startDate: string, endDate: string) {
  return apiClient.get<ApiResponse<MyScheduleData>>('/schedules/my', {
    params: { employee_id: employeeId, start_date: startDate, end_date: endDate },
  })
}
