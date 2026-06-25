<!--
  ============================================================================
  自动发薪页面（AutoPayroll.vue）— CRUSH 风格
  ============================================================================

  【页面布局】
  1. 顶部栏：月份 + 重新计算 + 设置
  2. 工资公式：参与计算的模块用 + 号连接 = 实发工资
  3. 合同模块行
  4. 业绩 + 考勤模块行（并排）
  5. KPI 模块行
  6. 奖惩模块行
  7. 加班费模块行
  8. 工资明细表格

  【交互】
  - 点击模块卡片 → 打开详情弹窗（看数据 + 改参数 + 切换启用）
  - 合同/考勤锁定，始终参与计算
  ============================================================================
-->

<template>
  <div class="auto-payroll">

    <!-- ============================================================
         顶部栏
         ============================================================ -->
    <div class="top-bar">
      <div class="period-picker">
        <button class="month-btn" @click="changeMonth(-1)">‹</button>
        <span class="period-text">{{ currentPeriod }}</span>
        <button class="month-btn" @click="changeMonth(1)">›</button>
      </div>
      <div class="top-actions">
        <button class="calc-btn" :disabled="loading || !canEdit" @click="recalculate">
          {{ loading ? '计算中...' : '重新计算' }}
        </button>
        <button class="finalize-btn" :disabled="finalizing || !canEdit" @click="finalizePayroll">
          {{ finalizing ? '发薪中...' : '一键发薪' }}
        </button>
      </div>
    </div>

    <!-- ============================================================
         会计权限设置（仅老板可见）
         ============================================================ -->
    <div v-if="(auth.isBoss || auth.role === 'admin') && isInSettings" class="permission-card">
      <div class="perm-header">
        <span class="perm-title">会计权限</span>
        <span class="perm-hint">控制会计能否使用自动发薪</span>
      </div>
      <div class="perm-options">
        <button
          class="perm-btn"
          :class="{ active: accountantAccess === 'none' }"
          @click="saveAccountantAccess('none')"
        >不允许访问</button>
        <button
          class="perm-btn"
          :class="{ active: accountantAccess === 'readonly' }"
          @click="saveAccountantAccess('readonly')"
        >只读</button>
        <button
          class="perm-btn"
          :class="{ active: accountantAccess === 'editable' }"
          @click="saveAccountantAccess('editable')"
        >可编辑</button>
      </div>
    </div>

    <!-- 会计无权限提示 -->
    <div v-if="!canEdit && auth.role === 'accountant' && accountantAccess === 'none'" class="no-access">
      老板未开放自动发薪权限，请联系老板开启
    </div>

    <!-- 会计只读提示 -->
    <div v-if="!canEdit && accountantAccess === 'readonly'" class="readonly-banner">
      当前为只读模式，仅查看不可修改
    </div>

    <!-- ============================================================
         第1行：工资公式
         ============================================================ -->
    <div class="section-title">工资公式</div>
    <div class="formula-box">
      <div class="formula-content">
        <template v-for="(info, code) in moduleInfo" :key="code">
          <span v-if="modules[code]" class="formula-tag">
            {{ info.name }}
            <span v-if="info.always_on" class="tag-lock">
              <svg width="10" height="10" viewBox="0 0 12 12" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2.5" y="5.5" width="7" height="5" rx="1"/><path d="M4 5.5V3.5a2 2 0 0 1 4 0v2"/></svg>
            </span>
          </span>
          <span v-if="modules[code] && hasMoreAfter(code)" class="plus-sign">+</span>
        </template>
        <span class="equals-sign">=</span>
        <span class="result-tag">实发工资</span>
      </div>
    </div>

    <!-- ============================================================
         6个模块行

         布局：
         - 第1行：合同 + 考勤（并排，都锁定）
         - 第2行：业绩
         - 第3行：KPI
         - 第4行：奖惩
         - 第5行：加班费

         交互：
         - 点击模块行 → 跳转到二级页面
         - 右边开关：勾上=参与计算，不勾=不参与
         - 合同/考勤锁定，显示锁图标
         ============================================================ -->
    <div class="modules-list">

      <!-- 合同 + 考勤（锁定模块，并排） -->
      <div class="dual-row">
        <div class="module-row locked" @click="goToModule('contract')">
          <div class="module-row-left">
            <span class="module-icon" v-html="moduleSvg('contract', true)"></span>
            <div class="module-info">
              <div class="module-name">合同</div>
            </div>
          </div>
          <div class="module-row-right">
            <span class="lock-icon">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#7A7C80" stroke-width="1.5"><rect x="2.5" y="5.5" width="7" height="5" rx="1"/><path d="M4 5.5V3.5a2 2 0 0 1 4 0v2"/></svg>
            </span>
          </div>
        </div>
        <div class="module-row locked" @click="goToModule('attendance')">
          <div class="module-row-left">
            <span class="module-icon" v-html="moduleSvg('attendance', true)"></span>
            <div class="module-info">
              <div class="module-name">考勤</div>
            </div>
          </div>
          <div class="module-row-right">
            <span class="lock-icon">
              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" stroke="#7A7C80" stroke-width="1.5"><rect x="2.5" y="5.5" width="7" height="5" rx="1"/><path d="M4 5.5V3.5a2 2 0 0 1 4 0v2"/></svg>
            </span>
          </div>
        </div>
      </div>

      <!-- 业绩 -->
      <div class="module-row" :class="{ active: modules['performance'] }" @click="goToModule('performance')">
        <div class="module-row-left">
          <span class="module-icon" v-html="moduleSvg('performance', modules['performance'])"></span>
          <div class="module-info">
            <div class="module-name">业绩</div>
          </div>
        </div>
        <div class="module-row-right">
          <label class="switch" @click.stop="toggleModule('performance')">
            <input type="checkbox" :checked="modules['performance']" />
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <!-- KPI -->
      <div class="module-row" :class="{ active: modules['kpi'] }" @click="goToModule('kpi')">
        <div class="module-row-left">
          <span class="module-icon" v-html="moduleSvg('kpi', modules['kpi'])"></span>
          <div class="module-info">
            <div class="module-name">KPI</div>
          </div>
        </div>
        <div class="module-row-right">
          <label class="switch" @click.stop="toggleModule('kpi')">
            <input type="checkbox" :checked="modules['kpi']" />
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <!-- 奖惩 -->
      <div class="module-row" :class="{ active: modules['reward_penalty'] }" @click="goToModule('reward_penalty')">
        <div class="module-row-left">
          <span class="module-icon" v-html="moduleSvg('reward_penalty', modules['reward_penalty'])"></span>
          <div class="module-info">
            <div class="module-name">奖惩</div>
          </div>
        </div>
        <div class="module-row-right">
          <label class="switch" @click.stop="toggleModule('reward_penalty')">
            <input type="checkbox" :checked="modules['reward_penalty']" />
            <span class="slider"></span>
          </label>
        </div>
      </div>

      <!-- 加班费 -->
      <div class="module-row" :class="{ active: modules['overtime'] }" @click="goToModule('overtime')">
        <div class="module-row-left">
          <span class="module-icon" v-html="moduleSvg('overtime', modules['overtime'])"></span>
          <div class="module-info">
            <div class="module-name">加班费</div>
          </div>
        </div>
        <div class="module-row-right">
          <label class="switch" @click.stop="toggleModule('overtime')">
            <input type="checkbox" :checked="modules['overtime']" />
            <span class="slider"></span>
          </label>
        </div>
      </div>

    </div>

    <!-- ============================================================
         自动化流程（3个步骤，带开关）
         - 考勤锁定: 每月X日
         - 自动生成工资: 发薪日前X天
         - 自动锁定账期: 每月X日（即发薪日）
         ============================================================ -->
    <div class="section-title">自动化流程</div>
    <div class="flow-section">
      <div v-for="step in flowSteps" :key="step.rule_code" class="flow-step" :class="{ disabled: !step.is_active }">
        <div class="step-toggle">
          <label class="switch">
            <input type="checkbox" :checked="step.is_active" @change="toggleStep(step)" />
            <span class="slider"></span>
          </label>
        </div>
        <div class="step-info">
          <div class="step-title">{{ step.title }}</div>
          <div class="step-desc">{{ step.desc }}</div>
        </div>
        <!-- 补卡提醒: 考勤锁定前X天 -->
        <div v-if="step.is_active && step.rule_code === 'attendance_remind_days_before'" class="step-input">
          <span class="form-prefix">考勤锁定前</span>
          <input v-model.number="step.rule_value" type="number" min="1" max="28" step="1" class="input-sm" />
          <span class="form-suffix">天</span>
        </div>
        <!-- 考勤锁定: 每月X日 -->
        <div v-if="step.is_active && step.rule_code === 'attendance_lock_day'" class="step-input">
          <span class="form-prefix">每月</span>
          <input v-model.number="step.rule_value" type="number" min="1" max="28" step="1" class="input-sm" />
          <span class="form-suffix">日</span>
        </div>
        <!-- 自动生成: 发薪日前X天 -->
        <div v-if="step.is_active && step.rule_code === 'auto_generate_days_before'" class="step-input">
          <span class="form-prefix">发薪日前</span>
          <input v-model.number="step.rule_value" type="number" min="1" max="28" step="1" class="input-sm" />
          <span class="form-suffix">天</span>
        </div>
        <!-- 工资审批: 每月X日（发薪日，审批后自动锁定） -->
        <div v-if="step.is_active && step.rule_code === 'auto_lock_period'" class="step-input">
          <span class="form-prefix">每月</span>
          <input v-model.number="flowForm.payroll_day_of_month" type="number" min="1" max="28" step="1" class="input-sm" />
          <span class="form-suffix">日</span>
        </div>
        <!-- 发送工资单: 无输入框，只有开关 -->
        <span v-if="!step.is_active" class="step-closed">已关闭</span>
      </div>
      <button class="save-flow-btn" :disabled="savingFlow || !canEdit" @click="saveFlowRules">
        {{ savingFlow ? '保存中...' : '保存流程设置' }}
      </button>
    </div>

    <!-- ============================================================
         第7行：工资明细表格
         ============================================================ -->
    <div class="section-title">工资明细</div>
    <div class="table-wrap" v-loading="loading">
      <table class="payroll-table">
        <thead>
          <tr>
            <th class="col-name">员工</th>
            <th
              v-for="(info, code) in moduleInfo"
              v-show="modules[code]"
              :key="code"
            >{{ info.name }}</th>
            <th class="col-net">实发</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in tableData.employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td
              v-for="(info, code) in moduleInfo"
              v-show="modules[code]"
              :key="code"
              class="cell-amount"
              :class="amountClass(getModuleTotal(emp, code))"
              @click="startEdit(emp, code)"
            >
              <input
                v-if="editing?.employeeId === emp.employee_id && editing?.module === code"
                v-model="editValue"
                class="edit-input"
                type="number"
                step="0.01"
                @blur="saveEdit"
                @keyup.enter="saveEdit"
                @keyup.esc="cancelEdit"
                ref="editInput"
              />
              <span v-else>{{ formatAmount(getModuleTotal(emp, code)) }}</span>
            </td>
            <td class="cell-net">¥{{ emp.net_pay.toFixed(2) }}</td>
          </tr>
        </tbody>
        <tfoot>
          <tr>
            <td class="cell-summary">合计 {{ tableData.summary.employee_count }} 人</td>
            <td
              v-for="(info, code) in moduleInfo"
              v-show="modules[code]"
              :key="code"
              class="cell-summary-amount"
              :class="amountClass(tableData.summary.modules[code])"
            >{{ formatAmount(tableData.summary.modules[code]) }}</td>
            <td class="cell-summary-net">¥{{ tableData.summary.net_pay.toFixed(2) }}</td>
          </tr>
        </tfoot>
      </table>
      <div v-if="!loading && tableData.employees.length === 0" class="empty">暂无员工数据</div>
    </div>

  </div>
