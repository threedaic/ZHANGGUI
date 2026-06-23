<template>
  <div class="approval-page">
    <h1 class="page-title">
      审批
      <span v-if="canReview && pendingCount.assigned_to_me > 0" class="badge">
        {{ pendingCount.assigned_to_me }}
      </span>
    </h1>

    <!-- 视图切换：我发起的 / 待我审批 -->
    <div v-if="canReview" class="view-tabs">
      <button
        class="view-tab"
        :class="{ active: viewMode === 'mine' }"
        @click="switchView('mine')"
      >
        我发起的
      </button>
      <button
        class="view-tab"
        :class="{ active: viewMode === 'todo' }"
        @click="switchView('todo')"
      >
        待我审批
        <span v-if="pendingCount.assigned_to_me > 0" class="tab-badge">{{ pendingCount.assigned_to_me }}</span>
      </button>
    </div>

    <!-- 类型切换 -->
    <div class="type-tabs">
      <button
        v-for="t in types"
        :key="t.key"
        class="type-tab"
        :class="{ active: currentType === t.key }"
        @click="currentType = t.key"
      >
        {{ t.label }}
      </button>
    </div>

    <!-- 状态切换 -->
    <div class="status-tabs">
      <button
        v-for="s in statusList"
        :key="s.key"
        class="status-tab"
        :class="{ active: currentStatus === s.key }"
        @click="currentStatus = s.key"
      >
        {{ s.label }}
      </button>
    </div>

    <!-- 列表 -->
    <div class="approval-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="list.length === 0" class="empty">
        {{ viewMode === 'todo' ? '暂无待我审批的事项' : '暂无审批' }}
      </div>
      <div
        v-for="item in list"
        :key="item.id"
        class="approval-card"
        @click="goDetail(item)"
      >
        <div class="card-header">
          <span class="type-tag" :class="item.type">{{ item.type_label }}</span>
          <span class="status-tag" :class="item.status">{{ statusLabel(item.status) }}</span>
        </div>
        <div class="card-body">
          <p class="employee">{{ item.employee_name }}</p>
          <p v-if="item.start_date" class="date">
            {{ formatChineseDate(item.start_date) }}
            <template v-if="item.end_date && item.end_date !== item.start_date">
              ~ {{ formatChineseDate(item.end_date) }}
            </template>
          </p>
          <p v-if="item.approver_name" class="approver">审批人：{{ item.approver_name }}</p>
          <p class="reason">{{ item.reason }}</p>
        </div>
        <div v-if="canReviewItem(item)" class="card-actions">
          <button class="btn-reject" @click.stop="handleReject(item.id)">驳回</button>
          <button class="btn-approve" @click.stop="handleApprove(item.id)">通过</button>
        </div>
      </div>
    </div>

    <!-- 发起审批 -->
    <button class="fab" @click="showForm = true">+</button>

    <!-- 审批表单弹窗 -->
    <el-dialog
      v-model="showForm"
      title="发起审批"
      width="90%"
      :close-on-click-modal="false"
      class="approval-form-dialog"
    >
      <ApprovalForm @submitted="onFormSubmitted" />
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { approvalAPI, type ApprovalItem } from '@/api/approval'
import { useAuthStore } from '@/stores/auth'
import ApprovalForm from './ApprovalForm.vue'

const router = useRouter()
const auth = useAuthStore()

const role = computed(() => auth.info.role || 'staff')
const canReview = computed(() => role.value === 'boss' || role.value === 'store_manager')

const types = [
  { key: 'all', label: '全部' },
  { key: 'leave', label: '请假' },
  { key: 'makeup', label: '补卡' },
  { key: 'swap', label: '调班' },
  { key: 'expense', label: '报销' },
]

const statusList = [
  { key: 'pending', label: '待审批' },
  { key: 'approved', label: '已通过' },
  { key: 'rejected', label: '已驳回' },
]

const viewMode = ref<'mine' | 'todo'>('mine')
const currentType = ref('all')
const currentStatus = ref('pending')
const list = ref<ApprovalItem[]>([])
const loading = ref(false)
const showForm = ref(false)
const pendingCount = ref({ total_pending: 0, assigned_to_me: 0 })

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

// 待我审批视图：只显示 approver_id 等于当前用户的、或未指定审批人的待审批
function canReviewItem(item: ApprovalItem) {
  if (!canReview.value) return false
  if (item.status !== 'pending') return false
  if (viewMode.value === 'todo') return true
  // 在"我发起的"视图下，店长也能直接审批
  return true
}

function switchView(mode: 'mine' | 'todo') {
  viewMode.value = mode
  // 切换视图时重置筛选
  if (mode === 'todo') {
    currentStatus.value = 'pending'
  }
}

