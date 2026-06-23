<script setup lang="ts">
// 我的数据 - 统一可视化看板（KPI / 排名 / 业绩 / 工资）
import { ref, computed, onMounted, watch, nextTick, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { kpiResultAPI } from '@/api/kpi'
import { getMyRankings, RANK_TYPE_LABELS, type MyRanking } from '@/api/ranking'
import { getMyPayroll, type MyPayrollItem } from '@/api/payroll'
import apiClient from '@/api/client'

const router = useRouter()

// ---- 期间选择 ----
const period = ref<string>(dayjs().format('YYYY-MM'))

// ---- 加载状态 ----
const loadingKpi = ref(false)
const loadingRank = ref(false)
const loadingPerf = ref(false)
const loadingPay = ref(false)

// ---- 数据 ----
// 用 any 兼容后端实际返回（details/dimensions 字段名差异）
const kpiData = ref<any>(null)
const rankings = ref<MyRanking[]>([])
const perfDetail = ref<{ date: string; amount: number; cumulative: number }[]>([])
const payrollList = ref<MyPayrollItem[]>([])

// ---- 图表引用 ----
const kpiChartRef = ref<HTMLElement | null>(null)
const rankChartRef = ref<HTMLElement | null>(null)
const perfChartRef = ref<HTMLElement | null>(null)
const payChartRef = ref<HTMLElement | null>(null)

let kpiChart: echarts.ECharts | null = null
let rankChart: echarts.ECharts | null = null
let perfChart: echarts.ECharts | null = null
let payChart: echarts.ECharts | null = null

// ---- 摘要数字 ----
const kpiTotalScore = computed(() => kpiData.value?.total_score?.toFixed(1) ?? '--')
const perfTotal = computed(() => {
  if (perfDetail.value.length === 0) return 0
  return perfDetail.value[perfDetail.value.length - 1].cumulative
})
const latestPayroll = computed(() => payrollList.value[0] ?? null)

function fmtMoney(n: number | undefined | null) {
  if (n == null) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  return n.toLocaleString()
}

function fmtMoneyFull(n: number | undefined | null) {
  if (n == null) return '0.00'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

// ---- 加载函数 ----
async function loadKpi() {
  loadingKpi.value = true
  try {
    const res = await kpiResultAPI.my(period.value)
    const list = res.data?.data || []
    kpiData.value = list[0] || null
  } catch {
    kpiData.value = null
  } finally {
    loadingKpi.value = false
  }
}

async function loadRankings() {
  loadingRank.value = true
  try {
    const res = await getMyRankings(period.value)
    rankings.value = res.data?.data || []
  } catch {
    rankings.value = []
  } finally {
    loadingRank.value = false
  }
}

async function loadPerformance() {
  loadingPerf.value = true
  try {
    const res = await apiClient.get('/dashboard/my-performance-detail')
    perfDetail.value = res.data?.data || []
  } catch {
    perfDetail.value = []
  } finally {
    loadingPerf.value = false
  }
}

async function loadPayroll() {
  loadingPay.value = true
  try {
    const res = await getMyPayroll()
    payrollList.value = res.data?.data || []
  } catch {
    payrollList.value = []
  } finally {
    loadingPay.value = false
  }
}

// ---- 图表初始化 ----
function initKpiChart() {
  if (!kpiChartRef.value) return
  if (kpiChart) kpiChart.dispose()
  kpiChart = echarts.init(kpiChartRef.value)

  const dims = kpiData.value?.dimensions || []
  const details = kpiData.value?.details || []
  // 兼容后端返回的字段名
  const dimList = (details.length > 0 ? details : dims) as Array<{
    dimension?: string
    dimension_label?: string
    name?: string
    normalized_score?: number
    score?: number
    weight?: number
  }>

  const indicators = dimList.map(d => {
    const name = d.dimension_label || d.dimension || d.name || '维度'
    const weight = d.weight ?? 100
    return { name, max: weight }
  })
  const values = dimList.map(d => d.normalized_score ?? d.score ?? 0)

  if (indicators.length === 0) {
    kpiChart.setOption({
      title: { text: '暂无 KPI 数据', left: 'center', top: 'center', textStyle: { color: '#7A7C80', fontSize: 13 } },
    })
    return
  }

  kpiChart.setOption({
    tooltip: { trigger: 'item' },
    radar: {
      indicator: indicators,
      shape: 'polygon',
      splitNumber: 4,
      axisName: { color: '#C8C8C8', fontSize: 11 },
      splitLine: { lineStyle: { color: '#333333' } },
      splitArea: { areaStyle: { color: ['rgba(17,17,17,0.4)', 'rgba(34,34,34,0.3)'] } },
      axisLine: { lineStyle: { color: '#333333' } },
    },
    series: [
      {
        type: 'radar',
        data: [
          {
            value: values,
            name: '我的得分',
            areaStyle: { color: 'rgba(251, 0, 121, 0.25)' },
            lineStyle: { color: '#FB0079', width: 2 },
            itemStyle: { color: '#FB0079' },
          },
        ],
      },
    ],
  })
}

function initRankChart() {
  if (!rankChartRef.value) return
  if (rankChart) rankChart.dispose()
  rankChart = echarts.init(rankChartRef.value)

  const types = ['performance', 'kpi', 'attendance', 'rating'] as const
  const labels = types.map(t => RANK_TYPE_LABELS[t])
  // 百分位：越高代表排名越靠前
  const pcts = types.map(t => {
    const r = rankings.value.find(x => x.rank_type === t)
    if (!r || r.total_count === 0) return 0
    return ((r.total_count - r.rank_position + 1) / r.total_count) * 100
  })
  const positions = types.map(t => {
    const r = rankings.value.find(x => x.rank_type === t)
    return r ? `${r.rank_position}/${r.total_count}` : '--'
  })

  rankChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params: any) => {
        const idx = params[0].dataIndex
        return `${labels[idx]}<br/>排名：${positions[idx]}<br/>百分位：${pcts[idx].toFixed(0)}%`
      },
    },
    grid: { top: 10, right: 40, bottom: 10, left: 10, containLabel: true },
    xAxis: {
      type: 'value',
      max: 100,
      axisLine: { lineStyle: { color: '#333333' } },
      splitLine: { lineStyle: { color: '#222222', type: 'dashed' } },
      axisLabel: { color: '#7A7C80', fontSize: 10, formatter: '{value}%' },
    },
    yAxis: {
      type: 'category',
      data: labels,
      axisLine: { lineStyle: { color: '#333333' } },
      axisTick: { show: false },
      axisLabel: { color: '#C8C8C8', fontSize: 11 },
    },
    series: [
      {
        type: 'bar',
        data: pcts,
        barWidth: 14,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: 'rgba(251, 0, 121, 0.3)' },
            { offset: 1, color: '#FB0079' },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
        label: {
          show: true,
          position: 'right',
          color: '#FB0079',
          fontSize: 11,
          formatter: (p: any) => positions[p.dataIndex],
        },
      },
    ],
  })
}