</template>

<script setup lang="ts">
/**
 * ============================================================================
 * 自动发薪 - 逻辑层
 * ============================================================================
 *
 * 【布局说明】
 * 每个模块单独一行，按顺序排列：
 * 1. 工资公式（参与计算的模块用+号连接）
 * 2. 合同
 * 3. 业绩 + 考勤（并排）
 * 4. KPI
 * 5. 奖惩
 * 6. 加班费
 * 7. 工资明细表格
 *
 * 【交互说明】
 * - 点击模块卡片 → 打开详情弹窗
 * - 详情弹窗里可以：切换启用/禁用 + 看数据 + 改参数
 * ============================================================================
 */
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { autoPayrollAPI, type PayrollTable } from '@/api/autoPayroll'
import { storeAPI } from '@/api/store'
import { listRules, toggleRule, updateRule, type SalaryRule } from '@/api/payrollConfig'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const route = useRoute()
const auth = useAuthStore()

// 判断当前在设置端还是管理端（设置端才显示权限卡片）
const isInSettings = computed(() => route.path.startsWith('/settings'))

// ============================================================================
// 会计权限：老板控制会计能否访问 / 只读 / 可编辑
// ============================================================================
const accountantAccess = ref<'none' | 'readonly' | 'editable'>('none')
const extraConfigCache = ref<Record<string, any>>({})

