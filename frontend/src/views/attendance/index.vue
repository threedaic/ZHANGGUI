<template>
  <div class="attendance-page">
    <!-- 页面标题 -->
    <div class="page-header">
      <h1 class="page-title">考勤管理</h1>
      <el-button type="primary" class="sync-btn" :loading="syncing" @click="handleSync">
        {{ syncing ? '同步中...' : '指纹机同步' }}
      </el-button>
    </div>

    <!-- 今日打卡状态 -->
    <div class="section">
      <h2 class="section-title">今日打卡</h2>
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
            <span class="card-status" :class="'status-' + item.status">
              {{ statusLabel(item.status) }}
            </span>
          </div>
          <div class="card-time-row">
            <span class="time-label">上班</span>
            <span class="time-value">{{ item.clock_in || '--:--' }}</span>
            <span class="time-divider">|</span>
            <span class="time-label">下班</span>
            <span class="time-value">{{ item.clock_out || '--:--' }}</span>
          </div>
          <div v-if="item.late_minutes > 0" class="card-late-info">
            迟到 {{ item.late_minutes }} 分钟
            <template v-if="item.deduction > 0">
              · <span class="amount">-¥{{ item.deduction }}</span>
            </template>
          </div>
          <div class="card-source">{{ item.source === 'fingerprint' ? '指纹机' : item.source === 'makeup' ? '补卡' : '手动' }}</div>
        </div>
      </div>
    </div>

    <!-- 操作面板：补卡 + 请假 -->
    <div class="section">
      <h2 class="section-title">考勤操作</h2>
      <div class="action-tabs">
        <el-radio-group v-model="actionTab" size="small">
          <el-radio-button value="makeup">补卡申请</el-radio-button>
          <el-radio-button value="leave">请假申请</el-radio-button>
        </el-radio-group>
      </div>

      <!-- 补卡表单 -->
      <div v-if="actionTab === 'makeup'" class="form-card">
        <div class="form-item">
          <label class="form-label">员工</label>
          <el-select v-model="makeupForm.employee_id" placeholder="选择员工" class="full-width">
            <el-option
              v-for="e in employees"
              :key="e.id"
              :label="e.name"
              :value="e.id"
            />
          </el-select>
        </div>
        <div class="form-item">
          <label class="form-label">补卡日期</label>
          <el-date-picker
            v-model="makeupForm.date"
            type="date"
            placeholder="选择日期"
            value-format="YYYY-MM-DD"
            class="full-width"
          />
        </div>
        <div class="form-item form-row">
          <div class="half">
            <label class="form-label">上班时间</label>
            <el-time-picker
              v-model="makeupForm.clock_in"
              placeholder="HH:mm"
              format="HH:mm"
              value-format="HH:mm"
              class="full-width"
            />
          </div>
          <div class="half">
            <label class="form-label">下班时间</label>
            <el-time-picker
              v-model="makeupForm.clock_out"
              placeholder="HH:mm"
              format="HH:mm"
              value-format="HH:mm"
              class="full-width"
            />
          </div>
        </div>
        <div class="form-item">
          <label class="form-label">补卡原因</label>
          <el-input
            v-model="makeupForm.reason"
            type="textarea"
            :rows="2"
            placeholder="请说明补卡原因"
          />
        </div>
        <div class="makeup-rule">
          规则：每月前 2 次免费，第 3 次起 10 元/次
        </div>
        <el-button type="primary" class="submit-btn" :loading="makeupSubmitting" @click="handleMakeup">
          提交补卡
        </el-button>
      </div>

      <!-- 请假表单 -->
      <div v-if="actionTab === 'leave'" class="form-card">
        <div class="form-item">
          <label class="form-label">员工</label>
          <el-select v-model="leaveForm.employee_id" placeholder="选择员工" class="full-width">
            <el-option
              v-for="e in employees"
              :key="e.id"
              :label="e.name"
              :value="e.id"
            />
          </el-select>
        </div>
        <div class="form-item form-row">
          <div class="half">
            <label class="form-label">开始日期</label>
            <el-date-picker
              v-model="leaveForm.start_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              class="full-width"
            />
          </div>
          <div class="half">
            <label class="form-label">结束日期</label>
            <el-date-picker
              v-model="leaveForm.end_date"
              type="date"
              placeholder="选择日期"
              value-format="YYYY-MM-DD"
              class="full-width"
            />
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
          <el-input
            v-model="leaveForm.reason"
            type="textarea"
            :rows="2"
            placeholder="请说明请假原因"
          />
        </div>
        <el-button type="primary" class="submit-btn" :loading="leaveSubmitting" @click="handleLeave">
          提交请假 · 通知店长审批
        </el-button>
      </div>
    </div>

    <!-- 请假审批列表 -->
    <div class="section">
      <h2 class="section-title">请假审批</h2>
      <div v-if="leaveLoading" class="loading-text">加载中...</div>
      <div v-else-if="leaveRecords.length === 0" class="empty-text">暂无请假记录</div>
      <div v-else class="leave-list">
        <div
          v-for="item in leaveRecords"
          :key="item.id"
          class="leave-card"
        >
          <div class="leave-top">
            <span class="leave-name">{{ item.employee_name }}</span>
            <span
              class="leave-status-tag"
              :class="{
                'tag-pending': item.status === 'pending',
                'tag-approved': item.status === 'approved',
                'tag-rejected': item.status === 'rejected',
              }"
            >
              {{ item.status === 'pending' ? '待审批' : item.status === 'approved' ? '已通过' : '已驳回' }}
            </span>
          </div>
          <div class="leave-detail">
            {{ item.start_date }} ~ {{ item.end_date }}
            · {{ item.leave_type === 'personal' ? '事假' : item.leave_type === 'sick' ? '病假' : '年假' }}
          </div>
          <div class="leave-reason">原因：{{ item.reason }}</div>
          <div v-if="item.status === 'pending'" class="leave-actions">
            <el-button size="small" type="success" plain @click="handleApproveLeave(item.id, 'approved')">
              通过
            </el-button>
            <el-button size="small" type="danger" plain @click="handleApproveLeave(item.id, 'rejected')">
              驳回
            </el-button>
          </div>
        </div>
      </div>
    </div>

    <!-- 月末汇总 -->
    <div class="section">
      <h2 class="section-title">月末汇总</h2>
      <div class="section-subtitle">
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
              <th>员工</th>
              <th>岗位</th>
              <th>出勤</th>
              <th>迟到</th>
              <th>早退</th>
              <th>请假</th>
              <th>旷工</th>
              <th>补卡</th>
              <th>迟到扣款</th>
              <th>补卡费</th>
              <th>考勤扣款</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in summaryItems" :key="item.employee_id">
              <td>{{ item.employee_name }}</td>
              <td class="role-cell">{{ item.employee_role }}</td>
              <td>{{ item.present_days }}/{{ item.total_days }}</td>
              <td>{{ item.late_days }}</td>
              <td>{{ item.early_days }}</td>
              <td>{{ item.leave_days }}</td>
              <td>{{ item.absent_days }}</td>
              <td>{{ item.makeup_count }}</td>
              <td class="amount-cell">{{ item.late_fee > 0 ? '-¥' + item.late_fee : '0' }}</td>
              <td class="amount-cell">{{ item.makeup_fee > 0 ? '-¥' + item.makeup_fee : '0' }}</td>
              <td class="amount-cell amount-total">{{ item.total_deduction > 0 ? '-¥' + item.total_deduction : '0' }}</td>
            </tr>
          </tbody>
          <tfoot v-if="summaryTotal">
            <tr>
              <td colspan="8">合计</td>
              <td class="amount-cell">-¥{{ summaryTotal.late_fee }}</td>
              <td class="amount-cell">-¥{{ summaryTotal.makeup_fee }}</td>
              <td class="amount-cell amount-total">-¥{{ summaryTotal.total_deduction }}</td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>

    <!-- 打卡记录查询 -->
    <div class="section">
      <h2 class="section-title">打卡记录</h2>
      <div class="filter-row">
        <el-select v-model="recordFilter.employee_id" placeholder="全部员工" clearable size="small" class="filter-item">
          <el-option v-for="e in employees" :key="e.id" :label="e.name" :value="e.id" />
        </el-select>
        <el-select v-model="recordFilter.status" placeholder="全部状态" clearable size="small" class="filter-item">
          <el-option label="正常" value="present" />
          <el-option label="迟到" value="late" />
          <el-option label="早退" value="early" />
          <el-option label="请假" value="leave" />
          <el-option label="旷工" value="absent" />
        </el-select>
        <el-button size="small" @click="loadRecords">查询</el-button>
      </div>
      <div v-if="recordLoading" class="loading-text">加载中...</div>
      <div v-else-if="recordList.length === 0" class="empty-text">暂无记录</div>
      <div v-else class="record-list">
        <div
          v-for="item in recordList"
          :key="item.id"
          class="record-row"
        >
          <div class="record-main">
            <span class="record-name">{{ item.employee_name }}</span>
            <span class="record-date">{{ item.date }}</span>
            <span class="record-status-tag" :class="'rs-' + item.status">{{ statusLabel(item.status) }}</span>
          </div>
          <div class="record-sub">
            上班 {{ item.clock_in || '--:--' }} | 下班 {{ item.clock_out || '--:--' }}
            <template v-if="item.late_minutes > 0">
              · 迟到 {{ item.late_minutes }} 分钟
              <span class="amount">-¥{{ item.deduction }}</span>
            </template>
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
  </div>
