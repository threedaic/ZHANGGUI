import apiClient from './client'
import type { ApiResponse } from './types'

export interface RuleDetail {
  rule_name: string
  rule_label: string
  score: number
  max_score: number
  detail: string
  raw_data?: Record<string, unknown>
}

export interface SessionRisk {
  session_id: string
  store_id: string
  table_no: string
  employee_id: string
  employee_name: string
  opened_at: string
  closed_at: string | null
  guest_count: number
  crmeb_order_count: number
  crmeb_total_amount: number
  wework_pay_count: number
  wework_pay_amount: number
  risk_score: number
  risk_level: string
  rules: RuleDetail[]
  is_anomaly: boolean
  anomaly_reason: string | null
  status: string
}

export interface ScanResult {
  date: string
  store_id: string
  total_sessions: number
  anomaly_count: number
  anomaly_rate: number
  high_risk_count: number
  critical_count: number
  sessions: SessionRisk[]
}

export interface AlertListItem {
  session_id: string
  table_no: string
  employee_id: string
  employee_name: string
  risk_score: number
  risk_level: string
  anomaly_reason: string | null
  opened_at: string
  closed_at: string | null
  status: string
  is_anomaly: boolean
}

export interface AlertListData {
  items: AlertListItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface EmployeeStat {
  employee_id: string
  name: string
  anomaly_count: number
  total_sessions: number
  anomaly_rate: number
  avg_risk: number
}

export interface DailyTrend {
  date: string
  total: number
  anomaly_count: number
  anomaly_rate: number
}

export interface AntiFraudStats {
  store_id: string
  date_from: string
  date_to: string
  total_sessions: number
  anomaly_sessions: number
  anomaly_rate: number
  avg_risk_score: number
  by_employee: EmployeeStat[]
  by_rule: { rule_name: string; rule_label: string; avg_score: number; trigger_count: number }[]
  daily_trend: DailyTrend[]
}

export const antifraudAPI = {
  /** 手动触发扫描 */
  scan(date?: string) {
    return apiClient.post<ApiResponse<ScanResult>>(
      '/antifraud/scan',
      { date: date || '' }
    )
  },

  /** 预警列表 */
  getAlerts(params: {
    date_from?: string
    date_to?: string
    risk_level?: string
    employee_id?: string
    page?: number
    page_size?: number
  }) {
    return apiClient.get<ApiResponse<AlertListData>>('/antifraud/alerts', { params })
  },

  /** 预警详情 */
  getAlertDetail(sessionId: string) {
    return apiClient.get<ApiResponse<SessionRisk>>(
      `/antifraud/alerts/${sessionId}`
    )
  },

  /** 防飞单统计 */
  getStats(dateFrom: string, dateTo: string) {
    return apiClient.get<ApiResponse<AntiFraudStats>>('/antifraud/stats', {
      params: { date_from: dateFrom, date_to: dateTo },
    })
  },
}
