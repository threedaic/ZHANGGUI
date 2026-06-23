<script setup lang="ts">
// 管理首页（店长入口）
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const menus = [
  { key: 'payroll', label: '工资管理', desc: '月度工资汇总、确认、发放', path: '/management/payroll' },
  { key: 'period', label: '账期管理', desc: '锁定/关账/重新开放', path: '/management/period' },
  { key: 'rankings', label: '员工排行', desc: '业绩/KPI/考勤/评分排名', path: '/management/rankings' },
]
</script>

<template>
  <div class="mgmt-home">
    <div class="welcome">
      <div class="hello">你好，{{ auth.info.username || '店长' }}</div>
      <div class="role-tag">{{ auth.isBoss ? '老板' : '店长' }}</div>
    </div>

    <div class="menu-grid">
      <div
        v-for="m in menus"
        :key="m.key"
        class="menu-card"
        @click="router.push(m.path)"
      >
        <div class="menu-label">{{ m.label }}</div>
        <div class="menu-desc">{{ m.desc }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.mgmt-home {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background-color: $color-bg;
  border-radius: $radius-md;

  .hello {
    font-size: 18px;
    color: $brand-white;
    font-weight: 600;
  }

  .role-tag {
    font-size: 12px;
    color: $brand-primary;
    border: 1px solid $brand-primary;
    padding: 2px 8px;
    border-radius: 10px;
  }
}

.menu-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.menu-card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
  cursor: pointer;
  border: 1px solid $color-divider;

  &:hover {
    border-color: $brand-primary;
  }

  .menu-label {
    font-size: 15px;
    color: $brand-white;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .menu-desc {
    font-size: 12px;
    color: #888;
  }
}
</style>
