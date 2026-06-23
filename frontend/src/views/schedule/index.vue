<template>
  <div class="schedule-page">
    <!-- 顶部：标题 + 视图切换 + 操作 -->
    <div class="header">
      <h1 class="page-title">排班考勤</h1>
      <div class="header-actions">
        <button class="btn-icon" @click="showRuleSetting = true">排班规则</button>
        <button class="btn-icon" @click="showTemplate = true">周模板</button>
        <button class="btn-icon" @click="handleSync">同步打卡</button>
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
      <button class="btn-batch" :class="{ active: batchMode }" @click="batchMode = !batchMode">
        {{ batchMode ? '退出批量' : '批量排班' }}
      </button>
      <button v-if="batchMode && currentWeekIndex >= 0" class="btn-batch-copy" @click="copyWeekToMonth">
        复制到整月
      </button>
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

    <!-- 班次选择弹窗 -->
    <el-dialog
      v-model="selectorVisible"
      :title="`${selectorEmployeeName} - ${selectorDate}`"
      width="90%"
      :close-on-click-modal="false"
      class="shift-selector-dialog"
    >
      <div v-if="batchMode" class="batch-hint">
        批量模式：选择班次后将自动填写本周（周一~周日），并自动安排周日休息（月休4天规则）
      </div>
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

    <!-- 排班规则弹窗：设员工属性 -->
    <el-dialog
      v-model="showRuleSetting"
      title="排班规则"
      width="92%"
      :close-on-click-modal="false"
      class="rule-dialog"
    >
      <div class="rule-section">
        <div class="rule-subtitle">岗位出勤约束</div>
        <div class="rule-coverage-row">
          <span class="rule-coverage-label">每个岗位出勤人数不得低于</span>
          <input
            v-model.number="ruleCoveragePercent"
            type="number"
            min="0"
            max="100"
            class="rule-coverage-input"
          />
          <span class="rule-coverage-unit">%</span>
        </div>
        <div class="rule-coverage-hint">
          同岗位员工请假后，在岗人数不得低于此比例（病假不受此限制）。例如4个服务员设50%，则最多2人同时休假。
        </div>
      </div>

      <div class="rule-section">
        <div class="rule-subtitle">员工班组与管理顺位</div>
        <div class="rule-employee-list">
          <div v-for="emp in ruleEmployees" :key="emp.id" class="rule-emp-row">
            <span class="rule-emp-name">{{ emp.name }}</span>
            <select v-model="emp.shift_group" class="rule-select" :class="{ 'rule-select-day': emp.shift_group === 'day' }">
              <option :value="null">夜班组</option>
              <option value="day">白班组</option>
            </select>
            <label class="rule-check"><input type="checkbox" v-model="emp.is_first" /> 第一</label>
            <label class="rule-check"><input type="checkbox" v-model="emp.is_second" /> 第二</label>
            <label class="rule-check"><input type="checkbox" v-model="emp.is_third" /> 第三</label>
          </div>
        </div>
        <button class="btn-save rule-save" :disabled="savingRule" @click="saveRuleSettings">
          {{ savingRule ? '保存中...' : '保存规则' }}
        </button>
      </div>
    </el-dialog>

    <!-- 智能排班弹窗 -->
    <el-dialog
      v-model="showGenerate"
      title="智能排班"
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

    <!-- 周模板弹窗 -->
    <el-dialog
      v-model="showTemplate"
      title="周模板管理"
      width="92%"
      :close-on-click-modal="false"
      class="template-dialog"
    >
      <div class="template-section">
        <div class="template-subtitle">保存当前排班为模板</div>
        <div class="template-save-row">
          <input
            v-model="newTemplateName"
            class="template-input"
            placeholder="模板名称（如：常规周、节假日周）"
          />
          <button class="btn-primary template-save-btn" @click="saveAsTemplate">
            保存模板
          </button>
        </div>
        <div class="template-hint">
          保存后，可一键将模板应用到任意周/月。模板记录每个员工在一周中每天的班次模式。
        </div>
      </div>

      <div class="template-section">
        <div class="template-subtitle">已保存的模板</div>
        <div v-if="templateList.length === 0" class="template-empty">
          暂无模板，请先排好一周后保存为模板
        </div>
        <div v-else class="template-list">
          <div v-for="tpl in templateList" :key="tpl.id" class="template-item">
            <div class="template-item-info">
              <span class="template-item-name">{{ tpl.name }}</span>
              <span class="template-item-meta">{{ tpl.employee_count }}人 · {{ tpl.created_at.slice(0, 10) }}</span>
            </div>
            <div class="template-item-actions">
              <button class="btn-apply" @click="applyTemplate(tpl)">应用到本周</button>
              <button class="btn-apply" @click="applyTemplateToMonth(tpl)">应用到整月</button>
              <button class="btn-delete" @click="deleteTemplate(tpl.id)">删除</button>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
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