async function loadData() {
  loading.value = true
  try {
    const res = await approvalAPI.getList({
      status: currentStatus.value,
      type: currentType.value === 'all' ? undefined : currentType.value,
      page: 1,
      page_size: 50,
    })
    let items = res.data.data.items
    // 待我审批视图：只看 pending 且（指定给我 或 未指定审批人）
    if (viewMode.value === 'todo') {
      const myUserId = auth.info.user_id
      items = items.filter(i =>
        i.status === 'pending' &&
        (i.approver_id === null || i.approver_id === undefined || i.approver_id === myUserId)
      )
    }
    list.value = items
  } finally {
    loading.value = false
  }
}

async function loadPendingCount() {
  if (!canReview.value) return
  try {
    const res = await approvalAPI.getPendingCount()
    pendingCount.value = res.data.data
  } catch {
    // 静默
  }
}

async function handleApprove(id: string) {
  try {
    await approvalAPI.approve(id)
    await Promise.all([loadData(), loadPendingCount()])
  } catch (e: any) {
    alert(e.response?.data?.message || '操作失败')
  }
}

async function handleReject(id: string) {
  const reason = prompt('请输入驳回原因（可选）：')
  try {
    await approvalAPI.reject(id, reason || undefined)
    await Promise.all([loadData(), loadPendingCount()])
  } catch (e: any) {
    alert(e.response?.data?.message || '操作失败')
  }
}

function goDetail(item: ApprovalItem) {
  router.push(`/daily/approval/${item.id}`)
}

function onFormSubmitted() {
  showForm.value = false
  loadData()
  loadPendingCount()
}

watch([currentType, currentStatus, viewMode], loadData)
onMounted(() => {
  loadData()
  loadPendingCount()
})
</script>

<style scoped>
.approval-page {
  padding: 16px;
  padding-bottom: 80px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  border-radius: 10px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 600;
}

.view-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid #222222;
  padding-bottom: 8px;
}

.view-tab {
  flex: 1;
  padding: 8px 12px;
  border: 1px solid #333333;
  border-radius: 8px;
  background: #111111;
  color: #C8C8C8;
  font-size: 13px;
  cursor: pointer;
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.view-tab.active {
  background: rgba(251, 0, 121, 0.1);
  border-color: #FB0079;
  color: #FB0079;
}

.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 18px;
  height: 18px;
  padding: 0 5px;
  border-radius: 9px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 600;
}

.type-tabs,
.status-tabs {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  margin-bottom: 12px;
}

.type-tab,
.status-tab {
  padding: 6px 12px;
  border: 1px solid #333333;
  border-radius: 999px;
  background: #111111;
  color: #C8C8C8;
  font-size: 12px;
  white-space: nowrap;
  cursor: pointer;
}

.type-tab.active,
.status-tab.active {
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
}

.approval-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 32px;
}

.approval-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}

.type-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: #333333;
  color: #C8C8C8;
}

.type-tag.leave { background: #FB0079; color: #fff; }
.type-tag.makeup { background: #FB0079; color: #fff; }
.type-tag.swap { background: #FB0079; color: #fff; }
.type-tag.expense { background: #FB0079; color: #fff; }

.status-tag {
  font-size: 11px;
  color: #7A7C80;
}

.status-tag.approved { color: #4CAF50; }
.status-tag.rejected { color: #FB0079; }

.employee {
  font-size: 14px;
  color: #FFFFFF;
  margin: 0;
}

.date {
  font-size: 12px;
  color: #C8C8C8;
  margin: 4px 0;
}

.approver {
  font-size: 11px;
  color: #2196f3;
  margin: 2px 0;
}

.reason {
  font-size: 12px;
  color: #7A7C80;
  margin: 4px 0 0;
}

.card-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}

.btn-reject,
.btn-approve {
  flex: 1;
  padding: 8px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  border: none;
}

.btn-reject {
  background: #333333;
  color: #C8C8C8;
}

.btn-approve {
  background: #FB0079;
  color: #FFFFFF;
}

.fab {
  position: fixed;
  right: 16px;
  bottom: 80px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 24px;
  border: none;
  box-shadow: 0 4px 12px rgba(251, 0, 121, 0.3);
  cursor: pointer;
}

/* ---- el-dialog 暗色主题覆盖 ---- */
.approval-form-dialog :deep(.el-dialog) {
  background: #111111;
  border-radius: 12px;
  max-width: 400px;
  margin: 0 auto;
}

.approval-form-dialog :deep(.el-dialog__header) {
  background: #111111;
  border-bottom: 1px solid #333333;
  margin-right: 0;
  padding: 16px;
}

.approval-form-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}

.approval-form-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #7A7C80;
}

.approval-form-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}
</style>
