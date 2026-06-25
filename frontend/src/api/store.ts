import apiClient from './client'
import type { ApiResponse, EmployeeBrief } from './types'

export interface StoreInfo {
  id: string
  name: string
  store_code: string
  address: string | null
  city: string | null
  status: string
  daily_booking_limit: number | null
  wework_status: string | null
  wework_corp_id: string | null
  wework_agent_id: string | null
  wework_department_id: number | null
  frontend_base_url?: string
}

export interface StoreSettingsData {
  rest_days_per_month: number
  rest_allowed_weekdays: string[]
  rest_forbidden_weekdays: string[]
  max_same_position_off: number
  min_position_coverage_percent: number
  manager_order_constraint: boolean
  holiday_policy: string
  auto_schedule_enabled: boolean
  schedule_lock_after_publish: boolean
  payroll_day_of_month: number
  kpi_coefficient_min: number
  kpi_coefficient_max: number
  // 合同配置（可选）
  contract_initiator_ids?: string[]
  contract_company_name?: string
  contract_company_phone?: string
  contract_company_address?: string
  contract_base_salary?: number
  contract_probation_months?: number
  contract_notice_days?: number
  contract_duration_years?: number
  // 云打印机配置（可选）
  printer_enabled?: boolean
  label_printer_enabled?: boolean      // 标签打印机：存酒出标签
  receipt_printer_enabled?: boolean    // 取酒单打印机：取酒出小票
  printer_brand?: string
  printer_api_url?: string
  printer_sn?: string
  printer_user?: string
  printer_ukey?: string
  printer_label_width?: number
  printer_label_height?: number
  // 扩展配置：订桌规则/评分码/存酒配置/防飞单规则
  extra_config?: Record<string, any>
}

export interface StoreBrief {
  id: string
  name: string
  store_code: string
  city: string | null
  is_current: boolean
}

export const storeAPI = {
  /** 获取门店基本信息 */
  getInfo() {
    return apiClient.get<ApiResponse<StoreInfo>>('/stores')
  },

  /** 列出所有门店（仅 admin/boss，用于切换门店下拉） */
  listAll() {
    return apiClient.get<ApiResponse<StoreBrief[]>>('/stores/all')
  },

  /** 获取门店设置 */
  getSettings() {
    return apiClient.get<ApiResponse<StoreSettingsData>>('/stores/settings')
  },

  /** 更新门店设置 */
  updateSettings(data: Partial<StoreSettingsData>) {
    return apiClient.put<ApiResponse<StoreSettingsData>>('/stores/settings', data)
  },

  /** 更新企微配置 */
  updateWework(data: {
    wework_corp_id?: string
    wework_agent_id?: string
    wework_secret?: string
    wework_token?: string
    wework_aes_key?: string
    wework_department_id?: number | null
  }) {
    return apiClient.put<ApiResponse<StoreInfo>>('/stores/wework', data)
  },

  /** 获取门店员工列表 */
  listEmployees() {
    return apiClient.get<ApiResponse<EmployeeBrief[]>>('/stores/employees')
  },
}
