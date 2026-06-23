// 认证 API
import client from './client'
import type { ApiResponse } from './types'
import type { UserInfo } from '@/stores/auth'

export interface LoginRequest {
  username: string
  password: string
}

export interface LoginResponse {
  access_token: string
  token_type: string
  user: {
    user_id: string
    username: string
    role: string
    store_id: string | null
    employee_id: string | null
    must_change_password: boolean
  }
}

export function login(body: LoginRequest) {
  return client.post<ApiResponse<LoginResponse>>('/auth/login', body)
}

export function getCurrentUser() {
  return client.get<ApiResponse<UserInfo>>('/auth/me')
}
