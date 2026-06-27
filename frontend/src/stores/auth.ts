import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getCurrentUser } from '@/api/auth'

export type UserRole = 'system_admin' | 'admin' | 'boss' | 'store_manager' | 'accountant' | 'bar_manager' | 'service_manager' | 'kitchen_manager' | 'staff'

export interface UserInfo {
  user_id: string | null
  employee_id: string | null
  store_id: string | null
  role: UserRole
  username?: string
}

const STORAGE_KEY = 'crush_auth'

function loadFromStorage(): UserInfo {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw) return JSON.parse(raw) as UserInfo
  } catch (e) {
    /* ignore */
  }
  return {
    user_id: null,
    employee_id: null,
    store_id: null,
    role: 'staff',
  }
}

export const useAuthStore = defineStore('auth', () => {
  const info = ref<UserInfo>(loadFromStorage())
  const token = ref<string>(localStorage.getItem('crush_token') || '')

  const isLoggedIn = computed(() => !!token.value)
  const role = computed(() => info.value.role)
  const isBoss = computed(() => info.value.role === 'boss' || info.value.role === 'system_admin' || info.value.role === 'admin')
  const isSystemAdmin = computed(() => info.value.role === 'system_admin')
  const isManager = computed(() =>
    ['system_admin', 'admin', 'boss', 'store_manager', 'accountant', 'bar_manager', 'service_manager', 'kitchen_manager'].includes(info.value.role)
  )

  function setAuth(t: string, payload: UserInfo) {
    token.value = t
    info.value = payload
    localStorage.setItem('crush_token', t)
    localStorage.setItem(STORAGE_KEY, JSON.stringify(payload))
  }

  // 拉取当前用户信息（用于 OAuth 回调等场景）
  async function fetchUser() {
    const res = await getCurrentUser()
    const data = res.data.data
    info.value = {
      user_id: data.user_id,
      employee_id: data.employee_id,
      store_id: data.store_id,
      role: (data.role as UserRole) || 'staff',
      username: data.username,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(info.value))
  }

  function logout() {
    token.value = ''
    info.value = {
      user_id: null,
      employee_id: null,
      store_id: null,
      role: 'staff',
    }
    localStorage.removeItem('crush_token')
    localStorage.removeItem(STORAGE_KEY)
  }

  return {
    info,
    token,
    isLoggedIn,
    role,
    isBoss,
    isSystemAdmin,
    isManager,
    setAuth,
    fetchUser,
    logout,
  }
})
