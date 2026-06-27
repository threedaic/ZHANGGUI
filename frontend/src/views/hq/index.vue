<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { hqAPI, type HQDashboard } from '@/api/hq'

const router = useRouter()
const loading = ref(true)
const data = ref<HQDashboard | null>(null)

async function loadData() {
  loading.value = true
  try {
    const res = await hqAPI.getDashboard()
    data.value = res.data.data
  } catch {} finally { loading.value = false }
}

function fmtMoney(n: number) {
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  return n.toLocaleString()
}

function fmtGrowth(n: number) {
  return n > 0 ? '+' + n + '%' : n + '%'
}

const maxRevenue = computed(() => {
  if (!data.value?.chart?.length) return 1
  return Math.max(...data.value.chart.map(c => c.revenue), 1)
})

onMounted(() => loadData())
</script>

<template>
  <div class="hq">
    <!-- 顶部光效背景 -->
    <div class="glow-bg"></div>

    <!-- 品牌标识 -->
    <div class="brand-area">
      <div class="brand-mark">CRUSH</div>
      <h1>总店控制台</h1>
      <p>{{ data ? `${data.store_count} 家门店 · 实时数据` : '加载中...' }}</p>
    </div>

    <!-- 主营收卡片 -->
    <div class="hero-card" v-if="data">
      <div class="hero-top">
        <span class="hero-label">今日总营收</span>
        <span class="hero-trend" :class="{ up: data.growth_rate > 0, down: data.growth_rate < 0 }">
          <svg v-if="data.growth_rate > 0" width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M5 2l3 4H2z" fill="currentColor"/></svg>
          <svg v-else width="10" height="10" viewBox="0 0 10 10" fill="none"><path d="M5 8l3-4H2z" fill="currentColor"/></svg>
          {{ fmtGrowth(data.growth_rate) }}
        </span>
      </div>
      <div class="hero-value">¥{{ fmtMoney(data.today_revenue) }}</div>
      <div class="hero-foot">vs 昨日 ¥{{ fmtMoney(data.yesterday_revenue) }}</div>
    </div>

    <!-- 双指标卡片 -->
    <div class="dual-grid" v-if="data">
      <div class="dual-card">
        <span class="dual-label">门店</span>
        <span class="dual-num">{{ data.store_count }}</span>
        <span class="dual-unit">家</span>
      </div>
      <div class="dual-card">
        <span class="dual-label">员工</span>
        <span class="dual-num">{{ data.employee_count }}</span>
        <span class="dual-unit">人</span>
      </div>
    </div>

    <!-- 营收趋势图 -->
    <div class="chart-card" v-if="data && data.chart.length > 0">
      <div class="card-head">
        <span class="card-title">近7天趋势</span>
      </div>
      <div class="chart-body">
        <div v-for="(item, idx) in data.chart" :key="idx" class="bar-col">
          <div class="bar-track">
            <div
              class="bar-fill"
              :style="{ height: Math.max(6, (item.revenue / maxRevenue) * 100) + '%' }"
            ></div>
          </div>
          <span class="bar-label">{{ item.date.slice(5) }}</span>
          <span class="bar-val">¥{{ fmtMoney(item.revenue) }}</span>
        </div>
      </div>
    </div>

    <!-- 各店概览 -->
    <div class="stores-card" v-if="data && data.store_breakdown.length > 0">
      <div class="card-head">
        <span class="card-title">各店今日</span>
        <span class="card-more" @click="router.push('/hq/stores')">全部 ></span>
      </div>
      <div class="store-row" v-for="s in data.store_breakdown" :key="s.store_id" @click="router.push('/hq/stores')">
        <div class="store-dot"></div>
        <span class="store-name">{{ s.store_name }}</span>
        <span class="store-rev">¥{{ fmtMoney(s.today_revenue) }}</span>
        <span class="store-emp">{{ s.employee_count }}人</span>
      </div>
    </div>

    <!-- 快捷入口 -->
    <div class="action-grid">
      <div class="action-tile" @click="router.push('/hq/stores')">
        <div class="tile-icon">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M3 18h16M5 18V9l6-5 6 5v9M10 18v-5h2v5"/></svg>
        </div>
        <span class="tile-label">门店</span>
      </div>
      <div class="action-tile" @click="router.push('/hq/employees')">
        <div class="tile-icon">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="8" r="3.5"/><path d="M4 19c0-3.5 3-6 7-6s7 2.5 7 6"/></svg>
        </div>
        <span class="tile-label">员工</span>
      </div>
      <div class="action-tile" @click="router.push('/hq/ai-config')">
        <div class="tile-icon">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><circle cx="11" cy="11" r="7"/><path d="M11 7v8M7 11h8"/></svg>
        </div>
        <span class="tile-label">AI配置</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.hq {
  position: relative;
  max-width: 600px;
  margin: 0 auto;
  padding: 0 16px calc(64px + 24px);
  overflow: hidden;
}