const canEdit = computed(() => {
  if (auth.role === 'boss' || auth.role === 'admin') return true
  if (auth.role === 'accountant') return accountantAccess.value === 'editable'
  return false
})

async function saveAccountantAccess(val: 'none' | 'readonly' | 'editable') {
  try {
    const merged = { ...extraConfigCache.value, accountant_payroll_access: val }
    await storeAPI.updateSettings({ extra_config: merged })
    accountantAccess.value = val
    extraConfigCache.value = merged
    ElMessage.success('权限已更新')
  } catch {
    ElMessage.error('权限更新失败')
  }
}

// ============================================================================
// 1. 状态
// ============================================================================

const loading = ref(false)
const finalizing = ref(false)

const tableData = ref<PayrollTable>({
  period: '',
  modules: {},
  module_info: {},
  rules: {},
  employees: [],
  summary: { modules: {}, net_pay: 0, employee_count: 0 },
})

const currentPeriod = computed(() => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
})

const editing = ref<{ employeeId: string; module: string } | null>(null)
const editValue = ref('')
const editInput = ref<HTMLInputElement[]>([])

// ============================================================================
// 2. 计算属性
// ============================================================================

const moduleInfo = computed(() => tableData.value.module_info)
const modules = computed(() => tableData.value.modules)
const rules = computed(() => tableData.value.rules)