// 选择器
const selectorVisible = ref(false)
const selectorEmployeeId = ref<string | null>(null)
const selectorDate = ref<string>('')
const selectorEmployeeName = ref('')

const batchMode = ref(false)
const currentWeekIndex = ref(-1)

// ==================== 周模板 ====================
interface ScheduleTemplate {
  id: string
  name: string
  created_at: string
  employee_count: number
  // pattern[employee_id][dayOfWeek] = shift_code
  // dayOfWeek: 0=周日, 1=周一, ..., 6=周六
  pattern: Record<string, Record<number, string>>
}

const showTemplate = ref(false)
const newTemplateName = ref('')
const templateList = ref<ScheduleTemplate[]>([])

function loadTemplates() {
  try {
    const raw = localStorage.getItem('schedule_templates')
    templateList.value = raw ? JSON.parse(raw) : []
  } catch {
    templateList.value = []
  }
}

function persistTemplates() {
  localStorage.setItem('schedule_templates', JSON.stringify(templateList.value))
}

function saveAsTemplate() {
  const name = newTemplateName.value.trim()
  if (!name) {
    ElMessage.warning('请输入模板名称')
    return
  }
  // 收集当前排班数据，按员工和星期几分组
  const pattern: Record<string, Record<number, string>> = {}
  let hasData = false
  for (const emp of employees.value) {
    pattern[emp.employee_id] = {}
    for (const cell of emp.cells) {
      const shift = scheduleMap.value[`${emp.employee_id}_${cell.date}`]
      if (shift) {
        const dow = new Date(cell.date).getDay()
        pattern[emp.employee_id][dow] = shift
        hasData = true
      }
    }
  }
  if (!hasData) {
    ElMessage.warning('当前没有排班数据，请先排班再保存模板')
    return
  }
  const tpl: ScheduleTemplate = {
    id: `tpl_${Date.now()}`,
    name,
    created_at: new Date().toISOString(),
    employee_count: Object.keys(pattern).length,
    pattern,
  }
  templateList.value.unshift(tpl)
  persistTemplates()
  newTemplateName.value = ''
  ElMessage.success(`模板「${name}」已保存`)
}

function applyTemplate(tpl: ScheduleTemplate) {
  // 应用到当前视图的所有日期
  const dates = dateList.value
  let applied = 0
  for (const emp of employees.value) {
    const empPattern = tpl.pattern[emp.employee_id]
    if (!empPattern) continue
    for (const d of dates) {
      const dow = new Date(d).getDay()
      const shift = empPattern[dow]
      if (shift) {
        scheduleMap.value[`${emp.employee_id}_${d}`] = shift
        applied++
      }
    }
  }
  dirty.value = true
  ElMessage.success(`已应用模板「${tpl.name}」到当前${viewMode.value === 'week' ? '周' : '月'}（${applied}格）`)
}

function applyTemplateToMonth(tpl: ScheduleTemplate) {
  // 切换到月视图并应用
  viewMode.value = 'month'
  const dates = dateList.value
  let applied = 0
  for (const emp of employees.value) {
    const empPattern = tpl.pattern[emp.employee_id]
    if (!empPattern) continue
    for (const d of dates) {
      const dow = new Date(d).getDay()
      const shift = empPattern[dow]
      if (shift) {
        scheduleMap.value[`${emp.employee_id}_${d}`] = shift
        applied++
      }
    }
  }
  dirty.value = true
  ElMessage.success(`已应用模板「${tpl.name}」到整月（${applied}格）`)
}

