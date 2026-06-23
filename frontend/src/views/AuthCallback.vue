<template>
  <div class="callback-loading">
    <div class="spinner"></div>
    <span class="text">登录中...</span>
  </div>
</template>
<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

onMounted(() => {
  // createWebHistory() — 参数在 search，不在 hash
  const params = new URLSearchParams(window.location.search)
  const accessToken = params.get('access_token')
  const role = (params.get('role') || 'staff') as 'boss' | 'store_manager' | 'staff'

  if (accessToken) {
    // 先用 token + role 占位设置，随后 fetchUser 补全完整用户信息
    auth.setAuth(accessToken, {
      user_id: null,
      employee_id: null,
      store_id: null,
      role,
    })
    auth.fetchUser().finally(() => router.replace('/'))
  } else {
    router.replace('/login')
  }
})
</script>
<style scoped>
.callback-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  height: 100vh;
  background: #000;
}

.text {
  color: #7A7C80;
  font-size: 14px;
}

.spinner {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  border: 3px solid rgba(251, 0, 121, 0.15);
  border-top-color: #FB0079;
  border-right-color: #FF68A2;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
