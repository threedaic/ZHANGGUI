<!--
  ============================================================================
  业绩模块 - 二级页面
  ============================================================================

  【功能】
  1. 显示每个员工的业绩数据（业绩总额、提成比例、提成金额）
  2. 提成比例参数设置
  3. 可切换启用/禁用

  【数据来源】
  - hr_performance 表（员工业绩数据）
  - wage_salary_rules.commission_rate（提成比例）
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">业绩</span>
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
      <div class="desc-text">根据员工个人业绩（订桌到企微个人支付）计算提成奖金。业绩数据来自业绩录入表。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">业绩提成 = 业绩总额 × 提成比例（默认10%）</div>
    </div>

    <!-- 员工业绩数据 -->
    <div class="section-title">员工业绩数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>业绩总额</th>
            <th>提成比例</th>
            <th>提成金额</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td>¥{{ Number(emp.modules.performance?.total_amount || 0).toFixed(2) }}</td>
            <td>{{ (Number(emp.modules.performance?.commission_rate || 0) * 100).toFixed(1) }}%</td>
            <td class="amount-positive">¥{{ Number(emp.modules.performance?.commission || 0).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无员工数据</div>
    </div>

    <!-- 提成计算方式（3种模式） -->
    <div class="section-title">提成计算方式</div>
    <div class="commission-card">
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
        <div class="rule-item">
          <span class="rule-label">提成比例</span>
          <input v-model.number="commissionRate" type="number" min="0" max="1" step="0.01" class="rule-input" />
          <span class="rule-unit">（0.10 = 10%）</span>
        </div>
        <div class="rule-hint">所有员工统一比例，最简单。业绩 × 比例 = 提成</div>
      </div>

      <!-- 按角色设比例 -->
      <div v-if="commissionMode === 'by_role'" class="mode-config">
        <div class="rule-hint">不同岗位不同比例，激励关键岗位</div>
        <div v-for="role in roleList" :key="role.key" class="rule-item">
          <span class="rule-label">{{ role.name }}</span>
          <input v-model.number="commissionRatesByRole[role.key]" type="number" min="0" max="1" step="0.01" class="rule-input" />
          <span class="rule-unit">（{{ Math.round((commissionRatesByRole[role.key] || 0) * 100) }}%）</span>
        </div>
      </div>

      <!-- 阶梯提成 -->
      <div v-if="commissionMode === 'tiered'" class="mode-config">
        <div class="rule-hint">业绩越高比例越高，按命中最高档计算</div>
        <div v-for="(tier, idx) in commissionTiers" :key="idx" class="tier-row">
          <span class="tier-label">第 {{ idx + 1 }} 档</span>
          <span class="rule-unit">业绩≥</span>
          <input v-model.number="tier.min" type="number" min="0" step="1000" class="rule-input" />
          <span class="rule-unit">元</span>
          <span class="rule-unit" style="margin-left:8px">比例</span>
          <input v-model.number="tier.rate" type="number" min="0" max="1" step="0.01" class="rule-input" />
          <span class="rule-unit">（{{ Math.round((tier.rate || 0) * 100) }}%）</span>
          <button v-if="commissionTiers.length > 1" class="tier-del" @click="commissionTiers.splice(idx, 1)">删</button>
        </div>
        <button class="tier-add" @click="commissionTiers.push({ min: 0, rate: 0.05 })">+ 添加一档</button>
      </div>

      <button class="save-commission-btn" :disabled="savingCommission" @click="saveCommission">
        {{ savingCommission ? '保存中...' : '保存提成设置' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
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
const enabled = computed(() => tableData.value.modules.performance || false)

// ====== 提成规则（从设置页迁入）======
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
const savingCommission = ref(false)

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

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const [tableRes, rulesRes] = await Promise.all([
      autoPayrollAPI.getTable(period),
      autoPayrollAPI.getRules(),
    ])
    tableData.value = tableRes.data.data

    // 加载提成规则
    const autoRules = rulesRes.data.data
    commissionMode.value = autoRules.commission_mode || 'fixed'
    commissionRate.value = autoRules.commission_rate ?? 0.10
    if (autoRules.commission_rates_by_role) {
      Object.assign(commissionRatesByRole, autoRules.commission_rates_by_role)
    }
    if (autoRules.commission_tiers && autoRules.commission_tiers.length > 0) {
      commissionTiers.value = autoRules.commission_tiers
    }
  } catch (e) {
    console.error('[业绩] 加载失败:', e)
  }
  loading.value = false
}

async function toggleModule() {
  const newVal = !tableData.value.modules.performance
  try {
    await autoPayrollAPI.setModules({ performance: newVal })
    tableData.value.modules.performance = newVal
  } catch (e) {
    console.error('[业绩] 切换失败:', e)
  }
}

async function saveCommission() {
  savingCommission.value = true
  try {
    await autoPayrollAPI.setRules({
      commission_mode: commissionMode.value,
      commission_rate: commissionRate.value,
      commission_rates_by_role: commissionRatesByRole,
      commission_tiers: commissionTiers.value,
    })
    ElMessage.success('提成设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingCommission.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
@import './_shared.css';

.amount-positive {
  color: #4CAF50;
  font-weight: 600;
}

/* ==================== 提成计算方式 ==================== */
.commission-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 0 16px 16px;
  margin-bottom: 20px;
}

.mode-cards {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding-top: 16px;
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

.rule-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
  font-size: 13px;
  color: #C8C8C8;
}
.rule-item:last-child { border-bottom: none; }

.rule-label {
  min-width: 80px;
}

.rule-input {
  width: 80px;
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  text-align: center;
}
.rule-input:focus { outline: none; border-color: #FB0079; }

.rule-unit {
  font-size: 12px;
  color: #7A7C80;
}

.rule-hint {
  width: 100%;
  font-size: 11px;
  color: #7A7C80;
  margin-top: -4px;
  margin-bottom: 8px;
  padding-left: 4px;
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

.save-commission-btn {
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
}
.save-commission-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
