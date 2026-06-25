<template>
  <div class="daily-page">
    <div class="xiao-c-entry" @click="showChat = true">
      <img src="/laoc-avatar.png" class="xiao-c-avatar" alt="老C" />
      <div class="xiao-c-text">
        <span class="xiao-c-title">老C</span>
        <Transition name="hint-fade" mode="out-in">
          <span class="xiao-c-hint" :key="hintIndex">{{ hints[hintIndex] }}</span>
        </Transition>
      </div>
      <span class="xiao-c-arrow">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/></svg>
      </span>
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
        <div class="cd-item cd-pink" @click="router.push('/profile/my-data')">
          <span class="cd-value revenue">{{ fmtMoney(dashboard?.my_performance?.total_wework_pay || 0) }}</span>
          <span class="cd-label">我的业绩</span>
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
import { ref, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import ChatWidget from '@/components/ChatWidget.vue'
import { dashboardAPI } from '@/api/dashboard'
import type { DashboardData } from '@/api/dashboard'
import { signTaskAPI } from '@/api/sign-tasks'
import { approvalAPI } from '@/api/approval'

const router = useRouter()
const showChat = ref(false)

const dashboard = ref<DashboardData | null>(null)

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

function fmtMoney(n: number | undefined) {
  if (n == null) return '0'
  if (n >= 10000) return (n / 10000).toFixed(1) + 'w'
  return n.toLocaleString()
}

onMounted(() => {
  loadDashboard()
  loadInboxCount()
  loadApprovalCount()
  startHintRotation()
})

onUnmounted(() => {
  if (hintTimer) clearInterval(hintTimer)
})

async function loadInboxCount() {
  try {
    const res = await signTaskAPI.getCount()
    if (res.data.code === 0) {
      const inboxCard = cards.find(c => c.path === '/daily/inbox')
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
      const approvalCard = cards.find(c => c.path === '/daily/approval')
      if (approvalCard) approvalCard.badge = count
    }
  } catch (e) { console.error('[HomePage] loadApprovalCount failed:', e) }
}

interface FuncCard {
  label: string
  path: string
  icon: string
  badge?: number
}

const cards: FuncCard[] = [
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
]
</script>

<style scoped>
.daily-page {
  padding: 16px;
}

.xiao-c-entry {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  margin-bottom: 16px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}

.xiao-c-entry:hover {
  border-color: #FB0079;
}

.xiao-c-entry:active {
  transform: scale(0.98);
}

.xiao-c-avatar {
  width: 40px;
  height: 40px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
}

.xiao-c-text {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.xiao-c-title {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.xiao-c-hint {
  font-size: 12px;
  color: #7A7C80;
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

.card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.func-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, transform 0.15s ease, box-shadow 0.2s;
  position: relative;
  -webkit-tap-highlight-color: transparent;
}

.func-card:hover {
  border-color: #FB0079;
}

.func-card:active {
  transform: scale(0.96);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
}

.card-label {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 400;
  color: #C8C8C8;
}

.card-arrow {
  position: absolute;
  top: 8px;
  right: 8px;
  display: flex;
  align-items: center;
}

.card-badge {
  position: absolute;
  top: 8px;
  right: 28px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 10px;
  font-weight: 700;
  padding: 2px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
  line-height: 1.4;
}

/* 浓缩看板 */
.compact-dashboard {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 12px 16px;
  margin-bottom: 12px;
  cursor: pointer;
}

.cd-row {
  display: flex;
  align-items: center;
  gap: 0;
}

.cd-row + .cd-row {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid #1a1a1a;
}

.cd-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.cd-value {
  font-size: 16px;
  font-weight: 700;
  color: #FFFFFF;
}

.cd-pink .cd-value {
  color: #FB0079;
}

.cd-white .cd-value {
  color: #FFFFFF;
}

.cd-label {
  font-size: 11px;
  color: #7A7C80;
}

.cd-div {
  width: 1px;
  height: 24px;
  background: #222222;
}
</style>
