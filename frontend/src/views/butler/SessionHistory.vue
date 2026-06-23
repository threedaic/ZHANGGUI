<template>
  <div class="history-page">
    <div class="page-header">
      <h1>历史记录</h1>
    </div>

    <div class="tab-switch">
      <button :class="{ active: filter === 'all' }" @click="filter = 'all'; loadSessions()">全部</button>
      <button :class="{ active: filter === 'closing' }" @click="filter = 'closing'; loadSessions()">闭店</button>
      <button :class="{ active: filter === 'opening' }" @click="filter = 'opening'; loadSessions()">开店</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="sessions.length === 0" class="empty">暂无记录</div>
    <div v-else class="session-list">
      <div
        v-for="s in sessions"
        :key="s.id"
        class="session-card"
        @click="$router.push(`/management/butler/${s.id}`)"
      >
        <div class="card-top">
          <span class="badge" :class="s.session_type">
            {{ s.session_type === 'closing' ? '闭店' : '开店' }}
          </span>
          <span class="badge" :class="s.status">
            {{ statusLabel(s.status) }}
          </span>
          <span class="count">{{ s.completed_items }}/{{ s.total_items }}</span>
        </div>
        <div class="card-bottom">
          <span>{{ formatDate(s.started_at) }}</span>
          <span class="arrow">&#8594;</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { listSessions } from '@/api/butler'

const sessions = ref<any[]>([])
const loading = ref(false)
const filter = ref('all')

onMounted(() => {
  loadSessions()
})

async function loadSessions() {
  loading.value = true
  try {
    const params: any = { page: 1, page_size: 50 }
    if (filter.value !== 'all') params.session_type = filter.value
    const res: any = await listSessions(params)
    sessions.value = res.data.items || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function statusLabel(s: string): string {
  const map: Record<string, string> = { completed: '已完成', in_progress: '进行中', abnormal: '异常' }
  return map[s] || s
}

function formatDate(t: string | null) {
  if (!t) return ''
  return new Date(t).toLocaleString('zh-CN', {
    month: 'numeric', day: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}
</script>

<style scoped>
.history-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
  min-height: 100vh;
  background: #111111;
  color: #e0e0e0;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.page-header h1 {
  font-size: 18px;
  margin: 0;
  color: #fff;
}

.tab-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.tab-switch button {
  background: none;
  border: 1px solid #333;
  color: #888;
  padding: 6px 16px;
  border-radius: 20px;
  font-size: 13px;
  cursor: pointer;
}

.tab-switch button.active {
  background: #FB0079;
  border-color: #FB0079;
  color: #fff;
}

.session-card {
  padding: 14px;
  background: #1a1a1a;
  border-radius: 8px;
  margin-bottom: 8px;
  cursor: pointer;
}

.card-top {
  display: flex;
  gap: 8px;
  align-items: center;
  margin-bottom: 6px;
}

.count {
  margin-left: auto;
  font-size: 14px;
  color: #ccc;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #666;
}

.badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}
.badge.closing { background: rgba(251, 0, 121, 0.15); color: #FB0079; }
.badge.opening { background: #1a3d2a; color: #4caf50; }
.badge.completed { background: #1a3d2a; color: #4caf50; }
.badge.in_progress { background: #3d3d1a; color: #ffc107; }
.badge.abnormal { background: #3d1a1a; color: #f44336; }

.arrow { color: #FB0079; }
.loading, .empty { text-align: center; padding: 32px; color: #666; }
</style>
