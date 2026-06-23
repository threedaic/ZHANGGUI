// 员工排名 API
import client from './client'
import type { ApiResponse } from './types'

export type RankType = 'performance' | 'kpi' | 'attendance' | 'rating'

export const RANK_TYPE_LABELS: Record<RankType, string> = {
  performance: '业绩排名',
  kpi: 'KPI排名',
  attendance: '考勤排名',
  rating: '评分排名',
}

export interface LeaderboardItem {
  rank_position: number
  employee_id: string
  employee_name: string
  rank_value: number
  detail: Record<string, unknown>
}

export interface Leaderboard {
  period: string
  rank_type: RankType
  items: LeaderboardItem[]
}

export interface MyRanking {
  rank_type: RankType
  rank_position: number
  total_count: number
  rank_value: number
  detail: Record<string, unknown>
}

export interface CalculateResult {
  period: string
  total: number
  by_type: Record<string, number>
  rank_types: RankType[]
}

export function getLeaderboard(
  period: string,
  rank_type: RankType,
  limit = 50
) {
  return client.get<ApiResponse<Leaderboard>>('/rankings/leaderboard', {
    params: { period, rank_type, limit },
  })
}

export function calculateRankings(period: string, rank_type?: RankType) {
  return client.post<ApiResponse<CalculateResult>>('/rankings/calculate', null, {
    params: { period, rank_type: rank_type ?? undefined },
  })
}

export function getMyRankings(period: string) {
  return client.get<ApiResponse<MyRanking[]>>('/rankings/my', {
    params: { period },
  })
}
