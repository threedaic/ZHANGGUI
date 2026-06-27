<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { hqAPI, type HQEmployee } from '@/api/hq'

const loading = ref(true)
const employees = ref<HQEmployee[]>([])

const roleMap: Record<string, string> = {
  system_admin: '系统管理员',
  boss: '老板',
  store_manager: '店长',
  accountant: '会计',
  bar_manager: '吧台长',
  service_manager: '服务主管',
  kitchen_manager: '厨房主管',
  staff: '员工',
}

async function loadData() {
  loading.value = true
  try {
    const res = await hqAPI.getEmployees()
    employees.value = res.data.data
  } catch (e) {
    // 全局拦截器已提示
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadData()
})
</script>

<template>
  <div class="hq-employees">
    <div class="page-header">
      <h2>全局员工</h2>
      <span class="count">{{ employees.length }} 人</span>
    </div>

    <div v-if="!loading" class="emp-list">
      <div v-for="emp in employees" :key="emp.id" class="emp-item">
        <div class="emp-avatar">{{ emp.name.charAt(0) }}</div>
        <div class="emp-info">
          <div class="emp-name">{{ emp.name }}</div>
          <div class="emp-meta">
            <span class="emp-store">{{ emp.store_name }}</span>
          </div>
        </div>
        <div class="emp-role" :class="emp.role">{{ roleMap[emp.role] || emp.role }}</div>
      </div>
      <div v-if="employees.length === 0" class="empty">暂无员工数据</div>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
  </div>
</template>

<style scoped lang="scss">
@use "@/styles/variables.scss" as *;

.hq-employees {
  padding: 16px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h2 {
    font-size: 20px;
    font-weight: 700;
    color: $brand-white;
    margin: 0;
  }
}

.count {
  font-size: 14px;
  color: $brand-text-light;
}

.emp-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.emp-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: $radius-md;
}

.emp-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: linear-gradient(135deg, $brand-primary, rgba(251, 0, 121, 0.5));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  font-weight: 600;
  color: $brand-white;
  flex-shrink: 0;
}

.emp-info {
  flex: 1;
  min-width: 0;
}

.emp-name {
  font-size: 15px;
  font-weight: 600;
  color: $brand-white;
}

.emp-meta {
  margin-top: 2px;
}

.emp-store {
  font-size: 12px;
  color: $brand-text-light;
}

.emp-role {
  font-size: 12px;
  padding: 3px 10px;
  border-radius: 4px;
  background: rgba(255, 255, 255, 0.08);
  color: $brand-text-light;
  white-space: nowrap;

  &.system_admin, &.boss {
    background: rgba(251, 0, 121, 0.15);
    color: $brand-primary;
  }
  &.store_manager {
    background: rgba(255, 152, 0, 0.15);
    color: #ff9800;
  }
}

.empty, .loading {
  text-align: center;
  padding: 40px;
  color: $brand-text-light;
  font-size: 14px;
}
</style>
