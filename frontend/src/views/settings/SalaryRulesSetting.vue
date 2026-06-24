<template>
  <div class="salary-rules-page">
    <div class="page-header">
      <span class="page-title">薪资规则</span>
    </div>

    <!-- 基本参数 -->
    <div class="section">
      <div class="section-header">
        <span>基本参数</span>
      </div>
      <div class="section-body">
        <div class="form-row">
          <span class="form-label">发薪日</span>
          <div class="form-control">
            <span class="form-prefix">每月</span>
            <input v-model.number="form.payroll_day_of_month" type="number" min="1" max="28" class="input input-sm" />
            <span class="form-suffix">日</span>
          </div>
        </div>
        <div class="form-row">
          <span class="form-label">KPI 系数下限</span>
          <div class="form-control">
            <input v-model.number="form.kpi_coefficient_min" type="number" min="0.1" max="2" step="0.05" class="input" :disabled="!kpiEnabled" />
          </div>
        </div>
        <div class="form-row">
          <span class="form-label">KPI 系数上限</span>
          <div class="form-control">
            <input v-model.number="form.kpi_coefficient_max" type="number" min="0.5" max="3" step="0.05" class="input" :disabled="!kpiEnabled" />
          </div>
        </div>
      </div>
    </div>

    <!-- 自动化流程（带开关） -->
    <div class="section">
      <div class="section-header">
        <span>自动化流程</span>
        <span class="section-hint">点击开关可启用/关闭步骤</span>
      </div>
      <div class="section-body">
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
          <div v-if="step.is_active && step.rule_code !== 'auto_lock_period'" class="step-input">
            <input
              v-model.number="step.rule_value"
              type="number"
              min="0"
              max="28"
              step="1"
              class="input input-sm"
            />
            <span class="form-suffix">{{ step.rule_unit || '日' }}</span>
          </div>
          <span v-if="!step.is_active" class="step-closed">已关闭</span>
        </div>
      </div>
    </div>

    <!-- 扣款规则 -->
    <div class="section">
      <div class="section-header">
        <span>扣款规则</span>
      </div>
      <div class="section-body">
        <div v-for="rule in deductionRules" :key="rule.rule_code" class="form-row">
          <span class="form-label">{{ rule.rule_name }}</span>
          <div class="form-control">
            <input
              v-model.number="rule.rule_value"
              type="number"
              min="0"
              step="0.01"
              class="input"
            />
            <span class="form-suffix">{{ rule.rule_unit }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 提成规则 -->
    <div class="section">
      <div class="section-header">
        <span>提成与休息</span>
      </div>
      <div class="section-body">
        <div v-for="rule in incomeRules" :key="rule.rule_code" class="form-row">
          <span class="form-label">{{ rule.rule_name }}</span>
          <div class="form-control">
            <input
              v-model.number="rule.rule_value"
              type="number"
              min="0"
              step="0.01"
              class="input"
            />
            <span class="form-suffix">{{ rule.rule_unit }}</span>
          </div>
        </div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="saveAll">
      {{ saving ? '保存中...' : '保存所有规则' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI } from '@/api/store'
import { listRules, updateRule, toggleRule, type SalaryRule } from '@/api/payrollConfig'

// ====== 基本参数（store settings）======
const form = reactive({
  payroll_day_of_month: 5,
  kpi_coefficient_min: 0.60,
  kpi_coefficient_max: 1.50,
})

// ====== 薪资规则（wage_salary_rules）======
const rules = ref<SalaryRule[]>([])
const saving = ref(false)

// KPI 是否启用
const kpiEnabled = computed(() => {
  const r = rules.value.find((r) => r.rule_code === 'kpi_deadline_day')
  return r ? r.is_active : true
})

// 分类规则
const deductionRules = computed(() =>
  rules.value.filter((r) =>
    ['late_deduction_per_minute', 'absent_factor', 'early_deduction_per_time'].includes(r.rule_code)
  )
)

const incomeRules = computed(() =>
  rules.value.filter((r) =>
    ['commission_rate', 'rest_days_per_month'].includes(r.rule_code)
  )
)

// 流程步骤（带开关）
const FLOW_STEP_META: Record<string, { title: string; desc: string }> = {
  attendance_lock_day: {
    title: '考勤锁定',
    desc: '锁定上月考勤数据，不再接受补卡申请',
  },
  kpi_deadline_day: {
    title: 'KPI 评分截止',
    desc: '店长完成上月员工KPI评分（不考核KPI可关闭）',
  },
  auto_generate_days_before: {
    title: '自动生成工资',
    desc: '系统根据合同+考勤+业绩+KPI自动计算工资草稿',
  },
  auto_lock_period: {
    title: '自动锁定账期',
    desc: '发薪日自动锁定账期，防止后续修改',
  },
}

const flowSteps = computed(() => {
  return rules.value
    .filter((r) => r.rule_code in FLOW_STEP_META)
    .map((r) => ({
      ...r,
      title: FLOW_STEP_META[r.rule_code]?.title || r.rule_name,
      desc: FLOW_STEP_META[r.rule_code]?.desc || r.note || '',
    }))
})

async function toggleStep(step: SalaryRule & { title: string }) {
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

async function loadData() {
  try {
    const [settingsRes, rulesRes] = await Promise.all([
      storeAPI.getSettings(),
      listRules(),
    ])
    const s = settingsRes.data.data
    form.payroll_day_of_month = s.payroll_day_of_month
    form.kpi_coefficient_min = s.kpi_coefficient_min
    form.kpi_coefficient_max = s.kpi_coefficient_max
    rules.value = rulesRes.data.data
  } catch { /* silent */ }
}

async function saveAll() {
  saving.value = true
  try {
    await storeAPI.updateSettings({
      payroll_day_of_month: form.payroll_day_of_month,
      kpi_coefficient_min: form.kpi_coefficient_min,
      kpi_coefficient_max: form.kpi_coefficient_max,
    })

    for (const rule of rules.value) {
      await updateRule(rule.rule_code, rule.rule_value)
    }

    ElMessage.success('规则已保存')
    await loadData()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.salary-rules-page {
  padding: 16px;
  padding-bottom: 80px;
  min-height: 100vh;
  background: #000000;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #C8C8C8;
}

.section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
}
.section-hint {
  font-size: 11px;
  color: #7A7C80;
}
.section-body {
  padding: 0 16px 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
  font-size: 13px;
  color: #C8C8C8;
  flex-wrap: wrap;
}
.form-row:last-child { border-bottom: none; }

.form-label {
  min-width: 100px;
  font-size: 13px;
}

.form-control {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: auto;
}

.form-prefix,
.form-suffix {
  font-size: 12px;
  color: #7A7C80;
}

.form-hint {
  width: 100%;
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
  padding-left: 112px;
}

.input {
  width: 80px;
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  text-align: center;
}
.input-sm { width: 50px; }
.input:focus { outline: none; border-color: #FB0079; }
.input:disabled { opacity: 0.4; }

/* 流程步骤 */
.flow-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 0;
  border-bottom: 1px solid #222222;
}
.flow-step:last-child { border-bottom: none; }
.flow-step.disabled { opacity: 0.45; }

.step-toggle { flex-shrink: 0; }

.step-info { flex: 1; }
.step-title {
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

.step-closed {
  font-size: 12px;
  color: #ef4444;
  background: rgba(239, 68, 68, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 开关样式 */
.switch {
  position: relative;
  display: inline-block;
  width: 40px;
  height: 22px;
}
.switch input { opacity: 0; width: 0; height: 0; }
.slider {
  position: absolute;
  cursor: pointer;
  inset: 0;
  background: #333;
  border-radius: 22px;
  transition: 0.3s;
}
.slider::before {
  content: '';
  position: absolute;
  height: 16px;
  width: 16px;
  left: 3px;
  bottom: 3px;
  background: #888;
  border-radius: 50%;
  transition: 0.3s;
}
.switch input:checked + .slider {
  background: #FB0079;
}
.switch input:checked + .slider::before {
  transform: translateX(18px);
  background: #fff;
}

.save-btn {
  width: 100%;
  margin-top: 14px;
  padding: 12px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
  transition: opacity 0.2s;
  position: fixed;
  bottom: 80px;
  left: 16px;
  right: 16px;
  width: calc(100% - 32px);
  z-index: 10;
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
