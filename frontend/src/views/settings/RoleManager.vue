<template>
  <div class="role-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">角色管理</h1>
        <span class="page-subtitle">管理员工权限与角色分配</span>
      </div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="error" class="error-msg">{{ error }}</div>
    <template v-else>
      <div class="role-legend">
        <span class="legend-item" v-for="r in roleOptions" :key="r.value" :class="'role-' + r.value">
          {{ r.label }}
        </span>
      </div>

      <div class="employee-list">
        <div
          v-for="emp in employees"
          :key="emp.id"
          class="employee-row"
        >
          <div class="emp-info">
            <span class="emp-name">{{ emp.name }}</span>
            <span class="emp-wid" v-if="emp.wework_userid">{{ emp.wework_userid }}</span>
          </div>
          <select
            class="role-select"
            :value="emp.role"
            @change="handleRoleChange(emp, ($event.target as HTMLSelectElement).value)"
          >
            <option v-for="r in roleOptions" :key="r.value" :value="r.value">{{ r.label }}</option>
          </select>
        </div>
      </div>
    </template>

    <div v-if="toastVisible" class="toast-msg">{{ toastMsg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apiClient from '@/api/client'

interface Employee {
  id: number
  name: string
  role: string
  wework_userid: string | null
  status: string
  phone: string | null
}

const employees = ref<Employee[]>([])
const loading = ref(true)
const error = ref('')
const toastVisible = ref(false)
const toastMsg = ref('')

const roleOptions = [
  { value: 'boss', label: '老板' },
  { value: 'store_manager', label: '店长' },
  { value: 'accountant', label: '会计' },
  { value: 'bar_manager', label: '吧台负责人' },
  { value: 'service_manager', label: '服务负责人' },
  { value: 'kitchen_manager', label: '厨房负责人' },
  { value: 'staff', label: '员工' },
]

function showToast(msg: string) {
  toastMsg.value = msg
  toastVisible.value = true
  setTimeout(() => { toastVisible.value = false }, 2000)
}

async function loadEmployees() {
  loading.value = true
  error.value = ''
  try {
    const res = await apiClient.get('/store/employees')
    employees.value = res.data.data || []
  } catch (e: any) {
    error.value = e.response?.data?.message || '加载失败'
  } finally {
    loading.value = false
  }
}

async function handleRoleChange(emp: Employee, newRole: string) {
  if (newRole === emp.role) return
  try {
    await apiClient.put(`/store/employees/${emp.id}/role`, { role: newRole })
    emp.role = newRole
    showToast(`${emp.name} → ${roleOptions.find(r => r.value === newRole)?.label}`)
  } catch (e: any) {
    showToast(e.response?.data?.message || '更新失败')
  }
}

onMounted(loadEmployees)
</script>

<style scoped>
.role-page {
  padding: 16px;
  padding-bottom: calc(56px + 24px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}
.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}
.page-subtitle {
  font-size: 12px;
  color: #7A7C80;
}

.loading, .error-msg {
  text-align: center;
  color: #7A7C80;
  padding: 40px 0;
  font-size: 14px;
}
.error-msg {
  color: #ff4444;
}

.role-legend {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 16px;
}
.legend-item {
  font-size: 11px;
  padding: 3px 10px;
  border-radius: 999px;
  color: #7A7C80;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid #333;
}
.legend-item.role-boss {
  color: #FB0079;
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
}

.employee-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.employee-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
}
.emp-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.emp-name {
  font-size: 15px;
  font-weight: 500;
  color: #FFFFFF;
}
.emp-wid {
  font-size: 11px;
  color: #555;
}
.role-select {
  background: #1a1a1a;
  border: 1px solid #333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  padding: 6px 10px;
  cursor: pointer;
  outline: none;
}
.role-select:focus {
  border-color: #FB0079;
}

.toast-msg {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: rgba(0,0,0,0.85);
  color: #fff;
  padding: 12px 24px;
  border-radius: 8px;
  font-size: 14px;
  z-index: 200;
}
</style>
