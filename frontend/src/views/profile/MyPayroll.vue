<script setup lang="ts">
// 我的工资条列表（员工视角）
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { getMyPayroll, type MyPayrollItem } from '@/api/payroll'

const router = useRouter()
const items = ref<MyPayrollItem[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getMyPayroll()
    items.value = res.data.data
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function goDetail(item: MyPayrollItem) {
  router.push({ name: 'MyPayrollDetail', params: { id: item.id } })
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
  <div class="my-payroll">
    <div v-loading="loading" class="list">
      <div v-if="items.length === 0 && !loading" class="empty-state">
        暂无工资记录
      </div>
      <div
        v-for="item in items"
        :key="item.id"
        class="list-item"
        @click="goDetail(item)"
      >
        <div class="info">
          <div class="period">{{ item.period }}</div>
          <div class="status-tag" :class="item.status">{{ statusLabel(item.status) }}</div>
        </div>
        <div class="amount">
          <div class="label">实发</div>
          <div class="value">¥{{ item.net_pay.toFixed(2) }}</div>
        </div>
      </div>
    </div>

    <div class="privacy-tip">
      <span>仅本人可见工资条明细</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.my-payroll {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.list-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 14px 16px;
  cursor: pointer;

  &:hover {
    background-color: $color-divider;
  }
}

.info {
  display: flex;
  flex-direction: column;
  gap: 4px;

  .period {
    font-size: 15px;
    color: $brand-white;
    font-weight: 500;
  }
}

.status-tag {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  width: fit-content;

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

.amount {
  text-align: right;

  .label {
    font-size: 11px;
    color: #888;
  }

  .value {
    font-size: 18px;
    color: $brand-primary;
    font-weight: 700;
    font-family: $font-family-number;
  }
}

.privacy-tip {
  text-align: center;
  font-size: 11px;
  color: #555;
  padding: 8px;
}
</style>
