<script setup lang="ts">
// 我的工资预览 - 多维可视化看板（实时同步6张表）
import { ref, computed, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'
import { useRouter } from 'vue-router'
import * as echarts from 'echarts'
import dayjs from 'dayjs'
import { getMyPayrollPreview, type PayrollPreviewData } from '@/api/payroll'

const router = useRouter()

// ---- 状态 ----
const loading = ref(false)
const period = ref<string>(dayjs().format('YYYY-MM'))
const data = ref<PayrollPreviewData | null>(null)

// ---- 图表 ----
const pieChartRef = ref<HTMLElement | null>(null)
let pieChart: echarts.ECharts | null = null

// ---- 计算属性 ----
const incomeItems = computed(() => data.value?.items.filter(i => i.type === 'income') ?? [])
const deductionItems = computed(() => data.value?.items.filter(i => i.type === 'deduction') ?? [])
const totalIncome = computed(() => incomeItems.value.reduce((s, i) => s + i.amount, 0))
const totalDeduction = computed(() => deductionItems.value.reduce((s, i) => s + i.amount, 0))

// 关键指标（从 detail 提取）
const kpiStats = computed(() => {
  if (!data.value) return []
  const att = data.value.items.find(i => i.code === 'attendance')?.detail as Record<string, number> | undefined
  const perf = data.value.items.find(i => i.code === 'performance')?.detail as Record<string, number> | undefined
  const kpi = data.value.items.find(i => i.code === 'kpi')?.detail as Record<string, number> | undefined
  return [
    { label: '本月迟到', value: att?.total_late_minutes ?? 0, unit: '分钟', color: '#FF5722' },
    { label: '旷工天数', value: att?.absent_count ?? 0, unit: '天', color: '#F44336' },
    { label: '业绩总额', value: perf?.total_amount ?? 0, unit: '元', color: '#4CAF50' },
    { label: 'KPI系数', value: kpi?.coefficient ?? 1.0, unit: '', color: '#00BCD4' },
  ]
})

// ---- 工具函数 ----
function fmtMoney(n: number | undefined | null) {
  if (n == null) return '0'
  return Number(n).toLocaleString('zh-CN', { maximumFractionDigits: 0 })
}

function formatDate() {
  return dayjs().format('M月D日')
}

// ---- 加载数据 ----
async function loadData() {
  loading.value = true
  try {
    const res = await getMyPayrollPreview(period.value)
    if (res.data.code === 0) {
      data.value = res.data.data
      await nextTick()
      renderPie()
    }
  } catch (e) {
    console.error('加载工资预览失败', e)
  } finally {
    loading.value = false
  }
}

// ---- 饼图 ----
function renderPie() {
  if (!pieChartRef.value || !data.value) return
  if (!pieChart) {
    pieChart = echarts.init(pieChartRef.value)
  }
  const pieData = data.value.items.map(i => ({
    name: i.name + (i.type === 'deduction' ? '(扣)' : ''),
    value: Number(i.amount.toFixed(2)),
    itemStyle: { color: getColor(i.code, i.type) },
  }))
  pieChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: ¥{c} ({d}%)' },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['50%', '45%'],
      avoidLabelOverlap: true,
      label: { show: false },
      emphasis: {
        label: { show: true, fontSize: 14, fontWeight: 'bold' }
      },
      data: pieData,
    }],
  })
}

function getColor(code: string, type: string) {
  if (type === 'deduction') return '#FF5722'
  const map: Record<string, string> = {
    contract: '#4CAF50',
    performance: '#E91E63',
    kpi: '#00BCD4',
    reward: '#9C27B0',
    overtime: '#3F51B5',
  }
  return map[code] || '#999'
}

// ---- 生命周期 ----
onMounted(() => loadData())
onBeforeUnmount(() => {
  pieChart?.dispose()
  pieChart = null
})
watch(period, () => loadData())

// 窗口resize
function handleResize() { pieChart?.resize() }
onMounted(() => window.addEventListener('resize', handleResize))
onBeforeUnmount(() => window.removeEventListener('resize', handleResize))
</script>