function initPerfChart() {
  if (!perfChartRef.value) return
  if (perfChart) perfChart.dispose()
  perfChart = echarts.init(perfChartRef.value)

  const rows = perfDetail.value
  if (rows.length === 0) {
    perfChart.setOption({
      title: { text: '暂无业绩数据', left: 'center', top: 'center', textStyle: { color: '#7A7C80', fontSize: 13 } },
    })
    return
  }

  const dates = rows.map(r => r.date.slice(5))
  const amounts = rows.map(r => r.amount)
  const cumul = rows.map(r => r.cumulative)

  perfChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: '#111111',
      borderColor: '#333333',
      textStyle: { color: '#FFFFFF', fontSize: 12 },
      formatter: (params: any) => {
        let s = params[0].axisValue + '<br/>'
        params.forEach((p: any) => {
          s += `${p.marker}${p.seriesName}：¥${Number(p.value).toLocaleString()}<br/>`
        })
        return s
      },
    },
    legend: {
      data: ['日收款', '累计'],
      textStyle: { color: '#C8C8C8', fontSize: 11 },
      top: 0,
      right: 0,
    },
    grid: { top: 30, right: 8, bottom: 24, left: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: dates,
      axisLine: { lineStyle: { color: '#333333' } },
      axisTick: { show: false },
      axisLabel: { color: '#7A7C80', fontSize: 10, interval: Math.floor(rows.length / 6) },
    },
    yAxis: [
      {
        type: 'value',
        splitLine: { lineStyle: { color: '#222222', type: 'dashed' } },
        axisLabel: {
          color: '#7A7C80',
          fontSize: 10,
          formatter: (v: number) => {
            if (v >= 10000) return (v / 10000).toFixed(1) + 'w'
            return v.toString()
          },
        },
      },
    ],
    series: [
      {
        name: '日收款',
        type: 'bar',
        data: amounts,
        barWidth: 8,
        itemStyle: { color: 'rgba(251, 0, 121, 0.5)', borderRadius: [2, 2, 0, 0] },
      },
      {
        name: '累计',
        type: 'line',
        data: cumul,
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: '#FB0079', width: 2 },
        itemStyle: { color: '#FB0079' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(251, 0, 121, 0.25)' },
            { offset: 1, color: 'rgba(251, 0, 121, 0)' },
          ]),
        },
      },
    ],
  })
}

