// 账期管理 API
import client from './client'
import type { ApiResponse } from './types'

export type PeriodStatus = 'open' | 'locked' | 'closed'

export interface PeriodInfo {
  period: string
  status: PeriodStatus
  locked_at: string | null
  locked_by: number | null
  closed_at: string | null
  closed_by: number | null
  note: string | null
  message?: string
}

export function getPeriod(period: string) {
  return client.get<ApiResponse<PeriodInfo>>(`/periods/${period}`)
}

export function lockPeriod(period: string) {
  return client.post<ApiResponse<{ period: string; status: PeriodStatus }>>(
    `/periods/${period}/lock`
  )
}

export function closePeriod(period: string) {
  return client.post<ApiResponse<{ period: string; status: PeriodStatus }>>(
    `/periods/${period}/close`
  )
}

export function reopenPeriod(period: string) {
  return client.post<ApiResponse<{ period: string; status: PeriodStatus }>>(
    `/periods/${period}/reopen`
  )
}
