import apiClient from './client'
import type { ApiResponse } from './types'

export interface HQStore {
  id: string
  name: string
  store_code: string
  city: string | null
  address: string | null
  status: string
  opened_at: string | null
  employee_count: number
  today_revenue: number
  wework_department_id: number | null
  wework_status: string | null
}

export interface HQDashboard {
  store_count: number
  employee_count: number
  today_revenue: number
  yesterday_revenue: number
  growth_rate: number
  chart: { date: string; revenue: number }[]
  store_breakdown: {
    store_id: string
    store_name: string
    today_revenue: number
    employee_count: number
  }[]
}

export interface HQEmployee {
  id: string
  name: string
  role: string
  store_id: string | null
  store_name: string
  status: string
  phone: string | null
}

export interface StoreCreateBody {
  store_code: string
  name: string
  city?: string
  address?: string
  wework_department_id?: number
}

export interface GlobalAIConfig {
  chat_api_url: string | null
  chat_api_key_masked: string | null
  chat_model: string | null
  chat_temperature: number
  vision_api_url: string | null
  vision_api_key_masked: string | null
  vision_model: string | null
  vision_temperature: number
}

export interface GlobalAIConfigUpdate {
  chat_api_url?: string | null
  chat_api_key?: string | null
  chat_model?: string | null
  chat_temperature?: number | null
  vision_api_url?: string | null
  vision_api_key?: string | null
  vision_model?: string | null
  vision_temperature?: number | null
}

export const hqAPI = {
  getStores() {
    return apiClient.get<ApiResponse<HQStore[]>>('/hq/stores')
  },
  createStore(data: StoreCreateBody) {
    return apiClient.post<ApiResponse<any>>('/hq/stores', data)
  },
  getDashboard() {
    return apiClient.get<ApiResponse<HQDashboard>>('/hq/dashboard')
  },
  getEmployees() {
    return apiClient.get<ApiResponse<HQEmployee[]>>('/hq/employees')
  },
  getGlobalAIConfig() {
    return apiClient.get<ApiResponse<GlobalAIConfig>>('/hq/ai-config')
  },
  updateGlobalAIConfig(data: GlobalAIConfigUpdate) {
    return apiClient.put<ApiResponse<any>>('/hq/ai-config', data)
  },
}
