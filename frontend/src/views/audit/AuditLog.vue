<template>
  <div class="audit-page">
    <h1 class="page-title">操作日志</h1>

    <!-- 筛选 -->
    <div class="filters">
      <select v-model="filterAction" class="filter-select" @change="search">
        <option value="">全部操作</option>
        <option value="create">创建</option>
        <option value="update">修改</option>
        <option value="delete">删除</option>
      </select>
      <select v-model="filterEntity" class="filter-select" @change="search">
        <option value="">全部模块</option>
        <option v-for="e in entityTypes" :key="e.value" :value="e.value">{{ e.label }}</option>
      </select>
      <input v-model="filterDateFrom" type="date" class="filter-date" @change="search" placeholder="从" />
      <input v-model="filterDateTo" type="date" class="filter-date" @change="search" placeholder="到" />
      <button class="btn-icon" @click="search">查询</button>
    </div>

    <!-- 列表 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="items.length === 0" class="empty">暂无操作记录</div>
    <div v-else class="log-list">
      <div v-for="log in items" :key="log.id" class="log-item" :class="'log-' + log.action">
        <div class="log-header">
          <span class="log-user">{{ log.username }}</span>
          <span class="log-action">{{ ACTION_LABELS[log.action] || log.action }}</span>
          <span class="log-entity">{{ ENTITY_LABELS[log.entity_type] || log.entity_type }}</span>
          <span class="log-time">{{ formatTime(log.created_at) }}</span>
        </div>
        <div v-if="log.action === 'update' && log.old_value && log.new_value" class="log-diff">
          <div class="diff-row" v-for="(change, key) in parseDiff(log.old_value, log.new_value)" :key="key">
            <span class="diff-field">{{ key }}</span>
            <span class="diff-old">{{ change.old }}</span>
            <span class="diff-arrow">-></span>
            <span class="diff-new">{{ change.new }}</span>
          </div>
        </div>
        <div v-else-if="log.new_value" class="log-value">
          {{ formatValue(log.new_value) }}
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="total > pageSize" class="pagination">
      <button :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ totalPages }} 页 (共 {{ total }} 条)</span>
      <button :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getAuditLogs } from '@/api/audit'
import type { AuditLogItem } from '@/api/audit'

const ACTION_LABELS: Record<string, string> = {
  create: '创建',
  update: '修改',
  delete: '删除',
}

const ENTITY_LABELS: Record<string, string> = {
  stores: '门店',
  store_settings: '门店配置',
  employees: '员工',
  users: '用户',
  schedules: '排班',
  schedule_snapshots: '排班快照',
  schedule_rules: '排班规则',
  shift_swap_requests: '调班申请',
  attendance_records: '考勤记录',
  shift_configs: '班次配置',
  kpi_templates: 'KPI模板',
  kpi_scores: 'KPI评分',
  kpi_results: 'KPI结果',
  kpi_appeals: 'KPI申诉',
  payroll_records: '工资记录',
  daily_revenue: '营收',
  guest_ratings: '评分',
  bookings: '订桌',
  tables: '桌位',
  wine_storage: '存酒',
  table_sessions: '防飞单',
  salary_matrix: '薪资矩阵',
  contracts: '合同',
  approval_requests: '审批',
  notifications: '通知',
  notification_settings: '通知设置',
  leave_balances: '假期余额',
  companies: '公司',
}

const entityTypes = Object.entries(ENTITY_LABELS).map(([value, label]) => ({ value, label }))

