<template>
  <div class="attendance-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">考勤管理</h1>
      <button class="header-btn config-btn" @click="router.push('/settings/checkin')">打卡设置</button>
    </div>

    <!-- 快捷操作 -->
    <div class="quick-actions">
      <button class="quick-btn" @click="openMakeup">补卡</button>
      <button class="quick-btn" @click="openLeave">请假</button>
    </div>

    <!-- Tab 分区 -->
    <div class="tab-bar">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        class="tab-btn"
        :class="{ active: activeTab === tab.key }"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
        <span v-if="tab.badge" class="tab-badge">{{ tab.badge }}</span>
      </button>
    </div>

    <!-- 今日 -->
    <div v-show="activeTab === 'today'" class="tab-content">
      <!-- 统计条 -->
      <div class="stats-bar">
        <div class="stat-item stat-present">
          <span class="stat-num">{{ stats.present }}</span>
          <span class="stat-label">已到</span>
        </div>
        <div class="stat-item stat-late">
          <span class="stat-num">{{ stats.late }}</span>
          <span class="stat-label">迟到</span>
        </div>
        <div class="stat-item stat-absent">
          <span class="stat-num">{{ stats.absent }}</span>
          <span class="stat-label">未打卡</span>
        </div>
        <div class="stat-item stat-leave">
          <span class="stat-num">{{ stats.leave }}</span>
          <span class="stat-label">请假</span>
        </div>
      </div>

      <div class="section-subtitle">{{ today }}</div>
      <div v-if="todayLoading" class="loading-text">加载中...</div>
      <div v-else-if="todayRecords.length === 0" class="empty-text">今日暂无打卡记录</div>
      <div v-else class="today-cards">
        <div
          v-for="item in todayRecords"
          :key="item.id"
          class="today-card"
          :class="{ 'card-late': item.status === 'late', 'card-absent': item.status === 'absent' }"
        >
          <div class="card-top">
            <span class="card-name">{{ item.employee_name }}</span>
            <span class="card-status" :class="'status-' + item.status">{{ statusLabel(item.status) }}</span>
          </div>
          <div class="card-time-row">
            <span class="time-label">上</span>
            <span class="time-value">{{ item.clock_in || '--:--' }}</span>
            <span class="time-divider">|</span>
            <span class="time-label">下</span>
            <span class="time-value">{{ item.clock_out || '--:--' }}</span>
            <span v-if="item.late_minutes > 0" class="card-late-tag">迟{{ item.late_minutes }}分</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 审批 -->
    <div v-show="activeTab === 'approve'" class="tab-content">
      <div v-if="leaveLoading" class="loading-text">加载中...</div>
      <div v-else-if="leaveRecords.length === 0" class="empty-text">暂无待审批请假</div>
      <div v-else class="leave-list">
        <div v-for="item in leaveRecords" :key="item.id" class="leave-card">
          <div class="leave-top">
            <span class="leave-name">{{ item.employee_name }}</span>
            <span class="leave-type-tag">{{ leaveTypeLabel(item.leave_type) }}</span>
          </div>
          <div class="leave-detail">{{ item.start_date }} ~ {{ item.end_date }}</div>
          <div class="leave-reason">{{ item.reason }}</div>
          <div class="leave-actions">
            <button class="action-btn approve-btn" @click="handleApproveLeave(item.id, 'approved')">通过</button>
            <button class="action-btn reject-btn" @click="handleApproveLeave(item.id, 'rejected')">驳回</button>
          </div>
        </div>
      </div>
    </div>

    <!-- 月报 -->
    <div v-show="activeTab === 'monthly'" class="tab-content">
      <div class="filter-bar">
        <el-date-picker
          v-model="summaryPeriod"
          type="month"
          placeholder="选择月份"
          value-format="YYYY-MM"
          @change="loadMonthlySummary"
          class="month-picker"
        />
      </div>
      <div v-if="summaryLoading" class="loading-text">加载中...</div>
      <div v-else-if="summaryItems.length === 0" class="empty-text">暂无数据</div>
      <div v-else class="summary-table-wrap">
        <table class="summary-table">
          <thead>
            <tr>
              <th>员工</th><th>出勤</th><th>迟到</th><th>早退</th><th>请假</th><th>旷工</th><th>补卡</th><th>扣款</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in summaryItems" :key="item.employee_id">
              <td class="name-cell">{{ item.employee_name }}</td>
              <td>{{ item.present_days }}/{{ item.total_days }}</td>
              <td>{{ item.late_days }}</td>
              <td>{{ item.early_days }}</td>
              <td>{{ item.leave_days }}</td>
              <td>{{ item.absent_days }}</td>
              <td>{{ item.makeup_count }}</td>
              <td class="amount-cell">{{ item.total_deduction > 0 ? '-¥' + item.total_deduction : '0' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 记录 -->
    <div v-show="activeTab === 'records'" class="tab-content">
      <div class="filter-bar">
        <el-select v-model="recordFilter.employee_id" placeholder="全部员工" clearable size="small" class="filter-item" @change="loadRecords">
          <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
        <el-select v-model="recordFilter.status" placeholder="全部状态" clearable size="small" class="filter-item" @change="loadRecords">
          <el-option label="正常" value="present" />
          <el-option label="迟到" value="late" />
          <el-option label="早退" value="early" />
          <el-option label="请假" value="leave" />
          <el-option label="旷工" value="absent" />
        </el-select>
      </div>
      <div v-if="recordLoading" class="loading-text">加载中...</div>
      <div v-else-if="recordList.length === 0" class="empty-text">暂无记录</div>
      <div v-else class="record-list">
        <div v-for="item in recordList" :key="item.id" class="record-row">
          <div class="record-main">
            <span class="record-name">{{ item.employee_name }}</span>
            <span class="record-date">{{ item.date }}</span>
            <span class="record-status-tag" :class="'rs-' + item.status">{{ statusLabel(item.status) }}</span>
          </div>
          <div class="record-sub">
            上{{ item.clock_in || '--:--' }} | 下{{ item.clock_out || '--:--' }}
            <span v-if="item.late_minutes > 0" class="record-late">·迟{{ item.late_minutes }}分</span>
          </div>
        </div>
        <div class="pagination-row" v-if="recordTotal > recordFilter.page_size">
          <el-pagination
            v-model:current-page="recordFilter.page"
            :page-size="recordFilter.page_size"
            :total="recordTotal"
            layout="prev, pager, next"
            small
            @current-change="loadRecords"
          />
        </div>
      </div>
    </div>

    <!-- 补卡弹窗 -->
    <el-dialog v-model="showMakeup" title="补卡申请" width="90%" class="dark-dialog">
      <div class="form-item">
        <label class="form-label">员工</label>
        <el-select v-model="makeupForm.employee_id" placeholder="选择员工" class="full-width">
          <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
      </div>
      <div class="form-item">
        <label class="form-label">补卡日期</label>
        <el-date-picker v-model="makeupForm.date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" class="full-width" />
      </div>
      <div class="form-item form-row">
        <div class="half">
          <label class="form-label">上班时间</label>
          <el-time-picker v-model="makeupForm.clock_in" placeholder="HH:mm" format="HH:mm" value-format="HH:mm" class="full-width" />
        </div>
        <div class="half">
          <label class="form-label">下班时间</label>
          <el-time-picker v-model="makeupForm.clock_out" placeholder="HH:mm" format="HH:mm" value-format="HH:mm" class="full-width" />
        </div>
      </div>
      <div class="form-item">
        <label class="form-label">补卡原因</label>
        <el-input v-model="makeupForm.reason" type="textarea" :rows="2" placeholder="请说明补卡原因" />
      </div>
      <div class="makeup-rule">每月前2次免费，第3次起10元/次</div>
      <el-button type="primary" class="submit-btn" :loading="makeupSubmitting" @click="handleMakeup">提交补卡</el-button>
    </el-dialog>

    <!-- 请假弹窗 -->
    <el-dialog v-model="showLeave" title="请假申请" width="90%" class="dark-dialog">
      <div class="form-item">
        <label class="form-label">员工</label>
        <el-select v-model="leaveForm.employee_id" placeholder="选择员工" class="full-width">
          <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
      </div>
      <div class="form-item form-row">
        <div class="half">
          <label class="form-label">开始日期</label>
          <el-date-picker v-model="leaveForm.start_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" class="full-width" />
        </div>
        <div class="half">
          <label class="form-label">结束日期</label>
          <el-date-picker v-model="leaveForm.end_date" type="date" placeholder="选择日期" value-format="YYYY-MM-DD" class="full-width" />
        </div>
      </div>
      <div class="form-item">
        <label class="form-label">请假类型</label>
        <el-select v-model="leaveForm.leave_type" placeholder="选择类型" class="full-width">
          <el-option label="事假" value="personal" />
          <el-option label="病假" value="sick" />
          <el-option label="年假" value="annual" />
        </el-select>
      </div>
      <div class="form-item">
        <label class="form-label">请假原因</label>
        <el-input v-model="leaveForm.reason" type="textarea" :rows="2" placeholder="请说明请假原因" />
      </div>
      <el-button type="primary" class="submit-btn" :loading="leaveSubmitting" @click="handleLeave">提交请假</el-button>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { attendanceAPI } from '@/api/attendance'
import type { AttendanceRecord, MonthlySummaryItem, LeaveResponse, PageResult } from '@/api/attendance'

const router = useRouter()
const today = new Date().toISOString().slice(0, 10)

// ==================== Tab ====================
const activeTab = ref<'today' | 'approve' | 'monthly' | 'records'>('today')
const leaveRecords = ref<LeaveResponse[]>([])
const tabs = computed(() => [
  { key: 'today', label: '今日', badge: 0 },
  { key: 'approve', label: '审批', badge: leaveRecords.value.length || 0 },
  { key: 'monthly', label: '月报', badge: 0 },
  { key: 'records', label: '记录', badge: 0 },
])

// ==================== 员工 ====================
interface EmpItem { id: string; name: string }
const employees = ref<EmpItem[]>([])

async function loadEmployees() {
  try {
    const today = new Date().toISOString().slice(0, 10)
    const res = await attendanceAPI.getScheduleTable({ date_from: today, date_to: today })
    employees.value = (res.data.data?.employees || []).map((e: any) => ({
      id: e.employee_id,
      name: e.employee_name,
    }))
  } catch { /* */ }
}

// ==================== 今日打卡 ====================
const todayRecords = ref<AttendanceRecord[]>([])
const todayLoading = ref(false)

const stats = computed(() => {
  const s = { present: 0, late: 0, absent: 0, leave: 0 }
  for (const r of todayRecords.value) {
    if (r.status === 'present') s.present++
    else if (r.status === 'late') s.late++
    else if (r.status === 'absent') s.absent++
    else if (r.status === 'leave') s.leave++
  }
  return s
})

async function loadToday() {
  todayLoading.value = true
  try {
    const res = await attendanceAPI.getToday()
    todayRecords.value = res.data.data || []
  } catch { /* */ } finally {
    todayLoading.value = false
  }
}

// ==================== 补卡弹窗 ====================
const showMakeup = ref(false)
const makeupForm = reactive({
  employee_id: null as string | null,
  date: today,
  clock_in: null as string | null,
  clock_out: null as string | null,
  reason: '',
})
const makeupSubmitting = ref(false)

function openMakeup() {
  showMakeup.value = true
}

async function handleMakeup() {
  if (!makeupForm.employee_id || !makeupForm.date) { ElMessage.warning('请填写员工和日期'); return }
  if (!makeupForm.clock_in && !makeupForm.clock_out) { ElMessage.warning('请至少填写一个时间'); return }
  if (!makeupForm.reason.trim()) { ElMessage.warning('请填写补卡原因'); return }
  makeupSubmitting.value = true
  try {
    const res = await attendanceAPI.requestMakeup({
      employee_id: makeupForm.employee_id,
      date: makeupForm.date,
      clock_in: makeupForm.clock_in,
      clock_out: makeupForm.clock_out,
      reason: makeupForm.reason.trim(),
    })
    const d = res.data.data
    ElMessage.success(`补卡成功！${d.fee > 0 ? `费用¥${d.fee}` : '免费'}（本月已补${d.month_count}次）`)
    showMakeup.value = false
    makeupForm.reason = ''
    makeupForm.clock_in = null
    makeupForm.clock_out = null
    await loadToday()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '补卡失败')
  } finally {
    makeupSubmitting.value = false
  }
}

// ==================== 请假弹窗 ====================
const showLeave = ref(false)
const leaveForm = reactive({
  employee_id: null as string | null,
  start_date: null as string | null,
  end_date: null as string | null,
  leave_type: 'personal' as string,
  reason: '',
})
const leaveSubmitting = ref(false)

function openLeave() {
  showLeave.value = true
}

async function handleLeave() {
  if (!leaveForm.employee_id || !leaveForm.start_date || !leaveForm.end_date) { ElMessage.warning('请完整填写'); return }
  if (!leaveForm.reason.trim()) { ElMessage.warning('请填写原因'); return }
  leaveSubmitting.value = true
  try {
    await attendanceAPI.requestLeave({
      employee_id: leaveForm.employee_id,
      start_date: leaveForm.start_date,
      end_date: leaveForm.end_date,
      leave_type: leaveForm.leave_type,
      reason: leaveForm.reason.trim(),
    })
    ElMessage.success('请假已提交，等待审批')
    showLeave.value = false
    leaveForm.reason = ''
    await loadLeaveRecords()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '请假失败')
  } finally {
    leaveSubmitting.value = false
  }
}