</template>

<script setup lang="ts">
// TODO: 修复剩余类型不匹配
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { attendanceAPI } from '@/api/attendance'
import type {
  AttendanceRecord,
  MonthlySummaryItem,
  LeaveResponse,
  PageResult,
} from '@/api/attendance'

// ==================== 当前日期 ====================
const today = new Date().toISOString().slice(0, 10)

// ==================== 员工列表 ====================
interface EmpItem { id: string; name: string }
const employees = ref<EmpItem[]>([])

// ==================== 今日打卡 ====================
const todayRecords = ref<AttendanceRecord[]>([])
const todayLoading = ref(false)

async function loadToday() {
  todayLoading.value = true
  try {
    const res = await attendanceAPI.getToday()
    todayRecords.value = res.data.data || []
  } catch {
    // handle
  } finally {
    todayLoading.value = false
  }
}

// ==================== 指纹机同步 ====================
const syncing = ref(false)
async function handleSync() {
  syncing.value = true
  try {
    const res = await attendanceAPI.syncFingerprint(today)
    const d = res.data.data
    ElMessage.success(`同步完成：${d.synced_count} 条记录（新增 ${d.new_records}，更新 ${d.updated_records}）`)
    if (d.errors.length > 0) {
      ElMessage.warning(`有 ${d.errors.length} 条记录同步失败`)
    }
    await loadToday()
  } catch {
    ElMessage.error('同步失败')
  } finally {
    syncing.value = false
  }
}