/* 光效背景 */
.glow-bg {
  position: absolute;
  top: -60px;
  left: 50%;
  transform: translateX(-50%);
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(251, 0, 121, 0.12) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

/* 品牌标识 */
.brand-area {
  position: relative;
  z-index: 1;
  text-align: center;
  padding: 16px 0 24px;
}
.brand-mark {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 4px;
  color: rgba(251, 0, 121, 0.5);
  margin-bottom: 4px;
}
.brand-area h1 {
  font-size: 24px;
  font-weight: 700;
  color: #fff;
  margin: 0;
  letter-spacing: -0.5px;
}
.brand-area p {
  font-size: 12px;
  color: #555;
  margin: 4px 0 0;
}

/* 主营收卡片 - Apple 风格毛玻璃 */
.hero-card {
  position: relative;
  z-index: 1;
  background: linear-gradient(135deg, rgba(251, 0, 121, 0.12) 0%, rgba(251, 0, 121, 0.03) 100%);
  border: 1px solid rgba(251, 0, 121, 0.15);
  border-radius: 16px;
  padding: 20px;
  margin-bottom: 10px;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}
.hero-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.hero-label {
  font-size: 13px;
  color: #888;
  font-weight: 500;
}
.hero-trend {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 12px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}
.hero-trend.up { color: #34c759; background: rgba(52, 199, 89, 0.1); }
.hero-trend.down { color: #ff3b30; background: rgba(255, 59, 48, 0.1); }
.hero-value {
  font-size: 36px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -1px;
  line-height: 1.1;
}
.hero-foot {
  font-size: 12px;
  color: #555;
  margin-top: 6px;
}

/* 双指标 */
.dual-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  margin-bottom: 10px;
}
.dual-card {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 2px;
  backdrop-filter: blur(10px);
}
.dual-label {
  font-size: 12px;
  color: #666;
  font-weight: 500;
}
.dual-num {
  font-size: 28px;
  font-weight: 700;
  color: #fff;
  letter-spacing: -0.5px;
}
.dual-unit {
  font-size: 12px;
  color: #555;
}

/* 图表卡片 */
.chart-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 10px;
  backdrop-filter: blur(10px);
}
.card-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
}
.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #ddd;
}
.card-more {
  font-size: 12px;
  color: #FB0079;
  cursor: pointer;
}

.chart-body {
  display: flex;
  gap: 6px;
  align-items: flex-end;
  height: 120px;
}
.bar-col {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
}
.bar-track {
  flex: 1;
  width: 100%;
  display: flex;
  align-items: flex-end;
  justify-content: center;
  min-height: 0;
}
.bar-fill {
  width: 60%;
  max-width: 20px;
  background: linear-gradient(180deg, #FB0079 0%, rgba(251, 0, 121, 0.3) 100%);
  border-radius: 3px 3px 0 0;
  min-height: 6px;
  transition: height 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.bar-label {
  font-size: 9px;
  color: #555;
  margin-top: 4px;
}
.bar-val {
  font-size: 8px;
  color: #444;
  white-space: nowrap;
}

/* 门店列表 */
.stores-card {
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 16px;
  padding: 16px;
  margin-bottom: 10px;
  backdrop-filter: blur(10px);
}
.store-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  cursor: pointer;
}
.store-row:last-child { border-bottom: none; }
.store-row:active { opacity: 0.6; }
.store-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #FB0079;
  flex-shrink: 0;
}
.store-name {
  flex: 1;
  font-size: 14px;
  color: #ccc;
  font-weight: 500;
}
.store-rev {
  font-size: 15px;
  color: #fff;
  font-weight: 700;
}
.store-emp {
  font-size: 12px;
  color: #555;
  min-width: 32px;
  text-align: right;
}

/* 快捷入口 */
.action-grid {
  position: relative;
  z-index: 1;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin-top: 6px;
}
.action-tile {
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
  border-radius: 14px;
  padding: 16px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  cursor: pointer;
  transition: all 0.2s;
  backdrop-filter: blur(10px);
}
.action-tile:active {
  transform: scale(0.96);
  background: rgba(251, 0, 121, 0.05);
}
.tile-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: rgba(251, 0, 121, 0.08);
  color: #FB0079;
  display: flex;
  align-items: center;
  justify-content: center;
}
.tile-label {
  font-size: 12px;
  color: #aaa;
  font-weight: 500;
}
</style>
