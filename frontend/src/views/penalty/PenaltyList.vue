<template>
  <div class="penalty-list-page">
    <div class="page-header">
      <h2 class="page-title">奖惩通知</h2>
      <button class="btn-create" @click="router.push('/management/penalties/create')">+ 新建</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="items.length === 0" class="empty">暂无奖惩通知</div>
    <div v-else class="penalty-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="penalty-card"
        :class="statusClass(item.status)"
      >
        <div class="card-top">
          <span class="penalty-type-badge">{{ item.penalty_type_name }}</span>
          <span class="penalty-amount">¥{{ item.amount }}</span>
        </div>
        <div class="card-reason">{{ item.reason }}</div>
        <div class="card-bottom">
          <div class="card-meta">
            <span>员工: {{ item.employee_name }}</span>
            <span>发布人: {{ item.issued_by_name }}</span>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="card-status-row">
            <span class="status-tag" :class="item.status">
              {{ statusLabel(item.status) }}
            </span>
            <span v-if="item.sign_task_status" class="sign-status">
              {{ signStatusLabel(item.sign_task_status) }}
            </span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { penaltyAPI, type PenaltyItem } from '@/api/penalties'

const router = useRouter()
const items = ref<PenaltyItem[]>([])
const loading = ref(false)

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    issued: '已发布',
    acknowledged: '已签收',
  }
  return map[status] || status
}

function signStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待签收',
    signed: '已签收',
    disputed: '有异议',
  }
  return map[status] || status
}

function statusClass(status: string): string {
  return `status-${status}`
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const res = await penaltyAPI.getList({ page: 1, page_size: 50 })
    items.value = res.data.data.items || []
  } catch { /* */ }
  loading.value = false
}

onMounted(loadData)
</script>

<style scoped>
.penalty-list-page {
  padding: 0 16px;
  padding-bottom: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.btn-create {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 48px;
}

.penalty-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.penalty-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
}

.penalty-card.status-draft {
  border-left: 3px solid #333333;
}

.penalty-card.status-issued {
  border-left: 3px solid #FB0079;
}

.penalty-card.status-acknowledged {
  border-left: 3px solid #FB0079;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.penalty-type-badge {
  font-size: 11px;
  color: #FB0079;
  padding: 2px 8px;
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 4px;
}

.penalty-amount {
  font-size: 16px;
  font-weight: 700;
  color: #FB0079;
}

.card-reason {
  font-size: 13px;
  color: #C8C8C8;
  line-height: 1.5;
  margin-bottom: 10px;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.card-meta {
  font-size: 11px;
  color: #7A7C80;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.card-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag.draft {
  background: #333333;
  color: #7A7C80;
}

.status-tag.issued {
  background: rgba(255, 104, 162, 0.15);
  color: #FB0079;
}

.status-tag.acknowledged {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}

.sign-status {
  font-size: 11px;
  color: #7A7C80;
}
</style>