// ==================== 操作切换 ====================
const actionTab = ref<'makeup' | 'leave'>('makeup')

// ==================== 补卡 ====================
const makeupForm = reactive({
  employee_id: null as string | null,
  date: today,
  clock_in: null as string | null,
  clock_out: null as string | null,
  reason: '',
})
const makeupSubmitting = ref(false)

async function handleMakeup() {
  if (!makeupForm.employee_id || !makeupForm.date) {
    ElMessage.warning('请填写员工和日期')
    return
  }
  if (!makeupForm.clock_in && !makeupForm.clock_out) {
    ElMessage.warning('请至少填写上班或下班时间')
    return
  }
  if (!makeupForm.reason.trim()) {
    ElMessage.warning('请填写补卡原因')
    return
  }

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
    ElMessage.success(
      `补卡成功！${d.fee > 0 ? `本次费用 ¥${d.fee}` : '本次免费'}（本月已补 ${d.month_count} 次）`
    )
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

// ==================== 请假 ====================
const leaveForm = reactive({
  employee_id: null as string | null,
  start_date: null as string | null,
  end_date: null as string | null,
  leave_type: 'personal' as string,
  reason: '',
})
const leaveSubmitting = ref(false)

async function handleLeave() {
  if (!leaveForm.employee_id || !leaveForm.start_date || !leaveForm.end_date) {
    ElMessage.warning('请完整填写信息')
    return
  }
  if (!leaveForm.reason.trim()) {
    ElMessage.warning('请填写请假原因')
    return
  }

  leaveSubmitting.value = true
  try {
    await attendanceAPI.requestLeave({
      employee_id: leaveForm.employee_id,
      start_date: leaveForm.start_date,
      end_date: leaveForm.end_date,
      leave_type: leaveForm.leave_type,
      reason: leaveForm.reason.trim(),
    })
    ElMessage.success('请假申请已提交，等待店长审批')
    leaveForm.reason = ''
    await loadLeaveRecords()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '请假失败')
  } finally {
    leaveSubmitting.value = false
  }
}