// ============================================================================
// 3. 数据加载
// ============================================================================

async function loadData(period: string) {
  loading.value = true
  try {
    const res = await autoPayrollAPI.getTable(period)
    tableData.value = res.data.data
  } catch (e) {
    console.error('[自动发薪] 加载失败:', e)
  }
  loading.value = false
}

async function recalculate() {
  loading.value = true
  try {
    const res = await autoPayrollAPI.calculate(currentPeriod.value)
    tableData.value = res.data.data
  } catch (e) {
    console.error('[自动发薪] 计算失败:', e)
  }
  loading.value = false
}

async function finalizePayroll() {
  // 确认弹窗，避免误操作
  const totalNet = tableData.value.summary.net_pay.toFixed(2)
  const empCount = tableData.value.summary.employee_count
  if (!confirm(`确认对 ${currentPeriod.value} 账期发薪？\n\n共 ${empCount} 人，实发合计 ¥${totalNet}\n\n点击确认后：\n1. 工资存档（员工可查历史工资单）\n2. 推送签收任务到员工收件箱`)) {
    return
  }
  finalizing.value = true
  try {
    const res = await autoPayrollAPI.finalize(currentPeriod.value)
    const data = res.data.data
    ElMessage.success(`发薪成功！${data.count} 人已存档，${data.tasks_created} 个签收任务已推送`)
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || '未知错误'
    ElMessage.error('发薪失败: ' + msg)
  }
  finalizing.value = false
}

