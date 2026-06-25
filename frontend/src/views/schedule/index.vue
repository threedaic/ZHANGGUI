<template>
  <div class="schedule-page">
    <!-- 顶部：标题 + 操作（只留2个按钮） -->
    <div class="header">
      <h1 class="page-title">排班管理</h1>
      <div class="header-actions">
        <button class="btn-highlight" @click="openGenerate">一键排班</button>
        <button class="btn-save" :disabled="!dirty" @click="handleSave">
          {{ saving ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>

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

    <!-- 图例 + 休息天数提示（让猴子也看明白） -->
    <div class="legend-bar">
      <div class="legend-items">
        <span v-for="s in shifts" :key="s.shift_code" class="legend-item">
          <span class="legend-dot" :style="{ background: s.color }"></span>
          {{ s.shift_name }}
        </span>
        <span class="legend-item"><span class="legend-dot legend-rest"></span>休息</span>
        <span class="legend-item"><span class="legend-dot legend-leave"></span>请假</span>
      </div>
      <div class="rest-hint" v-if="restDaysPerMonth > 0">
        本店每月休 <b>{{ restDaysPerMonth }}</b> 天 · 点格子改班次
      </div>
    </div>

    <!-- 排班表格 -->
    <div class="table-wrapper">
      <table class="schedule-grid">
        <thead>
          <tr>
            <th class="col-employee">员工</th>
            <th v-for="d in dateList" :key="d" class="col-day">
              <div class="day-header">{{ formatDayHeader(d) }}</div>
              <div class="date-header">{{ formatDateShort(d) }}</div>
            </th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="col-employee">
              <span class="emp-name">{{ emp.employee_name }}</span>
              <span class="emp-role">{{ emp.employee_role_label || emp.employee_role }}</span>
            </td>
            <td
              v-for="d in dateList"
              :key="`${emp.employee_id}-${d}`"
              class="col-cell"
              :class="{ 'cell-late': getCellStatus(emp.employee_id, d) === 'late', 'cell-absent': getCellStatus(emp.employee_id, d) === 'absent' }"
              @click="openCellSelector(emp.employee_id, d)"
            >
              <span
                class="shift-badge"
                :style="getShiftStyle(emp.employee_id, d)"
              >
                {{ getShiftLabel(emp.employee_id, d) }}
              </span>
              <div v-if="!isRestOrLeave(emp.employee_id, d) && formatShiftTime(getCell(emp.employee_id, d))" class="shift-time">
                {{ formatShiftTime(getCell(emp.employee_id, d)) }}
              </div>
              <div v-if="getCell(emp.employee_id, d)?.clock_in" class="clock-info">
                上 {{ formatClock(getCell(emp.employee_id, d)?.clock_in) }}
              </div>
              <div v-if="getCell(emp.employee_id, d)?.clock_out" class="clock-info">
                下 {{ formatClock(getCell(emp.employee_id, d)?.clock_out) }}
              </div>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 班次选择弹窗（简化：点格子直接选） -->
    <el-dialog
      v-model="selectorVisible"
      :title="`${selectorEmployeeName} - ${selectorDate}`"
      width="90%"
      :close-on-click-modal="true"
      class="shift-selector-dialog"
    >
      <div class="selector-options">
        <button
          v-for="opt in shiftOptions"
          :key="opt.value"
          class="selector-btn"
          :style="{ background: opt.color, color: '#fff' }"
          @click="selectShift(opt.value)"
        >
          {{ opt.label }}
        </button>
        <button class="selector-btn rest" @click="selectShift('休息')">休息</button>
        <button class="selector-btn leave" @click="selectShift('请假')">请假</button>
      </div>
    </el-dialog>

    <!-- 智能排班弹窗 -->
    <el-dialog
      v-model="showGenerate"
      title="一键排班"
      width="95%"
      :close-on-click-modal="false"
      class="generate-dialog"
    >
      <div class="generate-controls">
        <select v-model="genYear" class="gen-select">
          <option v-for="y in yearOptions" :key="y" :value="y">{{ y }}年</option>
        </select>
        <select v-model="genMonth" class="gen-select">
          <option v-for="m in 12" :key="m" :value="m">{{ m }}月</option>
        </select>
        <button class="btn-primary" :disabled="generating" @click="doGenerate">
          {{ generating ? '生成中...' : '一键生成' }}
        </button>
      </div>

      <div v-if="genData" class="gen-result">
        <div class="gen-stats">
          共 {{ genStats.entries }} 格 · {{ genStats.night }} 晚班 · {{ genStats.rest }} 休息
        </div>
        <div class="gen-grid" ref="genGridRef">
          <table>
            <thead>
              <tr>
                <th class="gen-name">员工</th>
                <th v-for="d in genDates" :key="d" class="gen-day">{{ d.slice(8) }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="emp in genEmployees" :key="emp.id">
                <td class="gen-name">{{ emp.name }}</td>
                <td
                  v-for="d in genDates"
                  :key="d"
                  class="gen-cell"
                  :class="getGenClass(emp.id, d)"
                  @click="toggleGenCell(emp.id, d)"
                >
                  {{ getGenLabel(emp.id, d) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <button class="btn-save gen-save" :disabled="savingGen" @click="applyGenerate">
          {{ savingGen ? '保存中...' : '应用此排班' }}
        </button>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { attendanceAPI } from '@/api/attendance'
import type { ShiftConfig } from '@/api/attendance'
import { storeAPI } from '@/api/store'

interface ScheduleCell {
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

interface ScheduleEmployeeRow {
  employee_id: string
  employee_name: string
  employee_role: string
  employee_role_label?: string
  shift_group?: string | null
  is_first_manager?: boolean
  is_second_manager?: boolean
  is_third_manager?: boolean
  cells: ScheduleCell[]
}

const viewMode = ref<'week' | 'month'>('month')
const currentDate = ref(new Date())

const employees = ref<ScheduleEmployeeRow[]>([])
const shifts = ref<ShiftConfig[]>([])
const scheduleMap = ref<Record<string, string>>({})
const dirty = ref(false)
const saving = ref(false)

// 当月休息天数（从排班规则读，显示给用户看）
const restDaysPerMonth = ref(0)

// 选择器
const selectorVisible = ref(false)
const selectorEmployeeId = ref<string | null>(null)
const selectorDate = ref<string>('')
const selectorEmployeeName = ref('')

// 手动选择弹窗的班次选项
const shiftOptions = computed(() =>
  shifts.value.map(s => ({
    value: s.shift_code,
    label: s.shift_name,
    color: s.shift_code === 'day' ? '#FB0079' : s.shift_code === 'night' ? '#FB0079' : '#333333',
  }))
)

// ---- 日期计算 ----

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

// ---- 班次操作 ----

function getShift(empId: string, dateStr: string): string {
  return scheduleMap.value[`${empId}_${dateStr}`] || ''
}

function getShiftLabel(empId: string, dateStr: string): string {
  const s = getShift(empId, dateStr)
  const config = shifts.value.find((x) => x.shift_code === s || x.shift_name === s)
  if (config) return config.shift_name
  if (s === '休息') return '休'
  if (s === '请假') return '假'
  return s || '—'
}

function getShiftStyle(empId: string, dateStr: string) {
  const s = getShift(empId, dateStr)
  const config = shifts.value.find((x) => x.shift_code === s || x.shift_name === s)
  if (config) {
    return { background: config.color, color: '#fff' }
  }
  if (s === '休息') return { color: '#7A7C80' }
  if (s === '请假') return { background: '#FB0079', color: '#fff' }
  return { color: '#7A7C80' }
}

function getCell(empId: string, dateStr: string): ScheduleCell | null {
  const emp = employees.value.find((e) => e.employee_id === empId)
  if (!emp) return null
  return emp.cells.find((c) => c.date === dateStr) || null
}

function formatClock(clock: string | null | undefined): string {
  if (!clock) return ''
  if (clock.includes('T')) return clock.slice(11, 16)
  return clock.slice(0, 5)
}

function formatShiftTime(cell: ScheduleCell | null): string {
  if (!cell || !cell.shift_start_time || !cell.shift_end_time) return ''
  return `${cell.shift_start_time}-${cell.shift_end_time}`
}

function isRestOrLeave(empId: string, dateStr: string): boolean {
  const s = getShift(empId, dateStr)
  return s === '休息' || s === '请假'
}

function getCellStatus(empId: string, dateStr: string): string {
  const cell = getCell(empId, dateStr)
  return cell?.status || 'unknown'
}

function openCellSelector(empId: string, dateStr: string) {
  selectorEmployeeId.value = empId
  selectorDate.value = dateStr
  const emp = employees.value.find((e) => e.employee_id === empId)
  selectorEmployeeName.value = emp?.employee_name || ''
  selectorVisible.value = true
}

function selectShift(value: string) {
  if (selectorEmployeeId.value && selectorDate.value) {
    scheduleMap.value[`${selectorEmployeeId.value}_${selectorDate.value}`] = value
    dirty.value = true
  }
  selectorVisible.value = false
}

// ---- 保存 ----

async function handleSave() {
  saving.value = true
  try {
    const payload: { employee_id: string; date: string; scheduled_shift: string }[] = []
    for (const emp of employees.value) {
      for (const d of dateList.value) {
        const shift = scheduleMap.value[`${emp.employee_id}_${d}`]
        if (shift) {
          payload.push({
            employee_id: emp.employee_id,
            date: d,
            scheduled_shift: shift,
          })
        }
      }
    }

    await attendanceAPI.batchSaveSchedules({
      schedules: payload,
    })
    dirty.value = false
    await loadData()
    ElMessage.success('排班已保存')
  } catch (e: any) {
    const msg = e.response?.data?.message || '保存失败'
    ElMessage.error(msg)
  } finally {
    saving.value = false
  }
}

// ---- 智能排班 ----

const showGenerate = ref(false)
const generating = ref(false)
const savingGen = ref(false)
const genYear = ref(new Date().getFullYear())
const genMonth = ref(new Date().getMonth() + 1)
const genData = ref<Record<string, Record<string, string>> | null>(null)
const genStats = ref({ entries: 0, night: 0, rest: 0 })

const yearOptions = computed(() => {
  const y = new Date().getFullYear()
  return [y - 1, y, y + 1]
})

const genDates = computed(() => {
  if (!genData.value) return []
  const dates = new Set<string>()
  for (const empData of Object.values(genData.value)) {
    for (const d of Object.keys(empData)) dates.add(d)
  }
  return Array.from(dates).sort()
})

const genEmployees = computed(() => {
  if (!genData.value) return []
  return Object.entries(genData.value).map(([id, shifts]) => {
    const emp = employees.value.find(e => String(e.employee_id) === String(id))
    return { id: String(id), name: emp?.employee_name || id }
  })
})

function openGenerate() {
  genData.value = null
  showGenerate.value = true
}

async function doGenerate() {
  generating.value = true
  try {
    const res = await attendanceAPI.generateSchedule({ year: genYear.value, month: genMonth.value })
    const schedules = res.data.data.schedules as Array<{ employee_id: string; date: string; scheduled_shift: string }>
    const map: Record<string, Record<string, string>> = {}
    for (const s of schedules) {
      const eid = String(s.employee_id)
      if (!map[eid]) map[eid] = {}
      map[eid][s.date] = s.scheduled_shift
    }
    genData.value = map
    const night = schedules.filter(s => s.scheduled_shift === 'night').length
    const rest = schedules.filter(s => s.scheduled_shift === 'rest').length
    genStats.value = { entries: schedules.length, night, rest }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '生成失败')
  } finally {
    generating.value = false
  }
}

function getGenClass(empId: string, date: string) {
  const shift = genData.value?.[String(empId)]?.[date]
  if (shift === 'night') return 'gen-night'
  if (shift === 'day') return 'gen-day'
  if (shift === 'rest') return 'gen-rest'
  return ''
}

const GEN_LABELS: Record<string, string> = { night: '晚', day: '白', rest: '休' }
function getGenLabel(empId: string, date: string) {
  const shift = genData.value?.[String(empId)]?.[date]
  return GEN_LABELS[shift || ''] || ''
}

function toggleGenCell(empId: string, date: string) {
  if (!genData.value) return
  const eid = String(empId)
  const current = genData.value[eid]?.[date]
  const next = current === 'night' ? 'rest' : current === 'rest' ? '' : 'night'
  if (!genData.value[eid]) genData.value[eid] = {}
  genData.value[eid][date] = next
}

async function applyGenerate() {
  if (!genData.value) return
  savingGen.value = true
  try {
    const payload: { employee_id: string; date: string; scheduled_shift: string }[] = []
    for (const [eid, shifts] of Object.entries(genData.value)) {
      for (const [date, shift] of Object.entries(shifts)) {
        if (shift) {
          payload.push({ employee_id: String(eid), date, scheduled_shift: shift })
        }
      }
    }
    await attendanceAPI.batchSaveSchedules({ schedules: payload })
    showGenerate.value = false
    await loadData()
    ElMessage.success('排班已应用')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '应用失败')
  } finally {
    savingGen.value = false
  }
}

// ---- 数据加载 ----

async function loadData() {
  try {
    const dateFrom = dateList.value[0]
    const dateTo = dateList.value[dateList.value.length - 1]
    const res = await attendanceAPI.getScheduleTable({ date_from: dateFrom, date_to: dateTo })
    const data = res.data?.data || {}

    employees.value = (data.employees || []) as ScheduleEmployeeRow[]
    shifts.value = (data.shifts || []) as ShiftConfig[]

    scheduleMap.value = {}
    for (const emp of (data.employees || []) as ScheduleEmployeeRow[]) {
      for (const cell of emp.cells) {
        if (cell.scheduled_shift) {
          scheduleMap.value[`${emp.employee_id}_${cell.date}`] = cell.scheduled_shift
        }
      }
    }

    dirty.value = false
  } catch (e) {
    console.error('[Schedule] loadData failed:', e)
    ElMessage.error('加载排班数据失败')
  }
}

// 加载休息天数（显示用）
async function loadRestDays() {
  try {
    const res = await storeAPI.getSettings()
    restDaysPerMonth.value = res.data.data?.rest_days_per_month ?? 0
  } catch { /* silent */ }
}

onMounted(() => {
  loadData()
  loadRestDays()
})
</script>

<style scoped>
.schedule-page {
  padding: 16px;
  padding-bottom: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
}

.btn-save {
  padding: 6px 16px;
  border: none;
  border-radius: 8px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-save:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* ---- 周期选择 ---- */
.period-picker {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 12px;
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

/* ---- 图例 ---- */
.legend-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  margin-bottom: 12px;
}
.legend-items {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}
.legend-item {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: #C8C8C8;
}
.legend-dot {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 3px;
  background: #FB0079;
}
.legend-rest {
  background: transparent;
  border: 1px solid #7A7C80;
}
.legend-leave {
  background: #FB0079;
  opacity: 0.5;
}
.rest-hint {
  font-size: 11px;
  color: #7A7C80;
}
.rest-hint b {
  color: #FB0079;
}

/* ---- 表格 ---- */
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

.col-employee {
  width: 80px;
  text-align: left !important;
  padding-left: 12px !important;
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

.emp-name {
  font-size: 13px;
  color: #FFFFFF;
  display: block;
}

.emp-role {
  font-size: 10px;
  color: #7A7C80;
}

.col-cell {
  cursor: pointer;
}

.shift-badge {
  display: inline-block;
  min-width: 32px;
  padding: 3px 6px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.shift-time {
  font-size: 9px;
  color: #7A7C80;
  margin-top: 2px;
  font-family: 'Poppins', sans-serif;
}

.clock-info {
  font-size: 9px;
  color: #7A7C80;
  margin-top: 1px;
  font-family: 'Poppins', sans-serif;
}

.col-cell.cell-late .shift-badge {
  border: 1px solid #FB0079;
}

.col-cell.cell-absent {
  opacity: 0.6;
}

.col-cell.cell-absent .shift-badge {
  border: 1px dashed #FB0079;
}

/* ---- 选择器 ---- */
.selector-options {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  padding: 8px 0;
}

.selector-btn {
  padding: 12px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.selector-btn.rest {
  background: #333333;
  color: #C8C8C8;
}

.selector-btn.leave {
  background: #FB0079;
  color: #FFFFFF;
}

/* ---- el-dialog 暗色主题覆盖 ---- */
.shift-selector-dialog :deep(.el-dialog),
.generate-dialog :deep(.el-dialog) {
  background: #111111;
  border-radius: 12px;
}

.shift-selector-dialog :deep(.el-dialog__header),
.generate-dialog :deep(.el-dialog__header) {
  background: #111111;
  border-bottom: 1px solid #333333;
  margin-right: 0;
  padding: 16px;
}

.shift-selector-dialog :deep(.el-dialog__title),
.generate-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}

.shift-selector-dialog :deep(.el-dialog__headerbtn .el-dialog__close),
.generate-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #7A7C80;
}

.shift-selector-dialog :deep(.el-dialog__body),
.generate-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}

/* ---- 智能排班 ---- */
.btn-primary {
  padding: 8px 14px;
  background: linear-gradient(135deg, #FB0079, #FB0079);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  cursor: pointer;
}
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }

.generate-controls {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.gen-select {
  padding: 8px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 14px;
}
.gen-result { margin-top: 8px; }
.gen-stats {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 8px;
}
.gen-grid {
  overflow-x: auto;
  max-height: 320px;
  overflow-y: auto;
}
.gen-grid table {
  border-collapse: collapse;
  font-size: 11px;
  white-space: nowrap;
}
.gen-grid th, .gen-grid td {
  padding: 3px 4px;
  text-align: center;
  border: 1px solid #222;
  min-width: 24px;
}
.gen-grid thead th {
  position: sticky;
  top: 0;
  background: #1a1a1a;
  color: #7A7C80;
  font-weight: 400;
}
.gen-name {
  text-align: left;
  min-width: 60px;
  color: #C8C8C8;
  font-weight: 500;
}
.gen-cell {
  cursor: pointer;
  font-weight: 600;
  border-radius: 2px;
  transition: background 0.15s;
}
.gen-night { background: #FB0079; color: #fff; }
.gen-day { background: #FB0079; color: #fff; }
.gen-rest { background: #333; color: #7A7C80; }
.gen-save {
  width: 100%;
  margin-top: 12px;
  padding: 12px;
}

/* ---- 高亮按钮 ---- */
.btn-highlight {
  padding: 8px 16px;
  background: linear-gradient(135deg, #FB0079, #FB0079);
  border: none;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 700;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(251, 0, 121, 0.3);
}
.btn-highlight:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