function initPayChart() {
  if (!payChartRef.value) return
  if (payChart) payChart.dispose()
  payChart = echarts.init(payChartRef.value)

  const list = [...payrollList.value].reverse() // 旧→新
  if (list.length === 0) {
    payChart.setOption({
      title: { text: '暂无工资数据', left: 'center', top: 'center', textStyle: { color: '#7A7C80', fontSize: 13 } },
    })
    return
  }

  const periods = list.map(p => p.period)
  const netPays = list.map(p => p.net_pay)

  payChart.setOption({
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      backgroundColor: '#111111',
      borderColor: '#333333',
      textStyle: { color: '#FFFFFF', fontSize: 12 },
      formatter: (params: any) => {
        const p = params[0]
        return `${p.axisValue}<br/>实发：¥${Number(p.value).toLocaleString()}`
      },
    },
    grid: { top: 16, right: 8, bottom: 24, left: 8, containLabel: true },
    xAxis: {
      type: 'category',
      data: periods,
      axisLine: { lineStyle: { color: '#333333' } },
      axisTick: { show: false },
      axisLabel: { color: '#7A7C80', fontSize: 10 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#222222', type: 'dashed' } },
      axisLabel: {
        color: '#7A7C80',
        fontSize: 10,
        formatter: (v: number) => {
          if (v >= 10000) return (v / 10000).toFixed(1) + 'w'
          return v.toString()
        },
      },
    },
    series: [
      {
        type: 'bar',
        data: netPays,
        barWidth: 20,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: '#FB0079' },
            { offset: 1, color: 'rgba(251, 0, 121, 0.3)' },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      },
    ],
  })
}

function refreshCharts() {
  nextTick(() => {
    initKpiChart()
    initRankChart()
    initPerfChart()
    initPayChart()
  })
}

async function loadAll() {
  await Promise.all([loadKpi(), loadRankings(), loadPerformance(), loadPayroll()])
  refreshCharts()
}

function handleResize() {
  kpiChart?.resize()
  rankChart?.resize()
  perfChart?.resize()
  payChart?.resize()
}

// 月份切换只刷新 KPI + 排名
watch(period, async () => {
  await Promise.all([loadKpi(), loadRankings()])
  nextTick(() => {
    initKpiChart()
    initRankChart()
  })
})

onMounted(() => {
  loadAll()
  window.addEventListener('resize', handleResize)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  kpiChart?.dispose()
  rankChart?.dispose()
  perfChart?.dispose()
  payChart?.dispose()
})

function goPayrollDetail(id: string) {
  router.push({ name: 'MyPayrollDetail', params: { id } })
}
</script>

