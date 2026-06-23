<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()

const icons: Record<string, string> = {
  daily: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <rect x="3" y="4" width="16" height="15" rx="2"/><line x1="3" y1="9" x2="19" y2="9"/><line x1="8" y1="2" x2="8" y2="5"/><line x1="14" y1="2" x2="14" y2="5"/>
  </svg>`,
  management: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <rect x="2" y="7" width="18" height="12" rx="2"/><path d="M14 7V5a3 3 0 0 0-6 0v2"/><line x1="11" y1="11" x2="11" y2="15"/>
  </svg>`,
  settings: `<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
    <path d="M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"/>
  </svg>`,
  profile: `<svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
    <circle cx="11" cy="7" r="4"/><path d="M3 20c0-4.4 3.6-7 8-7s8 2.6 8 7"/>
  </svg>`,
}

// SPEC 2.0 §5.4 角色权限：日常/我的=全员，管理=店长及以上，设置=boss/admin
const ALL_ROLES = ['admin', 'boss', 'store_manager', 'accountant', 'bar_manager', 'service_manager', 'kitchen_manager', 'staff']
const MANAGER_ROLES = ['admin', 'boss', 'store_manager', 'accountant', 'bar_manager', 'service_manager', 'kitchen_manager']

const tabs = computed(() => {
  const list = [
    { key: 'daily', label: '日常', path: '/daily', roles: ALL_ROLES },
    { key: 'management', label: '管理', path: '/management', roles: MANAGER_ROLES },
    { key: 'settings', label: '设置', path: '/settings', roles: ['boss', 'admin'] },
    { key: 'profile', label: '我的', path: '/profile', roles: ALL_ROLES },
  ]
  return list.filter((t) => t.roles.includes(auth.role))
})

const activeKey = computed(() => {
  const path = route.path
  if (path.startsWith('/daily')) return 'daily'
  if (path.startsWith('/management')) return 'management'
  if (path.startsWith('/settings')) return 'settings'
  if (path.startsWith('/profile')) return 'profile'
  return ''
})

function go(path: string) {
  router.push(path)
}
</script>

<template>
  <nav class="bottom-nav">
    <div
      v-for="tab in tabs"
      :key="tab.key"
      class="nav-item"
      :class="{ active: activeKey === tab.key }"
      @click="go(tab.path)"
    >
      <span class="nav-icon" v-html="icons[tab.key]"></span>
      <span class="nav-label">{{ tab.label }}</span>
    </div>
  </nav>
</template>

<style scoped lang="scss">
.bottom-nav {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: 64px;
  /* 毛玻璃效果 */
  background: rgba(17, 17, 17, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  display: flex;
  align-items: center;
  z-index: 100;
  padding-bottom: env(safe-area-inset-bottom, 0);
}

.nav-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  color: #666;
  transition: color 0.2s ease;
  position: relative;
  -webkit-tap-highlight-color: transparent;

  .nav-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 56px;
    height: 32px;
    border-radius: 16px;
    transition: background-color 0.25s ease, color 0.25s ease;
  }

  .nav-label {
    font-size: 11px;
    color: #888;
    transition: color 0.25s ease, font-weight 0.25s ease;
    letter-spacing: 0.2px;
  }

  &.active {
    color: $brand-primary;

    .nav-icon {
      background-color: rgba(251, 0, 121, 0.15);
      color: $brand-primary;
    }

    .nav-label {
      color: $brand-primary;
      font-weight: 600;
    }
  }

  &:active {
    transform: scale(0.92);
    transition: transform 0.1s ease;
  }
}
</style>