const items = ref<AuditLogItem[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = 20

const filterAction = ref('')
const filterEntity = ref('')
const filterDateFrom = ref('')
const filterDateTo = ref('')

const totalPages = computed(() => Math.ceil(total.value / pageSize))

async function search() {
  loading.value = true
  page.value = 1
  await loadPage()
}

async function loadPage() {
  loading.value = true
  try {
    const res = await getAuditLogs({
      page: page.value,
      page_size: pageSize,
      action: filterAction.value || undefined,
      entity_type: filterEntity.value || undefined,
      date_from: filterDateFrom.value || undefined,
      date_to: filterDateTo.value || undefined,
    })
    const data = res.data.data
    items.value = data.items
    total.value = data.total
  } catch (e: any) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  page.value = p
  loadPage()
}

function formatTime(ts: string) {
  if (!ts) return ''
  const d = new Date(ts)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function parseDiff(oldStr: string, newStr: string): Record<string, { old: string; new: string }> {
  try {
    const oldObj = JSON.parse(oldStr) as Record<string, unknown>
    const newObj = JSON.parse(newStr) as Record<string, unknown>
    const diff: Record<string, { old: string; new: string }> = {}
    const skipFields = new Set(['updated_at', 'created_at', 'id'])

    for (const key of Object.keys(newObj)) {
      if (skipFields.has(key)) continue
      const ov = String(oldObj[key] ?? '(空)')
      const nv = String(newObj[key] ?? '(空)')
      if (ov !== nv) {
        diff[key] = { old: ov, new: nv }
      }
    }
    return diff
  } catch {
    return {}
  }
}

function formatValue(jsonStr: string) {
  try {
    const obj = JSON.parse(jsonStr) as Record<string, unknown>
    const skip = new Set(['id', 'created_at', 'updated_at', 'password_hash'])
    const parts = Object.entries(obj)
      .filter(([k]) => !skip.has(k))
      .map(([k, v]) => `${k}: ${v}`)
    return parts.slice(0, 5).join(' | ') + (parts.length > 5 ? '...' : '')
  } catch {
    return jsonStr ? jsonStr.substring(0, 100) : ''
  }
}

onMounted(() => {
  loadPage()
})
</script>

<style scoped>
.audit-page {
  padding: 16px;
  padding-bottom: 80px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 16px;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.filter-select {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
}

.filter-date {
  padding: 6px 10px;
  border-radius: 6px;
  border: 1px solid #333;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
  color-scheme: dark;
}

.btn-icon {
  padding: 6px 14px;
  border: 1px solid #333;
  border-radius: 6px;
  background: #111;
  color: #FFFFFF;
  font-size: 13px;
  cursor: pointer;
}

.loading, .empty {
  color: #7A7C80;
  text-align: center;
  padding: 40px 0;
  font-size: 14px;
}

.log-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.log-item {
  padding: 12px;
  border-radius: 8px;
  background: #111111;
  border: 1px solid #222222;
}

.log-item.log-create { border-left: 3px solid #FB0079; }
.log-item.log-update { border-left: 3px solid #FF9800; }
.log-item.log-delete { border-left: 3px solid #FB0079; }

.log-header {
  display: flex;
  gap: 10px;
  font-size: 13px;
  align-items: center;
  flex-wrap: wrap;
}

.log-user { color: #FB0079; font-weight: 600; }
.log-action {
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  color: #fff;
}
.log-create .log-action { background: #FB0079; }
.log-update .log-action { background: #FF9800; }
.log-delete .log-action { background: #FB0079; }

.log-entity { color: #aaa; }
.log-time { color: #7A7C80; margin-left: auto; font-size: 12px; }

.log-diff {
  margin-top: 8px;
  font-size: 12px;
}

.diff-row {
  display: flex;
  gap: 6px;
  padding: 2px 0;
  align-items: center;
}

.diff-field { color: #7A7C80; min-width: 80px; }
.diff-old { color: #FB0079; text-decoration: line-through; max-width: 120px; overflow: hidden; text-overflow: ellipsis; }
.diff-arrow { color: #7A7C80; }
.diff-new { color: #FB0079; max-width: 120px; overflow: hidden; text-overflow: ellipsis; }

.log-value {
  margin-top: 6px;
  font-size: 12px;
  color: #7A7C80;
}

.pagination {
  display: flex;
  gap: 12px;
  align-items: center;
  justify-content: center;
  margin-top: 16px;
  font-size: 13px;
  color: #aaa;
}

.pagination button {
  padding: 4px 12px;
  border: 1px solid #333;
  border-radius: 4px;
  background: #111111;
  color: #FFFFFF;
  cursor: pointer;
}

.pagination button:disabled {
  opacity: 0.4;
  cursor: default;
}
</style>
