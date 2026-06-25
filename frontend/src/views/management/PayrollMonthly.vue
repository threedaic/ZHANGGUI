<script setup lang="ts">
// 店长月度工资汇总（4步审批流：生成→复核→确认→发放）
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  generatePayroll,
  getMonthlyPayroll,
  reviewPayroll,
  finalizePayroll,
  markPaidPayroll,
  type PayrollMonthlyItem,
  type PayrollMonthlySummary,
} from '@/api/payroll'
import { getPeriod, type PeriodInfo } from '@/api/period'
import { storeAPI } from '@/api/store'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const router = useRouter()
const auth = useAuthStore()

const period = ref<string>(dayjs().format('YYYY-MM'))
const summary = ref<PayrollMonthlySummary | null>(null)
const periodInfo = ref<PeriodInfo | null>(null)
const loading = ref(false)
const generating = ref(false)
const reviewing = ref(false)
const finalizing = ref(false)
const paying = ref(false)
const selectedIds = ref<string[]>([])
const payrollDay = ref<number>(5)

// 角色判断
const role = computed(() => auth.role)
const canReview = computed(() =>
  ['boss', 'store_manager', 'accountant'].includes(role.value)
)
const canConfirm = computed(() =>
  ['boss', 'store_manager'].includes(role.value)
)
const canPay = computed(() =>
  ['boss', 'store_manager', 'accountant'].includes(role.value)
)

const isLocked = computed(
  () => periodInfo.value?.status === 'locked' || periodInfo.value?.status === 'closed'
)
const isClosed = computed(() => periodInfo.value?.status === 'closed')

// 选中项的状态分布
const selectedItems = computed<PayrollMonthlyItem[]>(() =>
  summary.value?.items.filter((i) => selectedIds.value.includes(i.record_id)) ?? []
)
const selectedHasDraft = computed(() => selectedItems.value.some((i) => i.status === 'draft'))
const selectedHasReviewed = computed(() => selectedItems.value.some((i) => i.status === 'reviewed'))
const selectedHasConfirmed = computed(() => selectedItems.value.some((i) => i.status === 'confirmed'))

// 流程进度：根据全店状态汇总判断当前所处步骤
// step: 1=生成 2=复核 3=确认 4=发放
const flowStep = computed(() => {
  const s = summary.value?.status_summary ?? {}
  const has = (k: string) => (s[k] ?? 0) > 0
  if (!summary.value || summary.value.items.length === 0) return 0 // 未生成
  if (has('draft')) return 2 // 等待复核
  if (has('reviewed')) return 3 // 等待确认
  if (has('confirmed')) return 4 // 等待发放
  return 5 // 全部已发放
})

const flowSteps = [
  { code: 'generate', label: '系统算薪', desc: '自动汇总考勤/业绩/KPI' },
  { code: 'review', label: '会计复核', desc: '会计核对金额' },
  { code: 'confirm', label: '老板确认', desc: '老板点头通过' },
  { code: 'pay', label: '会计发放', desc: '操作网银发放' },
]

async function load() {
  loading.value = true
  try {
    const [sumRes, periodRes] = await Promise.all([
      getMonthlyPayroll(period.value),
      getPeriod(period.value).catch(() => null),
    ])
    summary.value = sumRes.data.data
    periodInfo.value = periodRes?.data.data ?? null
  } catch (e) {
    summary.value = null
  } finally {
    loading.value = false
  }
}

async function onGenerate() {
  if (isLocked.value) {
    ElMessage.warning('账期已锁定，无法重新生成')
    return
  }
  try {
    await ElMessageBox.confirm(
      `将为 ${period.value} 重新生成所有员工工资，已有数据会被覆盖。是否继续？`,
      '生成工资',
      { type: 'warning' }
    )
    generating.value = true
    const res = await generatePayroll(period.value)
    ElMessage.success(`已生成 ${res.data.data.count} 条工资记录`)
    await load()
  } catch (e) {
    /* 取消或错误 */
  } finally {
    generating.value = false
  }
}

