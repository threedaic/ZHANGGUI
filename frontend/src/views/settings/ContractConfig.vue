<template>
  <div class="contract-config">
    <h2 class="section-title">合同默认配置</h2>
    <p class="section-desc">以下信息将自动填入劳动合同模板，签订时无需重复填写</p>

    <!-- 公司信息 -->
    <div class="config-block">
      <h3>公司信息</h3>
      <div class="form-group">
        <label>公司全称</label>
        <input v-model="form.contract_company_name" placeholder="如：北京跨时餐饮有限公司" />
      </div>
      <div class="form-group">
        <label>联系电话</label>
        <input v-model="form.contract_company_phone" placeholder="如：010-88870388" />
      </div>
      <div class="form-group">
        <label>联系地址</label>
        <input v-model="form.contract_company_address" placeholder="如：北京市朝阳区xx路xx号" />
      </div>
    </div>

    <!-- 薪资默认 -->
    <div class="config-block">
      <h3>薪资与制度默认值</h3>
      <div class="form-row">
        <div class="form-group">
          <label>基本工资（元/月）</label>
          <input v-model.number="form.contract_base_salary" type="number" />
        </div>
        <div class="form-group">
          <label>试用期（月）</label>
          <input v-model.number="form.contract_probation_months" type="number" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>每月休息（天）</label>
          <input v-model.number="form.rest_days_per_month" type="number" />
        </div>
        <div class="form-group">
          <label>发薪日（号）</label>
          <input v-model.number="form.payroll_day_of_month" type="number" />
        </div>
      </div>
      <div class="form-row">
        <div class="form-group">
          <label>离职提前通知（天）</label>
          <input v-model.number="form.contract_notice_days" type="number" />
        </div>
        <div class="form-group">
          <label>合同期限（年）</label>
          <input v-model.number="form.contract_duration_years" type="number" />
        </div>
      </div>
    </div>

    <!-- 合同发起权限 -->
    <div class="config-block">
      <h3>合同发起权限</h3>
      <p class="section-desc">选择哪些员工允许发起/创建合同。留空表示所有人均可发起。</p>
      <div class="employee-list">
        <label
          v-for="emp in employees"
          :key="emp.id"
          class="employee-item"
          :class="{ checked: (form.contract_initiator_ids || []).includes(emp.id) }"
        >
          <input
            type="checkbox"
            :value="emp.id"
            v-model="form.contract_initiator_ids"
            class="checkbox"
          />
          <span class="emp-name">{{ emp.name }}</span>
          <span class="emp-role">{{ emp.role || '员工' }}</span>
        </label>
      </div>
    </div>

    <!-- 按钮 -->
    <div class="btn-row">
      <button class="btn-save" @click="save" :disabled="saving">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { storeAPI, type StoreSettingsData } from '@/api/store'
import apiClient from '@/api/client'

const saving = ref(false)

const form = ref<StoreSettingsData>({
  rest_days_per_month: 4,
  rest_allowed_weekdays: [],
  rest_forbidden_weekdays: [],
  max_same_position_off: 1,
  min_position_coverage_percent: 50,
  manager_order_constraint: true,
  holiday_policy: 'comp_leave',
  auto_schedule_enabled: false,
  schedule_lock_after_publish: true,
  payroll_day_of_month: 5,
  kpi_coefficient_min: 0.6,
  kpi_coefficient_max: 1.5,
  contract_initiator_ids: [],
  contract_company_name: '',
  contract_company_phone: '',
  contract_company_address: '',
  contract_base_salary: 3000,
  contract_probation_months: 6,
  contract_notice_days: 45,
  contract_duration_years: 3,
})

interface Employee {
  id: string
  name: string
  role: string
}

const employees = ref<Employee[]>([])

onMounted(async () => {
  try {
    const [settingsRes, empRes] = await Promise.all([
      storeAPI.getSettings(),
      apiClient.get<{ code: number; data: Employee[] }>('/contracts/employees'),
    ])
    if (settingsRes.data.data) {
      Object.assign(form.value, settingsRes.data.data)
    }
    if (empRes.data.data) {
      employees.value = empRes.data.data
    }
  } catch (e) {
    console.error('加载设置失败', e)
  }
})

async function save() {
  saving.value = true
  try {
    await storeAPI.updateSettings({
      ...form.value,
      rest_allowed_weekdays: undefined,
      rest_forbidden_weekdays: undefined,
    } as any)
    alert('保存成功')
  } catch (e: any) {
    alert('保存失败：' + (e?.message || '未知错误'))
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.contract-config {
  padding: 16px;
  max-width: 640px;
  margin: 0 auto;
}
.section-title {
  font-size: 20px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0 0 4px;
}
.section-desc {
  font-size: 13px;
  color: #888;
  margin: 0 0 20px;
}
.config-block {
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.config-block h3 {
  font-size: 15px;
  font-weight: 600;
  color: #FB0079;
  margin: 0 0 12px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 13px;
  color: #888;
  margin-bottom: 4px;
}
.form-group input {
  width: 100%;
  height: 40px;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 0 12px;
  font-size: 14px;
  outline: none;
  background: #111111;
  color: #FFFFFF;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-group input:focus {
  border-color: #FB0079;
}
.form-row {
  display: flex;
  gap: 12px;
}
.form-row .form-group {
  flex: 1;
}
.employee-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.employee-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border: 1px solid #333333;
  border-radius: 20px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 14px;
}
.employee-item.checked {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
}
.checkbox {
  accent-color: #FB0079;
  width: 16px;
  height: 16px;
}
.emp-name {
  color: #FFFFFF;
  font-weight: 500;
}
.emp-role {
  color: #888;
  font-size: 12px;
}
.btn-row {
  padding: 16px 0 40px;
}
.btn-save {
  width: 100%;
  height: 44px;
  background: #FB0079;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-save:disabled {
  opacity: 0.6;
}
</style>
