import apiClient from './client'
import type { ApiResponse } from './types'

export interface SignTaskItem {
  id: string
  store_id: string
  employee_id: string
  type: string
  title: string
  ref_type: string
  ref_id: string
  status: string
  signed_at: string | null
  signature_data: string | null
  dispute_reason: string | null
  disputed_at: string | null
  issued_by: string
  issued_at: string
  notes: string | null
  extra: Record<string, unknown> | null
  created_at: string | null
  employee_name: string | null
  issued_by_name: string | null
  ref_data: Record<string, unknown> | null
}

export interface SignTaskListResponse {
  items: SignTaskItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export const signTaskAPI = {
  getInbox(params: { status?: string; page?: number; page_size?: number } = {}) {
    return apiClient.get<ApiResponse<SignTaskListResponse>>(
      '/sign-tasks/inbox',
      { params }
    )
  },

  getCount() {
    return apiClient.get<ApiResponse<{ pending: number }>>(
      '/sign-tasks/inbox/count'
    )
  },

  getDetail(taskId: string) {
    return apiClient.get<ApiResponse<SignTaskItem>>(
      `/sign-tasks/${taskId}`
    )
  },

  sign(taskId: string, signatureData: string, notes?: string) {
    return apiClient.post<ApiResponse<SignTaskItem>>(
      `/sign-tasks/${taskId}/sign`,
      { signature_data: signatureData, notes }
    )
  },

  batchSign(taskIds: string[], signatureData: string, notes?: string) {
    return apiClient.post<ApiResponse<{
      success_count: number
      failed_count: number
      success_ids: string[]
      failed: { task_id: string; reason: string }[]
    }>>(
      `/sign-tasks/batch/sign`,
      { task_ids: taskIds, signature_data: signatureData, notes }
    )
  },

  dispute(taskId: string, reason: string) {
    return apiClient.post<ApiResponse<SignTaskItem>>(
      `/sign-tasks/${taskId}/dispute`,
      { reason }
    )
  },

  getIssued(params: { status?: string; page?: number; page_size?: number } = {}) {
    return apiClient.get<ApiResponse<SignTaskListResponse>>(
      '/sign-tasks/issued',
      { params }
    )
  },

  getDisputes(params: { page?: number; page_size?: number } = {}) {
    return apiClient.get<ApiResponse<SignTaskListResponse>>(
      '/sign-tasks/issued/disputes',
      { params }
    )
  },

  remind(taskId: string) {
    return apiClient.post<ApiResponse<{ sent: boolean }>>(
      `/sign-tasks/${taskId}/remind`
    )
  },

  revoke(taskId: string, reason?: string) {
    return apiClient.post<ApiResponse<{ revoked: boolean }>>(
      `/sign-tasks/${taskId}/revoke`,
      { reason }
    )
  },
}
