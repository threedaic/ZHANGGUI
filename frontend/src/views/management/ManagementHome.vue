<script setup lang="ts">
// 管理首页（店长入口）
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const auth = useAuthStore()

const menus = [
  // 排班与人
  { key: 'schedule', label: '排班管理', desc: '排班表、一键排班、周模板', path: '/management/schedule' },
  { key: 'attendance', label: '考勤管理', desc: '打卡记录、到岗统计、打卡设置', path: '/management/attendance' },
  { key: 'kpi', label: 'KPI考核', desc: '模板、评分、申诉', path: '/management/kpi' },
  { key: 'rankings', label: '员工排行', desc: '业绩/KPI/考勤/评分排名', path: '/management/rankings' },
  // 工资与账期
  { key: 'payroll', label: '工资管理', desc: '月度工资汇总、确认、发放', path: '/management/payroll' },
  { key: 'period', label: '账期管理', desc: '锁定/关账/重新开放', path: '/management/period' },
  // 数据与风控
  { key: 'dashboard', label: '数据看板', desc: '营收、考勤、预订总览', path: '/management/dashboard' },
  { key: 'antifraud', label: '防飞单', desc: '飞单检测与处理', path: '/management/antifraud' },
  { key: 'audit', label: '操作日志', desc: '系统操作审计', path: '/management/audit' },
  // 店铺运营
  { key: 'tables', label: '桌位管理', desc: '桌台状态、开台/关台', path: '/management/tables' },
  { key: 'wine', label: '存酒盘点', desc: '库存、盘点、酒水台账', path: '/management/wine-inventory' },
  { key: 'rating', label: '评分管理', desc: '桌面评分码、评分统计', path: '/management/rating' },
  { key: 'contracts', label: '合同管理', desc: '员工合同、到期提醒', path: '/management/contracts' },
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
