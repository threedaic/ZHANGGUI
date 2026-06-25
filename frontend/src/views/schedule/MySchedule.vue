<template>
  <div class="my-schedule-page">
    <h1 class="page-title">我的排班考勤</h1>

    <!-- 周期切换 -->
    <div class="period-picker">
      <select v-model="viewMode" class="mode-select">
        <option value="week">按周</option>
        <option value="month">按月</option>
      </select>
      <button class="period-arrow" @click="prevPeriod">&lt;</button>
      <span class="period-label">{{ periodLabel }}</span>
      <button class="period-arrow" @click="nextPeriod">&gt;</button>
    </div>

    <!-- 统计 -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ stats.work_days }}</span>
        <span class="stat-label">上班天数</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ stats.present_days }}</span>
        <span class="stat-label">正常出勤</span>
      </div>
      <div class="stat-card">
        <span class="stat-value" :class="{ alert: stats.late_days > 0 }">{{ stats.late_days }}</span>
        <span class="stat-label">迟到</span>
      </div>
      <div class="stat-card">
        <span class="stat-value">{{ stats.leave_days }}</span>
        <span class="stat-label">请假</span>
      </div>
    </div>

    <!-- 表格 -->
    <div class="table-wrapper">
      <table class="schedule-grid">
        <thead>
          <tr>
            <th v-for="d in dateList" :key="d" class="col-day">
              <div class="day-header">{{ formatDayHeader(d) }}</div>
              <div class="date-header">{{ formatDateShort(d) }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td
              v-for="d in dateList"
              :key="d"
              class="col-cell"
            >
              <span
                class="shift-badge"
                :style="getShiftStyle(d)"
              >
                {{ getShiftLabel(d) }}
              </span>
              <div v-if="getCell(d).clock_in" class="clock-info">
                上 {{ formatClock(getCell(d).clock_in) }}
              </div>
              <div v-if="getCell(d).clock_out" class="clock-info">
                下 {{ formatClock(getCell(d).clock_out) }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { attendanceAPI } from '@/api/attendance'
import type { ShiftConfig } from '@/api/attendance'

interface MyScheduleCell {
  date: string
  scheduled_shift: string | null
  shift_start_time: string | null
  shift_end_time: string | null
  is_overnight: boolean
  clock_in: string | null
  clock_out: string | null
  status: string
  late_minutes: number
  early_minutes: number
}

const viewMode = ref<'week' | 'month'>('month')
const currentDate = ref(new Date())

const cells = ref<MyScheduleCell[]>([])
const shifts = ref<ShiftConfig[]>([])
const stats = ref({
  work_days: 0,
  present_days: 0,
  late_days: 0,
  leave_days: 0,
  absent_days: 0,
})

const dateList = computed(() => {
  const list: string[] = []
  const start = getPeriodStart(currentDate.value, viewMode.value)
  const end = getPeriodEnd(currentDate.value, viewMode.value)
  const cur = new Date(start)
  while (cur <= end) {
    list.push(toDateStr(cur))
    cur.setDate(cur.getDate() + 1)
  }
  return list
})

const periodLabel = computed(() => {
  const start = getPeriodStart(currentDate.value, viewMode.value)
  const end = getPeriodEnd(currentDate.value, viewMode.value)
  if (viewMode.value === 'month') {
    return `${start.getFullYear()}年${start.getMonth() + 1}月`
  }
  return `${start.getMonth() + 1}/${start.getDate()} - ${end.getMonth() + 1}/${end.getDate()}`
})

function getPeriodStart(d: Date, mode: 'week' | 'month') {
  const date = new Date(d)
  if (mode === 'month') {
    date.setDate(1)
    return date
  }
  const day = date.getDay()
  const diff = day === 0 ? -6 : 1 - day
  date.setDate(date.getDate() + diff)
  return date
}

function getPeriodEnd(d: Date, mode: 'week' | 'month') {
  const date = new Date(d)
  if (mode === 'month') {
    date.setMonth(date.getMonth() + 1)
    date.setDate(0)
    return date
  }
  const start = getPeriodStart(d, mode)
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  return end
}

function toDateStr(d: Date) {
  return d.toISOString().slice(0, 10)
}

function formatDayHeader(dateStr: string) {
  const d = new Date(dateStr)
  const labels = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  return labels[d.getDay()]
}

function formatDateShort(dateStr: string) {
  const d = new Date(dateStr)
  return `${d.getMonth() + 1}/${d.getDate()}`
}

function formatClock(clock: string | null) {
  if (!clock) return ''
  if (clock.includes('T')) return clock.slice(11, 16)
  return clock.slice(0, 5)
}

function prevPeriod() {
  const d = new Date(currentDate.value)
  if (viewMode.value === 'month') {
    d.setMonth(d.getMonth() - 1)
  } else {
    d.setDate(d.getDate() - 7)
  }
  currentDate.value = d
  loadData()
}

function nextPeriod() {
  const d = new Date(currentDate.value)
  if (viewMode.value === 'month') {
    d.setMonth(d.getMonth() + 1)
  } else {
    d.setDate(d.getDate() + 7)
  }
  currentDate.value = d
  loadData()
}

// 班次名称映射：英文code → 中文
const SHIFT_NAME_MAP: Record<string, string> = {
  day: '白班',
  night: '晚班',
  rest: '休息',
  leave: '请假',
  EVENNING: '晚班',
  EVENING: '晚班',
  evening: '晚班',
  EVENing: '晚班',
  morning: '早班',
  afternoon: '午班',
}

function getShiftDisplayName(shift?: string | null): string {
  if (!shift) return ''
  // 先精确匹配，再小写匹配
  return SHIFT_NAME_MAP[shift] || SHIFT_NAME_MAP[shift.toLowerCase()] || shift
}

function getCell(dateStr: string): MyScheduleCell {
  return cells.value.find((c: MyScheduleCell) => c.date === dateStr) || {
    date: dateStr,
    scheduled_shift: null,
    shift_start_time: null,
    shift_end_time: null,
    is_overnight: false,
    clock_in: null,
    clock_out: null,
    status: 'unknown',
    late_minutes: 0,
    early_minutes: 0,
  }
}

function getShiftLabel(dateStr: string): string {
  const cell = getCell(dateStr)
  return getShiftDisplayName(cell.scheduled_shift) || '—'
}

function getShiftStyle(dateStr: string) {
  const cell = getCell(dateStr)
  const config = shifts.value.find((s: ShiftConfig) => s.shift_name === cell.scheduled_shift)
  if (config) return { background: config.color, color: '#fff' }
  if (cell.scheduled_shift === '休息') return { color: '#7A7C80' }
  if (cell.scheduled_shift === '请假') return { background: '#2196F3', color: '#fff' }
  return { color: '#7A7C80' }
}

async function loadData() {
  const dateFrom = dateList.value[0]
  const dateTo = dateList.value[dateList.value.length - 1]
  const res = await attendanceAPI.getMySchedule({ date_from: dateFrom, date_to: dateTo })
  const data = res.data?.data || {}
  cells.value = (data.cells || []) as MyScheduleCell[]
  shifts.value = (data.shifts || []) as ShiftConfig[]
  stats.value = (data.stats || stats.value) as typeof stats.value
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.my-schedule-page {
  padding: 16px;
  padding-bottom: 24px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 16px;
}

.period-picker {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 16px;
}

.mode-select {
  padding: 6px 10px;
  border: 1px solid #333333;
  border-radius: 8px;
  background: #111111;
  color: #C8C8C8;
  font-size: 13px;
}

.period-arrow {
  width: 28px;
  height: 28px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #111111;
  color: #C8C8C8;
  cursor: pointer;
}

.period-label {
  font-size: 14px;
  color: #FFFFFF;
  font-weight: 600;
  min-width: 120px;
  text-align: center;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.stat-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 12px 4px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.stat-value {
  font-family: 'Poppins', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
}

.stat-value.alert {
  color: #FB0079;
}

.stat-label {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.table-wrapper {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}

.schedule-grid {
  width: 100%;
  min-width: 560px;
  border-collapse: collapse;
  background: #111111;
  border-radius: 12px;
  overflow: hidden;
}

.schedule-grid th,
.schedule-grid td {
  padding: 6px 4px;
  text-align: center;
  border-bottom: 1px solid #222222;
}

.col-day {
  min-width: 48px;
}

.schedule-grid thead th {
  background: #333333;
  padding: 8px 4px;
  position: sticky;
  top: 0;
  z-index: 1;
}

.day-header {
  font-size: 12px;
  color: #C8C8C8;
  font-weight: 600;
}

.date-header {
  font-size: 10px;
  color: #7A7C80;
  margin-top: 2px;
}

.shift-badge {
  display: inline-block;
  min-width: 32px;
  padding: 3px 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.clock-info {
  font-size: 9px;
  color: #7A7C80;
  margin-top: 2px;
}
</style>
