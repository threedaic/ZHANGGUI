import apiClient from './client'

export interface NotificationItem {
  id: string
  type: string
  title: string
  content: string
  channel: string
  is_read: boolean
  created_at: string | null
}

export interface NotificationSetting {
  id: string
  setting_key: string
  enabled: boolean
  channel: string
  push_to_group: boolean
  target_roles: string[]
  schedule_time: string | null
}

export const notificationAPI = {
  getList(page = 1, page_size = 20) {
    return apiClient.get<{
      code: number
      message: string
      data: { items: NotificationItem[]; total: number; page: number; page_size: number; total_pages: number }
    }>('/notifications', { params: { page, page_size } })
  },

  markRead(id: string) {
    return apiClient.put<{ code: number; message: string; data: { success: boolean } }>(`/notifications/${id}/read`, {})
  },

  markAllRead() {
    return apiClient.put<{ code: number; message: string; data: { count: number } }>('/notifications/read-all', {})
  },

  getUnreadCount() {
    return apiClient.get<{ code: number; message: string; data: { unread_count: number } }>('/notifications/unread-count')
  },

  getSettings() {
    return apiClient.get<{ code: number; message: string; data: NotificationSetting[] }>('/notifications/settings')
  },

  saveSetting(data: NotificationSetting) {
    return apiClient.post<{ code: number; message: string; data: NotificationSetting }>('/notifications/settings', data)
  },
}