function deleteTemplate(id: string) {
  templateList.value = templateList.value.filter(t => t.id !== id)
  persistTemplates()
  ElMessage.success('模板已删除')
}

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
  if (batchMode.value) {
    // 批量模式：选中这一周（周一到周日）
    currentWeekIndex.value = getWeekIndex(dateStr)
    selectorEmployeeId.value = empId
    selectorDate.value = dateStr
    const emp = employees.value.find((e) => e.employee_id === empId)
    const weekDates = getWeekDates(currentWeekIndex.value)
    const weekLabel = weekDates.length > 0
      ? `${weekDates[0].slice(5)} ~ ${weekDates[weekDates.length - 1].slice(5)}`
      : `第${currentWeekIndex.value + 1}周`
    selectorEmployeeName.value = `${emp?.employee_name || ''} (${weekLabel})`
    selectorVisible.value = true
  } else {
    // 逐日模式
    selectorEmployeeId.value = empId
    selectorDate.value = dateStr
    const emp = employees.value.find((e) => e.employee_id === empId)
    selectorEmployeeName.value = emp?.employee_name || ''
    selectorVisible.value = true
  }
}

function getWeekIndex(dateStr: string): number {
  // 以周一为一周起点，计算该日期所在自然周是本月的第几周
  const d = new Date(dateStr)
  // 找到该日期所在周的周一
  const dayOfWeek = d.getDay() // 0=周日, 1=周一...
  const diffToMonday = dayOfWeek === 0 ? -6 : 1 - dayOfWeek
  const monday = new Date(d)
  monday.setDate(d.getDate() + diffToMonday)
  // 计算该周一在本月的第几周（以本月第一个周一为第0周）
  const monthStart = getPeriodStart(currentDate.value, 'month')
  const firstDayOfWeek = monthStart.getDay()
  const firstMondayOffset = firstDayOfWeek === 0 ? 1 : 8 - firstDayOfWeek
  const firstMonday = new Date(monthStart)
  firstMonday.setDate(monthStart.getDate() + firstMondayOffset)
  if (monday < firstMonday) return 0
  const weekDiff = Math.floor((monday.getTime() - firstMonday.getTime()) / (7 * 86400000))
  return weekDiff + 1
}

function getWeekDates(weekIndex: number): string[] {
  // 返回第 weekIndex 周的周一到周日（7天）
  const monthStart = getPeriodStart(currentDate.value, 'month')
  const firstDayOfWeek = monthStart.getDay()
  const firstMondayOffset = firstDayOfWeek === 0 ? 1 : 8 - firstDayOfWeek
  const firstMonday = new Date(monthStart)
  firstMonday.setDate(monthStart.getDate() + firstMondayOffset)

  let weekMonday: Date
  if (weekIndex === 0) {
    // 第0周：月初到第一个周一之前（可能不满7天）
    weekMonday = new Date(monthStart)
  } else {
    weekMonday = new Date(firstMonday)
    weekMonday.setDate(firstMonday.getDate() + (weekIndex - 1) * 7)
  }

  const result: string[] = []
  const monthEnd = getPeriodEnd(currentDate.value, 'month')
  for (let i = 0; i < 7; i++) {
    const d = new Date(weekMonday)
    d.setDate(weekMonday.getDate() + i)
    // 只包含本月内的日期
    if (d >= monthStart && d <= monthEnd) {
      result.push(toDateStr(d))
    }
  }
  return result
}

function selectShift(value: string) {
  if (selectorEmployeeId.value) {
    if (batchMode.value && currentWeekIndex.value >= 0) {
      // 批量模式：填写整周，自动安排休息日（月休4天 ≈ 每周休1天）
      const weekDates = getWeekDates(currentWeekIndex.value)
      if (value === '休息' || value === '请假') {
        // 选休息/请假：整周都设为该状态
        for (const d of weekDates) {
          scheduleMap.value[`${selectorEmployeeId.value}_${d}`] = value
        }
      } else {
        // 选班次：6天上班 + 1天休息（默认周日休息）
        // 找到周日作为休息日，如果没有周日则取最后一天
        let restDate = weekDates[weekDates.length - 1]
        for (const d of weekDates) {
          if (new Date(d).getDay() === 0) { // 周日
            restDate = d
            break
          }
        }
        for (const d of weekDates) {
          if (d === restDate) {
            scheduleMap.value[`${selectorEmployeeId.value}_${d}`] = '休息'
          } else {
            scheduleMap.value[`${selectorEmployeeId.value}_${d}`] = value
          }
        }
      }
    } else if (selectorDate.value) {
      // 逐日模式
      scheduleMap.value[`${selectorEmployeeId.value}_${selectorDate.value}`] = value
    }
    dirty.value = true
  }
  selectorVisible.value = false
  currentWeekIndex.value = -1
}

