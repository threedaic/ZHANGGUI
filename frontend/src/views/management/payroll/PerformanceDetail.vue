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

    <!-- 参数设置 -->
    <div class="section-title">参数设置</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">提成比例</span>
        <input
          :value="rules.commission_rate"
          class="rule-input"
          type="number"
          step="0.01"
          @change="updateRule('commission_rate', $event)"
        />
        <span class="rule-unit">（0.1 = 10%）</span>
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
const rules = computed(() => tableData.value.rules)
const enabled = computed(() => tableData.value.modules.performance || false)

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const res = await autoPayrollAPI.getTable(period)
    tableData.value = res.data.data
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

async function updateRule(key: string, event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseFloat(target.value)
  if (isNaN(value)) return
  try {
    await autoPayrollAPI.setRules({ [key]: value })
    rules.value[key] = value
  } catch (e) {
    console.error('[业绩] 更新参数失败:', e)
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
</style>
