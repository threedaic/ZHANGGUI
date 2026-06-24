<script setup lang="ts">
// 店长月度工资汇总
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  generatePayroll,
  getMonthlyPayroll,
  finalizePayroll,
  markPaidPayroll,
  type PayrollMonthlyItem,
  type PayrollMonthlySummary,
} from '@/api/payroll'
import { getPeriod, type PeriodInfo } from '@/api/period'
import { storeAPI } from '@/api/store'
import dayjs from 'dayjs'

const router = useRouter()

const period = ref<string>(dayjs().format('YYYY-MM'))
const summary = ref<PayrollMonthlySummary | null>(null)
const periodInfo = ref<PeriodInfo | null>(null)
const loading = ref(false)
const generating = ref(false)
const selectedIds = ref<string[]>([])
const payrollDay = ref<number>(5)

const isLocked = computed(
  () => periodInfo.value?.status === 'locked' || periodInfo.value?.status === 'closed'
)
const isClosed = computed(() => periodInfo.value?.status === 'closed')

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

async function onFinalize() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要确认的工资记录')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认 ${selectedIds.value.length} 条工资记录？确认后将无法修改。`,
      '确认工资',
      { type: 'warning' }
    )
    await finalizePayroll(selectedIds.value)
    ElMessage.success('已确认')
    selectedIds.value = []
    await load()
  } catch (e) {
    /* ignore */
  }
}

async function onMarkPaid() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请先勾选要标记发放的工资记录')
    return
  }
  try {
    await ElMessageBox.confirm(
      `标记 ${selectedIds.value.length} 条工资为已发放？`,
      '发放工资',
      { type: 'warning' }
    )
    await markPaidPayroll(selectedIds.value)
    ElMessage.success('已标记发放')
    selectedIds.value = []
    await load()
  } catch (e) {
    /* ignore */
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
    draft: '待确认',
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
        <button class="config-link" @click="router.push({ name: 'PayrollConfig' })">
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

    <!-- 批量操作 -->
    <div v-if="summary && summary.items.length > 0 && !isClosed" class="batch-actions">
      <span class="selected-count">已选 {{ selectedIds.length }} 项</span>
      <button class="btn-ghost small" :disabled="isLocked" @click="onFinalize">
        确认工资
      </button>
      <button class="btn-ghost small" @click="onMarkPaid">标记发放</button>
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
