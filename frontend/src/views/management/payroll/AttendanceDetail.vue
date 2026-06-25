<!--
  ============================================================================
  考勤模块 - 二级页面
  ============================================================================

  【功能】
  1. 显示每个员工的考勤数据（迟到次数、迟到扣款、旷工天数、旷工扣款、早退次数、早退扣款）
  2. 考勤扣款参数设置（迟到每分钟、旷工倍数、早退每次、月休息天数）
  3. 考勤锁定，始终参与计算

  【数据来源】
  - att_records 表（员工考勤记录）
  - wage_salary_rules（扣款参数）
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">考勤</span>
      <span class="lock-badge">常开模块</span>
    </div>

    <!-- 模块说明 -->
    <div class="module-desc-card">
      <div class="desc-title">模块作用</div>
      <div class="desc-text">根据员工考勤记录，每日实时统计。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">考勤扣款 = 迟到分钟×5 + 旷工天数×日薪×3 + 早退次数×100</div>
    </div>

    <!-- 员工考勤数据 -->
    <div class="section-title">员工考勤数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>迟到次数</th>
            <th>迟到扣款</th>
            <th>旷工天数</th>
            <th>旷工扣款</th>
            <th>早退次数</th>
            <th>早退扣款</th>
            <th>合计</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td>{{ emp.modules.attendance?.late_count || 0 }}</td>
            <td class="amount-negative">¥{{ Number(emp.modules.attendance?.late_deduction || 0).toFixed(2) }}</td>
            <td>{{ emp.modules.attendance?.absent_count || 0 }}</td>
            <td class="amount-negative">¥{{ Number(emp.modules.attendance?.absent_deduction || 0).toFixed(2) }}</td>
            <td>{{ emp.modules.attendance?.early_count || 0 }}</td>
            <td class="amount-negative">¥{{ Number(emp.modules.attendance?.early_deduction || 0).toFixed(2) }}</td>
            <td class="amount-negative">¥{{ Number(emp.modules.attendance?.total || 0).toFixed(2) }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无员工数据</div>
    </div>

    <!-- 参数设置 -->
    <div class="section-title">参数设置</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">迟到每分钟扣款</span>
        <input
          :value="rules.late_deduction_per_minute"
          class="rule-input"
          type="number"
          step="0.01"
          @change="updateRule('late_deduction_per_minute', $event)"
        />
        <span class="rule-unit">元</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">旷工倍数（日薪倍数）</span>
        <input
          :value="rules.absent_factor"
          class="rule-input"
          type="number"
          step="0.01"
          @change="updateRule('absent_factor', $event)"
        />
        <span class="rule-unit">倍</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">早退每次扣款</span>
        <input
          :value="rules.early_deduction_per_time"
          class="rule-input"
          type="number"
          step="0.01"
          @change="updateRule('early_deduction_per_time', $event)"
        />
        <span class="rule-unit">元</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">月休息天数</span>
        <input
          :value="rules.rest_days_per_month"
          class="rule-input"
          type="number"
          step="1"
          @change="updateRule('rest_days_per_month', $event)"
        />
        <span class="rule-unit">天</span>
      </div>
      <div class="rule-item">
        <span class="rule-label">迟到多久算旷工</span>
        <input
          :value="rules.late_to_absent_minutes"
          class="rule-input"
          type="number"
          step="1"
          @change="updateRule('late_to_absent_minutes', $event)"
        />
        <span class="rule-unit">分钟</span>
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
    console.error('[考勤] 加载失败:', e)
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
    console.error('[考勤] 更新参数失败:', e)
  }
}

onMounted(loadData)
</script>

<style scoped>
@import './_shared.css';

.amount-negative {
  color: #FF5252;
  font-weight: 600;
}
</style>
