<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

onMounted(async () => {
  const accessToken = route.query.access_token as string | undefined
  const refreshToken = route.query.refresh_token as string | undefined
  const role = route.query.role as string | undefined
  const error = route.query.error as string | undefined

  // OAuth 失败回调
  if (error) {
    const errorMap: Record<string, string> = {
      config: '门店未配置企微，请联系管理员',
      oauth_fail: '企微授权失败，请重试',
      no_user: '未能获取企微身份，请重试',
      not_found: '企微账号未绑定员工，请联系管理员',
    }
    ElMessage.error(errorMap[error] || `登录失败: ${error}`)
    router.replace('/login')
    return
  }

  // OAuth 成功回调
  if (!accessToken) {
    ElMessage.error('回调参数缺失')
    router.replace('/login')
    return
  }

  // 先存 token，再拉取完整用户信息
  auth.setAuth(accessToken, {
    user_id: null,
    employee_id: null,
    store_id: null,
    role: (role as 'boss' | 'store_manager' | 'staff') || 'staff',
    username: '',
  })

  try {
    await auth.fetchUser()
  } catch {
    // fetchUser 失败不影响登录，用 token 中的信息继续
  }

  ElMessage.success('企微登录成功')
  router.replace('/')
})
</script>

<template>
  <div class="auth-callback">
    <div class="loading-card">
      <div class="spinner"></div>
      <p>正在完成企微登录...</p>
    </div>
  </div>
</template>

<style scoped lang="scss">
.auth-callback {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $color-black;
}

.loading-card {
  text-align: center;
  color: $brand-white;
}

.spinner {
  width: 40px;
  height: 40px;
  margin: 0 auto 16px;
  border: 3px solid rgba(255, 255, 255, 0.1);
  border-top-color: $brand-primary;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
