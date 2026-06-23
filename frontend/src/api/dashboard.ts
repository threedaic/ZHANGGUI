import apiClient from './client'
import type { ApiResponse } from './types'

export interface RevenueBlock {
  today_revenue: number
  yesterday_revenue: number
  growth_rate: number
  total_orders: number
  total_guests: number
  avg_order_value: number
}

export interface RevenueBreakdown {
  bottle_sales: number
  card_sales: number
  other_sales: number
  total: number
  bottle_pct: number
  card_pct: number
  other_pct: number
}

export interface ChartPoint {
  date: string
  weekday: string
  revenue: number
  orders: number
}

export interface LowScoreAlert {
  id: string
  table_no: string
  overall_score: number
  comment: string
  created_at: string
}

export interface RatingSummary {
  avg_score: number
  total_ratings: number
  low_score_count: number
  alerts: LowScoreAlert[]
}

export interface BookingSummary {
  confirmed: number
  total_tables: number
  available: number
}

export interface AttendanceSummary {
  scheduled_count: number
  actual_count: number
  late_count: number
  absent_count: number
  early_count: number
  leave_count: number
}

export interface MyPerformance {
  total_wework_pay: number
  period: string
}

export interface DashboardData {
  revenue: RevenueBlock
  breakdown: RevenueBreakdown
  chart: ChartPoint[]
  rating: RatingSummary
  booking: BookingSummary
  attendance: AttendanceSummary
  my_performance: MyPerformance
  updated_at: string
}

export const dashboardAPI = {
  getDashboard() {
    return apiClient.get<ApiResponse<DashboardData>>('/dashboard')
  },
}
