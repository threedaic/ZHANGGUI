import apiClient from './client'
import type { ApiResponse } from './types'

// ==================== 模板 ====================

export interface KPITemplate {
  id: string
  store_id: string | null
  role: string
  dimension: string
  dimension_label: string
  weight: number
  formula_type: string
  formula_config: string
  data_source: string
  is_active: boolean
}

export const kpiTemplateAPI = {
  list(role?: string) {
    return apiClient.get<ApiResponse<KPITemplate[]>>('/kpi/templates', {
      params: { role },
    })
  },
}

// ==================== 评分 ====================

export interface KPIScoreItem {
  id: string
  employee_id: string
  store_id: string
  period: string
  dimension: string
  raw_value: number | null
  raw_description: string | null
  normalized_score: number
  weight: number
  weighted_score: number
  data_source: string | null
  source_reference: string | null
  calculated_at: string | null
}

export interface KPIScoreCreateItem {
  employee_id: string
  period: string
  dimension: string
  raw_value: number | null
  raw_description: string | null
  data_source: string | null
}

export const kpiScoreAPI = {
  list(params?: { employee_id?: string; period?: string; dimension?: string }) {
    return apiClient.get<ApiResponse<KPIScoreItem[]>>('/kpi/scores', { params })
  },

  batchCreate(data: { period: string; scores: KPIScoreCreateItem[] }) {
    return apiClient.post<ApiResponse<{ created: number }>>('/kpi/scores/batch', data)
  },

  calculate(data: { employee_ids?: string[]; period: string }) {
    return apiClient.post<ApiResponse<KPIResultItem[]>>('/kpi/scores/calculate', data)
  },
}

// ==================== 结果 ====================

export interface KPIResultItem {
  id: string
  employee_id: string
  store_id: string
  period: string
  total_score: number
  coefficient: number
  coefficient_reason: string | null
  rank_in_store: number | null
  status: string
  confirmed_by: string | null
  confirmed_at: string | null
  created_at: string | null
}

export interface KPIResultDetail extends KPIResultItem {
  employee_name: string
  employee_role: string
  dimensions: KPIScoreItem[]
}

export interface KPIResultSummary {
  period: string
  store_avg: number
  store_count: number
  results: KPIResultDetail[]
}

export const kpiResultAPI = {
  list(period: string, page = 1, pageSize = 20) {
    return apiClient.get<ApiResponse<KPIResultSummary>>('/kpi/results', {
      params: { period, page, page_size: pageSize },
    })
  },

  my(period?: string) {
    return apiClient.get<ApiResponse<KPIResultDetail[]>>('/kpi/results/my', {
      params: { period },
    })
  },

  detail(resultId: string) {
    return apiClient.get<ApiResponse<KPIResultDetail>>(`/kpi/results/${resultId}`)
  },

  confirm(resultId: string, data: { coefficient?: number; coefficient_reason?: string }) {
    return apiClient.post<ApiResponse<KPIResultItem>>(
      `/kpi/results/${resultId}/confirm`,
      data
    )
  },
}

// ==================== 申诉 ====================

export interface KPIAppealItem {
  id: string
  result_id: string
  employee_id: string
  dimension: string | null
  reason: string
  evidence: string | null
  status: string
  reviewed_by: string | null
  resolution: string | null
  resolved_at: string | null
  created_at: string | null
  employee_name: string
  period: string
  current_score: number
}

export interface KPIAppealList {
  items: KPIAppealItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const kpiAppealAPI = {
  create(data: { result_id: string; dimension?: string; reason: string; evidence?: string }) {
    return apiClient.post<ApiResponse<KPIAppealItem>>('/kpi/appeals', data)
  },

  list(params?: { status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<KPIAppealList>>('/kpi/appeals', { params })
  },

  my(params?: { status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<KPIAppealList>>('/kpi/appeals/my', { params })
  },

  review(appealId: string, data: { action: string; resolution?: string }) {
    return apiClient.put<ApiResponse<KPIAppealItem>>(
      `/kpi/appeals/${appealId}/review`,
      data
    )
  },
}
