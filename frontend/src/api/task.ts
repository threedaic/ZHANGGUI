import apiClient from './client'
import type { ApiResponse } from './types'

// ===================== Types =====================

export interface TaskItem {
  id: string
  store_id: string
  title: string
  description: string
  priority: string
  priority_label: string
  status: string
  status_label: string
  task_type: string
  task_type_label: string
  created_by: string
  created_by_name: string
  assignee_id: string | null
  assignee_name: string | null
  due_date: string | null
  template_id: string | null
  created_at: string | null
  updated_at: string | null
  completed_at: string | null
  attachments_count: number
  require_photo: boolean
  require_note: boolean
  requirements: string | null
  completion_note: string | null
}

export interface TaskDetail extends TaskItem {
  attachments: Attachment[]
}

export interface Attachment {
  id: string
  file_url: string
  file_name: string | null
  file_size: number | null
  stage: string
  uploaded_by: string
  created_at: string | null
}

export interface TemplateItem {
  id: string
  title: string
  description: string
  priority: string
  assignee_id: string
  assignee_name: string
  due_time: string | null
  recurrence_type: string
  recurrence_type_label: string
  recurrence_rule: Record<string, unknown>
  enabled: boolean
  created_at: string | null
  last_generated_at: string | null
}

export interface EmployeeOption {
  id: string
  name: string
  role: string
  role_label: string
}

export interface TaskCreateData {
  title: string
  description?: string
  priority?: 'high' | 'medium' | 'low'
  task_type: 'direct' | 'pool'
  assignee_id?: string | null
  due_date?: string | null
  require_photo?: boolean
  require_note?: boolean
  requirements?: string | null
}

export interface TemplateCreateData {
  title: string
  description?: string
  priority?: string
  assignee_id: string
  due_time?: string | null
  recurrence_type: 'daily' | 'weekly' | 'monthly'
  recurrence_rule?: Record<string, unknown>
  require_photo?: boolean
  require_note?: boolean
  requirements?: string | null
}

export interface TaskListResponse {
  items: TaskItem[]
  total: number
  page: number
  page_size: number
}

// ===================== API =====================

export const taskAPI = {
  // 任务列表
  list(params?: { status?: string; task_type?: string; priority?: string; assignee_id?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<TaskListResponse>>('/tasks', { params })
  },

  // 我的任务
  myTasks(params?: { status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<TaskListResponse>>('/tasks/my', { params })
  },

  // 认领池
  pool(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<TaskListResponse>>('/tasks/pool', { params })
  },

  // 任务详情
  get(taskId: string) {
    return apiClient.get<ApiResponse<TaskDetail>>(`/tasks/${taskId}`)
  },

  // 创建任务
  create(data: TaskCreateData) {
    return apiClient.post<ApiResponse<TaskItem>>('/tasks', data)
  },

  // 编辑任务
  update(taskId: string, data: Partial<TaskCreateData>) {
    return apiClient.patch<ApiResponse<TaskItem>>(`/tasks/${taskId}`, data)
  },

  // 更新状态
  updateStatus(taskId: string, status: string, completionNote?: string) {
    const payload: Record<string, unknown> = { status }
    if (completionNote !== undefined) {
      payload.completion_note = completionNote
    }
    return apiClient.patch<ApiResponse<TaskItem>>(`/tasks/${taskId}/status`, payload)
  },

  // 认领
  claim(taskId: string) {
    return apiClient.post<ApiResponse<TaskItem>>(`/tasks/${taskId}/claim`)
  },

  // 上传附件
  uploadAttachment(taskId: string, file: File, stage: string = 'progress') {
    const form = new FormData()
    form.append('file', file)
    form.append('stage', stage)
    return apiClient.post<ApiResponse<{ id: string; file_url: string }>>(
      `/tasks/${taskId}/attachments`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    )
  },

  // 获取附件
  getAttachments(taskId: string) {
    return apiClient.get<ApiResponse<Attachment[]>>(`/tasks/${taskId}/attachments`)
  },

  // 删除附件
  deleteAttachment(taskId: string, attId: string) {
    return apiClient.delete<ApiResponse<null>>(`/tasks/${taskId}/attachments/${attId}`)
  },

  // ===================== 模板 =====================

  listTemplates() {
    return apiClient.get<ApiResponse<TemplateItem[]>>('/tasks/templates')
  },

  createTemplate(data: TemplateCreateData) {
    return apiClient.post<ApiResponse<{ id: string }>>('/tasks/templates', data)
  },

  updateTemplate(templateId: string, data: Partial<TemplateCreateData>) {
    return apiClient.patch<ApiResponse<null>>(`/tasks/templates/${templateId}`, data)
  },

  toggleTemplate(templateId: string) {
    return apiClient.patch<ApiResponse<null>>(`/tasks/templates/${templateId}/toggle`)
  },

  deleteTemplate(templateId: string) {
    return apiClient.delete<ApiResponse<null>>(`/tasks/templates/${templateId}`)
  },

  // ===================== 员工 =====================

  listEmployees() {
    return apiClient.get<ApiResponse<EmployeeOption[]>>('/tasks/employees')
  },
}
