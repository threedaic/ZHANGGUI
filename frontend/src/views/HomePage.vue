<template>
  <div class="daily-page">
    <!-- 老C + 任务中心：左右各一半 -->
    <div class="top-row">
      <div class="xiao-c-entry" @click="showChat = true">
        <img src="/laoc-avatar.png" class="xiao-c-avatar" alt="老C" />
        <div class="xiao-c-text">
          <span class="xiao-c-title">老C</span>
          <Transition name="hint-fade" mode="out-in">
            <span class="xiao-c-hint" :key="hintIndex">{{ hints[hintIndex] }}</span>
          </Transition>
        </div>
        <span class="xiao-c-arrow">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/></svg>
        </span>
      </div>

      <div
        class="task-center"
        :class="{ 'has-urgent': butlerPending || oaPendingCount > 0 }"
        @click="goTaskList()"
      >
        <div class="tc-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M9 11l2 2 4-4"/><path d="M21 12c0 5-3.5 7.5-7.5 9.5C9.5 19.5 6 17 6 12V5l7.5-3L21 5v7z"/>
          </svg>
          <span v-if="butlerPending || oaPendingCount > 0" class="tc-badge"></span>
        </div>
        <div class="tc-body">
          <span class="tc-title">任务中心</span>
          <span v-if="butlerPending" class="tc-hint urgent">
            {{ butlerPending.label }}未完成
          </span>
          <span v-else-if="oaPendingCount > 0" class="tc-hint urgent">
            {{ oaPendingCount }}个任务待处理
          </span>
          <span v-else class="tc-hint">今日暂无待办</span>
        </div>
        <span class="tc-arrow">
          <svg width="14" height="14" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/></svg>
        </span>
      </div>
    </div>

    <!-- 浓缩看板：2行x3列 粉白粉 -->
    <div class="compact-dashboard">
      <div class="cd-row">
        <div class="cd-item cd-pink" @click="router.push('/management/dashboard')">
          <span class="cd-value revenue">{{ fmtMoney(dashboard?.revenue?.today_revenue) }}</span>
          <span class="cd-label">今日营收</span>
        </div>
        <div class="cd-div"></div>
        <div class="cd-item cd-white" @click="router.push('/daily/attendance-detail?view=arrival')">
          <span class="cd-value">{{ (dashboard?.attendance?.scheduled_count ?? 0) }}/{{ (dashboard?.attendance?.actual_count ?? 0) }}</span>
          <span class="cd-label">应到/实到</span>
        </div>
        <div class="cd-div"></div>
        <div class="cd-item cd-pink" @click="router.push('/daily/attendance-detail?view=lateearly')">
          <span class="cd-value">{{ (dashboard?.attendance?.late_count ?? 0) }}/{{ (dashboard?.attendance?.early_count ?? 0) }}</span>
          <span class="cd-label">迟到/早退</span>
        </div>
      </div>
      <div class="cd-row">
        <div class="cd-item cd-pink" @click="router.push('/daily/my-payroll-preview')">
          <span class="cd-value revenue">{{ fmtMoney(myPayrollNet) }}</span>
          <span class="cd-label">我的工资</span>
        </div>
        <div class="cd-div"></div>
        <div class="cd-item cd-white" @click="router.push('/daily/booking')">
          <span class="cd-value">{{ (dashboard?.booking?.confirmed ?? 0) }}/{{ (dashboard?.booking?.total_tables ?? 0) }}</span>
          <span class="cd-label">订桌（已订/总桌）</span>
        </div>
        <div class="cd-div"></div>
        <div class="cd-item cd-pink" @click="router.push('/daily/attendance-detail?view=leave')">
          <span class="cd-value">{{ (dashboard?.attendance?.leave_count ?? 0) }}/{{ (dashboard?.attendance?.absent_count ?? 0) }}</span>
          <span class="cd-label">请假/旷工</span>
        </div>
      </div>
    </div>

    <div class="card-grid">
      <button
        v-for="card in cards"
        :key="card.path"
        class="func-card"
        @click="router.push(card.path)"
      >
        <span class="card-icon" v-html="card.icon"></span>
        <span class="card-label">{{ card.label }}</span>
        <span v-if="card.badge && card.badge > 0" class="card-badge">{{ card.badge > 99 ? '99+' : card.badge }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
        </span>
      </button>
    </div>

    <ChatWidget :visible="showChat" @close="showChat = false" />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import ChatWidget from '@/components/ChatWidget.vue'
import { dashboardAPI } from '@/api/dashboard'
import type { DashboardData } from '@/api/dashboard'
import { signTaskAPI } from '@/api/sign-tasks'
import { approvalAPI } from '@/api/approval'
import { getMyPayrollPreview } from '@/api/payroll'
import { getTodayStatus, type ButlerTodayStatus } from '@/api/butler'
import { taskAPI } from '@/api/task'

const router = useRouter()
const showChat = ref(false)

const dashboard = ref<DashboardData | null>(null)
const myPayrollNet = ref<number>(0)
const butlerStatus = ref<ButlerTodayStatus | null>(null)
const oaPendingCount = ref(0)

// 首页提醒条：取第一个待办项
const butlerPending = computed(() => {
  if (!butlerStatus.value || butlerStatus.value.pending.length === 0) return null
  const p = butlerStatus.value.pending[0]
  // 判断是否超时：闭店超过当晚23:30 / 开店超过当日11:30
  const now = new Date()
  const hour = now.getHours()
  const min = now.getMinutes()
  let is_overdue = false
  if (p.type === 'closing' && (hour > 23 || (hour === 23 && min > 30))) is_overdue = true
  if (p.type === 'opening' && (hour > 11 || (hour === 11 && min > 30))) is_overdue = true
  return { ...p, is_overdue }
})

function goButler() {
  router.push('/daily/butler')
}

function goTaskList() {
  router.push('/daily/tasks')
}

async function loadButlerStatus() {
  try {
    const res = await getTodayStatus()
    if (res.data.code === 0) {
      butlerStatus.value = res.data.data
    }
  } catch { /* silent */ }
}

// 老C滚动提示
const hints = [
  '今天谁晚班？',
  'A桌有人吗？',
  '今天排班情况',
  '本月工资多少？',
  '存酒还剩几瓶？',
  '今天迟到几个人？',
  '本周业绩怎么样？',
  '待审批有几条？',
]
const hintIndex = ref(0)
let hintTimer: ReturnType<typeof setInterval> | null = null

function startHintRotation() {
  hintTimer = setInterval(() => {
    hintIndex.value = (hintIndex.value + 1) % hints.length
  }, 3000)
}

async function loadDashboard() {
  try {
    const res = await dashboardAPI.getDashboard()
    dashboard.value = res.data.data
  } catch { /* silent */ }
}

async function loadMyPayroll() {
  try {
    const res = await getMyPayrollPreview()
    if (res.data.code === 0) {
      myPayrollNet.value = res.data.data.net_pay || 0
    }
  } catch { /* silent */ }
}

function fmtMoney(n: number | undefined) {
  if (n == null) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  return n.toLocaleString()
}

onMounted(() => {
  loadDashboard()
  loadMyPayroll()
  loadButlerStatus()
  loadInboxCount()
  loadApprovalCount()
  loadOaPendingCount()
  startHintRotation()
})

onUnmounted(() => {
  if (hintTimer) clearInterval(hintTimer)
})

async function loadInboxCount() {
  try {
    const res = await signTaskAPI.getCount()
    if (res.data.code === 0) {
      const inboxCard = cards.value.find(c => c.path === '/daily/inbox')
      if (inboxCard) inboxCard.badge = res.data.data.pending
    }
  } catch (e) { console.error('[HomePage] loadInboxCount failed:', e) }
}

async function loadApprovalCount() {
  try {
    const res = await approvalAPI.getPendingCount()
    if (res.data.code === 0) {
      const d = res.data.data
      // 普通员工看 assigned_to_me，店长/老板看 total_pending
      const count = d.assigned_to_me || d.total_pending || 0
      const approvalCard = cards.value.find(c => c.path === '/daily/approval')
      if (approvalCard) approvalCard.badge = count
    }
  } catch (e) { console.error('[HomePage] loadApprovalCount failed:', e) }
}

async function loadOaPendingCount() {
  try {
    const res = await taskAPI.myTasks({ status: 'pending', page: 1, page_size: 1 })
    if (res.data.code === 0) {
      oaPendingCount.value = res.data.data.total || 0
    }
  } catch { /* silent */ }
}

interface FuncCard {
  label: string
  path: string
  icon: string
  badge?: number
}

const cards = ref<FuncCard[]>([
  {
    label: '打卡',
    path: '/daily/checkin',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <circle cx="14" cy="14" r="10"/><circle cx="14" cy="14" r="5"/><circle cx="14" cy="14" r="1.5" fill="#FB0079"/>
    </svg>`,
  },
  {
    label: '订桌',
    path: '/daily/booking',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="5" y="6" width="18" height="16" rx="3"/><line x1="10" y1="12" x2="18" y2="12"/><line x1="10" y1="17" x2="15" y2="17"/>
    </svg>`,
  },
  {
    label: '存酒',
    path: '/daily/wine',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M9 4h10l2 6H7l2-6z"/><path d="M12 10v10c0 3-4 3-4 0v-10"/><rect x="16" y="10" width="5" height="12" rx="2"/>
    </svg>`,
  },
  {
    label: '审批',
    path: '/daily/approval',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <path d="M5 4h13l5 5v15H5z"/><path d="M18 4v5h5"/><path d="M10 14h8"/><path d="M10 18h5"/>
    </svg>`,
    badge: 0,
  },
  {
    label: '开闭店',
    path: '/daily/butler',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="4" y="3" width="18" height="22" rx="2"/><line x1="9" y1="8" x2="17" y2="8"/><line x1="9" y1="13" x2="17" y2="13"/><line x1="9" y1="18" x2="13" y2="18"/>
    </svg>`,
  },
  {
    label: '收件箱',
    path: '/daily/inbox',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="4" y="6" width="20" height="16" rx="2"/><path d="M4 10l10 6 10-6"/>
    </svg>`,
    badge: 0,
  },
  {
    label: '游戏',
    path: '/daily/game',
    icon: `<svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
      <rect x="3" y="8" width="22" height="14" rx="4"/><circle cx="9" cy="15" r="1.5"/><circle cx="19" cy="15" r="1.5"/><line x1="13" y1="13" x2="15" y2="13"/><line x1="14" y1="12" x2="14" y2="14"/>
    </svg>`,
  },
])
</script>

<style scoped>
.daily-page {
  padding: 16px;
}

/* ========== 老C + 任务中心 ========== */
.top-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.xiao-c-entry {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 16px;
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.25s ease;
  -webkit-tap-highlight-color: transparent;
}

.xiao-c-entry:active {
  transform: scale(0.97);
  background: rgba(251, 0, 121, 0.05);
}

.xiao-c-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  flex-shrink: 0;
  box-shadow: 0 0 0 2px rgba(251, 0, 121, 0.4), 0 0 16px rgba(251, 0, 121, 0.35), 0 0 32px rgba(251, 0, 121, 0.15), 0 0 48px rgba(251, 0, 121, 0.05);
}