// ==================== 请假审批 ====================
const leaveRecords = ref<LeaveResponse[]>([])
const leaveLoading = ref(false)

async function loadLeaveRecords() {
  leaveLoading.value = true
  try {
    const res = await attendanceAPI.getLeaveRecords({ status: 'pending', page_size: 50 })
    leaveRecords.value = res.data.data?.items || []
  } catch {
    // handle
  } finally {
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

// ==================== 月末汇总 ====================
const summaryPeriod = ref(today.slice(0, 7))
const summaryItems = ref<MonthlySummaryItem[]>([])
const summaryTotal = ref<{ late_fee: number; makeup_fee: number; total_deduction: number } | null>(null)
const summaryLoading = ref(false)

async function loadMonthlySummary() {
  if (!summaryPeriod.value) return
  summaryLoading.value = true
  try {
    const res = await attendanceAPI.getMonthlySummary(summaryPeriod.value)
    const data = res.data.data
    summaryItems.value = data.items || []
    summaryTotal.value = {
      late_fee: data.items.reduce((s: number, i: MonthlySummaryItem) => s + i.late_fee, 0),
      makeup_fee: data.items.reduce((s: number, i: MonthlySummaryItem) => s + i.makeup_fee, 0),
      total_deduction: data.total_deduction,
    }
  } catch {
    // handle
  } finally {
    summaryLoading.value = false
  }
}

// ==================== 打卡记录 ====================
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
  } catch {
    // handle
  } finally {
    recordLoading.value = false
  }
}

// ==================== 工具 ====================
function statusLabel(s: string): string {
  const map: Record<string, string> = {
    present: '正常',
    late: '迟到',
    early: '早退',
    leave: '请假',
    leave_pending: '待审批',
    absent: '旷工',
    unknown: '未知',
  }
  return map[s] || s
}

// ==================== 初始化 ====================
onMounted(async () => {
  await loadToday()
  await loadLeaveRecords()
  await loadMonthlySummary()
  await loadRecords()
})
</script>

<style scoped>
/* ==================== 页面容器 ==================== */
.attendance-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px 16px 96px;
  font-family: 'Source Han Sans SC', 'Poppins', sans-serif;
}

/* ==================== 头部 ==================== */
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 24px;
}
.page-title {
  font-size: 24px;
  font-weight: 900;
  color: #FFFFFF;
  margin: 0;
  font-family: 'Source Han Sans SC', 'Poppins', sans-serif;
}
.sync-btn {
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 13px;
  height: 36px;
  padding: 0 16px;
}
.sync-btn:hover {
  background: #FB0079;
  border-color: #FB0079;
}

/* ==================== 分区 ==================== */
.section {
  margin-bottom: 24px;
}
.section-title {
  font-size: 16px;
  font-weight: 600;
  color: #C8C8C8;
  margin: 0 0 4px 0;
}
.section-subtitle {
  font-size: 13px;
  color: #7A7C80;
  margin-bottom: 12px;
}
.loading-text,
.empty-text {
  color: #7A7C80;
  font-size: 13px;
  padding: 24px 0;
  text-align: center;
}

