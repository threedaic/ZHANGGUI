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
          <span class="form-label">KPI 系数下限</span>
          <div class="form-control">
            <input v-model.number="form.kpi_coefficient_min" type="number" min="0.1" max="2" step="0.05" class="input" />
          </div>
        </div>
        <div class="form-hint">KPI最差时工资乘以这个数（如0.6=扣40%）</div>
        <div class="form-row">
          <span class="form-label">KPI 系数上限</span>
          <div class="form-control">
            <input v-model.number="form.kpi_coefficient_max" type="number" min="0.5" max="3" step="0.05" class="input" />
          </div>
        </div>
        <div class="form-hint">KPI最好时工资乘以这个数（如1.5=加50%）</div>
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

    <!-- 提成规则（3种模式可选） -->
    <div class="section">
      <div class="section-header">
        <span>提成计算方式</span>
        <span class="section-hint">点击切换模式</span>
      </div>
      <div class="section-body">

        <!-- 3个模式卡片 -->
        <div class="mode-cards">
          <button
            v-for="m in commissionModes"
            :key="m.key"
            class="mode-card"
            :class="{ active: commissionMode === m.key }"
            @click="commissionMode = m.key"
          >
            <span class="mode-icon" v-html="m.icon"></span>
            <span class="mode-name">{{ m.name }}</span>
            <span class="mode-desc">{{ m.desc }}</span>
          </button>
        </div>

        <!-- 固定比例 -->
        <div v-if="commissionMode === 'fixed'" class="mode-config">
          <div class="form-row">
            <span class="form-label">提成比例</span>
            <div class="form-control">
              <input v-model.number="commissionRate" type="number" min="0" max="1" step="0.01" class="input" />
              <span class="form-suffix">（0.10 = 10%）</span>
            </div>
          </div>
          <div class="form-hint">所有员工统一比例，最简单。业绩 × 比例 = 提成</div>
        </div>

        <!-- 按角色设比例 -->
        <div v-if="commissionMode === 'by_role'" class="mode-config">
          <div class="form-hint">不同岗位不同比例，激励关键岗位</div>
          <div v-for="role in roleList" :key="role.key" class="form-row">
            <span class="form-label">{{ role.name }}</span>
            <div class="form-control">
              <input v-model.number="commissionRatesByRole[role.key]" type="number" min="0" max="1" step="0.01" class="input" />
              <span class="form-suffix">（{{ Math.round((commissionRatesByRole[role.key] || 0) * 100) }}%）</span>
            </div>
          </div>
        </div>

        <!-- 阶梯提成 -->
        <div v-if="commissionMode === 'tiered'" class="mode-config">
          <div class="form-hint">业绩越高比例越高，按命中最高档计算</div>
          <div v-for="(tier, idx) in commissionTiers" :key="idx" class="tier-row">
            <span class="tier-label">第 {{ idx + 1 }} 档</span>
            <span class="form-prefix">业绩≥</span>
            <input v-model.number="tier.min" type="number" min="0" step="1000" class="input" />
            <span class="form-suffix">元</span>
            <span class="form-prefix" style="margin-left:8px">比例</span>
            <input v-model.number="tier.rate" type="number" min="0" max="1" step="0.01" class="input" />
            <span class="form-suffix">（{{ Math.round((tier.rate || 0) * 100) }}%）</span>
            <button v-if="commissionTiers.length > 1" class="tier-del" @click="commissionTiers.splice(idx, 1)">删</button>
          </div>
          <button class="tier-add" @click="commissionTiers.push({ min: 0, rate: 0.05 })">+ 添加一档</button>
        </div>

      </div>
    </div>

    <!-- 休息天数（只读，由排班模式自动算，保证考勤/工资一致） -->
    <div class="section">
      <div class="section-header">
        <span>休息天数</span>
        <span class="section-hint">由排班模式自动算</span>
      </div>
      <div class="section-body">
        <div class="form-row readonly-row">
          <span class="form-label">月休息天数</span>
          <div class="form-control">
            <span class="readonly-value">{{ restDaysFromSchedule }} 天</span>
          </div>
        </div>
        <div class="form-hint">
          这里不能改。去「设置 → 排班规则」选排班模式（单休/大小周/双休），会自动算休息天数并同步到这里，保证考勤和工资算的一致。
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
import { listRules, updateRule, type SalaryRule } from '@/api/payrollConfig'
import { autoPayrollAPI } from '@/api/autoPayroll'

