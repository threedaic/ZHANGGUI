<template>
  <div class="management-page">
    <div class="page-header">
      <h1 class="page-title">管理</h1>
      <span class="page-subtitle">店长工作台</span>
    </div>

    <div class="section-title">排班与人</div>
    <div class="card-grid">
      <button
        v-for="card in peopleCards"
        :key="card.path"
        class="func-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon" v-html="card.icon"></span>
        <span class="card-label">{{ card.label }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </span>
      </button>
    </div>

    <div class="section-title">数据与考核</div>
    <div class="card-grid">
      <button
        v-for="card in dataCards"
        :key="card.path"
        class="func-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon" v-html="card.icon"></span>
        <span class="card-label">{{ card.label }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </span>
      </button>
    </div>

    <div class="section-title">店铺运营</div>
    <div class="card-grid">
      <button
        v-for="card in opsCards"
        :key="card.path"
        class="func-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon" v-html="card.icon"></span>
        <span class="card-label">{{ card.label }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </span>
      </button>
    </div>

    <div class="section-title">风控与日志</div>
    <div class="card-grid">
      <button
        v-for="card in riskCards"
        :key="card.path"
        class="func-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon" v-html="card.icon"></span>
        <span class="card-label">{{ card.label }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

interface FuncCard {
  label: string
  path: string
  icon: string
}

const peopleCards: FuncCard[] = [
  {
    label: '排班考勤',
    path: '/management/schedule-attendance',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="3" y="4" width="22" height="20" rx="3"/><line x1="3" y1="11" x2="25" y2="11"/><line x1="10" y1="11" x2="10" y2="24"/>
    </svg>`,
  },
  {
    label: 'KPI 考核',
    path: '/management/kpi',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M3 25h22"/><rect x="6" y="12" width="5" height="13" rx="1"/><rect x="17" y="5" width="5" height="20" rx="1"/>
    </svg>`,
  },
  {
    label: '工资计算',
    path: '/management/payroll',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="3" y="6" width="22" height="16" rx="3"/><circle cx="14" cy="14" r="4"/><path d="M7 6l7-3 7 3"/>
    </svg>`,
  },
  {
    label: '合同系统',
    path: '/management/contracts',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M5 4h13l5 5v15H5z"/><path d="M18 4v5h5"/><path d="M10 14h8"/><path d="M10 18h8"/>
    </svg>`,
  },
]

const dataCards: FuncCard[] = [
  {
    label: '数据看板',
    path: '/management/dashboard',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="3" y="3" width="10" height="10" rx="2"/><rect x="15" y="3" width="10" height="10" rx="2"/>
      <rect x="3" y="15" width="10" height="10" rx="2"/><rect x="15" y="15" width="10" height="10" rx="2"/>
    </svg>`,
  },
]

const opsCards: FuncCard[] = [
  {
    label: '开闭店管理',
    path: '/management/butler',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="4" y="3" width="18" height="22" rx="2"/><line x1="9" y1="8" x2="17" y2="8"/><line x1="9" y1="13" x2="17" y2="13"/><line x1="9" y1="18" x2="13" y2="18"/>
    </svg>`,
  },
  {
    label: '桌位管理',
    path: '/management/tables',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="4" y="4" width="9" height="9" rx="1"/><rect x="15" y="4" width="9" height="9" rx="1"/><rect x="4" y="15" width="9" height="9" rx="1"/><rect x="15" y="15" width="9" height="9" rx="1"/>
    </svg>`,
  },
  {
    label: '存酒名单',
    path: '/management/wine-inventory',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M9 4h10l2 6H7l2-6z"/><path d="M12 10v10c0 3-4 3-4 0v-10"/><rect x="16" y="10" width="5" height="12" rx="2"/>
    </svg>`,
  },
  {
    label: '打印机配置',
    path: '/management/printer-config',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M7 5h14v8H7z"/><path d="M7 17h14v6H7z"/><rect x="10" y="19" width="8" height="2"/><path d="M10 8h8"/>
    </svg>`,
  },
  {
    label: '处罚通知',
    path: '/management/penalties',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <circle cx="14" cy="14" r="10"/><line x1="14" y1="9" x2="14" y2="14"/><circle cx="14" cy="18" r="0.5" fill="#FB0079"/>
    </svg>`,
  },
  {
    label: '桌面评分码',
    path: '/management/rating',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <polygon points="14 3 17 10 25 11 19 16 21 24 14 20 7 24 9 16 3 11 11 10 14 3"/>
    </svg>`,
  },
]

const riskCards: FuncCard[] = [
  {
    label: '防飞单',
    path: '/management/antifraud',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M14 3l8 5v7c0 6-8 11-8 11S6 21 6 15V8l8-5z"/>
    </svg>`,
  },
  {
    label: '操作日志',
    path: '/management/audit',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M5 5h18v18H5z"/><path d="M9 9h10"/><path d="M9 14h10"/><path d="M9 19h6"/>
    </svg>`,
  },
]
</script>

<style scoped>
.management-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}
.page-subtitle {
  font-size: 12px;
  color: #7A7C80;
}

.section-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #7A7C80;
  margin: 0 0 12px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}

.func-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s ease, box-shadow 0.2s;
  position: relative;
  -webkit-tap-highlight-color: transparent;
}

.func-card:hover {
  border-color: #FB0079;
}

.func-card:active {
  transform: scale(0.96);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.card-label {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 400;
  color: #C8C8C8;
}

.card-arrow {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
}
</style>
