<template>
  <div class="stocktake-list-page">
    <div class="page-header">
      <h1 class="page-title">盘点记录</h1>
      <button class="create-btn" @click="handleCreate">+ 本月</button>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <div v-else-if="list.length === 0" class="empty-state">
      <p class="empty-text">暂无盘点记录</p>
      <p class="empty-hint">每月1号自动生成，或点击右上角手动创建</p>
    </div>
    <div v-else class="stocktake-list">
      <div
        v-for="s in list"
        :key="s.id"
        class="stocktake-card"
        @click="router.push(`/management/wine-stocktake/${s.id}`)"
      >
        <div class="card-head">
          <span class="period">{{ s.period }}</span>
          <span class="status-badge" :class="s.status">{{ statusLabel(s.status) }}</span>
        </div>
        <div class="card-stats">
          <div class="stat">
            <span class="stat-num">{{ s.total_count }}</span>
            <span class="stat-label">应盘</span>
          </div>
          <div class="stat">
            <span class="stat-num matched">{{ s.matched_count }}</span>
            <span class="stat-label">匹配</span>
          </div>
          <div class="stat">
            <span class="stat-num missing">{{ s.missing_count }}</span>
            <span class="stat-label">缺失</span>
          </div>
          <div class="stat">
            <span class="stat-num">{{ s.checked_count }}/{{ s.total_count }}</span>
            <span class="stat-label">进度</span>
          </div>
        </div>
        <div class="card-foot" v-if="s.completed_at">
          <span class="foot-label">完成于</span>
          <span class="foot-value">{{ formatDate(s.completed_at) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { stocktakeAPI, type Stocktake } from '@/api/wine'

const router = useRouter()
const list = ref<Stocktake[]>([])
const loading = ref(false)

async function loadList() {
  loading.value = true
  try {
    const { data: res } = await stocktakeAPI.list({ page_size: 50 })
    if (res.code === 0) {
      list.value = res.data.items || []
    }
  } catch { list.value = [] }
  finally { loading.value = false }
}

async function handleCreate() {
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

function statusLabel(status: string): string {
  return { pending: '待盘点', in_progress: '盘点中', completed: '已完成' }[status] || status
}

function formatDate(iso: string): string {
  if (!iso) return '-'
  try {
    const d = new Date(iso)
    return `${d.getMonth() + 1}/${d.getDate()} ${d.getHours().toString().padStart(2, '0')}:${d.getMinutes().toString().padStart(2, '0')}`
  } catch { return iso }
}

onMounted(() => loadList())
</script>

<style scoped>
.stocktake-list-page {
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
  flex: 1;
}
.create-btn {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 8px 14px;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #7A7C80;
}
.empty-text { font-size: 14px; margin: 0 0 8px; }
.empty-hint { font-size: 12px; color: #555; margin: 0; }

.stocktake-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.stocktake-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.stocktake-card:hover { border-color: #FB0079; }

.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.period {
  font-family: 'Poppins', sans-serif;
  font-size: 16px;
  font-weight: 700;
  color: #FFFFFF;
}
.status-badge {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 6px;
  font-family: 'Source Han Sans SC', sans-serif;
}
.status-badge.pending { background: #333; color: #7A7C80; }
.status-badge.in_progress { background: rgba(251, 0, 121, 0.2); color: #FB0079; }
.status-badge.completed { background: rgba(100, 200, 100, 0.15); color: #6fcf6f; }

.card-stats {
  display: flex;
  gap: 8px;
}
.stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.stat-num {
  font-family: 'Poppins', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.stat-num.matched { color: #6fcf6f; }
.stat-num.missing { color: #FB0079; }
.stat-label {
  font-size: 10px;
  color: #7A7C80;
}

.card-foot {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #1a1a1a;
  display: flex;
  gap: 6px;
  font-size: 11px;
}
.foot-label { color: #7A7C80; }
.foot-value { color: #C8C8C8; }
</style>