function changeMonth(_delta: number) {
  loadData(currentPeriod.value)
}

// ============================================================================
// 4. 辅助函数
// ============================================================================

/**
 * 跳转到模块二级页面
 */
function goToModule(code: string) {
  const prefix = isInSettings.value ? '/settings' : '/management'
  router.push(`${prefix}/auto-payroll/${code}`)
}

/**
 * 点击开关切换模块启用/禁用
 * 注意：modules 是 computed（只读），要改 tableData.value.modules
 */
async function toggleModule(code: string) {
  if (!canEdit.value) return
  const newVal = !tableData.value.modules[code]
  try {
    await autoPayrollAPI.setModules({ [code]: newVal })
    tableData.value.modules[code] = newVal
  } catch (e) {
    console.error('[自动发薪] 切换模块失败:', e)
  }
}

/**
 * 判断公式框里某个模块后面是否还有更多启用的模块
 */
function hasMoreAfter(code: string): boolean {
  const codes = Object.keys(moduleInfo.value)
  const idx = codes.indexOf(code)
  for (let i = idx + 1; i < codes.length; i++) {
    if (modules.value[codes[i]]) return true
  }
  return false
}

// ============================================================================
// 5. 单元格编辑
// ============================================================================

function startEdit(emp: PayrollTable['employees'][0], code: string) {
  if (!canEdit.value) return
  editing.value = { employeeId: emp.employee_id, module: code }
  const moduleData = emp.modules[code as keyof typeof emp.modules]
  editValue.value = String(moduleData?.total || 0)
  nextTick(() => {
    editInput.value[0]?.focus()
    editInput.value[0]?.select()
  })
}

async function saveEdit() {
  if (!editing.value) return
  const value = parseFloat(editValue.value)
  if (isNaN(value)) { cancelEdit(); return }
  try {
    await autoPayrollAPI.updateCell(
      editing.value.employeeId,
      currentPeriod.value,
      editing.value.module,
      value
    )
    await loadData(currentPeriod.value)
  } catch (e) {
    console.error('[自动发薪] 保存失败:', e)
  }
  editing.value = null
}

function cancelEdit() {
  editing.value = null
}

// ============================================================================
// 6. 辅助函数
// ============================================================================

function getModuleTotal(emp: PayrollTable['employees'][0], code: string): number {
  const moduleData = emp.modules[code as keyof typeof emp.modules]
  return moduleData?.total || 0
}

function formatAmount(amount: number | undefined): string {
  if (amount === undefined || amount === 0) return '-'
  const sign = amount > 0 ? '+' : ''
  return `${sign}¥${Math.abs(amount).toFixed(2)}`
}

function amountClass(amount: number | undefined): string {
  if (amount === undefined || amount === 0) return 'amount-zero'
  return amount > 0 ? 'amount-positive' : 'amount-negative'
}

