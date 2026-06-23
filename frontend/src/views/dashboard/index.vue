<template>
  <div class="dashboard">
    <!-- Header -->
    <div class="dash-header">
      <h1 class="dash-title">数据看板</h1>
      <span class="dash-time" v-if="data?.updated_at">更新于 {{ formatTime(data.updated_at) }}</span>
    </div>

    <div class="dash-content" v-loading="loading">
      <!-- Block 1: 今日营收 -->
      <div class="card revenue-card">
        <div class="card-label">今日营收</div>
        <div class="revenue-amount">
          <span class="currency">¥</span>
          <span class="amount">{{ formatMoney(data?.revenue.today_revenue) }}</span>
        </div>
        <div class="revenue-growth" :class="growthClass">
          <span class="growth-arrow">{{ growthArrow }}</span>
          <span>{{ growthText }}</span>
          <span class="growth-label">较昨日</span>
        </div>
        <div class="revenue-subs">
          <div class="sub-item">
            <span class="sub-val">{{ data?.revenue.total_orders ?? '-' }}</span>
            <span class="sub-lbl">订单数</span>
          </div>
          <div class="sub-item">
            <span class="sub-val">{{ data?.revenue.total_guests ?? '-' }}</span>
            <span class="sub-lbl">客流量</span>
          </div>
          <div class="sub-item">
            <span class="sub-val">¥{{ formatMoney(data?.revenue.avg_order_value) }}</span>
            <span class="sub-lbl">客单价</span>
          </div>
        </div>
      </div>

      <!-- Block 2: 营收构成 -->
      <div class="card breakdown-card">
        <div class="card-label">营收构成</div>
        <div class="breakdown-bars">
          <div class="bar-row">
            <div class="bar-label">酒水</div>
            <div class="bar-track">
              <div class="bar-fill bar-bottle" :style="{ width: pct(data?.breakdown.bottle_pct) }"></div>
            </div>
            <div class="bar-val">¥{{ formatMoney(data?.breakdown.bottle_sales) }}</div>
          </div>
          <div class="bar-row">
            <div class="bar-label">充值卡</div>
            <div class="bar-track">
              <div class="bar-fill bar-card" :style="{ width: pct(data?.breakdown.card_pct) }"></div>
            </div>
            <div class="bar-val">¥{{ formatMoney(data?.breakdown.card_sales) }}</div>
          </div>
          <div class="bar-row">
            <div class="bar-label">其他</div>
            <div class="bar-track">
              <div class="bar-fill bar-other" :style="{ width: pct(data?.breakdown.other_pct) }"></div>
            </div>
            <div class="bar-val">¥{{ formatMoney(data?.breakdown.other_sales) }}</div>
          </div>
        </div>
        <div class="breakdown-total">合计 ¥{{ formatMoney(data?.breakdown.total) }}</div>
      </div>

      <!-- Block 3: 近7天营收趋势 -->
      <div class="card chart-card">
        <div class="card-label">近7天营收趋势</div>
        <div ref="chartRef" class="chart-container"></div>
      </div>

      <!-- Block 4: 顾客评分 -->
      <div class="card rating-card">
        <div class="card-label">顾客评分</div>
        <div class="rating-main">
          <div class="rating-score">
            <span class="score-num">{{ data?.rating.avg_score ?? '-' }}</span>
            <span class="score-unit">分</span>
          </div>
          <div class="rating-stats">
            <div class="stat-row">
              <span class="stat-lbl">今日评价</span>
              <span class="stat-val">{{ data?.rating.total_ratings ?? 0 }}条</span>
            </div>
            <div class="stat-row">
              <span class="stat-lbl">低分预警</span>
              <span class="stat-val alert-count" v-if="(data?.rating.low_score_count ?? 0) > 0">
                {{ data?.rating.low_score_count }}条
              </span>
              <span class="stat-val" v-else>无</span>
            </div>
          </div>
        </div>
        <!-- Low-score alerts -->
        <div class="alert-list" v-if="data?.rating.alerts?.length">
          <div class="alert-item" v-for="alert in data.rating.alerts" :key="alert.id">
            <div class="alert-head">
              <span class="alert-table">{{ alert.table_no }}桌</span>
              <span class="alert-score">{{ alert.overall_score }}分</span>
            </div>
            <div class="alert-comment" v-if="alert.comment">{{ alert.comment }}</div>
          </div>
        </div>
        <div class="no-alerts" v-else-if="data?.rating">
          暂无低分预警
        </div>
      </div>

      <!-- Block 5: 今日订桌 -->
      <div class="card booking-card">
        <div class="card-label">今日订桌</div>
        <div class="booking-grid">
          <div class="booking-item">
            <span class="booking-num booking-confirmed">{{ data?.booking.confirmed ?? 0 }}</span>
            <span class="booking-lbl">已订</span>
          </div>
          <div class="booking-item">
            <span class="booking-num">{{ data?.booking.total_tables ?? 0 }}</span>
            <span class="booking-lbl">总桌</span>
          </div>
          <div class="booking-item">
            <span class="booking-num booking-available">{{ data?.booking.available ?? 0 }}</span>
            <span class="booking-lbl">空闲</span>
          </div>
        </div>
      </div>

      <!-- Block 6: 今日考勤 -->
      <div class="card attendance-card">
        <div class="card-label">今日考勤</div>
        <div class="attendance-grid">
          <div class="att-item">
            <span class="att-num">{{ data?.attendance.scheduled_count ?? 0 }}</span>
            <span class="att-lbl">应出勤</span>
          </div>
          <div class="att-item">
            <span class="att-num att-actual">{{ data?.attendance.actual_count ?? 0 }}</span>
            <span class="att-lbl">实际出勤</span>
          </div>
          <div class="att-item">
            <span class="att-num att-warn" v-if="(data?.attendance.late_count ?? 0) > 0">{{ data?.attendance.late_count }}</span>
            <span class="att-num" v-else>0</span>
            <span class="att-lbl">迟到</span>
          </div>
          <div class="att-item">
            <span class="att-num att-danger" v-if="(data?.attendance.absent_count ?? 0) > 0">{{ data?.attendance.absent_count }}</span>
            <span class="att-num" v-else>0</span>
            <span class="att-lbl">旷工</span>
          </div>
          <div class="att-item">
            <span class="att-num att-warn" v-if="(data?.attendance.early_count ?? 0) > 0">{{ data?.attendance.early_count }}</span>
            <span class="att-num" v-else>0</span>
            <span class="att-lbl">早退</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts'