async function onReview() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要复核的工资记录')
    return
  }
  if (!selectedHasDraft.value) {
    ElMessage.warning('所选记录中没有待复核（草稿）状态')
    return
  }
  try {
    await ElMessageBox.confirm(
      `复核 ${selectedIds.value.length} 条工资记录？复核后提交老板确认。`,
      '会计复核',
      { type: 'warning' }
    )
    reviewing.value = true
    await reviewPayroll(selectedIds.value)
    ElMessage.success('已复核，等待老板确认')
    selectedIds.value = []
    await load()
  } catch (e) {
    /* ignore */
  } finally {
    reviewing.value = false
  }
}

async function onFinalize() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要确认的工资记录')
    return
  }
  if (!selectedHasReviewed.value) {
    ElMessage.warning('所选记录中没有已复核状态（需先会计复核）')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认 ${selectedIds.value.length} 条工资记录？确认后将无法修改。`,
      '老板确认',
      { type: 'warning' }
    )
    finalizing.value = true
    await finalizePayroll(selectedIds.value)
    ElMessage.success('已确认，可由会计发放')
    selectedIds.value = []
    await load()
  } catch (e) {
    /* ignore */
  } finally {
    finalizing.value = false
  }
}

async function onMarkPaid() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要发放的工资记录')
    return
  }
  if (!selectedHasConfirmed.value) {
    ElMessage.warning('所选记录中没有已确认状态（需先老板确认）')
    return
  }
  try {
    await ElMessageBox.confirm(
      `标记 ${selectedIds.value.length} 条工资为已发放？请确认已通过网银打款。`,
      '会计发放',
      { type: 'warning' }
    )
    paying.value = true
    await markPaidPayroll(selectedIds.value)
    ElMessage.success('已标记发放')
    selectedIds.value = []
    await load()
  } catch (e) {
    /* ignore */
  } finally {
    paying.value = false
  }
}

function toggleSelect(id: string) {
  const idx = selectedIds.value.indexOf(id)
  if (idx >= 0) selectedIds.value.splice(idx, 1)
  else selectedIds.value.push(id)
}

function goDetail(item: PayrollMonthlyItem) {
  router.push({ name: 'PayrollDetail', params: { id: item.record_id } })
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = {
    draft: '待复核',
    reviewed: '已复核',
    confirmed: '已确认',
    paid: '已发放',
  }
  return map[s] ?? s
}

watch(period, load)
onMounted(async () => {
  await load()
  try {
    const res = await storeAPI.getSettings()
    payrollDay.value = res.data.data.payroll_day_of_month
  } catch { /* silent */ }
})
</script>

<template>
  <div class="payroll-monthly">
    <!-- 月份 + 操作 -->
    <div class="top-bar">
      <input v-model="period" type="month" class="month-input" />
      <button
        class="btn-primary small"
        :disabled="generating || isLocked"
        @click="onGenerate"
      >
        {{ generating ? '生成中...' : '生成工资' }}
      </button>
    </div>

    <!-- 账期状态 -->
    <div v-if="periodInfo" class="period-status">
      <span class="status-tag" :class="periodInfo.status">
        {{ periodInfo.status === 'open' ? '开放中' : periodInfo.status === 'locked' ? '已锁定' : '已关账' }}
      </span>
      <span v-if="isLocked" class="lock-tip">账期已锁定，无法修改</span>
    </div>

    <!-- 流程进度条 -->
    <div v-if="summary && summary.items.length > 0" class="flow-progress">
      <div
        v-for="(step, idx) in flowSteps"
        :key="step.code"
        class="flow-node"
        :class="{
          done: flowStep > idx + 1,
          active: flowStep === idx + 1,
          waiting: flowStep < idx + 1,
        }"
      >
        <div class="flow-circle">
          <span v-if="flowStep > idx + 1" class="check-icon">✓</span>
          <span v-else class="flow-num">{{ idx + 1 }}</span>
        </div>
        <div class="flow-text">
          <div class="flow-label">{{ step.label }}</div>
          <div class="flow-desc">{{ step.desc }}</div>
        </div>
        <div v-if="idx < flowSteps.length - 1" class="flow-line" />
      </div>
    </div>

    <!-- 薪资配置快捷入口 -->
    <div class="payroll-config-bar">
      <div class="config-info">
        <span class="config-label">发薪日</span>
        <span class="config-value">每月 {{ payrollDay }} 日</span>
      </div>
      <div class="config-actions">
        <button class="config-link" @click="router.push({ name: 'SalaryRulesSetting' })">
          薪资规则
        </button>
        <button class="config-link" @click="router.push({ name: 'PayrollFormula' })">
          工资项公式
        </button>
      </div>
    </div>

    <!-- 汇总卡片 -->
    <div v-if="summary" class="summary-card">
      <div class="summary-row">
        <div class="summary-item">
          <div class="label">收入合计</div>
          <div class="value income">¥{{ summary.total_income.toFixed(2) }}</div>
        </div>
        <div class="summary-item">
          <div class="label">扣款合计</div>
          <div class="value deduction">¥{{ summary.total_deduction.toFixed(2) }}</div>
        </div>
        <div class="summary-item">
          <div class="label">实发合计</div>
          <div class="value net">¥{{ summary.total_net_pay.toFixed(2) }}</div>
        </div>
      </div>
    </div>

    <!-- 批量操作（按角色+状态显示） -->
    <div
      v-if="summary && summary.items.length > 0 && !isClosed"
      class="batch-actions"
    >
      <span class="selected-count">已选 {{ selectedIds.length }} 项</span>
      <button
        v-if="canReview"
        class="btn-ghost small"
        :disabled="isLocked || reviewing || !selectedHasDraft"
        @click="onReview"
      >
        {{ reviewing ? '复核中...' : '会计复核' }}
      </button>
      <button
        v-if="canConfirm"
        class="btn-ghost small"
        :disabled="isLocked || finalizing || !selectedHasReviewed"
        @click="onFinalize"
      >
        {{ finalizing ? '确认中...' : '老板确认' }}
      </button>
      <button
        v-if="canPay"
        class="btn-ghost small"
        :disabled="paying || !selectedHasConfirmed"
        @click="onMarkPaid"
      >
        {{ paying ? '发放中...' : '会计发放' }}
      </button>
    </div>

    <!-- 工资列表 -->
    <div v-loading="loading" class="list">
      <div v-if="summary && summary.items.length === 0 && !loading" class="empty-state">
        暂无工资数据，点击「生成工资」开始
      </div>
      <div
        v-for="item in summary?.items"
        :key="item.record_id"
        class="list-item"
        @click="goDetail(item)"
      >
        <div class="check" @click.stop>
          <input
            type="checkbox"
            :checked="selectedIds.includes(item.record_id)"
            @change="toggleSelect(item.record_id)"
          />
        </div>
        <div class="info">
          <div class="name">{{ item.employee_name }}</div>
          <div class="role">{{ item.employee_role }}</div>
        </div>
        <div class="amount">
          <div class="net">¥{{ item.net_pay.toFixed(2) }}</div>
          <div class="status-tag" :class="item.status">{{ statusLabel(item.status) }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payroll-monthly {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-bar {
  display: flex;
  gap: 8px;
}

.month-input {
  flex: 1;
  height: 38px;
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 0 10px;
  color: $brand-white;
  font-size: 14px;
  outline: none;
}

.btn-primary.small,
.btn-ghost.small {
  padding: 8px 14px;
  font-size: 12px;
}

.period-status {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

// 流程进度条
.flow-progress {
  display: flex;
  align-items: flex-start;
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 14px 12px;
}

.flow-node {
  position: relative;
  display: flex;
  flex: 1;
  align-items: flex-start;
  gap: 8px;

  &:last-child {
    flex: 0 0 auto;
  }
}

.flow-circle {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  border: 2px solid $color-divider;
  background-color: $color-bg;
  color: #888;
  transition: all 0.2s;
}

.flow-num {
  line-height: 1;
}

.check-icon {
  line-height: 1;
  color: $brand-white;
}

.flow-line {
  position: absolute;
  top: 12px;
  left: 32px;
  right: -50%;
  height: 2px;
  background-color: $color-divider;
  z-index: 0;
}

.flow-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  z-index: 1;
}

.flow-label {
  font-size: 12px;
  color: #888;
  font-weight: 500;
}

.flow-desc {
  font-size: 10px;
  color: #666;
}

// 状态：已完成
.flow-node.done {
  .flow-circle {
    background-color: $brand-primary;
    border-color: $brand-primary;
  }
  .flow-line {
    background-color: $brand-primary;
  }
  .flow-label {
    color: $brand-white;
  }
}

// 状态：进行中
.flow-node.active {
  .flow-circle {
    background-color: transparent;
    border-color: $brand-primary;
    color: $brand-primary;
    box-shadow: 0 0 0 3px rgba(251, 0, 121, 0.15);
  }
  .flow-label {
    color: $brand-primary;
    font-weight: 600;
  }
}

// 状态：等待
.flow-node.waiting {
  .flow-circle {
    opacity: 0.5;
  }
}

// 薪资配置快捷入口
.payroll-config-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 10px 14px;
}

.config-info {
  display: flex;
  align-items: center;
  gap: 8px;

  .config-label {
    font-size: 12px;
    color: #888;
  }

  .config-value {
    font-size: 13px;
    color: $brand-white;
    font-weight: 600;
    font-family: $font-family-number;
  }
}

.config-actions {
  display: flex;
  gap: 4px;
}

.config-link {
  padding: 4px 10px;
  font-size: 11px;
  color: $brand-primary;
  background: transparent;
  border: 1px solid $brand-primary;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    background-color: rgba(251, 0, 121, 0.1);
  }
}

.status-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;

  &.open {
    background-color: rgba(251, 0, 121, 0.15);
    color: $brand-primary;
  }
  &.locked {
    background-color: $color-divider;
    color: $brand-white;
  }
  &.closed {
    background-color: #333;
    color: #888;
  }
  &.draft {
    background-color: $color-divider;
    color: $brand-white;
  }
  &.reviewed {
    background-color: rgba(255, 180, 0, 0.15);
    color: #ffb400;
  }
  &.confirmed {
    background-color: rgba(251, 0, 121, 0.15);
    color: $brand-primary;
  }
  &.paid {
    background-color: #333;
    color: #888;
  }
}

.lock-tip {
  color: #888;
}

.summary-card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
}

.summary-row {
  display: flex;
  justify-content: space-between;
}

.summary-item {
  text-align: center;
  flex: 1;

  .label {
    font-size: 11px;
    color: #888;
    margin-bottom: 4px;
  }

  .value {
    font-size: 16px;
    font-weight: 700;
    font-family: $font-family-number;

    &.income {
      color: $brand-primary;
    }
    &.deduction {
      color: #888;
    }
    &.net {
      color: $brand-white;
    }
  }
}

.batch-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  background-color: $color-bg;
  border-radius: $radius-sm;

  .selected-count {
    font-size: 12px;
    color: #888;
    margin-right: auto;
  }
}

.list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.list-item {
  display: flex;
  align-items: center;
  background-color: $color-bg;
  border-radius: $radius-sm;
  padding: 12px;
  cursor: pointer;

  &:hover {
    background-color: $color-divider;
  }
}

.check {
  margin-right: 12px;

  input {
    width: 18px;
    height: 18px;
    accent-color: $brand-primary;
  }
}

.info {
  flex: 1;

  .name {
    font-size: 14px;
    color: $brand-white;
    font-weight: 500;
  }

  .role {
    font-size: 11px;
    color: #888;
    margin-top: 2px;
  }
}

.amount {
  text-align: right;

  .net {
    font-size: 16px;
    color: $brand-primary;
    font-weight: 600;
    font-family: $font-family-number;
  }
}
</style>
