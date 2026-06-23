<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import BottomNav from '@/components/BottomNav.vue'

defineProps<{
  title?: string
  showBack?: boolean
}>()

const router = useRouter()
const route = useRoute()

function back() {
  router.back()
}

// 判断是否是 Tab 首页（不需要返回箭头）
function isTabPage(path: string) {
  return ['/daily', '/management', '/settings', '/profile'].some(
    (p) => path === p || path === p + '/'
  )
}
</script>

<template>
  <div class="app-shell">
    <header class="shell-header">
      <div class="header-left">
        <span v-if="showBack || !isTabPage(route.path)" class="back-btn" @click="back">
          <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FFFFFF" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 4l-6 6 6 6"/>
          </svg>
        </span>
      </div>
      <h1 class="shell-title">{{ title }}</h1>
      <div class="header-right">
        <img src="/crush-ip.png" class="header-ip" alt="Crush" />
      </div>
    </header>
    <main class="shell-main">
      <slot />
    </main>
    <BottomNav />
  </div>
</template>

<style scoped lang="scss">
.app-shell {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.shell-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  min-height: 48px;
  /* 毛玻璃效果 */
  background: rgba(17, 17, 17, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  position: sticky;
  top: 0;
  z-index: 10;
}

.header-left {
  width: 40px;
  display: flex;
  align-items: center;
}

.back-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  -webkit-tap-highlight-color: transparent;

  &:active {
    background-color: rgba(255, 255, 255, 0.1);
    transform: scale(0.92);
  }
}

.shell-title {
  font-size: 16px;
  font-weight: 600;
  color: $brand-white;
  margin: 0;
  text-align: center;
  flex: 1;
}

.header-right {
  width: 40px;
  display: flex;
  align-items: center;
  justify-content: flex-end;
}

.header-ip {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  object-fit: contain;
}

.shell-main {
  flex: 1;
  padding-bottom: 88px;
}
</style>