// ==================== 审批 ====================
const leaveLoading = ref(false)

async function loadLeaveRecords() {
  leaveLoading.value = true
  try {
    const res = await attendanceAPI.getLeaveRecords({ status: 'pending', page_size: 50 })
    leaveRecords.value = res.data.data?.items || []
  } catch { /* */ } finally {
    leaveLoading.value = false
  }
}

async function handleApproveLeave(recordId: string, action: string) {
  try {
    await attendanceAPI.approveLeave(recordId, { action })
    ElMessage.success(action === 'approved' ? '已通过' : '已驳回')
    await loadLeaveRecords()
    await loadToday()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '操作失败')
  }
}

// ==================== 月报 ====================
const summaryPeriod = ref(today.slice(0, 7))
const summaryItems = ref<MonthlySummaryItem[]>([])
const summaryLoading = ref(false)

async function loadMonthlySummary() {
  if (!summaryPeriod.value) return
  summaryLoading.value = true
  try {
    const res = await attendanceAPI.getMonthlySummary(summaryPeriod.value)
    summaryItems.value = res.data.data?.items || []
  } catch { /* */ } finally {
    summaryLoading.value = false
  }
}

// ==================== 记录 ====================
const recordFilter = reactive({
  employee_id: null as string | null,
  status: null as string | null,
  page: 1,
  page_size: 20,
})
const recordList = ref<AttendanceRecord[]>([])
const recordTotal = ref(0)
const recordLoading = ref(false)