/** 生成模块 SVG 图标 */
function moduleSvg(code: string, active: boolean): string {
  const stroke = active ? '#FFFFFF' : '#555555'
  const icons: Record<string, string> = {
    contract: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><path d="M7 3h9l5 5v17H7z"/><path d="M16 3v5h5"/><path d="M10 14h8"/><path d="M10 18h8"/></svg>`,
    performance: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><path d="M10 3h8l-1 4h-6z"/><path d="M9 7h10c3 3 4 8 4 12s-4 6-9 6-9-2-9-6 1-9 4-12z"/><circle cx="14" cy="16" r="2"/></svg>`,
    attendance: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><circle cx="14" cy="14" r="10"/><path d="M14 8v6l4 2"/></svg>`,
    kpi: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><path d="M4 22h20"/><rect x="6" y="14" width="4" height="8"/><rect x="12" y="8" width="4" height="14"/><rect x="18" y="11" width="4" height="11"/></svg>`,
    reward_penalty: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><rect x="5" y="10" width="18" height="14" rx="1"/><path d="M5 14h18"/><path d="M14 10v14"/></svg>`,
    overtime: `<svg width="22" height="22" viewBox="0 0 28 28" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round"><path d="M20 18a8 8 0 1 1-10-10 6 6 0 0 0 10 10z"/><circle cx="22" cy="8" r="1.5"/></svg>`,
  }
  return icons[code] || ''
}

function ruleLabel(key: string): string {
  const labels: Record<string, string> = {
    commission_rate: '提成比例',
    late_deduction_per_minute: '迟到每分钟',
    absent_factor: '旷工倍数',
    early_deduction_per_time: '早退每次',
    rest_days_per_month: '月休息天数',
    overtime_multiplier: '加班倍数',
    base_salary: '底薪',
  }
  return labels[key] || key
}

// ============================================================================
// 7. 自动化流程（从薪资规则设置页挪过来）
//    3个步骤：考勤锁定 / 自动生成工资 / 自动锁定账期
//    开关即时切换，数值点「保存流程设置」统一保存
// ============================================================================

const flowForm = reactive({
  payroll_day_of_month: 5,  // 发薪日（存在 store settings）
})

const salaryRules = ref<SalaryRule[]>([])
const savingFlow = ref(false)

const FLOW_STEP_META: Record<string, { title: string; desc: string }> = {
  attendance_remind_days_before: {
    title: '补卡提醒',
    desc: '考勤锁定前X天，提醒还没补卡的员工',
  },
  attendance_lock_day: {
    title: '考勤锁定',
    desc: '每月这天锁定考勤，发考勤确认单给员工签收',
  },
  auto_generate_days_before: {
    title: '自动生成工资',
    desc: '在发薪日前X天，系统自动计算工资草稿',
  },
  auto_lock_period: {
    title: '工资审批',
    desc: '老板审批通过后自动锁定账期，锁定后工资不可修改',
  },
  send_payslip_day: {
    title: '发送工资单',
    desc: '账期锁定后，会计点发送，工资条推送到员工首页收件箱',
  },
}

const flowSteps = computed(() => {
  return salaryRules.value
    .filter((r) => r.rule_code in FLOW_STEP_META)
    .map((r) => ({
      ...r,
      title: FLOW_STEP_META[r.rule_code]?.title || r.rule_name,
      desc: FLOW_STEP_META[r.rule_code]?.desc || r.note || '',
    }))
})

async function toggleStep(step: SalaryRule & { title: string }) {
  if (!canEdit.value) return
  const newActive = !step.is_active
  step.is_active = newActive
  try {
    await toggleRule(step.rule_code, newActive)
    ElMessage.success(`「${step.title}」${newActive ? '已启用' : '已关闭'}`)
  } catch {
    step.is_active = !newActive
    ElMessage.error('操作失败')
  }
}

async function saveFlowRules() {
  savingFlow.value = true
  try {
    // 1. 保存发薪日到 store settings
    await storeAPI.updateSettings({
      payroll_day_of_month: flowForm.payroll_day_of_month,
    })
    // 2. 保存各步骤的 rule_value
    for (const step of flowSteps.value) {
      await updateRule(step.rule_code, step.rule_value)
    }
    ElMessage.success('流程设置已保存')
    await loadFlowData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingFlow.value = false
  }
}

