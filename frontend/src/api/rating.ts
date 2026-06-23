import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

export interface RatingCreate {
  store_id: string
  table_no: string
  food_quality: number
  food_speed: number
  drink_quality: number
  drink_speed: number
  service_attitude: number
  service_speed: number
  cleanliness: number
  comment?: string
  source?: string
}

export interface RatingItem {
  id: string
  store_id: string
  table_no: string
  food_quality: number | null
  food_speed: number | null
  drink_quality: number | null
  drink_speed: number | null
  service_attitude: number | null
  service_speed: number | null
  cleanliness: number | null
  overall_score: number
  comment: string | null
  is_low_score: boolean
  notified: boolean
  store_response: string | null
  created_at: string
}

export interface RatingSummary {
  total_count: number
  avg_overall: number
  low_score_count: number
  dimension_scores: Record<string, number>
}

export function submitRating(data: RatingCreate) {
  return apiClient.post<ApiResponse<RatingItem>>('/ratings', data)
}

export function getRatings(page = 1, pageSize = 20) {
  return apiClient.get<ApiResponse<PageResult<RatingItem>>>('/ratings', {
    params: { page, page_size: pageSize },
  })
}

export function getRatingSummary() {
  return apiClient.get<ApiResponse<RatingSummary>>('/ratings/summary')
}

export function getRatingAlerts() {
  return apiClient.get<ApiResponse<RatingItem[]>>('/ratings/alerts')
}

export function respondToRating(id: string, responseText: string) {
  return apiClient.put<ApiResponse<RatingItem>>(`/ratings/${id}/respond`, null, {
    params: { response_text: responseText },
  })
}
