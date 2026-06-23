<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})
const loading = ref(false)

async function onSubmit() {
  if (!form.username || !form.password) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await login(form)
    const data = res.data.data
    auth.setAuth(data.access_token, {
      user_id: data.user.user_id,
      employee_id: data.user.employee_id,
      store_id: data.user.store_id,
      role: data.user.role as 'boss' | 'store_manager' | 'staff',
      username: data.user.username,
    })
    ElMessage.success('登录成功')
    router.push('/')
  } catch (e) {
    /* 错误已在拦截器处理 */
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <div class="login-card">
      <h1 class="brand">Crush 掌柜</h1>
      <p class="subtitle">酒吧管理平台</p>

      <div class="form-group">
        <input
          v-model="form.username"
          type="text"
          placeholder="用户名"
          class="input"
          @keyup.enter="onSubmit"
        />
      </div>
      <div class="form-group">
        <input
          v-model="form.password"
          type="password"
          placeholder="密码"
          class="input"
          @keyup.enter="onSubmit"
        />
      </div>
      <button class="btn-primary login-btn" :disabled="loading" @click="onSubmit">
        {{ loading ? '登录中...' : '登录' }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  /* 背景：黑色底 + 主色径向渐变光晕，让毛玻璃有内容可透 */
  background-color: $color-black;
  background-image:
    radial-gradient(circle at 50% 30%, rgba(251, 0, 121, 0.18) 0%, transparent 55%),
    radial-gradient(circle at 80% 80%, rgba(251, 0, 121, 0.08) 0%, transparent 40%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 360px;
  /* 毛玻璃效果 */
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: $radius-lg;
  padding: 40px 24px;
  text-align: center;
  /* 主色辉光 */
  box-shadow: 0 8px 40px rgba(251, 0, 121, 0.15);
}

.brand {
  font-size: 28px;
  font-weight: 700;
  color: $brand-primary;
  margin: 0 0 8px;
  text-shadow: 0 0 12px rgba(251, 0, 121, 0.5);
}

.subtitle {
  color: #888;
  font-size: 13px;
  margin: 0 0 32px;
}

.form-group {
  margin-bottom: 16px;
}

.input {
  width: 100%;
  height: 44px;
  background-color: rgba(0, 0, 0, 0.4);
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 0 14px;
  color: $brand-white;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus {
    border-color: $brand-primary;
    box-shadow: 0 0 0 2px rgba(251, 0, 121, 0.15);
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  margin-top: 8px;
  font-size: 15px;
  /* 按钮辉光 */
  box-shadow: 0 4px 16px rgba(251, 0, 121, 0.35);
  transition: box-shadow 0.2s, transform 0.15s ease;
  -webkit-tap-highlight-color: transparent;

  &:active {
    transform: scale(0.97);
    box-shadow: 0 2px 8px rgba(251, 0, 121, 0.25);
  }
}
</style>