.xiao-c-text {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.xiao-c-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.xiao-c-hint {
  font-size: 11px;
  color: #666;
  display: inline-block;
}

.hint-fade-enter-active {
  transition: all 0.4s cubic-bezier(0.25, 0.46, 0.45, 0.94);
}
.hint-fade-leave-active {
  transition: all 0.3s cubic-bezier(0.55, 0.085, 0.68, 0.53);
}
.hint-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.hint-fade-leave-to {
  opacity: 0;
  transform: translateY(-8px);
}

.xiao-c-arrow {
  flex-shrink: 0;
  display: flex;
  align-items: center;
}

/* 任务中心 */
.task-center {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px;
  border-radius: 16px;
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.08);
  cursor: pointer;
  transition: all 0.25s ease;
  -webkit-tap-highlight-color: transparent;
}

.task-center.has-urgent {
  background: linear-gradient(135deg, rgba(251, 0, 121, 0.1) 0%, rgba(251, 0, 121, 0.02) 100%);
  border-color: rgba(251, 0, 121, 0.25);
}

.task-center:active {
  transform: scale(0.97);
}

.tc-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(251, 0, 121, 0.06);
  color: rgba(251, 0, 121, 0.5);
  position: relative;
  transition: all 0.2s;
  box-shadow: 0 0 16px rgba(251, 0, 121, 0.15), 0 0 32px rgba(251, 0, 121, 0.08);
}

