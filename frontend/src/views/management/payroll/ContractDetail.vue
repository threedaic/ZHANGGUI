<!--
  ============================================================================
  合同模块 - 二级页面
  ============================================================================

  【功能】
  1. 显示每个员工的合同薪资数据（月薪、底薪、补贴）
  2. 底薪参数设置（合同锁定，始终参与计算）

  【数据来源】
  - wage_contracts 表（员工合同薪资）
  - shared_store_settings.contract_base_salary（底薪参数）
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">合同</span>
      <span class="lock-badge">常开模块</span>
    </div>

    <!-- 模块说明 -->
    <div class="module-desc-card">
      <div class="desc-title">模块作用</div>
      <div class="desc-text">确定员工的基础薪资。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">合同薪资 = 底薪 + 补贴</div>
    </div>

    <!-- 员工数据表格 -->
    <div class="section-title">员工合同数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>月薪</th>
            <th>底薪</th>
            <th>补贴</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td>¥{{ Number(emp.modules.contract?.monthly_salary || 0).toFixed(2) }}</td>
            <td>¥{{ Number(emp.modules.contract?.base_salary || 0).toFixed(2) }}</td>
            <td>¥{{ Number(emp.modules.contract?.allowance || 0).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无员工数据</div>
    </div>

    <!-- 参数设置 -->
    <div class="section-title">参数设置</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">底薪</span>
        <input
          :value="rules.base_salary"
          class="rule-input"
          type="number"
          step="0.01"
          @change="updateRule('base_salary', $event)"
        />
        <span class="rule-unit">元</span>
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

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const res = await autoPayrollAPI.getTable(period)
    tableData.value = res.data.data
  } catch (e) {
    console.error('[合同] 加载失败:', e)
  }
  loading.value = false
}

async function updateRule(key: string, event: Event) {
  const target = event.target as HTMLInputElement
  const value = parseFloat(target.value)
  if (isNaN(value)) return
  try {
    await autoPayrollAPI.setRules({ [key]: value })
    rules.value[key] = value
  } catch (e) {
    console.error('[合同] 更新参数失败:', e)
  }
}

onMounted(loadData)
</script>

<style scoped>
@import './_shared.css';
</style>
