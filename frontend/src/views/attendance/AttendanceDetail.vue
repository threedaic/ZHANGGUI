<template>
  <div class="attendance-detail-page">
    <div class="page-header">
      <span class="page-title">{{ viewTitle }}</span>
      <span class="page-date" v-if="displayDate">{{ displayDate }}</span>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="filteredList.length === 0" class="empty">暂无数据</div>
    <div v-else class="list">
      <div v-for="emp in filteredList" :key="emp.employee_id" class="list-item">
        <div class="item-left">
          <span class="item-name">{{ emp.employee_name }}</span>
          <span class="item-role">{{ emp.employee_role_label || emp.employee_role }}</span>
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
const displayDate = ref('')

const viewTitle = computed(() => {
  const map: Record<string, string> = {
    arrival: '应到 / 实到',
    lateearly: '迟到 / 早退',
    leave: '请假 / 旷工',
  }
  return map[viewMode.value] || '考勤名单'
})

const filteredList = computed(() => {
  return allEmployees.value.filter(emp => {
    // 后端返回的 cells 只有1个元素（今日/回退日期）
    const cell = emp.cells?.[0]
    if (!cell) return false
    switch (viewMode.value) {
      case 'arrival':
        // 应到：有排班且非休息/请假
        return cell.scheduled_shift && cell.scheduled_shift !== 'rest' && cell.scheduled_shift !== '休息'
      case 'lateearly':
        // 迟到或早退
        return (cell.late_minutes && cell.late_minutes > 0) || (cell.early_minutes && cell.early_minutes > 0)
      case 'leave':
        // 请假 或 旷工（排班了但没打卡=旷工）
        if (cell.scheduled_shift === 'leave' || cell.scheduled_shift === '请假') return true
        // 有排班且非休息，但没打卡 = 旷工
        if (cell.scheduled_shift && cell.scheduled_shift !== 'rest' && cell.scheduled_shift !== '休息' && !cell.clock_in) return true
        return false
      default:
        return true
    }
  }).map(emp => {
    const cell = emp.cells?.[0] || {}
    return { ...emp, ...cell }
  })
})

onMounted(async () => {
  loading.value = true
  try {
    // 一次调用搞定，后端自动处理回退日期
    const res = await attendanceAPI.getTodayList()
    const data = res.data.data
    allEmployees.value = data?.employees || []
    displayDate.value = data?.date || ''
  } catch (e) {
    console.error('[考勤名单] 加载失败:', e)
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.attendance-detail-page { padding: 16px; padding-bottom: 80px; }
.page-header { margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center; }
.page-title { font-size: 18px; font-weight: 700; color: #FFFFFF; }
.page-date { font-size: 12px; color: #7A7C80; }
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
