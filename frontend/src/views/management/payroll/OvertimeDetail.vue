<!--
  ============================================================================
  加班费模块 - 二级页面
  ============================================================================

  【功能】
  1. 日历选择本月三薪日期（点击日期切换，可选倍数）
  2. 显示每个员工的加班数据（加班天数、日薪、倍数、加班费）
  3. 可切换启用/禁用

  【数据来源】
  - 老板手动选择三薪日期 + 倍数
  - 考勤记录自动匹配员工是否上班
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">加班费</span>
    </div>

    <!-- 启用开关 -->
    <div class="toggle-card">
      <span class="toggle-label">参与工资计算</span>
      <label class="switch" @click.stop="toggleModule">
        <input type="checkbox" :checked="enabled" />
        <span class="slider"></span>
      </label>
    </div>

    <!-- 模块说明 -->
    <div class="module-desc-card">
      <div class="desc-title">模块作用</div>
      <div class="desc-text">根据法定节假日加班天数计算加班费。系统自动匹配考勤记录，无需员工申请。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">加班费 = 日薪 × 倍数 × 加班天数（日薪 = 月薪 ÷ (月天数 - 4天休息)）</div>
    </div>

    <!-- 三薪日历 -->
    <div class="section-title">三薪日历 - {{ currentPeriod }}</div>
    <div class="calendar-card">
      <div class="calendar-header">
        <span class="cal-label">点击日期设置加班倍数</span>
        <div class="legend">
          <span class="legend-item"><span class="dot dot-3"></span>三薪</span>
          <span class="legend-item"><span class="dot dot-2"></span>双薪</span>
          <span class="legend-item"><span class="dot dot-0"></span>无</span>
        </div>
      </div>
      <div class="calendar-weekdays">
        <span>日</span><span>一</span><span>二</span><span>三</span><span>四</span><span>五</span><span>六</span>
      </div>
      <div class="calendar-grid">
        <div
          v-for="day in calendarDays"
          :key="day.key"
          class="calendar-cell"
          :class="{
            'empty': !day.day,
            'has-multiplier': day.multiplier > 0,
            'm3': day.multiplier === 3,
            'm2': day.multiplier === 2,
          }"
          @click="day.day && onDayClick(day.day)"
        >
          <span v-if="day.day" class="day-num">{{ day.day }}</span>
          <span v-if="day.multiplier > 0" class="day-multiplier">{{ day.multiplier }}x</span>
        </div>
      </div>
    </div>

    <!-- 员工加班数据 -->
    <div class="section-title">员工加班数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>加班天数</th>
            <th>日薪</th>
            <th>倍数</th>
            <th>加班费</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td>{{ emp.modules.overtime?.days || 0 }} 天</td>
            <td>¥{{ Number(emp.modules.overtime?.daily_wage || 0).toFixed(2) }}</td>
            <td>{{ Number(emp.modules.overtime?.multiplier || 0).toFixed(1) }}x</td>
            <td class="amount-positive">¥{{ Number(emp.modules.overtime?.total || 0).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无加班数据</div>
    </div>

    <!-- 说明 -->
    <div class="section-title">说明</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">日薪计算</span>
        <span class="rule-desc">日薪 = 总薪资 ÷ (当月天数 - 4天休息)</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">加班费计算</span>
        <span class="rule-desc">加班费 = 日薪 × 加班天数 × 倍数</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">加班天数来源</span>
        <span class="rule-desc">上方日历选择 + 考勤记录自动匹配</span>
      </div>
    </div>

    <!-- 倍数选择弹窗 -->
    <div v-if="showMultiplierPicker" class="picker-overlay" @click="showMultiplierPicker = false">
      <div class="picker-card" @click.stop>
        <div class="picker-title">{{ pickerDate }}日 - 选择加班倍数</div>
        <div class="picker-options">
          <button class="picker-btn" @click="setMultiplier(0)">无加班</button>
          <button class="picker-btn m2" @click="setMultiplier(2)">双薪 (2x)</button>
          <button class="picker-btn m3" @click="setMultiplier(3)">三薪 (3x)</button>
        </div>
        <button class="picker-cancel" @click="showMultiplierPicker = false">取消</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { autoPayrollAPI, type PayrollTable } from '@/api/autoPayroll'

const router = useRouter()
const loading = ref(false)

const tableData = ref<PayrollTable>({
  period: '',
  modules: {},
  module_info: {},
  rules: {},
  employees: [],
  summary: { modules: {}, net_pay: 0, employee_count: 0 },
})

const employees = computed(() => tableData.value.employees)
const enabled = computed(() => tableData.value.modules.overtime || false)

// 当前月份
const currentPeriod = ref('')
const currentYear = ref(0)
const currentMonth = ref(0)

// 三薪日期数据：{ "2026-06-01": 3, "2026-06-02": 2 }
const overtimeDays = ref<Record<string, number>>({})

// 倍数选择弹窗
const showMultiplierPicker = ref(false)
const pickerDay = ref(0)
const pickerDate = ref('')

// 生成日历格子
const calendarDays = computed(() => {
  const year = currentYear.value
  const month = currentMonth.value
  if (!year || !month) return []

  const firstDay = new Date(year, month - 1, 1).getDay() // 0=周日
  const daysInMonth = new Date(year, month, 0).getDate()
  const cells: { day: number; key: string; multiplier: number }[] = []

  // 前置空格
  for (let i = 0; i < firstDay; i++) {
    cells.push({ day: 0, key: `empty-${i}`, multiplier: 0 })
  }

  // 日期
  for (let d = 1; d <= daysInMonth; d++) {
    const dateStr = `${year}-${String(month).padStart(2, '0')}-${String(d).padStart(2, '0')}`
    cells.push({
      day: d,
      key: dateStr,
      multiplier: overtimeDays.value[dateStr] || 0,
    })
  }

  return cells
})

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    currentYear.value = d.getFullYear()
    currentMonth.value = d.getMonth() + 1
    currentPeriod.value = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`

    const res = await autoPayrollAPI.getTable(currentPeriod.value)
    tableData.value = res.data.data

    // 加载已保存的三薪日期
    try {
      const daysRes = await autoPayrollAPI.getOvertimeDays(currentPeriod.value)
      overtimeDays.value = daysRes.data.data || {}
    } catch {
      overtimeDays.value = {}
    }
  } catch (e) {
    console.error('[加班费] 加载失败:', e)
  }
  loading.value = false
}

async function toggleModule() {
  const newVal = !tableData.value.modules.overtime
  try {
    await autoPayrollAPI.setModules({ overtime: newVal })
    tableData.value.modules.overtime = newVal
  } catch (e) {
    console.error('[加班费] 切换失败:', e)
  }
}

// 点击日期 → 弹出倍数选择
function onDayClick(day: number) {
  pickerDay.value = day
  pickerDate.value = `${currentMonth.value}月${day}`
  showMultiplierPicker.value = true
}

// 设置倍数
async function setMultiplier(mult: number) {
  const dateStr = `${currentYear.value}-${String(currentMonth.value).padStart(2, '0')}-${String(pickerDay.value).padStart(2, '0')}`

  if (mult === 0) {
    delete overtimeDays.value[dateStr]
  } else {
    overtimeDays.value[dateStr] = mult
  }

  // 保存到后端
  try {
    await autoPayrollAPI.setOvertimeDays(currentPeriod.value, overtimeDays.value)
    // 重新加载工资表
    await loadData()
  } catch (e) {
    console.error('[加班费] 保存失败:', e)
  }

  showMultiplierPicker.value = false
}

onMounted(loadData)
</script>

<style scoped>
@import './_shared.css';

.amount-positive {
  color: #4CAF50;
  font-weight: 600;
}

.rule-desc {
  font-size: 12px;
  color: #7A7C80;
  text-align: right;
  max-width: 220px;
}

/* ==================== 日历 ==================== */
.calendar-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 14px;
  margin-bottom: 20px;
}

.calendar-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.cal-label {
  font-size: 12px;
  color: #7A7C80;
}

.legend {
  display: flex;
  gap: 12px;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #7A7C80;
}

.dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
}

.dot-3 { background: #FB0079; }
.dot-2 { background: #FF9800; }
.dot-0 { background: #333333; }

.calendar-weekdays {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
  margin-bottom: 6px;
}

.calendar-weekdays span {
  text-align: center;
  font-size: 11px;
  color: #7A7C80;
  padding: 4px 0;
}

.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 4px;
}

.calendar-cell {
  aspect-ratio: 1;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 6px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  position: relative;
  transition: all 0.15s;
}

.calendar-cell.empty {
  background: transparent;
  border: none;
  cursor: default;
}

.calendar-cell:not(.empty):hover {
  border-color: #FB0079;
}

.calendar-cell.has-multiplier {
  border-width: 2px;
}

.calendar-cell.m3 {
  background: rgba(251, 0, 121, 0.15);
  border-color: #FB0079;
}

.calendar-cell.m2 {
  background: rgba(255, 152, 0, 0.15);
  border-color: #FF9800;
}

.day-num {
  font-size: 13px;
  color: #FFFFFF;
  font-weight: 600;
}

.day-multiplier {
  font-size: 10px;
  color: #FB0079;
  margin-top: 2px;
}

.calendar-cell.m2 .day-multiplier {
  color: #FF9800;
}

/* ==================== 倍数选择弹窗 ==================== */
.picker-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.picker-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 14px;
  padding: 20px;
  width: 280px;
}

.picker-title {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  text-align: center;
  margin-bottom: 16px;
}

.picker-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.picker-btn {
  padding: 12px;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #C8C8C8;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.15s;
}

.picker-btn:hover {
  border-color: #FB0079;
  color: #FFFFFF;
}

.picker-btn.m2 {
  border-color: #FF9800;
  color: #FF9800;
}

.picker-btn.m3 {
  border-color: #FB0079;
  color: #FB0079;
}

.picker-cancel {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  background: transparent;
  border: none;
  color: #7A7C80;
  font-size: 13px;
  cursor: pointer;
}
</style>