<template>
  <div class="payroll-preview">
    <!-- 顶部大数字 -->
    <div class="hero-card">
      <div class="period">{{ data?.period }} · 截至{{ formatDate() }}</div>
      <div class="hero-label">本月预估实发</div>
      <div class="hero-amount">¥{{ fmtMoney(data?.net_pay) }}</div>
      <div class="hero-meta">
        <span class="meta-income">收入 +¥{{ fmtMoney(totalIncome) }}</span>
        <span class="meta-div">|</span>
        <span class="meta-deduction">扣款 -¥{{ fmtMoney(totalDeduction) }}</span>
      </div>
      <div class="hero-notice">⚠️ {{ data?.notice }}</div>
    </div>

    <!-- 关键指标卡片 -->
    <div class="kpi-grid" v-if="data">
      <div v-for="s in kpiStats" :key="s.label" class="kpi-card">
        <div class="kpi-value" :style="{ color: s.color }">
          {{ s.unit === '元' ? '¥' + fmtMoney(s.value) : s.value }}<small>{{ s.unit }}</small>
        </div>
        <div class="kpi-label">{{ s.label }}</div>
      </div>
    </div>

    <!-- 工资构成饼图 -->
    <div class="chart-card" v-if="data && data.items.length > 0">
      <div class="card-title">📊 工资构成</div>
      <div ref="pieChartRef" class="chart-box"></div>
    </div>

    <!-- 明细表格 -->
    <div class="detail-card" v-if="data">
      <div class="card-title">📋 明细表</div>
      <div class="detail-table">
        <div class="detail-header">
          <span>项目</span>
          <span>来源</span>
          <span class="num">金额</span>
        </div>
        <div v-for="i in data.items" :key="i.code" class="detail-row" :class="{ deduction: i.type === 'deduction' }">
          <span class="name">
            <span class="dot" :style="{ background: getColor(i.code, i.type) }"></span>
            {{ i.name }}
          </span>
          <span class="source">{{ i.source }}</span>
          <span class="num" :class="i.type">
            {{ i.type === 'deduction' ? '-' : '+' }}¥{{ fmtMoney(i.amount) }}
          </span>
        </div>
        <div class="detail-footer">
          <span>合计实发</span>
          <span class="num total">¥{{ fmtMoney(data.net_pay) }}</span>
        </div>
      </div>
    </div>

    <!-- 发薪日提示 -->
    <div class="payday-card" v-if="data">
      <div class="payday-icon">📅</div>
      <div class="payday-text">
        <div class="payday-title">发薪日：每月{{ data.pay_day }}日</div>
        <div class="payday-hint">最终金额以月底结算为准</div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<style scoped lang="scss">
.payroll-preview {
  min-height: 100vh;
  background: #0a0a0a;
  color: #fff;
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

/* 顶部大数字 */
.hero-card {
  background: linear-gradient(135deg, #FB0079 0%, #d10062 100%);
  border-radius: 20px;
  padding: 24px 20px;
  text-align: center;
  margin-bottom: 16px;
  box-shadow: 0 8px 24px rgba(251, 0, 121, 0.3);
}
.period { font-size: 12px; opacity: 0.8; margin-bottom: 8px; }
.hero-label { font-size: 14px; opacity: 0.9; }
.hero-amount {
  font-size: 42px;
  font-weight: 800;
  margin: 8px 0;
  letter-spacing: 1px;
}
.hero-meta { font-size: 13px; opacity: 0.9; display: flex; justify-content: center; gap: 8px; }
.meta-div { opacity: 0.5; }
.hero-notice { font-size: 11px; opacity: 0.7; margin-top: 12px; }

/* KPI 卡片 */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  margin-bottom: 16px;
}
.kpi-card {
  background: #1a1a1a;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.kpi-value {
  font-size: 22px;
  font-weight: 700;
  small { font-size: 12px; margin-left: 2px; }
}
.kpi-label { font-size: 12px; color: #888; margin-top: 4px; }

/* 图表卡片 */
.chart-card, .detail-card, .payday-card {
  background: #1a1a1a;
  border-radius: 14px;
  padding: 16px;
  margin-bottom: 14px;
}
.card-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; }
.chart-box { width: 100%; height: 240px; }

/* 明细表 */
.detail-table { font-size: 14px; }
.detail-header, .detail-row, .detail-footer {
  display: grid;
  grid-template-columns: 1.5fr 1fr 1fr;
  gap: 8px;
  padding: 10px 0;
  border-bottom: 1px solid #222;
}
.detail-header { color: #888; font-size: 12px; }
.detail-row { align-items: center; }
.detail-row.deduction .num { color: #FF5722; }
.name { display: flex; align-items: center; gap: 6px; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.source { color: #888; font-size: 12px; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.num.income { color: #4CAF50; }
.detail-footer {
  font-weight: 700;
  border-bottom: none;
  padding-top: 14px;
  font-size: 16px;
}
.detail-footer .total { color: #FB0079; font-size: 18px; }

/* 发薪日 */
.payday-card {
  display: flex;
  align-items: center;
  gap: 12px;
}
.payday-icon { font-size: 28px; }
.payday-title { font-size: 14px; font-weight: 600; }
.payday-hint { font-size: 12px; color: #888; margin-top: 2px; }

.loading { text-align: center; padding: 40px; color: #666; }
</style>
