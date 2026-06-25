<!--
  ============================================================================
  KPI模块 - 二级页面
  ============================================================================

  【功能】
  1. 显示每个员工的KPI数据（KPI系数、总分、奖金）
  2. 可切换启用/禁用
  3. 暂无可调参数

  【数据来源】
  - KPI考核数据（待建表）
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">KPI</span>
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
      <div class="desc-text">根据员工KPI考核结果调整工资。KPI系数大于1表示加薪，小于1表示扣薪。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">KPI奖金 = 底薪 × (KPI系数 - 1)</div>
    </div>

    <!-- 员工KPI数据 -->
    <div class="section-title">员工KPI数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>KPI系数</th>
            <th>总分</th>
            <th>奖金</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td>{{ Number(emp.modules.kpi?.coefficient || 0).toFixed(2) }}</td>
            <td>{{ Number(emp.modules.kpi?.total_score || 0).toFixed(1) }}</td>
            <td class="amount-positive">¥{{ Number(emp.modules.kpi?.bonus || 0).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无KPI数据</div>
    </div>

    <!-- 说明 -->
    <div class="section-title">说明</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">KPI系数应用规则</span>
        <span class="rule-desc">KPI系数会乘到工资总额上（系数 &gt; 1 加薪，&lt; 1 扣薪）</span>
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
const enabled = computed(() => tableData.value.modules.kpi || false)

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const res = await autoPayrollAPI.getTable(period)
    tableData.value = res.data.data
  } catch (e) {
    console.error('[KPI] 加载失败:', e)
  }
  loading.value = false
}

async function toggleModule() {
  const newVal = !tableData.value.modules.kpi
  try {
    await autoPayrollAPI.setModules({ kpi: newVal })
    tableData.value.modules.kpi = newVal
  } catch (e) {
    console.error('[KPI] 切换失败:', e)
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

.rule-desc {
  font-size: 12px;
  color: #7A7C80;
  text-align: right;
  max-width: 200px;
}
</style>