// ====== 基本参数（store settings）======
const form = reactive({
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

// ====== 提成规则（auto-payroll/rules）======
const commissionMode = ref<'fixed' | 'by_role' | 'tiered'>('fixed')
const commissionRate = ref(0.10)
const commissionRatesByRole = reactive<Record<string, number>>({
  boss: 0.03,
  store_manager: 0.03,
  bar_manager: 0.10,
  service_manager: 0.05,
  kitchen_manager: 0.03,
  staff: 0.05,
})
const commissionTiers = ref<Array<{ min: number; rate: number }>>([
  { min: 0, rate: 0.05 },
  { min: 10000, rate: 0.08 },
  { min: 30000, rate: 0.12 },
])

const commissionModes = [
  {
    key: 'fixed' as const,
    name: '固定比例',
    desc: '全员统一比例',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5"><line x1="4" y1="20" x2="20" y2="20"/><rect x="6" y="14" width="3" height="6"/><rect x="11" y="10" width="3" height="10"/><rect x="16" y="6" width="3" height="14"/></svg>',
  },
  {
    key: 'by_role' as const,
    name: '按角色',
    desc: '不同岗位不同比例',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5"><circle cx="8" cy="8" r="3"/><circle cx="16" cy="8" r="3"/><path d="M3 20c0-3 2-5 5-5s5 2 5 5"/><path d="M11 20c0-3 2-5 5-5s5 2 5 5"/></svg>',
  },
  {
    key: 'tiered' as const,
    name: '阶梯提成',
    desc: '业绩越高比例越高',
    icon: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#FB0079" stroke-width="1.5"><polyline points="4,18 9,13 13,15 20,6"/><polyline points="14,6 20,6 20,12"/></svg>',
  },
]

const roleList = [
  { key: 'boss', name: '老板' },
  { key: 'store_manager', name: '店长' },
  { key: 'bar_manager', name: '吧台长' },
  { key: 'service_manager', name: '服务主管' },
  { key: 'kitchen_manager', name: '厨师长' },
  { key: 'staff', name: '员工' },
]

// 月休息天数：只读，从排班规则（store settings）读，由排班模式自动算
const restDaysFromSchedule = ref(0)

async function loadData() {
  try {
    const [settingsRes, rulesRes, autoRulesRes] = await Promise.all([
      storeAPI.getSettings(),
      listRules(),
      autoPayrollAPI.getRules(),
    ])
    const s = settingsRes.data.data
    form.kpi_coefficient_min = s.kpi_coefficient_min
    form.kpi_coefficient_max = s.kpi_coefficient_max
    restDaysFromSchedule.value = s.rest_days_per_month ?? 0
    rules.value = rulesRes.data.data

    // 加载提成规则
    const autoRules = autoRulesRes.data.data
    commissionMode.value = autoRules.commission_mode || 'fixed'
    commissionRate.value = autoRules.commission_rate ?? 0.10
    if (autoRules.commission_rates_by_role) {
      Object.assign(commissionRatesByRole, autoRules.commission_rates_by_role)
    }
    if (autoRules.commission_tiers && autoRules.commission_tiers.length > 0) {
      commissionTiers.value = autoRules.commission_tiers
    }
  } catch { /* silent */ }
}

async function saveAll() {
  saving.value = true
  try {
    // 1. 保存基本参数
    await storeAPI.updateSettings({
      kpi_coefficient_min: form.kpi_coefficient_min,
      kpi_coefficient_max: form.kpi_coefficient_max,
    })

    // 2. 保存扣款规则（旧 API）
    for (const rule of rules.value) {
      if (rule.rule_code === 'rest_days_per_month') continue
      await updateRule(rule.rule_code, rule.rule_value)
    }

    // 3. 保存提成规则（新 API）
    await autoPayrollAPI.setRules({
      commission_mode: commissionMode.value,
      commission_rate: commissionRate.value,
      commission_rates_by_role: commissionRatesByRole,
      commission_tiers: commissionTiers.value,
    })

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
  margin-top: -4px;
  margin-bottom: 8px;
  padding-left: 4px;
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

.readonly-row {
  opacity: 0.85;
}
.readonly-value {
  font-size: 15px;
  font-weight: 700;
  color: #FB0079;
  margin-left: auto;
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

/* ==================== 提成模式卡片 ==================== */
.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  margin-bottom: 16px;
}
.mode-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 14px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.mode-card:hover { border-color: #555; }
.mode-card.active {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
  box-shadow: 0 0 0 1px #FB0079 inset;
}
.mode-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}
.mode-name {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
}
.mode-card.active .mode-name { color: #FB0079; }
.mode-desc {
  font-size: 10px;
  color: #7A7C80;
  text-align: center;
}

.mode-config {
  padding-top: 8px;
  border-top: 1px solid #222222;
}

/* 阶梯提成 */
.tier-row {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 0;
  border-bottom: 1px solid #222222;
  font-size: 12px;
  color: #C8C8C8;
  flex-wrap: wrap;
}
.tier-label {
  min-width: 50px;
  font-weight: 600;
  color: #FB0079;
}
.tier-del {
  margin-left: auto;
  padding: 4px 10px;
  background: rgba(244, 67, 54, 0.15);
  border: 1px solid #F44336;
  border-radius: 6px;
  color: #F44336;
  font-size: 11px;
  cursor: pointer;
}
.tier-del:active { transform: scale(0.95); }
.tier-add {
  width: 100%;
  margin-top: 10px;
  padding: 10px;
  background: transparent;
  border: 1px dashed #444444;
  border-radius: 8px;
  color: #7A7C80;
  font-size: 13px;
  cursor: pointer;
}
.tier-add:active { transform: scale(0.98); }
</style>