function copyWeekToMonth() {
  if (!selectorEmployeeId.value || currentWeekIndex.value < 0) return
  const weekDates = getWeekDates(currentWeekIndex.value)
  const srcPattern: Record<number, string> = {}
  for (const d of weekDates) {
    const shift = scheduleMap.value[`${selectorEmployeeId.value}_${d}`]
    if (shift) srcPattern[new Date(d).getDay()] = shift
  }
  if (Object.keys(srcPattern).length === 0) return

  const allDates = dateList.value
  for (const d of allDates) {
    if (weekDates.includes(d)) continue
    const dow = new Date(d).getDay()
    const shift = srcPattern[dow]
    if (shift) {
      scheduleMap.value[`${selectorEmployeeId.value}_${d}`] = shift
    }
  }
  dirty.value = true
  ElMessage.success(`已将本周排班模式复制到整月（含休息日）`)
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
  } catch (e: any) {
    const msg = e.response?.data?.message || '保存失败'
    alert(msg)
  } finally {
    saving.value = false
  }
}

async function handleSync() {
  try {
    await attendanceAPI.syncCheckin()
    alert('打卡同步完成')
    await loadData()
  } catch (e: any) {
    alert(e.response?.data?.message || '同步失败')
  }
}

// ---- 排班规则 ----

const showRuleSetting = ref(false)
const savingRule = ref(false)
const ruleCoveragePercent = ref(50)

interface RuleEmployee {
  id: string
  name: string
  shift_group: string | null
  is_first: boolean
  is_second: boolean
  is_third: boolean
}
const ruleEmployees = ref<RuleEmployee[]>([])

function loadRuleEmployees() {
  ruleEmployees.value = employees.value
    .filter(e => e.employee_role === 'staff' || e.employee_role === 'store_manager')
    .map(e => ({
      id: e.employee_id,
      name: e.employee_name,
      shift_group: e.shift_group || null,
      is_first: e.is_first_manager || false,
      is_second: e.is_second_manager || false,
      is_third: e.is_third_manager || false,
    }))
}

watch(showRuleSetting, async (val) => {
  if (val) {
    loadRuleEmployees()
    // 加载岗位覆盖率配置
    try {
      const res = await storeAPI.getSettings()
      const s = res.data.data
      ruleCoveragePercent.value = s.min_position_coverage_percent ?? 50
    } catch { /* silent */ }
  }
})

async function saveRuleSettings() {
  savingRule.value = true
  try {
    // 保存员工规则
    const updates = ruleEmployees.value.map(e => ({
      employee_id: e.id,
      shift_group: e.shift_group,
      is_first_manager: e.is_first,
      is_second_manager: e.is_second,
      is_third_manager: e.is_third,
    }))
    await attendanceAPI.batchUpdateEmployeeRules({ employees: updates })
    // 保存岗位覆盖率
    await storeAPI.updateSettings({
      min_position_coverage_percent: ruleCoveragePercent.value,
    })
    showRuleSetting.value = false
    alert('排班规则已保存')
  } catch (e: any) {
    alert(e.response?.data?.message || '保存失败')
  } finally {
    savingRule.value = false
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
    // 转为嵌套结构: { empId: { date: shift } }
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
    alert(e.response?.data?.message || '生成失败')
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
  } catch (e: any) {
    alert(e.response?.data?.message || '应用失败')
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

    // 重建 scheduleMap（用于单元格快速读写）
    scheduleMap.value = {}
    for (const emp of (data.employees || []) as ScheduleEmployeeRow[]) {
      for (const cell of emp.cells) {
        if (cell.scheduled_shift) {
          scheduleMap.value[`${emp.employee_id}_${cell.date}`] = cell.scheduled_shift
        }
      }
    }

    // 统计
    dirty.value = false
  } catch (e) {
    console.error('[Schedule] loadData failed:', e)
    ElMessage.error('加载排班数据失败')
  }
}

