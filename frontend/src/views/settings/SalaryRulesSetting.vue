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
            <input v-model.number="form.kpi_coefficient_min" type="number" min="0.1" max="2" step="0.05" class="input" />
          </div>
        </div>
        <div class="form-row">
          <span class="form-label">KPI 系数上限</span>
          <div class="form-control">
            <input v-model.number="form.kpi_coefficient_max" type="number" min="0.5" max="3" step="0.05" class="input" />
          </div>
        </div>
      </div>
    </div>

    <!-- 自动化流程 -->
    <div class="section">
      <div class="section-header">
        <span>自动化流程</span>
        <span class="section-hint">以发薪日为基准的自动算工资流程</span>
      </div>
      <div class="section-body">
        <div class="timeline">
          <div v-for="step in timelineSteps" :key="step.day" class="timeline-step">
            <div class="timeline-dot" :class="step.type"></div>
            <div class="timeline-content">
              <div class="timeline-title">{{ step.title }}</div>
              <div class="timeline-desc">{{ step.desc }}</div>
            </div>
          </div>
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

    <!-- 流程配置 -->
    <div class="section">
      <div class="section-header">
        <span>流程配置</span>
      </div>
      <div class="section-body">
        <div v-for="rule in workflowRules" :key="rule.rule_code" class="form-row">
          <span class="form-label">{{ rule.rule_name }}</span>
          <div class="form-control">
            <input
              v-model.number="rule.rule_value"
              type="number"
              min="0"
              max="28"
              step="1"
              class="input input-sm"
            />
            <span class="form-suffix">{{ rule.rule_unit || '' }}</span>
          </div>
          <span v-if="rule.note" class="form-hint">{{ rule.note }}</span>
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
import { storeAPI, type StoreSettingsData } from '@/api/store'
import { listRules, updateRule, type SalaryRule } from '@/api/payrollConfig'

// ====== 基本参数（store settings）======
const form = reactive({
  payroll_day_of_month: 5,
  kpi_coefficient_min: 0.60,
  kpi_coefficient_max: 1.50,
})

// ====== 薪资规则（wage_salary_rules）======
const rules = ref<SalaryRule[]>([])
const saving = ref(false)

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

const workflowRules = computed(() =>
  rules.value.filter((r) =>
    ['auto_generate_days_before', 'attendance_lock_day', 'auto_lock_period', 'kpi_deadline_day'].includes(r.rule_code)
  )
)

// ====== 自动化流程时间线 ======
const timelineSteps = computed(() => {
  const payDay = form.payroll_day_of_month
  const lockDay = rules.value.find((r) => r.rule_code === 'attendance_lock_day')?.rule_value ?? 2
  const kpiDay = rules.value.find((r) => r.rule_code === 'kpi_deadline_day')?.rule_value ?? 3
  const genDaysBefore = rules.value.find((r) => r.rule_code === 'auto_generate_days_before')?.rule_value ?? 1
  const genDay = payDay - genDaysBefore

  return [
    {
      day: `每月${lockDay}日`,
      title: `考勤锁定`,
      desc: '锁定上月考勤数据，不再接受补卡申请',
      type: 'lock',
    },
    {
      day: `每月${kpiDay}日`,
      title: `KPI 评分截止`,
      desc: '店长完成上月员工KPI评分',
      type: 'kpi',
    },
    {
      day: `每月${genDay}日`,
      title: `自动生成工资`,
      desc: '系统根据合同+考勤+业绩+KPI自动计算工资草稿',
      type: 'generate',
    },
    {
      day: `每月${genDay}-${payDay}日`,
      title: `老板审核`,
      desc: '检查工资明细，确认无误后点击「确认工资」',
      type: 'review',
    },
    {
      day: `每月${payDay}日`,
      title: `发放工资`,
      desc: '确认后自动推送工资条给员工，锁定账期',
      type: 'pay',
    },
  ]
})

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
    // 保存 store settings
    await storeAPI.updateSettings({
      payroll_day_of_month: form.payroll_day_of_month,
      kpi_coefficient_min: form.kpi_coefficient_min,
      kpi_coefficient_max: form.kpi_coefficient_max,
    })

    // 保存每条规则
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

/* 时间线 */
.timeline {
  display: flex;
  flex-direction: column;
  gap: 0;
  position: relative;
  padding-left: 20px;
}
.timeline::before {
  content: '';
  position: absolute;
  left: 6px;
  top: 8px;
  bottom: 8px;
  width: 2px;
  background: #333;
}
.timeline-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  position: relative;
}
.timeline-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  border: 2px solid #555;
  background: #1a1a1a;
  flex-shrink: 0;
  margin-top: 2px;
  position: relative;
  z-index: 1;
}
.timeline-dot.lock { border-color: #FF9800; background: #FF9800; }
.timeline-dot.kpi { border-color: #00BCD4; background: #00BCD4; }
.timeline-dot.generate { border-color: #FB0079; background: #FB0079; }
.timeline-dot.review { border-color: #9C27B0; background: #9C27B0; }
.timeline-dot.pay { border-color: #4CAF50; background: #4CAF50; }

.timeline-content {
  flex: 1;
}
.timeline-title {
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
}
.timeline-desc {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
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
