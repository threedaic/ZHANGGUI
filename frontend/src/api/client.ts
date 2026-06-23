// 统一 axios 封装：处理 token 注入、业务错误码、401 跳登录
import axios, { type AxiosInstance, type InternalAxiosRequestConfig } from 'axios'
import { ElMessage } from 'element-plus'
import { ERROR_CODES, type ApiResponse } from './types'
import { useAuthStore } from '@/stores/auth'
import router from '@/router'

const client: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 15000,
})

// 请求拦截：注入 JWT
client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const auth = useAuthStore()
  if (auth.token) {
    config.headers.Authorization = `Bearer ${auth.token}`
  }
  return config
})

// 响应拦截：统一处理业务错误码
// 注意：必须返回 response（AxiosResponse），调用方通过 res.data.data 取业务数据
client.interceptors.response.use(
  (response) => {
    const data = response.data as ApiResponse
    if (data.code !== ERROR_CODES.SUCCESS) {
      ElMessage.error(data.message || '请求失败')
      if (data.code === ERROR_CODES.UNAUTHORIZED) {
        const auth = useAuthStore()
        auth.logout()
        router.push({ name: 'Login' })
      }
      return Promise.reject(data)
    }
    return response
  },
  (error) => {
    if (error.response?.status === 401) {
      const auth = useAuthStore()
      auth.logout()
      router.push({ name: 'Login' })
    }
    const msg = error.response?.data?.message || error.message || '网络异常'
    ElMessage.error(msg)
    return Promise.reject(error)
  }
)

export default client