async function loadRecords() {
  recordLoading.value = true
  try {
    const res = await attendanceAPI.getRecords({
      employee_id: recordFilter.employee_id ?? undefined,
      status: recordFilter.status ?? undefined,
      page: recordFilter.page,
      page_size: recordFilter.page_size,
    })
    const data = res.data.data as PageResult<AttendanceRecord>
    recordList.value = data.items || []
    recordTotal.value = data.total
  } catch { /* */ } finally {
    recordLoading.value = false
  }
}

// ==================== 工具 ====================
function statusLabel(s: string): string {
  const map: Record<string, string> = {
    present: '正常', late: '迟到', early: '早退', leave: '请假', absent: '旷工', unknown: '未知',
  }
  return map[s] || s
}

function leaveTypeLabel(t: string): string {
  return t === 'personal' ? '事假' : t === 'sick' ? '病假' : '年假'
}

// ==================== 初始化 ====================
onMounted(async () => {
  await loadEmployees()
  await loadToday()
  await loadLeaveRecords()
  await loadMonthlySummary()
  await loadRecords()
})
</script>

<style scoped>
.attendance-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px 16px 96px;
  font-family: 'Source Han Sans SC', 'Poppins', sans-serif;
}

/* 头部 */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.page-title {
  font-size: 22px;
  font-weight: 900;
  color: #FFFFFF;
  margin: 0;
}
.header-btn {
  border-radius: 8px;
  font-size: 12px;
  height: 32px;
  padding: 0 12px;
  cursor: pointer;
  border: none;
}
.config-btn {
  background: #111111;
  border: 1px solid #FB0079;
  color: #FB0079;
}

