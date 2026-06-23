<script setup lang="ts">
// 我的排名（员工视角，4维汇总）
import { ref, onMounted, watch } from 'vue'
import { getMyRankings, RANK_TYPE_LABELS, type MyRanking } from '@/api/ranking'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const auth = useAuthStore()
const period = ref<string>(dayjs().format('YYYY-MM'))
const rankings = ref<MyRanking[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await getMyRankings(period.value)
    rankings.value = res.data.data
  } catch (e) {
    rankings.value = []
  } finally {
    loading.value = false
  }
}

watch(period, load)
onMounted(load)

function formatValue(r: MyRanking): string {
  if (r.rank_type === 'performance') return `¥${r.rank_value.toFixed(2)}`
  if (r.rank_type === 'attendance') return `${r.rank_value} 天`
  return r.rank_value.toFixed(2)
}
</script>

<template>
  <div class="my-rankings">
    <div class="period-bar">
      <input v-model="period" type="month" class="month-input" />
    </div>

    <div v-loading="loading" class="cards">
      <div v-if="rankings.length === 0 && !loading" class="empty-state">
        暂无排名数据
      </div>
      <div v-for="r in rankings" :key="r.rank_type" class="rank-card">
        <div class="card-header">
          <span class="type">{{ RANK_TYPE_LABELS[r.rank_type as keyof typeof RANK_TYPE_LABELS] }}</span>
          <span class="position">第 {{ r.rank_position }} 名 / 共 {{ r.total_count }} 人</span>
        </div>
        <div class="card-value">{{ formatValue(r) }}</div>
        <div class="progress-bar">
          <div
            class="progress-fill"
            :style="{
              width: r.total_count > 0 ? ((r.total_count - r.rank_position + 1) / r.total_count) * 100 + '%' : '0%',
            }"
          ></div>
        </div>
      </div>
    </div>

    <div class="privacy-tip">
      <span>排名透明激励，工资金额仅本人可见</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.my-rankings {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.period-bar {
  display: flex;
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

.cards {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.rank-card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
  border: 1px solid $color-divider;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;

  .type {
    font-size: 14px;
    color: $brand-white;
    font-weight: 600;
  }

  .position {
    font-size: 12px;
    color: $brand-primary;
  }
}

.card-value {
  font-size: 24px;
  font-weight: 700;
  color: $brand-primary;
  font-family: $font-family-number;
  margin-bottom: 12px;
}

.progress-bar {
  height: 6px;
  background-color: $color-black;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: $brand-primary;
  transition: width 0.3s;
}

.privacy-tip {
  text-align: center;
  font-size: 11px;
  color: #555;
  padding: 8px;
}
</style>
