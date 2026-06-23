import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

export interface ApprovalItem {
  id: string
  employee_id: string
  employee_name: string
  type: string
  type_label: string
  status: string
  start_date: string | null
  end_date: string | null
  reason: string | null
  extra: Record<string, unknown> | null
  approver_id: string | null
  approver_name: string | null
  reject_reason: string | null
  created_at: string | null
}

export interface ApprovalCreateData {
  type: 'leave' | 'makeup' | 'swap' | 'expense'
  start_date?: string
  end_date?: string
  reason: string
  extra?: Record<string, unknown>
  approver_id?: string | null
}

export interface LeaveType {
  label: string
  default_days: number
}

export interface LeaveBalanceItem {
  leave_type: string
  label: string
  total_days: number
  used_days: number
  remaining_days: number
}

export interface ApproverOption {
  id: string
  name: string
  role: string
}

export interface PendingCount {
  total_pending: number
  assigned_to_me: number
}

export const approvalAPI = {
  getList(params?: { status?: string; type?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<ApprovalItem>>>('/approvals', { params })
  },

  create(data: ApprovalCreateData) {
    return apiClient.post<ApiResponse<ApprovalItem>>('/approvals', data)
  },

  getDetail(id: string) {
    return apiClient.get<ApiResponse<ApprovalItem>>(`/approvals/${id}`)
  },

  approve(id: string) {
    return apiClient.put<ApiResponse<ApprovalItem>>(`/approvals/${id}/approve`, {})
  },

  reject(id: string, reason?: string) {
    return apiClient.put<ApiResponse<ApprovalItem>>(`/approvals/${id}/reject`, { action: 'rejected', reason: reason || null })
  },

  getLeaveTypes() {
    return apiClient.get<ApiResponse<{ types: Record<string, LeaveType> }>>('/approvals/leave-types')
  },

  getMyLeaveBalance(year?: number) {
    return apiClient.get<ApiResponse<{ year: number; balances: LeaveBalanceItem[] }>>('/approvals/leave-balance', { params: { year } })
  },

  getEmployeeLeaveBalance(employeeId: string, year?: number) {
    return apiClient.get<ApiResponse<{ year: number; balances: LeaveBalanceItem[] }>>(`/approvals/leave-balance/${employeeId}`, { params: { year } })
  },

  updateLeaveBalance(employeeId: string, leaveType: string, totalDays: number, year?: number) {
    return apiClient.put<ApiResponse<null>>(`/approvals/leave-balance/${employeeId}/${leaveType}`, null, { params: { total_days: totalDays, year } })
  },

  /** 待我审批数量（店长/老板） */
  getPendingCount() {
    return apiClient.get<ApiResponse<PendingCount>>('/approvals/pending-count')
  },

  /** 可指定的审批人列表 */
  listApprovers() {
    return apiClient.get<ApiResponse<ApproverOption[]>>('/approvals/approvers')
  },

  /** 上传报销附件图片 */
  uploadImage(file: File) {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post<ApiResponse<{ url: string }>>('/approvals/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
}
