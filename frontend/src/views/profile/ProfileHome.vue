<script setup lang="ts">
// 员工个人中心首页
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const menus = [
  { key: 'my-data', label: '我的数据', desc: 'KPI / 排名 / 业绩 / 工资 一图看清', path: '/profile/my-data', icon: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M3 17h14M5 12h2v5H5zM9 8h2v9H9zM13 4h2v13h-2z"/></svg>` },
  { key: 'my-schedule', label: '我的排班', desc: '查看个人排班表', path: '/profile/my-schedule', icon: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><rect x="2" y="3" width="16" height="14" rx="2"/><line x1="2" y1="8" x2="18" y2="8"/><line x1="6" y1="1" x2="6" y2="4"/><line x1="14" y1="1" x2="14" y2="4"/></svg>` },
  { key: 'my-contract', label: '我的合同', desc: '查看合同信息', path: '/profile/my-contract', icon: `<svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round"><path d="M4 3h9l4 4v10H4z"/><path d="M13 3v4h4"/><line x1="7" y1="10" x2="13" y2="10"/><line x1="7" y1="13" x2="11" y2="13"/></svg>` },
]

function handleLogout() {
  auth.logout()
  router.replace('/login')
}
</script>

<template>
  <div class="profile-home">
    <div class="user-card">
      <div class="avatar">{{ (auth.info.username || '?').charAt(0).toUpperCase() }}</div>
      <div class="info">
        <div class="name">{{ auth.info.username || '员工' }}</div>
        <div class="role">{{ auth.isBoss ? '老板' : auth.isManager ? '店长' : '员工' }}</div>
      </div>
    </div>

    <div class="menu-list">
      <div
        v-for="m in menus"
        :key="m.key"
        class="menu-item"
        @click="router.push(m.path)"
      >
        <div class="menu-left">
          <span class="menu-icon" v-html="m.icon"></span>
          <div>
            <div class="label">{{ m.label }}</div>
            <div class="desc">{{ m.desc }}</div>
          </div>
        </div>
        <span class="arrow">›</span>
      </div>
    </div>

    <button class="logout-btn" @click="handleLogout">退出登录</button>
  </div>
</template>

<style scoped lang="scss">
.profile-home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 16px;
  background-color: $color-bg;
  border-radius: $radius-md;
}

.avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  background-color: $brand-primary;
  color: $brand-white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
}

.info {
  .name {
    font-size: 18px;
    color: $brand-white;
    font-weight: 600;
  }
  .role {
    font-size: 12px;
    color: #888;
    margin-top: 2px;
  }
}

.menu-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.menu-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background-color: $color-bg;
  border-radius: $radius-md;
  cursor: pointer;
  transition: transform 0.15s ease, background-color 0.2s;
  -webkit-tap-highlight-color: transparent;

  &:hover {
    background-color: $color-divider;
  }

  &:active {
    transform: scale(0.98);
  }

  .menu-left {
    display: flex;
    align-items: center;
    gap: 14px;
  }

  .menu-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 36px;
    height: 36px;
    background: rgba(251, 0, 121, 0.08);
    border-radius: 10px;
    flex-shrink: 0;
  }

  .label {
    font-size: 15px;
    color: $brand-white;
  }

  .desc {
    font-size: 12px;
    color: #888;
    margin-top: 2px;
  }

  .arrow {
    font-size: 20px;
    color: #555;
  }
}

.logout-btn {
  margin-top: 8px;
  padding: 14px 16px;
  background-color: $color-bg;
  border: none;
  border-radius: $radius-md;
  color: $brand-primary;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;

  &:hover {
    background-color: $color-divider;
  }
}
</style>
