<!--
  ============================================================================
  奖惩模块 - 二级页面
  ============================================================================

  【功能】
  1. 显示每个员工的奖惩数据（奖励金额、惩罚金额、合计）
  2. 可切换启用/禁用
  3. 提供快捷入口去发布奖惩通知

  【数据来源】
  - hr_penalty_notices 表（奖惩通知，含 reward_ 和 penalty_ 类型）
  ============================================================================
-->
<template>
  <div class="module-detail-page">
    <!-- 顶部栏 -->
    <div class="top-bar">
      <span class="page-title">奖惩</span>
      <button class="action-btn" @click="router.push('/management/penalties/create')">+ 发布</button>
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
      <div class="desc-text">汇总员工本月的奖励和惩罚金额，自动计入工资。</div>
      <div class="desc-title">计算公式</div>
      <div class="desc-formula">奖惩金额 = 奖励总额 - 惩罚总额（正数加薪，负数扣薪）</div>
    </div>

    <!-- 员工奖惩数据 -->
    <div class="section-title">员工奖惩数据</div>
    <div class="table-wrap" v-loading="loading">
      <table class="data-table">
        <thead>
          <tr>
            <th>员工</th>
            <th>奖励</th>
            <th>惩罚</th>
            <th>合计</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="emp in employees" :key="emp.employee_id">
            <td class="cell-name">
              <div class="emp-name">{{ emp.employee_name }}</div>
              <div class="emp-role">{{ emp.position }}</div>
            </td>
            <td class="amount-positive">+¥{{ Number(emp.modules.reward_penalty?.reward || 0).toFixed(2) }}</td>
            <td class="amount-negative">-¥{{ Number(emp.modules.reward_penalty?.penalty || 0).toFixed(2) }}</td>
            <td :class="amountClass(emp.modules.reward_penalty?.total || 0)">
              {{ Number(emp.modules.reward_penalty?.total || 0) >= 0 ? '+' : '' }}¥{{ Math.abs(Number(emp.modules.reward_penalty?.total || 0)).toFixed(2) }}
            </td>
          </tr>
        </tbody>
      </table>
      <div v-if="!loading && employees.length === 0" class="empty">暂无奖惩数据</div>
    </div>

    <!-- 说明 -->
    <div class="section-title">说明</div>
    <div class="rules-card">
      <div class="rule-item">
        <span class="rule-label">奖惩数据来源</span>
        <span class="rule-desc">来自"奖惩通知"模块发布的奖励单和惩罚单</span>
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
const enabled = computed(() => tableData.value.modules.reward_penalty || false)

async function loadData() {
  loading.value = true
  try {
    const d = new Date()
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
    const res = await autoPayrollAPI.getTable(period)
    tableData.value = res.data.data
  } catch (e) {
    console.error('[奖惩] 加载失败:', e)
  }
  loading.value = false
}

async function toggleModule() {
  const newVal = !tableData.value.modules.reward_penalty
  try {
    await autoPayrollAPI.setModules({ reward_penalty: newVal })
    tableData.value.modules.reward_penalty = newVal
  } catch (e) {
    console.error('[奖惩] 切换失败:', e)
  }
}

function amountClass(amount: number): string {
  if (amount > 0) return 'amount-positive'
  if (amount < 0) return 'amount-negative'
  return ''
}

onMounted(loadData)
</script>

<style scoped>
@import './_shared.css';

.amount-positive {
  color: #4CAF50;
  font-weight: 600;
}

.amount-negative {
  color: #FF5252;
  font-weight: 600;
}

.action-btn {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 6px 14px;
  border-radius: 6px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}

.rule-desc {
  font-size: 12px;
  color: #7A7C80;
  text-align: right;
  max-width: 200px;
}
</style>
