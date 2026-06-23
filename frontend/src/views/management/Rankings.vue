<script setup lang="ts">
// 排行榜页面（4维榜单，全员可见，脱敏：不显示工资金额）
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getLeaderboard,
  calculateRankings,
  RANK_TYPE_LABELS,
  type RankType,
  type LeaderboardItem,
} from '@/api/ranking'
import { useAuthStore } from '@/stores/auth'
import dayjs from 'dayjs'

const auth = useAuthStore()

const period = ref<string>(dayjs().format('YYYY-MM'))
const activeType = ref<RankType>('performance')
const items = ref<LeaderboardItem[]>([])
const loading = ref(false)
const calculating = ref(false)

const rankTypes = Object.keys(RANK_TYPE_LABELS) as RankType[]

// 各排名类型的展示值单位
const unitMap: Record<RankType, string> = {
  performance: '元',
  kpi: '分',
  attendance: '天',
  rating: '分',
}

// 各排名类型的展示值字段
const valueFieldMap: Record<RankType, string> = {
  performance: 'total_amount',
  kpi: 'total_score',
  attendance: 'present_days',
  rating: 'avg_score',
}

// 各排名类型的副信息字段
const subInfoMap: Record<RankType, { field: string; label: string }[]> = {
  performance: [
    { field: 'booking', label: '订桌' },
    { field: 'wework_payment', label: '企微' },
  ],
  kpi: [{ field: 'coefficient', label: '系数' }],
  attendance: [
    { field: 'late_count', label: '迟到' },
    { field: 'absent_count', label: '旷工' },
  ],
  rating: [{ field: 'rating_count', label: '评价数' }],
}

async function loadLeaderboard() {
  loading.value = true
  try {
    const res = await getLeaderboard(period.value, activeType.value, 50)
    items.value = res.data.data.items
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

async function onCalculate() {
  calculating.value = true
  try {
    const res = await calculateRankings(period.value, activeType.value)
    ElMessage.success(`已计算 ${res.data.data.total} 条排名`)
    await loadLeaderboard()
  } catch (e) {
    /* ignore */
  } finally {
    calculating.value = false
  }
}

function formatValue(item: LeaderboardItem): string {
  const v = item.rank_value
  if (activeType.value === 'performance') {
    return `¥${v.toFixed(2)}`
  }
  if (activeType.value === 'attendance') {
    return `${v} 天`
  }
  return v.toFixed(2)
}

function getSubInfo(item: LeaderboardItem): string {
  const fields = subInfoMap[activeType.value]
  return fields
    .map((f) => {
      const v = (item.detail as Record<string, unknown>)?.[f.field]
      if (v === undefined || v === null) return ''
      if (f.field === 'total_amount' || f.field === 'booking' || f.field === 'wework_payment') {
        return `${f.label}: ¥${Number(v).toFixed(0)}`
      }
      return `${f.label}: ${v}`
    })
    .filter(Boolean)
    .join('  ')
}

watch([period, activeType], loadLeaderboard)
onMounted(loadLeaderboard)
</script>

<template>
  <div class="rankings-page">
    <!-- 月份选择 -->
    <div class="period-bar">
      <input v-model="period" type="month" class="month-input" />
      <button
        v-if="auth.isManager"
        class="btn-primary small"
        :disabled="calculating"
        @click="onCalculate"
      >
        {{ calculating ? '计算中...' : '重新计算' }}
      </button>
    </div>

    <!-- 排名类型 Tab -->
    <div class="type-tabs">
      <button
        v-for="t in rankTypes"
        :key="t"
        class="type-tab"
        :class="{ active: activeType === t }"
        @click="activeType = t"
      >
        {{ RANK_TYPE_LABELS[t] }}
      </button>
    </div>

    <!-- 榜单 -->
    <div v-loading="loading" class="leaderboard">
      <div v-if="items.length === 0 && !loading" class="empty-state">
        暂无排名数据，{{ auth.isManager ? '点击「重新计算」生成' : '请等待店长计算' }}
      </div>

      <!-- 前三名突出展示 -->
      <div v-if="items.length >= 3" class="podium">
        <div v-for="i in [1, 0, 2]" :key="i" class="podium-item" :class="`rank-${i + 1}`">
          <div class="podium-rank">{{ i + 1 }}</div>
          <div class="podium-name">{{ items[i]?.employee_name }}</div>
          <div class="podium-value">{{ formatValue(items[i]) }}</div>
        </div>
      </div>

      <!-- 完整榜单 -->
      <div class="list">
        <div
          v-for="item in items"
          :key="item.employee_id"
          class="list-item"
          :class="{ top: item.rank_position <= 3 }"
        >
          <div class="rank-num" :class="`rank-${item.rank_position}`">
            {{ item.rank_position }}
          </div>
          <div class="info">
            <div class="name">{{ item.employee_name }}</div>
            <div v-if="getSubInfo(item)" class="sub">{{ getSubInfo(item) }}</div>
          </div>
          <div class="value">{{ formatValue(item) }}</div>
        </div>
      </div>
    </div>

    <div class="privacy-tip">
      <span>仅显示排名与数值，不涉及工资金额</span>
    </div>
  </div>
</template>

<style scoped lang="scss">
.rankings-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.period-bar {
  display: flex;
  gap: 8px;
  align-items: center;
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

.btn-primary.small {
  padding: 8px 14px;
  font-size: 12px;
}

.type-tabs {
  display: flex;
  gap: 4px;
  background-color: $color-bg;
  border-radius: $radius-sm;
  padding: 4px;
}

.type-tab {
  flex: 1;
  background: transparent;
  border: none;
  color: #888;
  padding: 8px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 4px;

  &.active {
    background-color: $brand-primary;
    color: $brand-white;
    font-weight: 600;
  }
}

.podium {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  gap: 8px;
  padding: 16px 0;
  background-color: $color-bg;
  border-radius: $radius-md;
  margin-bottom: 8px;
}

.podium-item {
  flex: 1;
  text-align: center;
  padding: 12px 4px;
  border-radius: $radius-sm;
  background-color: $color-black;

  &.rank-1 {
    height: 110px;
    border: 1px solid $brand-primary;
  }
  &.rank-2 {
    height: 90px;
  }
  &.rank-3 {
    height: 80px;
  }
}

.podium-rank {
  font-size: 24px;
  font-weight: 700;
  color: $brand-primary;
  font-family: $font-family-number;
}

.podium-name {
  font-size: 13px;
  color: $brand-white;
  margin: 4px 0;
}

.podium-value {
  font-size: 12px;
  color: #888;
  font-family: $font-family-number;
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
  border: 1px solid transparent;

  &.top {
    border-color: rgba(251, 0, 121, 0.3);
  }
}

.rank-num {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background-color: $color-divider;
  color: #888;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 13px;
  margin-right: 12px;
  font-family: $font-family-number;

  &.rank-1 {
    background-color: $brand-primary;
    color: $brand-white;
  }
  &.rank-2 {
    background-color: #555;
    color: $brand-white;
  }
  &.rank-3 {
    background-color: #333;
    color: $brand-white;
  }
}

.info {
  flex: 1;

  .name {
    font-size: 14px;
    color: $brand-white;
    font-weight: 500;
  }

  .sub {
    font-size: 11px;
    color: #888;
    margin-top: 2px;
  }
}

.value {
  font-size: 14px;
  color: $brand-primary;
  font-weight: 600;
  font-family: $font-family-number;
}

.privacy-tip {
  text-align: center;
  font-size: 11px;
  color: #555;
  padding: 8px;
}
</style>
