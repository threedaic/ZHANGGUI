<script setup lang="ts">
// 我的工资条详情（员工视角，只读）
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getPayrollDetail, type PayrollRecordDetail } from '@/api/payroll'

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
  <div class="my-payroll-detail" v-loading="loading">
    <div class="page-header">
      <span class="page-title">我的工资条</span>
    </div>

    <div v-if="detail" class="content">
      <!-- 月份与状态 -->
      <div class="card period-card">
        <div class="period">{{ detail.period }}</div>
        <span class="status-tag" :class="detail.status">
          {{ statusLabel(detail.status) }}
        </span>
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
      </div>

      <div class="privacy-tip">
        此工资条仅本人可见，请勿外传
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.my-payroll-detail {
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

.period-card {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .period {
    font-size: 18px;
    color: $brand-white;
    font-weight: 600;
  }
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

.privacy-tip {
  text-align: center;
  font-size: 11px;
  color: #555;
  padding: 8px;
}
</style>
