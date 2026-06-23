<template>
  <div class="my-kpi-page">
    <div class="page-header">
      <h1 class="page-title">我的 KPI</h1>
      <el-date-picker
        v-model="period"
        type="month"
        placeholder="选择月份"
        value-format="YYYY-MM"
        size="small"
        @change="load"
      />
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!data" class="empty">暂无考核数据</div>
    <template v-else>
      <div class="score-card">
        <div class="score-value">{{ data.total_score?.toFixed(1) ?? '--' }}</div>
        <div class="score-label">综合评分</div>
      </div>

      <div class="section-title">维度得分</div>
      <div class="dimension-list">
        <div v-for="(dim, idx) in data.details || []" :key="idx" class="dim-item">
          <div class="dim-top">
            <span class="dim-name">{{ dim.name }}</span>
            <span class="dim-score">{{ dim.score }}/{{ dim.weight }}</span>
          </div>
          <div class="dim-bar">
            <div class="dim-fill" :style="{ width: pct(dim.score, dim.weight) + '%' }"></div>
          </div>
        </div>
      </div>

      <div v-if="data.remark" class="remark">
        <div class="remark-title">店长评语</div>
        <div class="remark-body">{{ data.remark }}</div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { kpiResultAPI } from '@/api/kpi'

const period = ref(new Date().toISOString().slice(0, 7))
const loading = ref(false)
const data = ref<any>(null)

function pct(score: number, weight: number) {
  if (!weight) return 0
  return Math.min(100, Math.max(0, (score / weight) * 100))
}

async function load() {
  loading.value = true
  try {
    const res = await kpiResultAPI.my(period.value)
    const list = res.data?.data || []
    data.value = list[0] || null
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.my-kpi-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px 16px 96px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}
.loading, .empty {
  color: #7A7C80;
  text-align: center;
  padding: 40px 0;
}
.score-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 24px;
  text-align: center;
  margin-bottom: 20px;
}
.score-value {
  font-family: 'Poppins', sans-serif;
  font-size: 48px;
  font-weight: 700;
  color: #FB0079;
  line-height: 1;
}
.score-label {
  font-size: 13px;
  color: #7A7C80;
  margin-top: 8px;
}
.section-title {
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
  margin-bottom: 12px;
}
.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}
.dim-item {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 14px;
}
.dim-top {
  display: flex;
  justify-content: space-between;
  margin-bottom: 8px;
}
.dim-name {
  font-size: 14px;
  color: #FFFFFF;
}
.dim-score {
  font-family: 'Poppins', sans-serif;
  font-size: 14px;
  color: #FB0079;
}
.dim-bar {
  height: 6px;
  background: #222222;
  border-radius: 3px;
  overflow: hidden;
}
.dim-fill {
  height: 100%;
  background: linear-gradient(90deg, #FB0079, #FB0079);
  border-radius: 3px;
}
.remark {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 14px;
}
.remark-title {
  font-size: 13px;
  color: #7A7C80;
  margin-bottom: 6px;
}
.remark-body {
  font-size: 14px;
  color: #C8C8C8;
  line-height: 1.5;
}
</style>
