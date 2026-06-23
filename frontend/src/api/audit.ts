import apiClient from './client'
import type { ApiResponse } from './types'

export interface AuditLogItem {
  id: string
  user_id: string | null
  username: string
  action: string
  entity_type: string
  entity_id: string | null
  old_value: string | null
  new_value: string | null
  request_id: string | null
  ip_address: string | null
  created_at: string
}

export interface AuditLogResponse {
  items: AuditLogItem[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export function getAuditLogs(params: {
  page?: number
  page_size?: number
  entity_type?: string
  action?: string
  user_id?: string
  date_from?: string
  date_to?: string
}) {
  return apiClient.get<ApiResponse<AuditLogResponse>>('/audit', { params })
}
