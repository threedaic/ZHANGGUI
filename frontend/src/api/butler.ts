/**
 * 智能管家模块 API 客户端
 */
import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

export interface ChecklistTemplate {
  id: string
  store_id: string
  name: string
  session_type: 'opening' | 'closing'
  role_tag: string
  sort_order: number
  is_active: boolean
  items: ChecklistItem[]
  results?: ItemResult[]
}

export interface ChecklistItem {
  id: string
  template_id: string
  item_name: string
  item_type: 'checkbox' | 'photo'
  required_photo: boolean
  sort_order: number
  ai_prompt?: string | null
}

export interface SessionDetail {
  id: string
  store_id: string
  session_type: string
  operator_user_id: string
  status: string
  started_at: string
  completed_at: string | null
  total_items: number
  completed_items: number
  templates: ChecklistTemplate[]
}

export interface ItemResult {
  id: string
  session_id: string
  template_id: string | null
  item_id: string | null
  item_name: string | null
  item_type: string | null
  completed_by: string | null
  photo_url: string | null
  ai_result: { pass: boolean | null; confidence: number; reason: string } | null
  review_status: string
  review_comment: string | null
  completed_at: string | null
}

export interface StoreClosingStatus {
  store_id: string
  store_name: string
  has_active_session: boolean
  session_type: string | null
  session_id: string | null
  session_status: string | null
  total_items: number
  completed_items: number
  started_at: string | null
  last_completed_type: string | null
  last_completed_at: string | null
}

/** 模板更新参数 */
export interface TemplateUpdateParams {
  name?: string
  session_type?: 'opening' | 'closing'
  role_tag?: string
  sort_order?: number
  is_active?: boolean
}

/** 管家看板数据 */
export interface ButlerDashboardData {
  stores: StoreClosingStatus[]
  summary: {
    total_stores: number
    active_sessions: number
    completed_today: number
  }
}

// ==================== 模板 ====================

export function listTemplates(sessionType?: string) {
  const params = sessionType ? { session_type: sessionType } : {}
  return apiClient.get<ApiResponse<ChecklistTemplate[]>>('/butler/templates', { params })
}

export function createTemplateAPI(data: { name: string; session_type: string; role_tag?: string; sort_order?: number }) {
  return apiClient.post<ApiResponse<ChecklistTemplate>>('/butler/templates', data)
}

export function updateTemplateAPI(id: string, data: TemplateUpdateParams) {
  return apiClient.put<ApiResponse<ChecklistTemplate>>(`/butler/templates/${id}`, data)
}

export function deleteTemplateAPI(id: string) {
  return apiClient.delete<ApiResponse<null>>(`/butler/templates/${id}`)
}

export function batchUpdateItems(templateId: string, items: { item_name: string; item_type: string; sort_order?: number; ai_prompt?: string | null }[]) {
  return apiClient.post<ApiResponse<ChecklistItem[]>>(`/butler/templates/${templateId}/items`, { items })
}

// ==================== 会话 ====================

export function startSession(sessionType: 'opening' | 'closing') {
  return apiClient.post<ApiResponse<SessionDetail>>('/butler/sessions', { session_type: sessionType })
}

export function getSession(sessionId: string) {
  return apiClient.get<ApiResponse<SessionDetail>>(`/butler/sessions/${sessionId}`)
}

export function listSessions(params?: { session_type?: string; page?: number; page_size?: number }) {
  return apiClient.get<ApiResponse<PageResult<SessionDetail>>>('/butler/sessions', { params })
}

// ==================== 检查项操作 ====================

export function confirmItem(sessionId: string, resultId: string, comment?: string) {
  return apiClient.post<ApiResponse<ItemResult>>(`/butler/sessions/${sessionId}/items/${resultId}/confirm`, { comment })
}

export function uploadPhoto(sessionId: string, resultId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<ApiResponse<ItemResult>>(`/butler/sessions/${sessionId}/items/${resultId}/photo`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

export function addAdHocItem(sessionId: string, itemName: string, itemType: 'checkbox' | 'photo') {
  return apiClient.post<ApiResponse<ItemResult>>(`/butler/sessions/${sessionId}/items`, { item_name: itemName, item_type: itemType })
}

// ==================== 人工复核 ====================

export function manualReview(sessionId: string, resultId: string, action: 'pass' | 'reject', comment?: string) {
  return apiClient.post<ApiResponse<ItemResult>>(`/butler/sessions/${sessionId}/items/${resultId}/review`, { action, comment })
}

export function resubmitPhoto(sessionId: string, resultId: string, file: File) {
  const formData = new FormData()
  formData.append('file', file)
  return apiClient.post<ApiResponse<ItemResult>>(`/butler/sessions/${sessionId}/items/${resultId}/resubmit`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// ==================== 看板 ====================

export function getDashboard() {
  return apiClient.get<ApiResponse<ButlerDashboardData>>('/butler/dashboard')
}

// ==================== 今日待办状态（首页提醒条用）====================

export interface ButlerTodayStatus {
  has_opening_template: boolean
  has_closing_template: boolean
  opening_done: boolean
  closing_done: boolean
  pending: {
    type: 'opening' | 'closing'
    label: string
    session_id: string | null
    completed: number
    total: number
    assignee_name: string | null
    assignee_id: string | null
    fallback_used: boolean
    fallback_reason: string | null
  }[]
}

export function getTodayStatus() {
  return apiClient.get<ApiResponse<ButlerTodayStatus>>('/butler/today-status')
}

// ==================== 执行人顺位配置 ====================

export interface AssigneeRule {
  rule_id: string
  session_type: 'opening' | 'closing'
  employee_id: string
  employee_name: string
  employee_role: string
  priority: number
  is_active: boolean
}

export interface AssignableEmployee {
  employee_id: string
  name: string
  role: string
}

export function listAssigneeRules(sessionType?: 'opening' | 'closing') {
  const params = sessionType ? { session_type: sessionType } : {}
  return apiClient.get<ApiResponse<AssigneeRule[]>>('/butler/assignee-rules', { params })
}

export function saveAssigneeRules(sessionType: 'opening' | 'closing', items: { employee_id: string; priority: number }[]) {
  return apiClient.post<ApiResponse<AssigneeRule[]>>('/butler/assignee-rules', { session_type: sessionType, items })
}

export function listAssignableEmployees() {
  return apiClient.get<ApiResponse<AssignableEmployee[]>>('/butler/assignee-employees')
}