async function loadFlowData() {
  try {
    const [settingsRes, rulesRes] = await Promise.all([
      storeAPI.getSettings(),
      listRules(),
    ])
    const s = settingsRes.data.data
    flowForm.payroll_day_of_month = s.payroll_day_of_month
    salaryRules.value = rulesRes.data.data
    // 加载会计权限
    extraConfigCache.value = s.extra_config || {}
    accountantAccess.value = (extraConfigCache.value.accountant_payroll_access as string) || 'none'
  } catch { /* silent */ }
}

onMounted(() => {
  loadData(currentPeriod.value)
  loadFlowData()
})
</script>

<style scoped>
/* ============================================================================
 * CRUSH 风格 - 暗色主题
 * ============================================================================ */

.auto-payroll {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

/* ==================== 会计权限卡片 ==================== */
.permission-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
}
.perm-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.perm-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.perm-hint {
  font-size: 11px;
  color: #7A7C80;
}
.perm-options {
  display: flex;
  gap: 8px;
}
.perm-btn {
  flex: 1;
  padding: 10px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  color: #C8C8C8;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.perm-btn:hover { border-color: #555; }
.perm-btn.active {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
  color: #FB0079;
  font-weight: 600;
}

.no-access {
  text-align: center;
  padding: 48px 16px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  color: #7A7C80;
}

.readonly-banner {
  text-align: center;
  padding: 8px;
  background: rgba(251, 0, 121, 0.08);
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 8px;
  font-size: 12px;
  color: #FB0079;
  margin-bottom: 16px;
}

/* ==================== 顶部栏 ==================== */
.top-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.period-picker {
  display: flex;
  align-items: center;
  gap: 12px;
}

.month-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #333333;
  background: #111111;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 18px;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.2s;
}

.month-btn:hover { border-color: #FB0079; }

.period-text {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  min-width: 80px;
  text-align: center;
}

.top-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.icon-btn {
  width: 32px;
  height: 32px;
  border: 1px solid #333333;
  background: #111111;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  -webkit-tap-highlight-color: transparent;
  transition: border-color 0.2s;
}

.icon-btn:hover { border-color: #FB0079; }

.calc-btn {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.15s;
}

.calc-btn:active { transform: scale(0.96); }
.calc-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.finalize-btn {
  background: linear-gradient(135deg, #FB0079 0%, #E6006A 100%);
  color: #FFFFFF;
  border: none;
  padding: 8px 20px;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(251, 0, 121, 0.4);
  -webkit-tap-highlight-color: transparent;
  transition: transform 0.15s, box-shadow 0.2s;
}
.finalize-btn:active { transform: scale(0.96); }
.finalize-btn:disabled { opacity: 0.5; cursor: not-allowed; box-shadow: none; }

/* ==================== 区块标题 ==================== */
.section-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #7A7C80;
  margin: 16px 0 8px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.section-title:first-of-type {
  margin-top: 0;
}

/* ==================== 公式框 ==================== */
.formula-box {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 20px 16px;
  margin-bottom: 8px;
  min-height: 80px;
  display: flex;
  align-items: center;
}

.formula-content {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  width: 100%;
}

.formula-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 8px 14px;
  border: 1px solid #555555;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #000000;
}

.tag-lock {
  display: inline-flex;
  color: #7A7C80;
}

.plus-sign {
  font-size: 18px;
  font-weight: 700;
  color: #7A7C80;
  user-select: none;
}

.equals-sign {
  font-size: 18px;
  font-weight: 700;
  color: #7A7C80;
  user-select: none;
  margin-left: 4px;
}

.result-tag {
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border: 1px solid #FB0079;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
}

/* ==================== 模块列表 ==================== */
.modules-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 20px;
}

/* 合同 + 考勤并排 */
.dual-row {
  display: flex;
  gap: 8px;
}

.dual-row .module-row {
  flex: 1;
}

/* 锁定模块样式 */
.module-row.locked {
  opacity: 0.8;
}

/* ==================== 模块行卡片 ==================== */
.module-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  cursor: pointer;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
  transition: all 0.2s ease;
}

