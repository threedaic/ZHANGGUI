import apiClient from './client'
import type { ApiResponse } from './types'

export interface PenaltyItem {
  id: string
  store_id: string
  employee_id: string
  penalty_type: string
  amount: number
  reason: string
  issued_by: string
  issued_at: string
  status: string
  extra: Record<string, unknown> | null
  created_at: string | null
  employee_name: string | null
  issued_by_name: string | null
  penalty_type_name: string | null
  sign_task_id: string | null
  sign_task_status: string | null
  signature_data: string | null
  signed_at: string | null
  dispute_reason: string | null
  disputed_at: string | null
  sign_notes: string | null
}

export interface PenaltyTypeOption {
  value: string
  label: string
}

export interface PenaltyListResponse {
  items: PenaltyItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const penaltyAPI = {
  create(data: { employee_id: string; penalty_type: string; amount: number; reason: string }) {
    return apiClient.post<ApiResponse<{ id: string; status: string }>>(
      '/penalties',
      data
    )
  },

  getList(params: {
    penalty_type?: string
    status?: string
    employee_id?: string
    page?: number
    page_size?: number
  } = {}) {
    return apiClient.get<ApiResponse<PenaltyListResponse>>(
      '/penalties',
      { params }
    )
  },

  getTypes() {
    return apiClient.get<ApiResponse<PenaltyTypeOption[]>>(
      '/penalties/types'
    )
  },

  getDetail(id: string) {
    return apiClient.get<ApiResponse<PenaltyItem>>(
      `/penalties/${id}`
    )
  },

  update(id: string, data: Partial<{ employee_id: string; penalty_type: string; amount: number; reason: string }>) {
    return apiClient.put<ApiResponse<{ id: string }>>(
      `/penalties/${id}`,
      data
    )
  },

  delete(id: string) {
    return apiClient.delete<ApiResponse<null>>(
      `/penalties/${id}`
    )
  },
}
