<template>
  <div class="butler-page">
    <div class="page-header">
      <h1>开闭店检查</h1>
      <p class="page-subtitle">员工执行开店/闭店检查流程</p>
    </div>

    <!-- 当前进行中的会话 -->
    <div v-if="activeSession" class="active-session-card" @click="goToSession(activeSession.id)">
      <div class="card-header">
        <span class="badge" :class="activeSession.session_type">
          {{ activeSession.session_type === 'closing' ? '闭店进行中' : '开店进行中' }}
        </span>
        <span class="progress-text">{{ activeSession.completed_items }}/{{ activeSession.total_items }}</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <span class="card-tip">点击继续检查</span>
    </div>

    <!-- 开始按钮 -->
    <div v-else class="action-bar">
      <div class="action-buttons">
        <button class="btn btn-closing" :disabled="loading || !hasClosingTemplate" @click="startClosing">
          <span class="btn-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <path d="M3 17h14"/>
              <path d="M5 17V8l5-5 5 5v9"/>
              <path d="M9 17v-5h2v5"/>
            </svg>
          </span>
          <span>开始闭店</span>
        </button>
        <button class="btn btn-opening" :disabled="loading || !hasOpeningTemplate" @click="startOpening">
          <span class="btn-icon">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
              <circle cx="10" cy="10" r="4"/>
              <path d="M10 2v2"/>
              <path d="M10 16v2"/>
              <path d="M2 10h2"/>
              <path d="M16 10h2"/>
              <path d="M4.2 4.2l1.4 1.4"/>
              <path d="M14.4 14.4l1.4 1.4"/>
              <path d="M4.2 15.8l1.4-1.4"/>
              <path d="M14.4 5.6l1.4-1.4"/>
            </svg>
          </span>
          <span>开始开店</span>
        </button>
      </div>
      <div v-if="!hasClosingTemplate && !hasOpeningTemplate" class="template-tip">
        本店尚未配置检查单，请联系店长在管理页配置
      </div>
      <div v-else-if="!hasClosingTemplate" class="template-tip">
        闭店检查单未配置，仅可执行开店检查
      </div>
      <div v-else-if="!hasOpeningTemplate" class="template-tip">
        开店检查单未配置，仅可执行闭店检查
      </div>
    </div>

    <!-- 我的历史记录 -->
    <div class="section-title">我的检查记录</div>
    <div v-if="mySessions.length === 0" class="empty-list">暂无检查记录</div>
    <div v-else class="session-list">
      <div
        v-for="s in mySessions"
        :key="s.id"
        class="session-item"
        @click="goToSession(s.id)"
      >
        <div class="session-left">
          <span class="session-badge" :class="s.session_type">
            {{ s.session_type === 'closing' ? '闭店' : '开店' }}
          </span>
          <div class="session-info">
            <span class="session-status">{{ statusLabel(s.status) }}</span>
            <span class="session-time">{{ formatTime(s.started_at) }}</span>
          </div>
        </div>
        <div class="session-right">
          <span class="session-progress">{{ s.completed_items }}/{{ s.total_items }}</span>
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
    </div>

    <div v-if="errorMsg" class="error-toast">{{ errorMsg }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { startSession, listSessions, listTemplates } from '@/api/butler'
import type { SessionDetail, ChecklistTemplate } from '@/api/butler'

const router = useRouter()
const route = useRoute()
const loading = ref(false)
const errorMsg = ref('')
const activeSession = ref<SessionDetail | null>(null)
const mySessions = ref<SessionDetail[]>([])
const templates = ref<ChecklistTemplate[]>([])

const hasClosingTemplate = computed(() =>
  templates.value.some(t => t.session_type === 'closing' && t.is_active !== false)
)
const hasOpeningTemplate = computed(() =>
  templates.value.some(t => t.session_type === 'opening' && t.is_active !== false)
)

const progressPercent = computed(() => {
  if (!activeSession.value || activeSession.value.total_items === 0) return 0
  return Math.round((activeSession.value.completed_items / activeSession.value.total_items) * 100)
})

onMounted(() => {
  loadData()
})

async function loadData() {
  try {
    const [tplRes, sessRes] = await Promise.all([
      listTemplates().catch(() => null),
      listSessions({ page: 1, page_size: 10 }).catch(() => null),
    ])
    if (tplRes) {
      templates.value = (tplRes.data as any).data || (tplRes.data as any) || []
    }
    if (sessRes) {
      const items = (sessRes.data as any).data?.items || (sessRes.data as any).items || []
      mySessions.value = items
      const active = items.find((s: SessionDetail) => s.status === 'in_progress')
      if (active) activeSession.value = active
    }
  } catch (e) {
    console.error('[butler/index] loadData failed:', e)
  }
}

async function startClosing() {
  await startSessionFlow('closing')
}

async function startOpening() {
  await startSessionFlow('opening')
}

async function startSessionFlow(sessionType: 'opening' | 'closing') {
  errorMsg.value = ''
  loading.value = true
  try {
    const res: any = await startSession(sessionType)
    const data = res.data?.data || res.data
    activeSession.value = data
    goToSession(data.id)
  } catch (e: any) {
    const msg = e?.response?.data?.message || ''
    if (msg.includes('尚未配置')) {
      errorMsg.value = '本店尚未配置检查单，请联系店长在管理页配置'
    } else {
      errorMsg.value = msg || '启动失败，请稍后重试'
    }
  } finally {
    loading.value = false
  }
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    in_progress: '进行中',
    completed: '已完成',
    abandoned: '已放弃',
  }
  return map[status] || status
}

function formatTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const mm = String(d.getMonth() + 1).padStart(2, '0')
  const dd = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mi = String(d.getMinutes()).padStart(2, '0')
  return `${mm}-${dd} ${hh}:${mi}`
}

function goToSession(id: string) {
  const prefix = route.path.startsWith('/daily') ? '/daily' : '/management'
  router.push(`${prefix}/butler/session/${id}`)
}
</script>

<style scoped>
.butler-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
  color: #FFFFFF;
  min-height: 100vh;
  background: #000000;
  padding-bottom: calc(56px + 24px);
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 4px;
}

.page-subtitle {
  font-size: 12px;
  color: #7A7C80;
  margin: 0;
}

/* 进行中会话卡片 */
.active-session-card {
  background: #111111;
  border: 1px solid #FB0079;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
  cursor: pointer;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.progress-text {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
}

.progress-bar {
  height: 6px;
  background: #333;
  border-radius: 3px;
  margin-bottom: 10px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #FB0079;
  border-radius: 3px;
  transition: width 0.3s;
}

.card-tip {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
  font-weight: 600;
  background: #222222;
  color: #FB0079;
}

/* 开始按钮区 */
.action-bar {
  margin-bottom: 24px;
}

.action-buttons {
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
}

.btn {
  flex: 1;
  padding: 18px 12px;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  transition: opacity 0.2s;
}

.btn:disabled {
  cursor: not-allowed;
  opacity: 0.4;
}

.btn-closing {
  background: #FB0079;
  color: #fff;
}

.btn-opening {
  background: #222222;
  color: rgba(255, 255, 255, 0.9);
  border: 1px solid #333333;
}

.btn-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.template-tip {
  font-size: 12px;
  color: #7A7C80;
  text-align: center;
  padding: 8px;
  background: rgba(251, 0, 121, 0.05);
  border-radius: 8px;
}

/* 区块标题 */
.section-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #7A7C80;
  margin: 0 0 12px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

/* 列表 */
.empty-list {
  text-align: center;
  padding: 24px;
  color: #7A7C80;
  font-size: 13px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}

.session-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.session-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 14px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  cursor: pointer;
  transition: border-color 0.2s;
}

.session-item:hover {
  border-color: #FB0079;
}

.session-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.session-badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  background: #222222;
  color: #FB0079;
}

.session-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.session-status {
  font-size: 13px;
  color: #C8C8C8;
}

.session-time {
  font-size: 11px;
  color: #7A7C80;
}

.session-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.session-progress {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}

.error-toast {
  position: fixed;
  bottom: 80px;
  left: 50%;
  transform: translateX(-50%);
  padding: 12px 20px;
  background: #111111;
  border: 1px solid #FB0079;
  border-radius: 8px;
  color: #FB0079;
  font-size: 13px;
  text-align: center;
  z-index: 100;
  max-width: 90%;
}
</style>