import { dashboardAPI, type DashboardData } from '@/api/dashboard'

const loading = ref(true)
const data = ref<DashboardData | null>(null)
const chartRef = ref<HTMLElement | null>(null)
let chartInstance: echarts.ECharts | null = null

// Growth display helpers
const growthClass = computed(() => {
  const rate = data.value?.revenue.growth_rate ?? 0
  if (rate > 0) return 'growth-up'
  if (rate < 0) return 'growth-down'
  return 'growth-flat'
})

const growthArrow = computed(() => {
  const rate = data.value?.revenue.growth_rate ?? 0
  if (rate > 0) return '↑'
  if (rate < 0) return '↓'
  return '→'
})

const growthText = computed(() => {
  const rate = data.value?.revenue.growth_rate
  if (rate === undefined || rate === null) return '--'
  return Math.abs(rate * 100).toFixed(1) + '%'
})

function formatMoney(val: number | undefined): string {
  if (val === undefined || val === null) return '0'
  return val.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 0 })
}

function pct(val: number | undefined): string {
  if (!val) return '0%'
  return (val * 100).toFixed(0) + '%'
}

function formatTime(ts: string): string {
  if (!ts) return ''
  const d = new Date(ts)
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  return `${hh}:${mm}`
}

function initChart() {
  if (!chartRef.value) return
  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const chartData = data.value?.chart ?? []
  const dates = chartData.map(p => p.date)
  const revenues = chartData.map(p => p.revenue)
  const weekdays = chartData.map(p => p.weekday)

  chartInstance.setOption({
    grid: {
      top: 16,
      right: 8,
      bottom: 24,
      left: 8,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111111',
      borderColor: '#333333',
      textStyle: { color: '#FFFFFF', fontSize: 12, fontFamily: 'Poppins' },
      formatter: (params: any) => {
        const p = params[0]
        const idx = p.dataIndex
        const wd = weekdays[idx]
        return `${wd} ${p.name}<br/>营收: ¥${p.value.toLocaleString()}<br/>订单: ${chartData[idx]?.orders ?? '-'}单`
      },
    },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#333333' } },
      axisTick: { show: false },
      axisLabel: {
        color: '#7A7C80',
        fontSize: 11,
        fontFamily: 'Poppins',
      },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#222222', type: 'dashed' } },
      axisLabel: {
        color: '#7A7C80',
        fontSize: 11,
        fontFamily: 'Poppins',
        formatter: (v: number) => {
          if (v >= 10000) return (v / 10000).toFixed(1) + '万'
          if (v >= 1000) return (v / 1000).toFixed(1) + '千'
          return v.toString()
        },
      },
    },
    series: [
      {
        type: 'bar',
        data: revenues,
        barWidth: 20,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#FB0079' },
            { offset: 1, color: '#FB0079' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
        emphasis: {
          itemStyle: {
            color: '#FB0079',
          },
        },
      },
    ],
  })
}

function handleResize() {
  chartInstance?.resize()
}

async function fetchDashboard() {
  loading.value = true
  try {
    const res = await dashboardAPI.getDashboard()
    if (res.data.code === 0) {
      data.value = res.data.data
      await nextTick()
      initChart()
    }
  } catch {
    // Error handled by interceptor
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboard()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  chartInstance?.dispose()
})
</script>

