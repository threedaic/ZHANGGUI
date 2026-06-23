import apiClient from './client'

export interface ChatRequest {
  message: string
  conversation_id?: string | null
}

export interface ChatResponse {
  reply: string
  conversation_id: string
  sql: string | null
}

export interface AIConfig {
  ai_api_url: string | null
  ai_api_key_masked: string | null
  ai_model: string | null
  ai_temperature: number
}

export interface AIConfigUpdate {
  ai_api_url?: string | null
  ai_api_key?: string | null
  ai_model?: string | null
  ai_temperature?: number | null
}

export const aiAPI = {
  /** 发送聊天消息 */
  chat(data: ChatRequest) {
    return apiClient.post<{ code: number; message: string; data: ChatResponse }>('/ai/chat', data)
  },

  /** 获取 AI 配置（key 脱敏） */
  getConfig() {
    return apiClient.get<{ code: number; message: string; data: AIConfig }>('/ai/config')
  },

  /** 更新 AI 配置 */
  updateConfig(data: AIConfigUpdate) {
    return apiClient.put<{ code: number; message: string; data: Record<string, unknown> }>('/ai/config', data)
  },
}
