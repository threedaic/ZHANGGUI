<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h1>开闭店看板</h1>
      <button class="refresh-btn" @click="loadData">刷新</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="stores.length === 0" class="empty">暂无门店数据</div>
    <div v-else class="store-grid">
      <div
        v-for="store in stores"
        :key="store.store_id"
        class="store-card"
        :class="{ active: store.has_active_session, 'no-session': !store.has_active_session }"
      >
        <div class="card-header">
          <h2>{{ store.store_name }}</h2>
          <span class="status-dot" :class="store.has_active_session ? 'active' : 'idle'"></span>
        </div>

        <div v-if="store.has_active_session" class="active-info">
          <span class="badge" :class="store.session_type">
            {{ store.session_type === 'closing' ? '闭店中' : '开店中' }}
          </span>
          <div class="progress-wrap">
            <div class="progress-bar">
              <div class="progress-fill" :style="{ width: getPercent(store) + '%' }"></div>
            </div>
            <span class="count">{{ store.completed_items }}/{{ store.total_items }}</span>
          </div>
          <div class="time">{{ formatTime(store.started_at) }}</div>
        </div>

        <div v-else class="idle-info">
          <div v-if="store.last_completed_at" class="last-status">
            <span class="badge" :class="store.last_completed_type">
              {{ store.last_completed_type === 'closing' ? '已闭店' : '已开店' }}
            </span>
            <span class="time">{{ formatTime(store.last_completed_at) }}</span>
          </div>
          <div v-else class="no-history">暂无记录</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { getDashboard } from '@/api/butler'
import type { StoreClosingStatus } from '@/api/butler'

const stores = ref<StoreClosingStatus[]>([])
const loading = ref(false)

onMounted(() => {
  loadData()
})

async function loadData() {
  loading.value = true
  try {
    const res: any = await getDashboard()
    stores.value = res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function getPercent(store: StoreClosingStatus): number {
  if (store.total_items === 0) return 0
  return Math.round((store.completed_items / store.total_items) * 100)
}

function formatTime(t: string | null) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', {
    month: 'numeric', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.dashboard-page {
  max-width: 800px;
  margin: 0 auto;
  padding: 16px;
  min-height: 100vh;
  background: #111111;
  color: #e0e0e0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h1 {
  font-size: 20px;
  color: #fff;
  margin: 0;
}

.refresh-btn {
  background: #1a1a1a;
  border: 1px solid #444;
  color: #ccc;
  padding: 6px 14px;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
}

.store-grid {
  display: grid;
  gap: 12px;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}

.store-card {
  padding: 16px;
  border-radius: 12px;
  border: 1px solid #333;
  background: #1a1a1a;
}

.store-card.active {
  border-color: #FB0079;
  background: linear-gradient(135deg, rgba(251, 0, 121, 0.08), #1a1a1a);
}

.store-card.no-session {
  border-color: #2a2a2a;
  opacity: 0.7;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.card-header h2 {
  font-size: 16px;
  margin: 0;
  color: #fff;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.status-dot.active {
  background: #4caf50;
  box-shadow: 0 0 6px #4caf50;
}

.status-dot.idle {
  background: #666;
}

.active-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.progress-wrap {
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background: #333;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, #FB0079, #ff3d9e);
  border-radius: 3px;
  transition: width 0.3s;
}

.count {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  white-space: nowrap;
}

.time {
  font-size: 11px;
  color: #666;
}

.idle-info {
  min-height: 40px;
  display: flex;
  align-items: center;
}

.last-status {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  width: fit-content;
}

.badge.closing { background: rgba(251, 0, 121, 0.15); color: #FB0079; }
.badge.opening { background: #1a3d2a; color: #4caf50; }

.no-history {
  font-size: 12px;
  color: #555;
}

.loading, .empty {
  text-align: center;
  padding: 48px;
  color: #666;
  font-size: 14px;
}
</style>