<style scoped>
.dashboard {
  min-height: 100vh;
  /* 背景：黑色底 + 主色径向渐变光晕，让毛玻璃有内容可透 */
  background-color: #000000;
  background-image:
    radial-gradient(circle at 20% 10%, rgba(251, 0, 121, 0.12) 0%, transparent 45%),
    radial-gradient(circle at 90% 60%, rgba(251, 0, 121, 0.06) 0%, transparent 35%);
  padding: 0 16px 24px;
}

/* ---- Header ---- */
.dash-header {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 16px 0 12px;
}
.dash-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-weight: 900;
  font-size: 20px;
  color: #FFFFFF;
  margin: 0;
}
.dash-time {
  font-family: Poppins, sans-serif;
  font-size: 11px;
  color: #7A7C80;
}

/* ---- Content ---- */
.dash-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* ---- Card ---- */
.card {
  /* 毛玻璃效果 */
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 14px;
}

/* 营收卡：主色辉光强调 */
.revenue-card {
  box-shadow: 0 4px 24px rgba(251, 0, 121, 0.12);
}

.card-label {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 10px;
}

/* ---- Block 1: Revenue ---- */
.revenue-amount {
  display: flex;
  align-items: baseline;
  gap: 2px;
  margin-bottom: 8px;
}
.currency {
  font-family: Poppins, sans-serif;
  font-weight: 400;
  font-size: 18px;
  color: #FB0079;
}
.amount {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 36px;
  color: #FB0079;
  line-height: 1.1;
  text-shadow: 0 0 16px rgba(251, 0, 121, 0.4);
}

.revenue-growth {
  display: flex;
  align-items: center;
  gap: 4px;
  font-family: Poppins, sans-serif;
  font-size: 13px;
  margin-bottom: 14px;
}
.growth-arrow {
  font-size: 14px;
}
.growth-label {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  margin-left: 4px;
}
.growth-up {
  color: #FB0079;
}
.growth-down {
  color: #7A7C80;
}
.growth-flat {
  color: #C8C8C8;
}

.revenue-subs {
  display: flex;
  gap: 12px;
  padding-top: 12px;
  border-top: 1px solid #222222;
}
.sub-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.sub-val {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 16px;
  color: #FFFFFF;
}
.sub-lbl {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}

/* ---- Block 2: Breakdown ---- */
.breakdown-bars {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 10px;
}
.bar-row {
  display: flex;
  align-items: center;
  gap: 10px;
}
.bar-label {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #C8C8C8;
  width: 40px;
  flex-shrink: 0;
}
.bar-track {
  flex: 1;
  height: 8px;
  background: #222222;
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 4px;
  transition: width 0.5s ease;
}
.bar-bottle {
  background: #FB0079;
}
.bar-card {
  background: #FB0079;
}
.bar-other {
  background: #333333;
}
.bar-val {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: #FFFFFF;
  width: 72px;
  text-align: right;
  flex-shrink: 0;
}
.breakdown-total {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: #FB0079;
  text-align: right;
  padding-top: 8px;
  border-top: 1px solid #222222;
}

/* ---- Block 3: Chart ---- */
.chart-container {
  width: 100%;
  height: 220px;
}

/* ---- Block 4: Rating ---- */
.rating-main {
  display: flex;
  align-items: center;
  gap: 20px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid #222222;
}
.rating-score {
  display: flex;
  align-items: baseline;
  gap: 2px;
}
.score-num {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 36px;
  color: #FB0079;
  line-height: 1.1;
}
.score-unit {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #C8C8C8;
}
.rating-stats {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.stat-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.stat-lbl {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}
.stat-val {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 14px;
  color: #C8C8C8;
}
.alert-count {
  color: #FB0079;
}

.alert-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.alert-item {
  background: rgba(0, 0, 0, 0.3);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 8px;
  padding: 10px 12px;
}
.alert-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.alert-table {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #C8C8C8;
}
.alert-score {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 13px;
  color: #FB0079;
}
.alert-comment {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.4;
}
.no-alerts {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  text-align: center;
  padding: 12px 0;
}

/* ---- Block 5: Booking ---- */
.booking-grid {
  display: flex;
  gap: 12px;
}
.booking-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 0;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
}
.booking-num {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 24px;
  color: #FFFFFF;
}
.booking-confirmed {
  color: #FB0079;
}
.booking-available {
  color: #C8C8C8;
}
.booking-lbl {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}

/* ---- Block 6: Attendance ---- */
.attendance-grid {
  display: flex;
  justify-content: space-between;
  gap: 4px;
}
.att-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 10px 4px;
  flex: 1;
  min-width: 0;
}
.att-num {
  font-family: Poppins, sans-serif;
  font-weight: 600;
  font-size: 20px;
  color: #FFFFFF;
}
.att-actual {
  color: #FB0079;
}
.att-warn {
  color: #FB0079;
}
.att-danger {
  color: #FB0079;
}
.att-lbl {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}

/* ---- Loading override ---- */
.dash-content :deep(.el-loading-mask) {
  background-color: rgba(0, 0, 0, 0.6);
}
</style>