.has-urgent .tc-icon {
  background: rgba(251, 0, 121, 0.12);
  color: #FB0079;
  box-shadow: 0 0 0 2px rgba(251, 0, 121, 0.25), 0 0 16px rgba(251, 0, 121, 0.35), 0 0 32px rgba(251, 0, 121, 0.15), 0 0 48px rgba(251, 0, 121, 0.05);
}

.tc-badge {
  position: absolute;
  top: -2px;
  right: -2px;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #FB0079;
  box-shadow: 0 0 6px rgba(251, 0, 121, 0.8), 0 0 12px rgba(251, 0, 121, 0.4);
  animation: tc-pulse 1.5s ease-in-out infinite;
}

@keyframes tc-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.tc-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tc-title {
  font-size: 13px;
  font-weight: 600;
  color: #fff;
}

.tc-hint {
  font-size: 11px;
  color: #555;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tc-hint.urgent {
  color: #FB0079;
}

.tc-arrow {
  flex-shrink: 0;
}

/* ========== 数据看板 ========== */
.compact-dashboard {
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  padding: 16px 14px;
  margin-bottom: 12px;
  box-shadow: 0 2px 12px rgba(0,0,0,0.3);
}

.cd-row {
  display: flex;
  align-items: center;
}

.cd-row + .cd-row {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.05);
}