.module-row.active {
  border-color: #555555;
}

.module-row:hover {
  border-color: #777777;
  transform: translateY(-1px);
}

.module-row:active {
  transform: scale(0.99);
}

.module-row-left {
  display: flex;
  align-items: center;
  gap: 12px;
}

.module-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.module-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.module-name {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.module-desc {
  font-size: 11px;
  color: #7A7C80;
}

.module-row-right {
  display: flex;
  align-items: center;
  gap: 10px;
}

.status-text {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 11px;
  color: #7A7C80;
}

.module-row.active .status-text {
  color: #FB0079;
}

.lock-icon {
  display: inline-flex;
  align-items: center;
}

/* ==================== 开关（Switch） ==================== */
.switch {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  cursor: pointer;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: #333333;
  border-radius: 20px;
  transition: 0.3s;
}

.slider:before {
  content: "";
  position: absolute;
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background-color: #7A7C80;
  border-radius: 50%;
  transition: 0.3s;
}

.switch input:checked + .slider {
  background-color: #FB0079;
}

.switch input:checked + .slider:before {
  transform: translateX(16px);
  background-color: #FFFFFF;
}

/* ==================== 工资表格 ==================== */
.table-wrap {
  overflow-x: auto;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.payroll-table {
  width: 100%;
  border-collapse: collapse;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
}

.payroll-table th {
  background: #000000;
  padding: 12px 8px;
  text-align: center;
  font-weight: 600;
  color: #7A7C80;
  border-bottom: 1px solid #333333;
  white-space: nowrap;
}

.payroll-table td {
  padding: 12px 8px;
  text-align: center;
  border-bottom: 1px solid #1a1a1a;
}

.col-name { text-align: left; min-width: 90px; padding-left: 14px; }
.cell-name { text-align: left; }

.emp-name {
  font-weight: 600;
  color: #FFFFFF;
  font-size: 14px;
}

.emp-role {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
}

.cell-amount {
  cursor: pointer;
  min-width: 70px;
  transition: background 0.15s;
}

.cell-amount:hover { background: rgba(251, 0, 121, 0.05); }

.amount-positive { color: #4CAF50; }
.amount-negative { color: #FF5252; }
.amount-zero { color: #555555; }

.cell-net {
  font-weight: 700;
  font-size: 15px;
  color: #FFFFFF;
}

.edit-input {
  width: 64px;
  padding: 4px;
  background: #000000;
  border: 1px solid #FB0079;
  border-radius: 4px;
  color: #FFFFFF;
  text-align: center;
  outline: none;
  font-size: 13px;
  font-family: inherit;
}

tfoot td {
  background: #000000;
  font-weight: 700;
  border-top: 2px solid #333333;
  border-bottom: none;
}

.cell-summary { text-align: left; color: #7A7C80; font-size: 12px; }
.cell-summary-amount { font-size: 13px; }
.cell-summary-net { font-size: 16px; color: #FB0079; }

.empty {
  text-align: center;
  color: #7A7C80;
  padding: 48px;
  font-size: 13px;
}

/* ==================== 自动化流程 ==================== */
.flow-section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 0 16px 16px;
  margin-bottom: 20px;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #222222;
}
.flow-step:last-of-type { border-bottom: none; }
.flow-step.disabled { opacity: 0.45; }

.step-toggle { flex-shrink: 0; }

.step-info { flex: 1; }

.step-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
}

.step-desc {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
}

.step-input {
  display: flex;
  align-items: center;
  gap: 6px;
}

.form-prefix,
.form-suffix {
  font-size: 12px;
  color: #7A7C80;
}

.input-sm {
  width: 50px;
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  text-align: center;
}
.input-sm:focus { outline: none; border-color: #FB0079; }

.step-closed {
  font-size: 12px;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.save-flow-btn {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
  transition: opacity 0.2s;
}
.save-flow-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
