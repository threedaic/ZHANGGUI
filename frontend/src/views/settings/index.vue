<template>
  <div class="settings-page">
    <div class="page-header">
      <h1 class="page-title">设置</h1>
      <span class="page-subtitle">老板配置核心参数</span>
    </div>

    <div class="category-list">
      <button
        v-for="cat in categories"
        :key="cat.key"
        class="category-card"
        @click="router.push({ path: '/settings/category/' + cat.key, query: { cat: cat.key } })"
      >
        <div class="cat-left">
          <span class="cat-icon" v-html="cat.icon"></span>
          <div class="cat-text">
            <span class="cat-name">{{ cat.title }}</span>
            <span class="cat-desc">服务：{{ cat.target }} | {{ cat.builtCount }}/{{ cat.totalCount }} 项已配置</span>
          </div>
        </div>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

interface CategoryDef {
  key: string
  title: string
  target: string
  builtCount: number
  totalCount: number
  icon: string
}

const categories: CategoryDef[] = [
  {
    key: 'store',
    title: '店铺管理',
    target: '店铺',
    builtCount: 3,
    totalCount: 3,
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M3 21h18"/><path d="M5 21V11l7-7 7 7v10"/>
    </svg>`,
  },
  {
    key: 'employee',
    title: '员工管理',
    target: '员工',
    builtCount: 3,
    totalCount: 3,
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <circle cx="12" cy="8" r="4"/><path d="M4 21c0-5 4-8 8-8s8 3 8 8"/>
    </svg>`,
  },
  {
    key: 'business',
    title: '经营管理',
    target: '客人',
    builtCount: 5,
    totalCount: 5,
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
    </svg>`,
  },
  {
    key: 'system',
    title: '系统设置',
    target: '系统',
    builtCount: 2,
    totalCount: 4,
    icon: `<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <circle cx="12" cy="12" r="3"/><path d="M12 2v3"/><path d="M12 19v3"/><path d="M2 12h3"/><path d="M19 12h3"/><path d="M4.9 4.9l2.1 2.1"/><path d="M16.9 16.9l2.1 2.1"/><path d="M4.9 19.1l2.1-2.1"/><path d="M16.9 7.1l2.1-2.1"/>
    </svg>`,
  },
]
</script>

<style scoped>
.settings-page {
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

.category-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.category-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  background: linear-gradient(135deg, #111111 0%, #1a1a1a 100%);
  border: 1px solid #333333;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  text-align: left;
  width: 100%;
  -webkit-tap-highlight-color: transparent;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.category-card:hover {
  border-color: #FB0079;
  box-shadow: 0 4px 16px rgba(251, 0, 121, 0.15);
  transform: translateY(-1px);
}

.category-card:active {
  transform: scale(0.98) translateY(0);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.cat-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.cat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: rgba(251, 0, 121, 0.08);
  border-radius: 10px;
  transition: transform 0.2s ease;
}

.category-card:hover .cat-icon {
  transform: scale(1.1);
}

.cat-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.cat-name {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}

.cat-desc {
  font-size: 11px;
  color: #7A7C80;
}
</style>
