// 工资申诉 API
import client from './client'
import type { ApiResponse } from './types'

// ====== 类型定义 ======

export interface WageDispute {
  dispute_id: string
  wage_id: string
  employee_id?: string
  employee_name?: string
  period: string
  dispute_type: 'less' | 'more' | 'wrong_formula' | 'other'
  original_amount: number | null
  expected_amount: number | null
  reason: string
  evidence?: Record<string, unknown> | null
  status: 'pending' | 'confirmed' | 'rejected' | 'adjusted'
  resolution: string | null
  adjusted_amount: number | null
  adjusted_in_period: string | null
  reviewer_name?: string | null
  reviewed_at: string | null
  created_at: string | null
}

export interface DisputeStats {
  total: number
  pending: number
  confirmed: number
  rejected: number
  adjusted: number
}

// ====== 员工端 API ======

/** 员工提交工资申诉 */
export function createDispute(data: {
  wage_id: string
  dispute_type: string
  expected_amount?: number
  reason: string
  evidence?: Record<string, unknown>
}) {
  return client.post<ApiResponse<{ dispute_id: string }>>('/disputes/', data)
}

/** 员工查看自己的申诉列表 */
export function getMyDisputes() {
  return client.get<ApiResponse<WageDispute[]>>('/disputes/my')
}

// ====== 管理端 API ======

/** 管理端查看所有申诉（收件箱） */
export function getDisputes(status?: string) {
  const params = status ? { status } : {}
  return client.get<ApiResponse<WageDispute[]>>('/disputes/list', { params })
}

/** 查看申诉详情 */
export function getDisputeDetail(disputeId: string) {
  return client.get<ApiResponse<WageDispute>>(`/disputes/${disputeId}`)
}

/** 驳回申诉（老板） */
export function rejectDispute(disputeId: string, resolution: string) {
  return client.put<ApiResponse<null>>(`/disputes/${disputeId}/reject`, { resolution })
}

/** 确认工资有误（老板） */
export function confirmDispute(disputeId: string, data: {
  adjusted_amount: number
  adjusted_in_period?: string
  resolution?: string
}) {
  return client.put<ApiResponse<null>>(`/disputes/${disputeId}/confirm`, data)
}

/** 申诉统计 */
export function getDisputeStats() {
  return client.get<ApiResponse<DisputeStats>>('/disputes/stats/summary')
}