.cd-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: transform 0.2s ease;
}

.cd-item:active {
  transform: scale(0.92);
}

.cd-value {
  font-size: 18px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.5px;
  line-height: 1.1;
}

.cd-pink .cd-value {
  background: linear-gradient(135deg, #FB0079, #FF6BAA);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  filter: drop-shadow(0 0 6px rgba(251, 0, 121, 0.15));
}

.cd-label {
  font-size: 10px;
  color: #666;
  font-weight: 500;
  letter-spacing: 0.3px;
}

.cd-div {
  width: 1px;
  height: 30px;
  background: linear-gradient(to bottom, transparent, rgba(255,255,255,0.1), transparent);
}

/* ========== 功能卡片 ========== */
.card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.func-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  padding: 22px 12px;
  background: #141414;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  -webkit-tap-highlight-color: transparent;
}

.func-card:active {
  transform: scale(0.95);
  background: rgba(251, 0, 121, 0.04);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 44px;
  height: 44px;
  border-radius: 14px;
  background: rgba(251, 0, 121, 0.06);
  transition: transform 0.2s ease;
}

.func-card:active .card-icon {
  transform: scale(1.1);
}

.card-label {
  font-size: 13px;
  font-weight: 500;
  color: #bbb;
}

.card-arrow {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0.3;
}

.card-badge {
  position: absolute;
  top: 8px;
  right: 10px;
  background: linear-gradient(135deg, #FB0079, #ff3d9a);
  color: #fff;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 7px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  line-height: 1.4;
  box-shadow: 0 2px 8px rgba(251, 0, 121, 0.35);
}

@keyframes badge-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}
</style>
