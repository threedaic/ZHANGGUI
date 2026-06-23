<template>
  <div class="wine-inventory-page">
    <div class="page-header">
      <h1 class="page-title">存酒管理</h1>
    </div>

    <!-- 概览统计 -->
    <div class="inventory-bar">
      <div class="stat-item">
        <span class="stat-num">{{ summary.total }}</span>
        <span class="stat-label">总存酒</span>
      </div>
      <div class="stat-item">
        <span class="stat-num stored">{{ summary.stored }}</span>
        <span class="stat-label">在库</span>
      </div>
      <div class="stat-item">
        <span class="stat-num retrieved">{{ summary.retrieved }}</span>
        <span class="stat-label">已取</span>
      </div>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <button class="quick-btn" @click="router.push('/management/wine-stocktake')">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FB0079" stroke-width="1.5"><rect x="3" y="3" width="14" height="14" rx="2"/><path d="M7 10l2 2 4-4"/></svg>
        <span>盘点记录</span>
      </button>
      <button class="quick-btn" @click="handleCreateStocktake">
        <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="#FB0079" stroke-width="1.5"><path d="M10 3v14M3 10h14"/></svg>
        <span>生成本月盘点</span>
      </button>
    </div>

    <!-- 在库记录 -->
    <div class="recent-section">
      <div class="recent-header">
        <span class="recent-title">在库记录</span>
        <input
          v-model="searchKeyword"
          class="search-input"
          placeholder="搜酒名/客人/手机号"
          @input="onSearchInput"
        />
      </div>

      <div v-if="listLoading" class="loading-state">
        <span class="loading-text">加载中...</span>
      </div>
      <div v-else-if="wineList.length === 0" class="empty-state">
        <span class="empty-text">暂无在库记录</span>
      </div>
      <div v-else class="wine-list">
        <div
          v-for="w in wineList"
          :key="w.id"
          class="wine-card"
          :class="{ 'is-retrieved': w.status === 'retrieved' }"
        >
          <div class="wine-head">
            <span class="wine-name">{{ w.wine_name }}</span>
            <span class="wine-status" :class="w.status">{{ w.status === 'stored' ? '在库' : '已取' }}</span>
          </div>
          <div class="wine-body">
            <div class="wine-row">
              <span class="label">客人</span>
              <span class="value">{{ w.customer_name }}</span>
            </div>
            <div class="wine-row">
              <span class="label">手机</span>
              <span class="value">{{ w.phone }}</span>
            </div>
            <div class="wine-row">
              <span class="label">剩余</span>
              <span class="value highlight">{{ remainingLabel(w.remaining_ml, w.initial_ml) }}</span>
            </div>
            <div class="wine-row" v-if="w.bottle_label">
              <span class="label">标签</span>
              <span class="value code">{{ w.bottle_label }}</span>
            </div>
            <div class="wine-row" v-if="w.cabinet_no">
              <span class="label">柜号</span>
              <span class="value">{{ w.cabinet_no }}</span>
            </div>
            <div class="wine-row" v-if="w.date_stored">
              <span class="label">存入</span>
              <span class="value">{{ w.date_stored }}</span>
            </div>
          </div>
          <div class="wine-foot" v-if="w.notes">
            <span class="notes">{{ w.notes }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { wineAPI, stocktakeAPI, type WineInfo, type InventorySummary } from '@/api/wine'

const router = useRouter()
const summary = reactive<InventorySummary>({ total: 0, stored: 0, retrieved: 0 })
const wineList = ref<WineInfo[]>([])
const searchKeyword = ref('')
const listLoading = ref(false)

async function loadSummary() {
  try {
    const { data: res } = await wineAPI.inventorySummary()
    if (res.code === 0 && res.data) {
      summary.total = res.data.total
      summary.stored = res.data.stored
      summary.retrieved = res.data.retrieved
    }
  } catch { /* ignore */ }
}

async function loadWineList() {
  listLoading.value = true
  try {
    const params: Record<string, unknown> = { page_size: 50 }
    if (searchKeyword.value.trim()) {
      params.keyword = searchKeyword.value.trim()
      params.search_type = 'all'
    } else {
      params.status = 'stored'
    }
    const { data: res } = await wineAPI.list(params)
    if (res.code === 0) {
      wineList.value = res.data.items || []
    }
  } catch { wineList.value = [] }
  finally { listLoading.value = false }
}

let searchTimer: ReturnType<typeof setTimeout> | null = null
function onSearchInput() {
  if (searchTimer) clearTimeout(searchTimer)
  searchTimer = setTimeout(() => loadWineList(), 300)
}

async function handleCreateStocktake() {
  try {
    const { data: res } = await stocktakeAPI.create()
    if (res.code === 0) {
      if (res.data.id === '0') {
        ElMessage.info('当前无在库酒，无需盘点')
      } else {
        ElMessage.success(`盘点单已生成 #${res.data.id}`)
        router.push(`/management/wine-stocktake/${res.data.id}`)
      }
    } else {
      ElMessage.error(res.message || '生成失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '生成失败')
  }
}

function remainingLabel(remaining: number | null, initial: number | null): string {
  if (remaining == null) return '-'
  if (initial && initial > 0) {
    const pct = Math.round((remaining / initial) * 100)
    return `${remaining}ml (${pct}%)`
  }
  return `${remaining}ml`
}

onMounted(() => {
  loadSummary()
  loadWineList()
})
</script>

<style scoped>
.wine-inventory-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.inventory-bar {
  display: flex;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}
.stat-item {
  flex: 1;
  text-align: center;
  display: flex;
  flex-direction: column;
  align-items: center;
}
.stat-num {
  font-family: 'Poppins', sans-serif;
  font-size: 24px;
  font-weight: 700;
  color: #FFFFFF;
}
.stat-num.stored { color: #FB0079; }
.stat-num.retrieved { color: #7A7C80; }
.stat-label {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.quick-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  cursor: pointer;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 12px;
  color: #C8C8C8;
  transition: border-color 0.2s;
}
.quick-btn:hover { border-color: #FB0079; }

.recent-section { margin-top: 8px; }
.recent-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.recent-title {
  font-size: 13px;
  color: #7A7C80;
  white-space: nowrap;
}
.search-input {
  flex: 1;
  height: 36px;
  padding: 0 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
  outline: none;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 40px 0;
  color: #7A7C80;
  font-size: 13px;
}

.wine-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.wine-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px;
}
.wine-card.is-retrieved { opacity: 0.5; }
.wine-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.wine-name {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.wine-status {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'Source Han Sans SC', sans-serif;
}
.wine-status.stored {
  background: rgba(251, 0, 121, 0.2);
  color: #FB0079;
}
.wine-status.retrieved {
  background: #333333;
  color: #7A7C80;
}
.wine-body {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 12px;
}
.wine-row {
  display: flex;
  gap: 6px;
  font-size: 12px;
}
.label { color: #7A7C80; min-width: 32px; }
.value { color: #C8C8C8; }
.value.highlight { color: #FB0079; font-weight: 600; }
.value.code {
  font-family: 'Poppins', monospace;
  font-size: 11px;
  color: #FB0079;
}
.wine-foot {
  margin-top: 8px;
  padding-top: 8px;
  border-top: 1px solid #1a1a1a;
}
.notes {
  font-size: 11px;
  color: #7A7C80;
}
</style>
