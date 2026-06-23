import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

// ==================== Types ====================

export interface TableItem {
  id: string
  store_id: string
  area: string
  table_no: string
  capacity: number
  status: string
  created_at: string | null
  updated_at: string | null
}

export interface TableCreateParams {
  area?: string
  table_no: string
  capacity?: number
}

export interface TableUpdateParams {
  area?: string
  table_no?: string
  capacity?: number
  status?: string
}

export interface BookingItem {
  id: string
  store_id: string
  customer_name: string
  phone: string
  date: string
  time_slot: string | null
  guests_count: number
  table_id: string | null
  table_no: string | null
  table_area: string | null
  source: string
  status: string
  notes: string | null
  created_by: string | null
  created_by_name: string | null
  created_at: string | null
  updated_at: string | null
}

export interface BookingCreateParams {
  customer_name: string
  phone: string
  date: string
  time_slot?: string
  guests_count?: number
  table_id?: string
  notes?: string
}

export interface BookingUpdateParams {
  time_slot?: string
  guests_count?: number
  table_id?: string | null
  status?: string
  notes?: string
}

export interface BookingStats {
  date: string
  total_tables: number
  booked: number
  free: number
}

// ==================== Table API ====================

export const tableAPI = {
  list(params?: { area?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<TableItem>>>('/tables', { params })
  },

  create(data: TableCreateParams) {
    return apiClient.post<ApiResponse<TableItem>>('/tables', data)
  },

  get(id: string) {
    return apiClient.get<ApiResponse<TableItem>>(`/tables/${id}`)
  },

  update(id: string, data: TableUpdateParams) {
    return apiClient.put<ApiResponse<TableItem>>(`/tables/${id}`, data)
  },

  delete(id: string) {
    return apiClient.delete<ApiResponse<null>>(`/tables/${id}`)
  },
}

// ==================== Booking API ====================

export const bookingAPI = {
  list(params?: { date?: string; status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<BookingItem>>>('/bookings', { params })
  },

  create(data: BookingCreateParams) {
    return apiClient.post<ApiResponse<BookingItem>>('/bookings', data)
  },

  get(id: string) {
    return apiClient.get<ApiResponse<BookingItem>>(`/bookings/${id}`)
  },

  update(id: string, data: BookingUpdateParams) {
    return apiClient.put<ApiResponse<BookingItem>>(`/bookings/${id}`, data)
  },

  cancel(id: string) {
    return apiClient.delete<ApiResponse<BookingItem>>(`/bookings/${id}`)
  },

  stats(date: string) {
    return apiClient.get<ApiResponse<BookingStats>>('/bookings/stats', { params: { date } })
  },
}
