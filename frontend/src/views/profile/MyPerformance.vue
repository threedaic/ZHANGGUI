<template>
  <div class="perf-page">
    <div class="page-header">
      <span class="page-title">我的业绩</span>
      <span class="page-period">{{ period }}月</span>
    </div>

    <div class="summary-card">
      <div class="summary-label">本月累计</div>
      <div class="summary-amount">¥{{ fmtMoney(totalAmount) }}</div>
    </div>

    <div class="table-wrap">
      <table class="perf-table" v-if="!loading && detail.length > 0">
        <thead>
          <tr>
            <th>日期</th>
            <th>收款(元)</th>
            <th>累计(元)</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in detail" :key="row.date" :class="{ highlight: row.amount > 0 }">
            <td class="col-date">{{ row.date.slice(5) }}</td>
            <td class="col-amount">{{ row.amount > 0 ? row.amount.toLocaleString() : '-' }}</td>
            <td class="col-cumul">{{ row.cumulative.toLocaleString() }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="detail.length === 0" class="empty">暂无业绩数据</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import apiClient from '@/api/client'

interface PerfRow {
  date: string
  amount: number
  cumulative: number
}

const detail = ref<PerfRow[]>([])
const loading = ref(false)

const period = computed(() => {
  const now = new Date()
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`
})

const totalAmount = computed(() => {
  if (detail.value.length === 0) return 0
  return detail.value[detail.value.length - 1].cumulative
})

function fmtMoney(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  return n.toLocaleString()
}

onMounted(async () => {
  loading.value = true
  try {
    const res = await apiClient.get('/dashboard/my-performance-detail')
    detail.value = res.data.data || []
  } catch { /* silent */ }
  finally { loading.value = false }
})
</script>

<style scoped>
.perf-page { padding: 16px; padding-bottom: 80px; }
.page-header { display: flex; align-items: baseline; gap: 10px; margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 700; color: #FFFFFF; }
.page-period { font-size: 12px; color: #7A7C80; }

.summary-card {
  padding: 16px; background: #111111; border: 1px solid #333333;
  border-radius: 12px; margin-bottom: 16px; text-align: center;
}
.summary-label { font-size: 12px; color: #7A7C80; margin-bottom: 6px; }
.summary-amount { font-size: 28px; font-weight: 700; color: #FB0079; }

.table-wrap { max-height: calc(100vh - 240px); overflow-y: auto; }
.perf-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.perf-table th {
  padding: 8px 12px; text-align: left; color: #7A7C80; font-weight: 500;
  border-bottom: 1px solid #222222; position: sticky; top: 0; background: #000000;
}
.perf-table td { padding: 10px 12px; border-bottom: 1px solid #1a1a1a; }
.col-date { color: #C8C8C8; width: 80px; }
.col-amount { color: #FB0079; font-weight: 600; width: 120px; }
.col-cumul { color: #FFFFFF; font-weight: 500; }
tr.highlight { background: rgba(251, 0, 121, 0.04); }

.loading, .empty { color: #888; text-align: center; padding: 40px 0; font-size: 14px; }
</style>