/* 快捷操作 */
.quick-actions {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.quick-btn {
  flex: 1;
  height: 40px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.quick-btn:active {
  border-color: #FB0079;
  color: #FB0079;
}

/* Tab */
.tab-bar {
  display: flex;
  gap: 4px;
  margin-bottom: 16px;
  background: #111111;
  border-radius: 10px;
  padding: 4px;
}
.tab-btn {
  flex: 1;
  height: 34px;
  background: transparent;
  border: none;
  border-radius: 8px;
  color: #7A7C80;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  position: relative;
}
.tab-btn.active {
  background: #FB0079;
  color: #FFFFFF;
}
.tab-badge {
  display: inline-block;
  min-width: 16px;
  height: 16px;
  line-height: 16px;
  padding: 0 4px;
  background: #FB0079;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 10px;
  margin-left: 2px;
}
.tab-btn.active .tab-badge {
  background: #FFFFFF;
  color: #FB0079;
}

.tab-content { animation: fadeIn 0.2s; }
@keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }

/* 统计条 */
.stats-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.stat-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 12px 4px;
  border-radius: 10px;
  background: #111111;
  border: 1px solid #333333;
}
.stat-num {
  font-size: 22px;
  font-weight: 800;
  font-family: 'Poppins', sans-serif;
}
.stat-label {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
}
.stat-present .stat-num { color: #34C759; }
.stat-late .stat-num { color: #FB0079; }
.stat-absent .stat-num { color: #7A7C80; }
.stat-leave .stat-num { color: #FF9500; }

.section-subtitle {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 8px;
}
.loading-text, .empty-text {
  color: #7A7C80;
  font-size: 13px;
  padding: 32px 0;
  text-align: center;
}

/* 今日卡片 */
.today-cards {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.today-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px;
}
.today-card.card-late { border-color: rgba(251, 0, 121, 0.4); }
.today-card.card-absent { opacity: 0.5; }
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.card-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.card-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}
.status-present { background: #333333; color: #C8C8C8; }
.status-late { background: rgba(251, 0, 121, 0.15); color: #FB0079; }
.status-absent { background: #333333; color: #7A7C80; }
.status-leave { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.card-time-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.time-label {
  font-size: 11px;
  color: #7A7C80;
}
.time-value {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  font-family: 'Poppins', sans-serif;
}
.time-divider { color: #333333; }
.card-late-tag {
  margin-left: auto;
  font-size: 11px;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
  padding: 1px 6px;
  border-radius: 4px;
}

/* 审批卡片 */
.leave-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.leave-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px;
}
.leave-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.leave-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.leave-type-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  background: rgba(255, 149, 0, 0.15);
  color: #FF9500;
}
.leave-detail {
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 2px;
}
.leave-reason {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 8px;
}
.leave-actions {
  display: flex;
  gap: 8px;
}
.action-btn {
  flex: 1;
  height: 32px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: none;
}
.approve-btn {
  background: #34C759;
  color: #FFFFFF;
}
.reject-btn {
  background: #333333;
  color: #FB0079;
  border: 1px solid #FB0079;
}

/* 月报 */
.filter-bar {
  margin-bottom: 12px;
}
.month-picker { width: 160px; }
.summary-table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  white-space: nowrap;
}
.summary-table th {
  background: #1a1a1a;
  color: #7A7C80;
  font-weight: 600;
  padding: 10px 6px;
  text-align: center;
}
.summary-table td {
  padding: 10px 6px;
  text-align: center;
  color: #C8C8C8;
  border-bottom: 1px solid #222222;
}
.name-cell {
  color: #FFFFFF;
  font-weight: 600;
  text-align: left;
}
.amount-cell {
  color: #FB0079;
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
}

/* 记录 */
.filter-item {
  width: 140px;
  margin-right: 8px;
}
.record-list {
  display: flex;
  flex-direction: column;
}
.record-row {
  background: #111111;
  border-bottom: 1px solid #222222;
  padding: 10px 0;
}
.record-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 2px;
}
.record-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.record-date {
  font-size: 11px;
  color: #7A7C80;
}
.record-status-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 4px;
  margin-left: auto;
}
.rs-present { background: #333333; color: #C8C8C8; }
.rs-late { background: rgba(251, 0, 121, 0.15); color: #FB0079; }
.rs-early { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.rs-leave { background: rgba(255, 149, 0, 0.15); color: #FF9500; }
.rs-absent { background: #333333; color: #7A7C80; }
.record-sub {
  font-size: 12px;
  color: #7A7C80;
}
.record-late { color: #FB0079; }
.pagination-row {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

/* 弹窗 */
.dark-dialog :deep(.el-dialog) {
  background: #111111;
  border-radius: 12px;
}
.dark-dialog :deep(.el-dialog__header) {
  background: #111111;
  border-bottom: 1px solid #333333;
  margin-right: 0;
  padding: 16px;
}
.dark-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}
.dark-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #7A7C80;
}
.dark-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}
.form-item { margin-bottom: 12px; }
.form-row { display: flex; gap: 12px; }
.half { flex: 1; }
.form-label {
  display: block;
  font-size: 13px;
  color: #C8C8C8;
  margin-bottom: 6px;
}
.full-width { width: 100%; }
.makeup-rule {
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 12px;
  padding: 8px;
  background: rgba(251, 0, 121, 0.06);
  border-radius: 6px;
}
.submit-btn {
  width: 100%;
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 14px;
  height: 40px;
  margin-top: 8px;
}

/* Element Plus 覆盖 */
:deep(.el-input__wrapper) {
  background: #1a1a1a;
  box-shadow: 0 0 0 1px #333333;
  border-radius: 8px;
}
:deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1.5px #FB0079;
}
:deep(.el-input__inner) {
  color: #FFFFFF;
  font-size: 13px;
}
:deep(.el-input__inner::placeholder) {
  color: #7A7C80;
}
:deep(.el-textarea__inner) {
  background: #1a1a1a;
  border-color: #333333;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 13px;
}
:deep(.el-textarea__inner:focus) {
  border-color: #FB0079;
}
:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next) {
  background: #111111;
  color: #C8C8C8;
}
:deep(.el-pagination .el-pager li) {
  background: #111111;
  color: #C8C8C8;
}
:deep(.el-pagination .el-pager li.is-active) {
  background: #FB0079;
  color: #FFFFFF;
}
</style>
