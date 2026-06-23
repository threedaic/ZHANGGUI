<template>
  <div class="attendance-detail-page">
    <div class="page-header">
      <span class="page-title">{{ viewTitle }}</span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="filteredList.length === 0" class="empty">暂无数据</div>
    <div v-else class="list">
      <div v-for="emp in filteredList" :key="emp.employee_id" class="list-item">
        <div class="item-left">
          <span class="item-name">{{ emp.employee_name }}</span>
          <span class="item-role">{{ emp.employee_role }}</span>
        </div>
        <div class="item-right">
          <span class="item-status" v-if="viewMode === 'arrival'">
            {{ emp.clock_in ? '已到' : '未到' }}
          </span>
          <span class="item-status late" v-else-if="viewMode === 'lateearly'">
            {{ emp.late_minutes > 0 ? `迟到${emp.late_minutes}分钟` : '' }}{{ emp.early_minutes > 0 ? `${emp.late_minutes > 0 ? ' / ' : ''}早退${emp.early_minutes}分钟` : '' }}
          </span>
          <span class="item-status absent" v-else-if="viewMode === 'leave'">
            {{ emp.scheduled_shift === 'leave' || emp.scheduled_shift === '请假' ? '请假' : '旷工' }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { attendanceAPI } from '@/api/attendance'

const route = useRoute()
const viewMode = computed(() => (route.query.view as string) || 'arrival')
const loading = ref(false)
const allEmployees = ref<any[]>([])

const viewTitle = computed(() => {
  const map: Record<string, string> = {
    arrival: '应到 / 实到',
    lateearly: '迟到 / 早退',
    leave: '请假 / 旷工',
  }
  return map[viewMode.value] || '考勤名单'
})

const filteredList = computed(() => {
  const today = new Date().toISOString().slice(0, 10)
  return allEmployees.value.filter(emp => {
    const cell = emp.cells?.find((c: any) => c.date === today)
    if (!cell) return false
    switch (viewMode.value) {
      case 'arrival':
        return cell.scheduled_shift && cell.scheduled_shift !== 'rest' && cell.scheduled_shift !== '休息'
      case 'lateearly':
        return cell.late_minutes > 0 || cell.early_minutes > 0
      case 'leave':
        return cell.scheduled_shift === 'leave' || cell.scheduled_shift === '请假' || cell.status === 'absent'
      default:
        return true
    }
  }).map(emp => {
    const cell = emp.cells?.find((c: any) => c.date === today)
    return { ...emp, ...cell }
  })
})

onMounted(async () => {
  loading.value = true
  try {
    const today = new Date().toISOString().slice(0, 10)
    const res = await attendanceAPI.getScheduleTable({ date_from: today, date_to: today })
    allEmployees.value = res.data.data?.employees || []
  } catch { /* silent */ }
  finally { loading.value = false }
})
</script>

<style scoped>
.attendance-detail-page { padding: 16px; padding-bottom: 80px; }
.page-header { margin-bottom: 16px; }
.page-title { font-size: 18px; font-weight: 700; color: #FFFFFF; }
.loading, .empty { color: #888; text-align: center; padding: 40px 0; font-size: 14px; }
.list { display: flex; flex-direction: column; gap: 6px; }
.list-item {
  display: flex; align-items: center; justify-content: space-between;
  padding: 12px; background: #111111; border: 1px solid #2a2a2a; border-radius: 8px;
}
.item-left { display: flex; flex-direction: column; gap: 2px; }
.item-name { font-size: 14px; font-weight: 600; color: #FFFFFF; }
.item-role { font-size: 11px; color: #7A7C80; }
.item-status { font-size: 13px; color: #4CAF50; font-weight: 500; }
.item-status.late { color: #FF9800; }
.item-status.early { color: #FF9800; }
.item-status.absent { color: #f44336; }
</style>
