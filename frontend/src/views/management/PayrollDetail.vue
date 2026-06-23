<script setup lang="ts">
// 工资记录详情（店长视角）
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  getPayrollDetail,
  finalizePayroll,
  markPaidPayroll,
  type PayrollRecordDetail,
} from '@/api/payroll'

const route = useRoute()
const router = useRouter()

const recordId = computed(() => String(route.params.id || ''))
const detail = ref<PayrollRecordDetail | null>(null)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getPayrollDetail(recordId.value)
    detail.value = res.data.data
  } catch (e) {
    router.back()
  } finally {
    loading.value = false
  }
}

async function onFinalize() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm('确认此工资记录？确认后无法修改。', '确认工资', {
      type: 'warning',
    })
    await finalizePayroll([detail.value.id])
    ElMessage.success('已确认')
    await load()
  } catch (e) {
    /* ignore */
  }
}

async function onMarkPaid() {
  if (!detail.value) return
  try {
    await ElMessageBox.confirm('标记此工资为已发放？', '发放工资', { type: 'warning' })
    await markPaidPayroll([detail.value.id])
    ElMessage.success('已标记发放')
    await load()
  } catch (e) {
    /* ignore */
  }
}

const statusLabel = (s: string) => {
  const map: Record<string, string> = {
    draft: '待确认',
    confirmed: '已确认',
    paid: '已发放',
  }
  return map[s] ?? s
}

onMounted(load)
</script>

<template>
  <div class="payroll-detail" v-loading="loading">
    <div class="page-header">
      <span class="page-title">工资详情</span>
    </div>

    <div v-if="detail" class="content">
      <!-- 员工信息 -->
      <div class="card">
        <div class="emp-name">{{ detail.employee_name }}</div>
        <div class="emp-meta">
          <span>{{ detail.employee_role }}</span>
          <span>账期：{{ detail.period }}</span>
        </div>
        <div class="status-row">
          <span class="status-tag" :class="detail.status">
            {{ statusLabel(detail.status) }}
          </span>
          <span v-if="detail.kpi_coefficient !== 1" class="kpi-coef">
            KPI系数 ×{{ detail.kpi_coefficient.toFixed(2) }}
          </span>
        </div>
      </div>

      <!-- 实发金额 -->
      <div class="card net-card">
        <div class="net-label">实发工资</div>
        <div class="net-value">¥{{ detail.net_pay.toFixed(2) }}</div>
        <div class="net-detail">
          收入 ¥{{ detail.total_income.toFixed(2) }} - 扣款 ¥{{ detail.total_deduction.toFixed(2) }}
        </div>
      </div>

      <!-- 工资明细 -->
      <div class="card">
        <div class="section-title">工资明细</div>
        <div
          v-for="item in detail.items"
          :key="item.item_code"
          class="item-row"
          :class="item.item_type"
        >
          <div class="item-info">
            <div class="item-name">{{ item.item_name }}</div>
            <div class="item-source">{{ item.data_source }}</div>
          </div>
          <div class="item-amount" :class="item.item_type">
            {{ item.item_type === 'income' ? '+' : '-' }}¥{{ item.amount.toFixed(2) }}
          </div>
        </div>
      </div>

      <!-- 时间信息 -->
      <div class="card">
        <div class="section-title">时间信息</div>
        <div class="time-row">
          <span>生成时间</span>
          <span>{{ detail.generated_at || '-' }}</span>
        </div>
        <div class="time-row">
          <span>确认时间</span>
          <span>{{ detail.finalized_at || '-' }}</span>
        </div>
        <div class="time-row">
          <span>发放时间</span>
          <span>{{ detail.paid_at || '-' }}</span>
        </div>
        <div v-if="detail.notes" class="time-row">
          <span>备注</span>
          <span>{{ detail.notes }}</span>
        </div>
      </div>

      <!-- 操作按钮 -->
      <div v-if="detail.status === 'draft'" class="actions">
        <button class="btn-primary" @click="onFinalize">确认工资</button>
      </div>
      <div v-else-if="detail.status === 'confirmed'" class="actions">
        <button class="btn-primary" @click="onMarkPaid">标记已发放</button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payroll-detail {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;

  .page-title {
    font-size: 18px;
    font-weight: 600;
    color: $brand-white;
  }
}

.card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
}

.emp-name {
  font-size: 18px;
  color: $brand-white;
  font-weight: 600;
  margin-bottom: 4px;
}

.emp-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}

.status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;

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

.kpi-coef {
  font-size: 11px;
  color: $brand-primary;
}

.net-card {
  text-align: center;
  background: linear-gradient(135deg, $color-bg 0%, $color-black 100%);
  border: 1px solid $brand-primary;
}

.net-label {
  font-size: 12px;
  color: #888;
}

.net-value {
  font-size: 32px;
  font-weight: 700;
  color: $brand-primary;
  font-family: $font-family-number;
  margin: 6px 0;
}

.net-detail {
  font-size: 12px;
  color: #888;
}

.section-title {
  font-size: 13px;
  color: $brand-primary;
  margin-bottom: 12px;
  font-weight: 600;
}

.item-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid $color-divider;

  &:last-child {
    border-bottom: none;
  }
}

.item-info {
  .item-name {
    font-size: 14px;
    color: $brand-white;
  }

  .item-source {
    font-size: 11px;
    color: #888;
    margin-top: 2px;
  }
}

.item-amount {
  font-size: 14px;
  font-family: $font-family-number;
  font-weight: 600;

  &.income {
    color: $brand-primary;
  }
  &.deduction {
    color: #888;
  }
}

.time-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  font-size: 13px;

  span:first-child {
    color: #888;
  }

  span:last-child {
    color: $brand-white;
  }
}

.actions {
  display: flex;
  gap: 12px;

  button {
    flex: 1;
    height: 44px;
  }
}
</style>
