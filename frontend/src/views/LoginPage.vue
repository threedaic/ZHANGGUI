<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { login, getWeworkOAuthConfig } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const form = reactive({
  username: '',
  password: '',
})
const loading = ref(false)
const showPasswordForm = ref(false)

/** 检测是否在企微内置浏览器中 */
function detectWeworkBrowser(): boolean {
  const ua = navigator.userAgent
  return ua.includes('wxwork') || ua.includes('MicroMessenger')
}

/** 发起企微 OAuth 跳转 */
async function startWeworkOAuth() {
  try {
    const res = await getWeworkOAuthConfig()
    const cfg = res.data.data
    if (!cfg?.corp_id || !cfg?.agent_id) {
      // 企微未配置，自动降级到密码登录
      showPasswordForm.value = true
      return
    }
    const redirectUri = encodeURIComponent(`${window.location.origin}/api/v1/auth/wework/login`)
    const oauthUrl =
      `https://open.weixin.qq.com/connect/oauth2/authorize` +
      `?appid=${cfg.corp_id}` +
      `&redirect_uri=${redirectUri}` +
      `&response_type=code` +
      `&scope=snsapi_base` +
      `&agentid=${cfg.agent_id}` +
      `&state=crush` +
      `#wechat_redirect`
    window.location.href = oauthUrl
  } catch {
    showPasswordForm.value = true
  }
}

onMounted(() => {
  // 企微浏览器自动跳转，普通浏览器显示企微登录按钮
  if (detectWeworkBrowser()) {
    startWeworkOAuth()
  }
})

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

      <!-- 默认：企微登录（主按钮） -->
      <template v-if="!showPasswordForm">
        <button class="btn-wework btn-main" @click="startWeworkOAuth">
          企微免密登录
        </button>
        <div class="divider">
          <span>或</span>
        </div>
        <button class="btn-link" @click="showPasswordForm = true">
          使用密码登录
        </button>
      </template>

      <!-- 备选：密码登录 -->
      <template v-else>
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
        <div class="divider">
          <span>或</span>
        </div>
        <button class="btn-wework" @click="startWeworkOAuth">
          企微免密登录
        </button>
      </template>
    </div>
  </div>
</template>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: $color-black;
  background-image:
    radial-gradient(circle at 50% 30%, rgba(251, 0, 121, 0.18) 0%, transparent 55%),
    radial-gradient(circle at 80% 80%, rgba(251, 0, 121, 0.08) 0%, transparent 40%);
  padding: 20px;
}

.login-card {
  width: 100%;
  max-width: 360px;
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: $radius-lg;
  padding: 40px 24px;
  text-align: center;
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
  box-shadow: 0 4px 16px rgba(251, 0, 121, 0.35);
  transition: box-shadow 0.2s, transform 0.15s ease;
  -webkit-tap-highlight-color: transparent;

  &:active {
    transform: scale(0.97);
    box-shadow: 0 2px 8px rgba(251, 0, 121, 0.25);
  }
}

.divider {
  display: flex;
  align-items: center;
  margin: 20px 0;
  color: #666;
  font-size: 12px;

  &::before,
  &::after {
    content: '';
    flex: 1;
    height: 1px;
    background: $color-divider;
  }

  span {
    padding: 0 12px;
  }
}

.btn-wework {
  width: 100%;
  height: 44px;
  background: #07c160;
  color: #fff;
  border: none;
  border-radius: $radius-sm;
  font-size: 15px;
  cursor: pointer;
  transition: opacity 0.2s;
  -webkit-tap-highlight-color: transparent;

  &:active {
    opacity: 0.85;
  }

  &.btn-main {
    height: 48px;
    font-size: 16px;
    font-weight: 600;
    box-shadow: 0 4px 16px rgba(7, 193, 96, 0.35);
  }
}

.btn-link {
  background: none;
  border: none;
  color: #888;
  font-size: 13px;
  cursor: pointer;
  padding: 8px;
  text-decoration: underline;
  text-underline-offset: 2px;

  &:active {
    color: #aaa;
  }
}
</style>