/* ==================== 今日打卡卡片 ==================== */
.today-cards {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.today-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
}
.today-card.card-late {
  border-color: rgba(251, 0, 121, 0.5);
}
.today-card.card-absent {
  border-color: #333333;
  opacity: 0.6;
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.card-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.card-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
.status-present {
  background: #333333;
  color: #C8C8C8;
}
.status-late {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}
.status-absent {
  background: #333333;
  color: #7A7C80;
}
.status-leave {
  background: #333333;
  color: #C8C8C8;
}
.card-time-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.time-label {
  font-size: 12px;
  color: #7A7C80;
}
.time-value {
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
  font-family: 'Poppins', sans-serif;
}
.time-divider {
  color: #7A7C80;
}
.card-late-info {
  font-size: 12px;
  color: #FB0079;
  margin-top: 4px;
}
.card-source {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}
.amount {
  color: #FB0079;
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
}

/* ==================== 操作面板 ==================== */
.action-tabs {
  margin-bottom: 12px;
}
.action-tabs :deep(.el-radio-button__inner) {
  background: #111111;
  border-color: #333333;
  color: #7A7C80;
  font-size: 13px;
}
.action-tabs :deep(.el-radio-button__original-radio:checked + .el-radio-button__inner) {
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
}

.form-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
}
.form-item {
  margin-bottom: 12px;
}
.form-row {
  display: flex;
  gap: 12px;
}
.half {
  flex: 1;
}
.form-label {
  display: block;
  font-size: 13px;
  color: #C8C8C8;
  margin-bottom: 6px;
}
.full-width {
  width: 100%;
}
.makeup-rule {
  font-size: 12px;
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
}
.submit-btn:hover {
  background: #FB0079;
  border-color: #FB0079;
}

/* ==================== 请假审批列表 ==================== */
.leave-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.leave-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
}
.leave-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.leave-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
}
.leave-status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}
.tag-pending {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}
.tag-approved {
  background: rgba(0, 200, 83, 0.15);
  color: #FB0079;
}
.tag-rejected {
  background: #333333;
  color: #7A7C80;
}
.leave-detail {
  font-size: 13px;
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

/* ==================== 月末汇总表格 ==================== */
.month-picker {
  width: 160px;
}
.summary-table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
}
.summary-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
  white-space: nowrap;
}
.summary-table th {
  background: #333333;
  color: #C8C8C8;
  font-weight: 600;
  padding: 10px 8px;
  text-align: center;
  font-size: 12px;
}
.summary-table td {
  padding: 10px 8px;
  text-align: center;
  color: #C8C8C8;
  border-bottom: 1px solid #222222;
}
.summary-table tfoot td {
  font-weight: 600;
  color: #FFFFFF;
  background: #111111;
  border-top: 2px solid #333333;
}
.role-cell {
  color: #7A7C80;
  font-size: 12px;
}
.amount-cell {
  color: #FB0079;
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
  text-align: right;
}
.amount-total {
  color: #FB0079;
  font-size: 14px;
}

/* ==================== 打卡记录 ==================== */
.filter-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  align-items: center;
}
.filter-item {
  width: 120px;
}
.record-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.record-row {
  background: #111111;
  border-bottom: 1px solid #222222;
  padding: 10px 0;
}
.record-main {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 2px;
}
.record-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.record-date {
  font-size: 12px;
  color: #7A7C80;
}
.record-status-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 4px;
}
.rs-present { background: #333333; color: #C8C8C8; }
.rs-late { background: rgba(251, 0, 121, 0.15); color: #FB0079; }
.rs-early { background: rgba(255, 104, 162, 0.15); color: #FB0079; }
.rs-leave { background: #333333; color: #C8C8C8; }
.rs-absent { background: #333333; color: #7A7C80; }
.record-sub {
  font-size: 12px;
  color: #7A7C80;
}
.pagination-row {
  margin-top: 12px;
  display: flex;
  justify-content: center;
}

/* ==================== Element Plus 覆盖 ==================== */
:deep(.el-input__wrapper) {
  background: #111111;
  box-shadow: 0 0 0 1px #333333;
  border-radius: 8px;
}
:deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #333333;
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
:deep(.el-select .el-input__wrapper) {
  background: #111111;
  box-shadow: 0 0 0 1px #333333;
}
:deep(.el-textarea__inner) {
  background: #111111;
  border-color: #333333;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 13px;
}
:deep(.el-textarea__inner:focus) {
  border-color: #FB0079;
  box-shadow: 0 0 0 1.5px #FB0079;
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