onMounted(() => {
  loadData()
  loadTemplates()
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

.btn-icon {
  padding: 6px 12px;
  border: 1px solid #333333;
  border-radius: 8px;
  background: #111111;
  color: #C8C8C8;
  font-size: 12px;
  cursor: pointer;
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
.batch-hint {
  background: rgba(251, 0, 121, 0.1);
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 8px;
  padding: 10px 12px;
  margin-bottom: 12px;
  font-size: 12px;
  color: #FB0079;
  line-height: 1.5;
}

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
.shift-setting-dialog :deep(.el-dialog) {
  background: #111111;
  border-radius: 12px;
}

.shift-selector-dialog :deep(.el-dialog__header),
.shift-setting-dialog :deep(.el-dialog__header) {
  background: #111111;
  border-bottom: 1px solid #333333;
  margin-right: 0;
  padding: 16px;
}

.shift-selector-dialog :deep(.el-dialog__title),
.shift-setting-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}

.shift-selector-dialog :deep(.el-dialog__headerbtn .el-dialog__close),
.shift-setting-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #7A7C80;
}

.shift-selector-dialog :deep(.el-dialog__body),
.shift-setting-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}

.shift-setting-dialog :deep(.el-dialog) {
  max-width: 400px;
  margin: 0 auto;
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

.generate-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 12px;
}

/* ---- 周模板 ---- */
.template-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}
.template-section {
  margin-bottom: 20px;
}
.template-subtitle {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 10px;
}
.template-save-row {
  display: flex;
  gap: 8px;
  margin-bottom: 8px;
}
.template-input {
  flex: 1;
  height: 40px;
  padding: 0 12px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
}
.template-input:focus { border-color: #FB0079; }
.template-save-btn {
  padding: 0 16px;
  height: 40px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
}
.template-hint {
  font-size: 12px;
  color: #7A7C80;
  line-height: 1.5;
}
.template-empty {
  text-align: center;
  padding: 24px 0;
  color: #7A7C80;
  font-size: 13px;
}
.template-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.template-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 8px;
}
.template-item-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.template-item-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.template-item-meta {
  font-size: 11px;
  color: #7A7C80;
}
.template-item-actions {
  display: flex;
  gap: 6px;
}
.btn-apply {
  padding: 6px 10px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
}
.btn-delete {
  padding: 6px 10px;
  background: transparent;
  color: #FB0079;
  border: 1px solid #FB0079;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

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

/* ---- 排班规则弹窗 ---- */
.rule-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 12px;
}

.rule-coverage-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 0;
}

.rule-coverage-label {
  color: #E8E8E8;
  font-size: 13px;
  flex: 1;
}

.rule-coverage-input {
  width: 60px;
  height: 32px;
  background: #0A0A0A;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #FB0079;
  text-align: center;
  font-size: 14px;
  font-weight: 600;
}

.rule-coverage-input:focus {
  outline: none;
  border-color: #FB0079;
}

.rule-coverage-unit {
  color: #7A7C80;
  font-size: 13px;
}

.rule-coverage-hint {
  padding: 4px 0 8px;
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
}
.rule-subtitle {
  font-size: 13px;
  color: #7A7C80;
  margin-bottom: 10px;
}
.rule-employee-list {
  max-height: 380px;
  overflow-y: auto;
}
.rule-emp-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid #222;
  font-size: 13px;
}
.rule-emp-name {
  width: 70px;
  color: #C8C8C8;
  font-weight: 500;
  flex-shrink: 0;
}
.rule-select {
  padding: 4px 6px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 4px;
  color: #C8C8C8;
  font-size: 12px;
}
.rule-select-day {
  background: #FB0079;
  color: #fff;
  border-color: #FB0079;
}
.rule-check {
  display: flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #7A7C80;
}
.rule-check input { accent-color: #FB0079; }
.rule-save {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
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

.btn-batch {
  padding: 4px 10px;
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 6px;
  color: #7A7C80;
  font-size: 12px;
  cursor: pointer;
  margin-left: 6px;
}
.btn-batch.active {
  background: #FB0079;
  border-color: #FB0079;
  color: #fff;
}
.btn-batch-copy {
  padding: 4px 10px;
  background: #FB0079;
  border: none;
  border-radius: 6px;
  color: #fff;
  font-size: 12px;
  cursor: pointer;
}
</style>