<template>
  <div class="my-data-page">
    <!-- 顶部期间选择 -->
    <div class="top-bar">
      <span class="page-title">我的数据</span>
      <input v-model="period" type="month" class="month-input" />
    </div>

    <!-- 摘要数字：3 列 -->
    <div class="summary-row">
      <div class="sum-item">
        <div class="sum-val">{{ kpiTotalScore }}</div>
        <div class="sum-lbl">KPI 综合</div>
      </div>
      <div class="sum-div"></div>
      <div class="sum-item">
        <div class="sum-val">¥{{ fmtMoney(perfTotal) }}</div>
        <div class="sum-lbl">本月业绩</div>
      </div>
      <div class="sum-div"></div>
      <div class="sum-item">
        <div class="sum-val">¥{{ fmtMoney(latestPayroll?.net_pay) }}</div>
        <div class="sum-lbl">最新工资</div>
      </div>
    </div>

    <!-- 图表区：2 列网格，部分跨列 -->
    <div class="chart-grid">
      <!-- KPI 雷达图 -->
      <div class="chart-card span-2">
        <div class="card-head">
          <span class="card-title">KPI 维度雷达</span>
          <span class="card-sub" v-if="kpiData">{{ period }}</span>
        </div>
        <div ref="kpiChartRef" class="chart-box" v-loading="loadingKpi"></div>
      </div>

      <!-- 排名横向柱图 -->
      <div class="chart-card span-2">
        <div class="card-head">
          <span class="card-title">四维排名</span>
          <span class="card-sub">{{ period }}</span>
        </div>
        <div ref="rankChartRef" class="chart-box" v-loading="loadingRank"></div>
      </div>

      <!-- 业绩趋势 -->
      <div class="chart-card span-2">
        <div class="card-head">
          <span class="card-title">本月业绩趋势</span>
          <span class="card-sub">日收款 / 累计</span>
        </div>
        <div ref="perfChartRef" class="chart-box" v-loading="loadingPerf"></div>
      </div>

      <!-- 工资趋势 -->
      <div class="chart-card">
        <div class="card-head">
          <span class="card-title">工资趋势</span>
        </div>
        <div ref="payChartRef" class="chart-box small" v-loading="loadingPay"></div>
      </div>

      <!-- 工资列表 -->
      <div class="chart-card">
        <div class="card-head">
          <span class="card-title">工资记录</span>
        </div>
        <div class="pay-list">
          <div
            v-for="item in payrollList.slice(0, 6)"
            :key="item.id"
            class="pay-item"
            @click="goPayrollDetail(item.id)"
          >
            <div class="pay-info">
              <div class="pay-period">{{ item.period }}</div>
              <div class="pay-status" :class="item.status">
                {{ item.status === 'paid' ? '已发放' : item.status === 'confirmed' ? '已确认' : '待确认' }}
              </div>
            </div>
            <div class="pay-amount">¥{{ fmtMoneyFull(item.net_pay) }}</div>
          </div>
          <div v-if="payrollList.length === 0 && !loadingPay" class="empty">暂无工资记录</div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.my-data-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px 16px 96px;
}

/* ---- 顶部 ---- */
.top-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.page-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
}
.month-input {
  height: 32px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 0 10px;
  color: #FFFFFF;
  font-size: 13px;
  outline: none;
  color-scheme: dark;
}

/* ---- 摘要行 ---- */
.summary-row {
  display: flex;
  align-items: center;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 8px;
  margin-bottom: 12px;
}
.sum-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.sum-val {
  font-family: 'Poppins', sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #FB0079;
  line-height: 1.1;
}
.sum-lbl {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}
.sum-div {
  width: 1px;
  height: 28px;
  background: #222222;
}

/* ---- 图表网格 ---- */
.chart-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}
.chart-card {
  background: rgba(17, 17, 17, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 12px;
  padding: 12px;
}
.span-2 {
  grid-column: span 2;
}
.card-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  margin-bottom: 8px;
}
.card-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
}
.card-sub {
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}
.chart-box {
  width: 100%;
  height: 220px;
}
.chart-box.small {
  height: 180px;
}

/* ---- 工资列表 ---- */
.pay-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  max-height: 180px;
  overflow-y: auto;
}
.pay-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.3);
  border-radius: 8px;
  cursor: pointer;
}
.pay-item:hover {
  background: rgba(251, 0, 121, 0.08);
}
.pay-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.pay-period {
  font-family: 'Poppins', sans-serif;
  font-size: 13px;
  color: #FFFFFF;
}
.pay-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 8px;
  width: fit-content;
}
.pay-status.draft {
  background: #333333;
  color: #888888;
}
.pay-status.confirmed {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}
.pay-status.paid {
  background: #333333;
  color: #C8C8C8;
}
.pay-amount {
  font-family: 'Poppins', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FB0079;
}
.empty {
  color: #7A7C80;
  text-align: center;
  padding: 20px 0;
  font-size: 12px;
}

/* ---- loading 覆盖 ---- */
.chart-card :deep(.el-loading-mask) {
  background-color: rgba(0, 0, 0, 0.5);
}
</style>
