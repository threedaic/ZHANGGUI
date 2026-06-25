// 工资计算 API
import client from './client'
import type { ApiResponse } from './types'

// ====== 类型定义 ======

export interface PayrollMonthlyItem {
  record_id: string
  employee_id: string
  employee_name: string
  employee_role: string
  total_income: number
  total_deduction: number
  net_pay: number
  status: 'draft' | 'reviewed' | 'confirmed' | 'paid'
}

export interface PayrollMonthlySummary {
  period: string
  store_id: string
  items: PayrollMonthlyItem[]
  total_income: number
  total_deduction: number
  total_net_pay: number
  status_summary: Record<string, number>
}

export interface PayrollRecordItem {
  item_code: string
  item_name: string
  item_type: 'income' | 'deduction'
  amount: number
  data_source: string
  sort_order: number
  detail: Record<string, unknown> | null
}

export interface PayrollRecordDetail {
  id: string
  employee_id: string
  store_id: string
  period: string
  total_income: number
  total_deduction: number
  net_pay: number
  kpi_coefficient: number
  status: 'draft' | 'confirmed' | 'paid'
  generated_at: string | null
  finalized_at: string | null
  paid_at: string | null
  notes: string | null
  employee_name: string
  employee_role: string
  items: PayrollRecordItem[]
  snapshot: Record<string, unknown> | null
}

export interface MyPayrollItem {
  id: string
  employee_id: string
  period: string
  total_income: number
  total_deduction: number
  net_pay: number
  status: 'draft' | 'confirmed' | 'paid'
  generated_at: string | null
  finalized_at: string | null
  paid_at: string | null
  employee_name: string
  employee_role: string
}

export interface PayrollGenerateResult {
  period: string
  count: number
  employees: { employee_id: string; net_pay: number; status: string }[]
}

// ====== API 方法 ======

export function generatePayroll(period: string, employee_ids?: string[]) {
  return client.post<ApiResponse<PayrollGenerateResult>>('/payroll/generate', {
    period,
    employee_ids: employee_ids ?? null,
  })
}

export function getMonthlyPayroll(
  period: string,
  page = 1,
  page_size = 50
) {
  return client.get<ApiResponse<PayrollMonthlySummary>>('/payroll/monthly', {
    params: { period, page, page_size },
  })
}

export function getPayrollDetail(recordId: string) {
  return client.get<ApiResponse<PayrollRecordDetail>>(
    `/payroll/records/${recordId}`
  )
}

export function getMyPayroll(period?: string) {
  return client.get<ApiResponse<MyPayrollItem[]>>('/payroll/my', {
    params: { period },
  })
}

export function reviewPayroll(record_ids: string[], notes?: string) {
  return client.post<ApiResponse<null>>('/payroll/review', {
    record_ids,
    notes,
  })
}

export function finalizePayroll(record_ids: string[], notes?: string) {
  return client.post<ApiResponse<null>>('/payroll/finalize', {
    record_ids,
    notes,
  })
}

export function markPaidPayroll(record_ids: string[], paid_at?: string) {
  return client.post<ApiResponse<null>>('/payroll/mark-paid', {
    record_ids,
    paid_at,
  })
}

// ====== 当月工资预览（每日同步）======

export interface PayrollPreviewItem {
  code: string
  name: string
  type: 'income' | 'deduction'
  amount: number
  source: string
  detail: Record<string, unknown>
}

export interface PayrollPreviewData {
  period: string
  employee_id: string
  employee_name: string
  position: string
  net_pay: number
  items: PayrollPreviewItem[]
  modules_enabled: Record<string, boolean>
  pay_day: number
  is_finalized: boolean
  notice: string
}

export function getMyPayrollPreview(period?: string) {
  return client.get<ApiResponse<PayrollPreviewData>>('/payroll/my-preview', {
    params: { period },
  })
}
