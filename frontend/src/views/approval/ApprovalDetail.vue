<template>
  <div class="approval-detail-page">
    <div class="detail-header">
      <span class="title">审批详情</span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!item" class="empty">审批不存在</div>
    <div v-else class="detail-card">
      <div class="detail-row">
        <span class="label">类型</span>
        <span class="value type-tag" :class="item.type">{{ item.type_label }}</span>
      </div>
      <div class="detail-row">
        <span class="label">状态</span>
        <span class="value status-tag" :class="item.status">{{ statusLabel(item.status) }}</span>
      </div>
      <div class="detail-row">
        <span class="label">申请人</span>
        <span class="value">{{ item.employee_name }}</span>
      </div>
      <div v-if="item.start_date" class="detail-row">
        <span class="label">开始日期</span>
        <span class="value">{{ formatChineseDate(item.start_date) }}</span>
      </div>
      <div v-if="item.end_date" class="detail-row">
        <span class="label">结束日期</span>
        <span class="value">{{ formatChineseDate(item.end_date) }}</span>
      </div>

      <!-- 请假天数 -->
      <div v-if="item.type === 'leave' && item.start_date && item.end_date" class="detail-row">
        <span class="label">请假天数</span>
        <span class="value">{{ leaveDays }} 天</span>
      </div>

      <!-- 请假子类型 -->
      <div v-if="item.type === 'leave' && leaveTypeLabel" class="detail-row">
        <span class="label">请假类型</span>
        <span class="value">{{ leaveTypeLabel }}</span>
      </div>

      <!-- 补卡信息 -->
      <template v-if="item.type === 'makeup'">
        <div v-if="item.extra?.date" class="detail-row">
          <span class="label">补卡日期</span>
          <span class="value">{{ item.extra.date }}</span>
        </div>
        <div v-if="item.extra?.clock_in" class="detail-row">
          <span class="label">上班时间</span>
          <span class="value">{{ item.extra.clock_in }}</span>
        </div>
        <div v-if="item.extra?.clock_out" class="detail-row">
          <span class="label">下班时间</span>
          <span class="value">{{ item.extra.clock_out }}</span>
        </div>
      </template>

      <!-- 调班信息 -->
      <template v-if="item.type === 'swap'">
        <div v-if="item.extra?.to_employee_id" class="detail-row">
          <span class="label">调班对象</span>
          <span class="value">员工 #{{ item.extra.to_employee_id }}</span>
        </div>
        <div v-if="item.extra?.date" class="detail-row">
          <span class="label">调班日期</span>
          <span class="value">{{ item.extra.date }}</span>
        </div>
      </template>

      <!-- 报销信息 -->
      <template v-if="item.type === 'expense'">
        <div v-if="item.extra?.amount" class="detail-row">
          <span class="label">金额</span>
          <span class="value">¥ {{ Number(item.extra.amount).toFixed(2) }}</span>
        </div>
      </template>

      <!-- 指定审批人 -->
      <div v-if="item.approver_name" class="detail-row">
        <span class="label">指定审批人</span>
        <span class="value">{{ item.approver_name }}</span>
      </div>

      <div class="detail-row">
        <span class="label">原因</span>
        <span class="value">{{ item.reason }}</span>
      </div>
      <div v-if="item.reject_reason" class="detail-row">
        <span class="label">驳回原因</span>
        <span class="value" style="color:#FB0079">{{ item.reject_reason }}</span>
      </div>
      <div v-if="item.created_at" class="detail-row">
        <span class="label">提交时间</span>
        <span class="value">{{ formatTime(item.created_at) }}</span>
      </div>

      <div v-if="canReview" class="actions">
        <button class="btn-reject" @click="handleReject">驳回</button>
        <button class="btn-approve" @click="handleApprove">通过</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { approvalAPI, type ApprovalItem, type LeaveType } from '@/api/approval'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()

const item = ref<ApprovalItem | null>(null)
const loading = ref(false)
const leaveTypes = ref<Record<string, LeaveType>>({})

const role = computed(() => auth.info.role || 'staff')
const canReview = computed(() => {
  return item.value?.status === 'pending' && (role.value === 'boss' || role.value === 'store_manager')
})

const leaveDays = computed(() => {
  if (!item.value?.start_date || !item.value?.end_date) return 0
  const s = new Date(item.value.start_date)
  const e = new Date(item.value.end_date)
  if (isNaN(s.getTime()) || isNaN(e.getTime())) return 0
  return Math.floor((e.getTime() - s.getTime()) / 86400000) + 1
})

const leaveTypeLabel = computed(() => {
  const lt = item.value?.extra?.leave_type as string | undefined
  if (!lt) return ''
  return leaveTypes.value[lt]?.label || lt
})

function statusLabel(status: string) {
  const map: Record<string, string> = { pending: '待审批', approved: '已通过', rejected: '已驳回' }
  return map[status] || status
}

function formatChineseDate(dateStr: string) {
  if (!dateStr) return ''
  const parts = dateStr.split('-')
  if (parts.length < 3) return dateStr
  return `${parseInt(parts[1])}月${parseInt(parts[2])}日`
}

function formatTime(s: string) {
  try {
    const d = new Date(s)
    return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日 ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return s
  }
}

async function loadData() {
  loading.value = true
  try {
    const id = String(route.params.id || '')
    const res = await approvalAPI.getDetail(id)
    item.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function loadLeaveTypes() {
  try {
    const res = await approvalAPI.getLeaveTypes()
    leaveTypes.value = res.data.data?.types || {}
  } catch {
    // 静默
  }
}

async function handleApprove() {
  if (!item.value) return
  if (!confirm('确定通过该审批？')) return
  try {
    await approvalAPI.approve(item.value.id)
    await loadData()
  } catch (e: any) {
    alert(e.response?.data?.message || '操作失败')
  }
}

async function handleReject() {
  if (!item.value) return
  const reason = prompt('请输入驳回原因（可选）：')
  try {
    await approvalAPI.reject(item.value.id, reason || undefined)
    await loadData()
  } catch (e: any) {
    alert(e.response?.data?.message || '操作失败')
  }
}

onMounted(() => {
  loadData()
  loadLeaveTypes()
})
</script>

<style scoped>
.approval-detail-page {
  padding: 16px;
}

.detail-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}

.title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 32px;
}

.detail-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
}

.detail-row:last-child {
  border-bottom: none;
}

.label {
  font-size: 13px;
  color: #7A7C80;
}

.value {
  font-size: 13px;
  color: #FFFFFF;
  text-align: right;
}

.type-tag {
  padding: 2px 8px;
  border-radius: 4px;
  background: #333333;
}

.status-tag.approved { color: #4CAF50; }
.status-tag.rejected { color: #FB0079; }

.actions {
  display: flex;
  gap: 12px;
  margin-top: 24px;
}

.btn-reject,
.btn-approve {
  flex: 1;
  padding: 12px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.btn-reject {
  background: #333333;
  color: #C8C8C8;
}

.btn-approve {
  background: #FB0079;
  color: #FFFFFF;
}
</style>
