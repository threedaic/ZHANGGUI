<template>
  <div class="contract-default">

    <div class="page-hint">以下信息将自动填入劳动合同模板，签订时无需重复填写</div>

    <!-- 公司信息 -->
    <div class="section">
      <div class="section-header" @click="sections.company = !sections.company">
        <span>公司信息</span>
        <span class="toggle">{{ sections.company ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.company" class="section-body">
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
    </div>

    <!-- 薪资与制度默认值 -->
    <div class="section">
      <div class="section-header" @click="sections.salary = !sections.salary">
        <span>薪资与制度默认值</span>
        <span class="toggle">{{ sections.salary ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.salary" class="section-body">
        <div class="form-row-pair">
          <div class="form-group half">
            <label>基本工资（元/月）</label>
            <input v-model.number="form.contract_base_salary" type="number" />
          </div>
          <div class="form-group half">
            <label>试用期（月）</label>
            <input v-model.number="form.contract_probation_months" type="number" />
          </div>
        </div>
        <div class="form-row-pair">
          <div class="form-group half">
            <label>离职提前通知（天）</label>
            <input v-model.number="form.contract_notice_days" type="number" />
          </div>
          <div class="form-group half">
            <label>合同期限（年）</label>
            <input v-model.number="form.contract_duration_years" type="number" />
          </div>
        </div>
      </div>
    </div>

    <!-- 合同发起权限 -->
    <div class="section">
      <div class="section-header" @click="sections.initiator = !sections.initiator">
        <span>合同发起权限</span>
        <span class="toggle">{{ sections.initiator ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.initiator" class="section-body">
        <p class="hint-text">选择哪些员工允许发起/创建合同。留空表示所有人均可发起。</p>
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
    </div>

    <button class="save-btn" :disabled="saving" @click="save">
      {{ saving ? '保存中...' : '保存设置' }}
    </button>

    <div style="height: 80px"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { storeAPI, type StoreSettingsData } from '@/api/store'
import apiClient from '@/api/client'

const saving = ref(false)

const sections = reactive({
  company: true,
  salary: false,
  initiator: false,
})

const form = reactive({
  contract_initiator_ids: [] as string[],
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
      const s = settingsRes.data.data
      form.contract_initiator_ids = s.contract_initiator_ids || []
      form.contract_company_name = s.contract_company_name || ''
      form.contract_company_phone = s.contract_company_phone || ''
      form.contract_company_address = s.contract_company_address || ''
      form.contract_base_salary = s.contract_base_salary || 3000
      form.contract_probation_months = s.contract_probation_months || 6
      form.contract_notice_days = s.contract_notice_days || 45
      form.contract_duration_years = s.contract_duration_years || 3
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
      contract_initiator_ids: form.contract_initiator_ids,
      contract_company_name: form.contract_company_name,
      contract_company_phone: form.contract_company_phone,
      contract_company_address: form.contract_company_address,
      contract_base_salary: form.contract_base_salary,
      contract_probation_months: form.contract_probation_months,
      contract_notice_days: form.contract_notice_days,
      contract_duration_years: form.contract_duration_years,
    } as any)
  } catch (e: any) {
    console.error('保存失败', e)
  }
  saving.value = false
}
</script>

<style scoped>
.contract-default {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

.nav-bar {
  display: flex;
  align-items: center;
  gap: 6px;
  color: #7A7C80;
  font-size: 14px;
  cursor: pointer;
  margin-bottom: 16px;
}

.page-hint {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(251, 0, 121, 0.06);
  border-radius: 8px;
}

/* 折叠区块 */
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
  cursor: pointer;
}

.toggle {
  font-size: 12px;
  color: #7A7C80;
}

.section-body {
  padding: 0 16px 16px;
}

/* 表单 */
.form-group {
  margin-bottom: 12px;
}

.form-group.half {
  flex: 1;
  margin-bottom: 0;
}

.form-group label {
  display: block;
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 6px;
}

.form-group input {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #C8C8C8;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
  transition: border-color 0.2s;
}

.form-group input:focus {
  border-color: #FB0079;
}

.form-row-pair {
  display: flex;
  gap: 12px;
  margin-bottom: 12px;
}

.hint-text {
  font-size: 11px;
  color: #7A7C80;
  margin: 0 0 12px;
}

/* 员工列表 */
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
  font-size: 13px;
}

.employee-item.checked {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
}

.checkbox {
  accent-color: #FB0079;
  width: 16px;
  height: 16px;
}

.emp-name {
  color: #C8C8C8;
  font-weight: 500;
}

.emp-role {
  color: #7A7C80;
  font-size: 11px;
}

.save-btn {
  width: 100%;
  margin-top: 16px;
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

.save-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
