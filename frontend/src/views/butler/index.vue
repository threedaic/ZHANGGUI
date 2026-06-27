<template>
  <div class="butler-page">
    <!-- 加载中 -->
    <div v-if="loading" class="screen-center">
      <div class="spinner"></div>
      <p class="muted">加载中...</p>
    </div>

    <!-- 没有检查单配置 -->
    <div v-else-if="!hasAnyTemplate" class="screen-center">
      <p class="title-lg">本店尚未配置检查单</p>
      <p class="muted">请联系店长在管理页配置</p>
    </div>

    <!-- ========== 任务列表模式 ========== -->
    <div v-else-if="!currentSession" class="task-list-mode">
      <div class="list-header">
        <h2>今日任务</h2>
        <p class="list-date">{{ todayStr }}</p>
      </div>

      <!-- 有进行中的会话：继续 -->
      <div v-if="activeSessionInfo" class="task-card resume-card" @click="resumeSession">
        <div class="task-card-left">
          <div class="task-icon progress">
            <svg width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="10" cy="10" r="7"/><path d="M10 6v4l3 2"/></svg>
          </div>
          <div class="task-info">
            <span class="task-name">{{ activeSessionInfo.session_type === 'closing' ? '闭店检查' : '开店检查' }}</span>
            <span class="task-sub">进行中 {{ activeSessionInfo.completed_items }}/{{ activeSessionInfo.total_items }}</span>
          </div>
        </div>
        <div class="task-arrow">
          <span class="resume-badge">继续</span>
        </div>
      </div>

      <!-- 可开始的任务 -->
      <div class="section-label" v-if="availableTasks.length > 0">待开始</div>
      <div
        v-for="task in availableTasks"
        :key="task.type"
        class="task-card"
        @click="startTask(task.type)"
      >
        <div class="task-card-left">
          <div class="task-icon" :class="task.type">
            <svg v-if="task.type === 'closing'" width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M3 17h14M5 17V8l5-5 5 5v9"/><path d="M9 17v-5h2v5"/></svg>
            <svg v-else width="20" height="20" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5"><circle cx="10" cy="10" r="4"/><path d="M10 2v2M10 16v2M2 10h2M16 10h2"/></svg>
          </div>
          <div class="task-info">
            <span class="task-name">{{ task.label }}</span>
            <span class="task-sub">{{ task.count }} 项检查</span>
          </div>
        </div>
        <div class="task-arrow">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M6 4l4 4-4 4" stroke="#555" stroke-width="1.5" stroke-linecap="round"/></svg>
        </div>
      </div>

      <!-- 已完成 -->
      <div class="section-label" v-if="doneTasks.length > 0">已完成</div>
      <div v-for="task in doneTasks" :key="task.type" class="task-card done-card">
        <div class="task-card-left">
          <div class="task-icon done">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M4 8l3 3 5-6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </div>
          <div class="task-info">
            <span class="task-name done-text">{{ task.label }}</span>
            <span class="task-sub">{{ task.completed }}/{{ task.count }} 已完成</span>
          </div>
        </div>
      </div>

      <div class="footer-link" @click="goHistory">历史记录</div>
    </div>

    <!-- ========== 检查执行模式 ========== -->
    <div v-else-if="currentSession" class="check-screen">
      <div class="header-row">
        <div class="header-left">
          <button class="back-btn" @click="exitToTaskList">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none"><path d="M10 4l-4 4 4 4" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/></svg>
          </button>
          <h2 class="header-title">{{ currentSession.session_type === 'closing' ? '闭店检查' : '开店检查' }}</h2>
        </div>
        <div class="header-right">
          <span class="big-num">{{ currentSession.completed_items }}</span>
          <span class="big-num-total">/{{ currentSession.total_items }}</span>
        </div>
      </div>
      <div class="progress-track">
        <div class="progress-knob" :style="{ width: progressPercent + '%' }"></div>
      </div>

      <div class="item-list">
        <div
          v-for="(item, idx) in flatItems"
          :key="item.id"
          class="item"
          :class="itemClass(item)"
          @click="onItemClick(item)"
        >
          <div class="item-left">
            <div class="item-index" :class="itemClass(item)">
              <svg v-if="isItemDone(item)" width="14" height="14" viewBox="0 0 14 14" fill="none">
                <path d="M3 7l3 3 5-6" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
              <span v-else>{{ idx + 1 }}</span>
            </div>
          </div>
          <div class="item-body">
            <span class="item-name">{{ item.item_name }}</span>
            <span v-if="item.item_type === 'photo' && !isItemDone(item)" class="item-tag">需拍照</span>
            <span v-if="item.review_status === 'manual_reviewing'" class="item-tag waiting">复核中</span>
            <span v-if="item.review_status === 'manual_rejected'" class="item-tag rejected">被驳回</span>
          </div>
          <div class="item-right">
            <button v-if="item.review_status === 'pending' && item.item_type === 'checkbox'" class="btn-do" @click.stop="doConfirm(item.id)">确认</button>
            <button v-if="item.review_status === 'pending' && item.item_type === 'photo'" class="btn-do outline" @click.stop="triggerUpload(item.id)">拍照</button>
            <button v-if="item.review_status === 'manual_rejected'" class="btn-do outline" @click.stop="triggerUpload(item.id)">重拍</button>
            <div v-if="item.photo_url && isItemDone(item)" class="thumb"><img :src="item.photo_url" alt="" /></div>
          </div>
          <input v-if="item.item_type === 'photo'" type="file" accept="image/*" capture="environment" :ref="(el: any) => fileInputs[item.id] = el" @change="(e: any) => doUpload(item.id, e)" style="display:none" />
        </div>
      </div>
    </div>

    <transition name="fade">
      <div v-if="errorMsg" class="toast">{{ errorMsg }}</div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { startSession, getSession, listSessions, listTemplates, confirmItem, uploadPhoto } from '@/api/butler'
import type { SessionDetail, ChecklistTemplate, ItemResult } from '@/api/butler'

const router = useRouter()
const loading = ref(true)
const errorMsg = ref('')
const currentSession = ref<SessionDetail | null>(null)
const templates = ref<ChecklistTemplate[]>([])
const recentSessions = ref<any[]>([])
const activeSessionInfo = ref<any>(null)
const fileInputs = reactive<Record<string, HTMLInputElement | null>>({})

const hasClosing = computed(() => templates.value.some(t => t.session_type === 'closing' && t.is_active !== false))
const hasOpening = computed(() => templates.value.some(t => t.session_type === 'opening' && t.is_active !== false))
const hasAnyTemplate = computed(() => hasClosing.value || hasOpening.value)

const todayStr = computed(() => {
  const d = new Date()
  return `${d.getMonth() + 1}月${d.getDate()}日`
})

// 可开始的任务
const availableTasks = computed(() => {
  const tasks: { type: 'opening' | 'closing'; label: string; count: number }[] = []
  const hour = new Date().getHours()

  // 闭店检查（16:00-04:00 显示）
  if (hasClosing.value && !doneToday('closing') && !activeSessionInfo.value) {
    const count = templates.value.filter(t => t.session_type === 'closing').reduce((sum, t) => sum + (t.items?.length || 0), 0)
    tasks.push({ type: 'closing', label: '闭店检查', count })
  }
  // 开店检查（06:00-14:00 显示）
  if (hasOpening.value && !doneToday('opening') && !activeSessionInfo.value) {
    const count = templates.value.filter(t => t.session_type === 'opening').reduce((sum, t) => sum + (t.items?.length || 0), 0)
    tasks.push({ type: 'opening', label: '开店检查', count })
  }
  return tasks
})

// 已完成的任务
const doneTasks = computed(() => {
  const tasks: { type: string; label: string; count: number; completed: number }[] = []
  if (doneToday('closing')) {
    const s = recentSessions.value.find(s => s.session_type === 'closing' && s.status === 'completed')
    tasks.push({ type: 'closing', label: '闭店检查', count: s?.total_items || 0, completed: s?.completed_items || 0 })
  }
  if (doneToday('opening')) {
    const s = recentSessions.value.find(s => s.session_type === 'opening' && s.status === 'completed')
    tasks.push({ type: 'opening', label: '开店检查', count: s?.total_items || 0, completed: s?.completed_items || 0 })
  }
  return tasks
})

function doneToday(type: string): boolean {
  return recentSessions.value.some(s =>
    s.status === 'completed' &&
    s.session_type === type &&
    new Date(s.started_at).toDateString() === new Date().toDateString()
  )
}

const progressPercent = computed(() => {
  if (!currentSession.value || currentSession.value.total_items === 0) return 0
  return Math.round((currentSession.value.completed_items / currentSession.value.total_items) * 100)
})

const flatItems = computed<ItemResult[]>(() => {
  if (!currentSession.value?.templates) return []
  const items: ItemResult[] = []
  for (const tpl of currentSession.value.templates) {
    if (tpl.results) items.push(...tpl.results)
  }
  return items
})

function itemClass(item: ItemResult): string {
  if (isItemDone(item)) return 'is-done'
  if (item.review_status === 'manual_reviewing') return 'is-waiting'
  if (item.review_status === 'manual_rejected') return 'is-rejected'
  return 'is-pending'
}

onMounted(() => init())

async function init() {
  loading.value = true
  try {
    const tplRes = await listTemplates().catch(() => null)
    if (tplRes) templates.value = (tplRes.data as any).data || []

    const sessRes = await listSessions({ page: 1, page_size: 10 }).catch(() => null)
    if (sessRes) {
      recentSessions.value = (sessRes.data as any).data?.items || []
      const active = recentSessions.value.find(s => s.status === 'in_progress')
      if (active) activeSessionInfo.value = active
    }
  } catch {} finally { loading.value = false }
}

async function startTask(type: 'opening' | 'closing') {
  try {
    const res: any = await startSession(type)
    currentSession.value = res.data?.data || res.data
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.message || '启动失败'
    setTimeout(() => errorMsg.value = '', 3000)
  }
}

async function resumeSession() {
  if (!activeSessionInfo.value) return
  const detail = await getSession(activeSessionInfo.value.id)
  currentSession.value = (detail.data as any).data || detail.data
}

function exitToTaskList() {
  currentSession.value = null
  init()
}

function isItemDone(item: ItemResult): boolean {
  return ['passed', 'auto_passed', 'manual_passed'].includes(item.review_status)
}

function onItemClick(item: ItemResult) {
  if (isItemDone(item)) return
  if (item.review_status === 'pending' && item.item_type === 'checkbox') doConfirm(item.id)
}

async function doConfirm(resultId: string) {
  if (!currentSession.value) return
  try {
    await confirmItem(currentSession.value.id, resultId)
    await refreshSession()
  } catch (e: any) {
    errorMsg.value = e?.response?.data?.message || '操作失败'
    setTimeout(() => errorMsg.value = '', 3000)
  }
}

function triggerUpload(itemId: string) { fileInputs[itemId]?.click() }

async function doUpload(itemId: string, e: Event) {
  if (!currentSession.value) return
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    await uploadPhoto(currentSession.value.id, itemId, file)
    await refreshSession()
  } catch (err: any) {
    errorMsg.value = err?.response?.data?.message || '上传失败'
    setTimeout(() => errorMsg.value = '', 3000)
  }
}

async function refreshSession() {
  if (!currentSession.value) return
  try {
    const res = await getSession(currentSession.value.id)
    currentSession.value = (res.data as any).data || res.data
    if (currentSession.value?.status === 'completed') {
      // 完成后等1秒返回任务列表
      setTimeout(() => exitToTaskList(), 1000)
    }
  } catch {}
}

function goHistory() { router.push('/management/butler/history') }
</script>

<style scoped>
.butler-page {
  max-width: 640px;
  margin: 0 auto;
  min-height: 100vh;
  background: #000;
  color: #fff;
  padding: 0 20px calc(64px + 20px);
}

.muted { color: #7A7C80; font-size: 14px; }
.title-lg { font-size: 18px; font-weight: 700; color: #fff; }

.screen-center {
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; min-height: 70vh; gap: 12px; text-align: center;
}

.spinner {
  width: 32px; height: 32px;
  border: 3px solid #222; border-top-color: #FB0079;
  border-radius: 50%; animation: spin 0.7s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* ========== 任务列表模式 ========== */
.task-list-mode { padding-top: 20px; }

.list-header { margin-bottom: 20px; }
.list-header h2 { font-size: 22px; font-weight: 700; margin: 0; }
.list-date { font-size: 13px; color: #555; margin: 2px 0 0; }

.section-label {
  font-size: 12px; color: #555; font-weight: 600;
  margin: 20px 0 8px 4px;
}

.task-card {
  display: flex; justify-content: space-between; align-items: center;
  padding: 16px; background: #0d0d0d;
  border: 1px solid transparent; border-radius: 14px;
  margin-bottom: 8px; cursor: pointer;
  transition: all 0.2s; -webkit-tap-highlight-color: transparent;
}
.task-card:active { transform: scale(0.98); }

.resume-card {
  background: linear-gradient(135deg, rgba(251, 0, 121, 0.1) 0%, rgba(251, 0, 121, 0.03) 100%);
  border-color: rgba(251, 0, 121, 0.2);
}

.done-card { opacity: 0.4; cursor: default; }
.done-card:active { transform: none; }

.task-card-left { display: flex; align-items: center; gap: 14px; }

.task-icon {
  width: 36px; height: 36px; border-radius: 10px;
  display: flex; align-items: center; justify-content: center;
  background: rgba(255, 255, 255, 0.05); color: #666;
}
.task-icon.closing { color: #FB0079; background: rgba(251, 0, 121, 0.08); }
.task-icon.opening { color: #FF9500; background: rgba(255, 149, 0, 0.08); }
.task-icon.progress { color: #FB0079; background: rgba(251, 0, 121, 0.12); }
.task-icon.done { color: #34c759; background: rgba(52, 199, 89, 0.08); }

.task-info { display: flex; flex-direction: column; gap: 2px; }
.task-name { font-size: 15px; font-weight: 600; color: #fff; }
.task-sub { font-size: 12px; color: #666; }
.done-text { color: #888; }

.resume-badge {
  padding: 4px 12px; border-radius: 12px;
  background: #FB0079; color: #fff;
  font-size: 12px; font-weight: 600;
}

.footer-link {
  margin-top: 24px; text-align: center;
  font-size: 13px; color: #444; cursor: pointer; padding: 8px;
}
.footer-link:active { color: #666; }

/* ========== 检查执行模式 ========== */
.check-screen { padding-top: 20px; }

.header-row {
  display: flex; justify-content: space-between;
  align-items: center; margin-bottom: 8px;
}
.header-left { display: flex; align-items: center; gap: 8px; }
.back-btn {
  border: none; background: transparent; color: #666;
  cursor: pointer; padding: 4px; display: flex; align-items: center;
}
.header-title { font-size: 20px; font-weight: 700; margin: 0; }
.header-right { display: flex; align-items: baseline; gap: 2px; }
.big-num { font-size: 28px; font-weight: 800; color: #FB0079; line-height: 1; }
.big-num-total { font-size: 14px; color: #555; font-weight: 600; }

.progress-track {
  height: 3px; background: #1a1a1a;
  border-radius: 2px; margin-bottom: 24px; overflow: hidden;
}
.progress-knob {
  height: 100%; background: linear-gradient(90deg, #FB0079, #FF4090);
  border-radius: 2px; transition: width 0.4s ease;
}

.item-list { display: flex; flex-direction: column; gap: 6px; }

.item {
  display: flex; align-items: center; gap: 14px;
  padding: 16px 14px; background: #0d0d0d;
  border: 1px solid transparent; border-radius: 12px;
  transition: all 0.2s; cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.item:active { transform: scale(0.99); }
.item.is-pending { border-color: rgba(251, 0, 121, 0.15); }
.item.is-done { opacity: 0.4; }
.item.is-waiting { background: rgba(255, 149, 0, 0.05); border-color: rgba(255, 149, 0, 0.15); }
.item.is-rejected { background: rgba(255, 59, 48, 0.05); border-color: rgba(255, 59, 48, 0.2); }

.item-left { flex-shrink: 0; }
.item-index {
  width: 28px; height: 28px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 13px; font-weight: 700; background: #1a1a1a; color: #666;
}
.item-index.is-done { background: #FB0079; color: #fff; }
.item-index.is-waiting { background: rgba(255, 149, 0, 0.2); color: #FF9500; }
.item-index.is-rejected { background: rgba(255, 59, 48, 0.2); color: #FF3B30; }
.item-index.is-pending { background: rgba(251, 0, 121, 0.1); color: #FB0079; }

.item-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 3px; }
.item-name { font-size: 15px; color: #fff; line-height: 1.3; }
.item-tag { font-size: 11px; color: #7A7C80; }
.item-tag.waiting { color: #FF9500; }
.item-tag.rejected { color: #FF3B30; }

.item-right { flex-shrink: 0; display: flex; align-items: center; gap: 8px; }
.btn-do {
  padding: 7px 18px; border: none; border-radius: 16px;
  font-size: 13px; font-weight: 600; cursor: pointer;
  background: #FB0079; color: #fff;
  -webkit-tap-highlight-color: transparent; transition: transform 0.1s;
}
.btn-do:active { transform: scale(0.93); }
.btn-do.outline { background: transparent; color: #FB0079; border: 1px solid #FB0079; }

.thumb { width: 32px; height: 32px; border-radius: 6px; overflow: hidden; flex-shrink: 0; }
.thumb img { width: 100%; height: 100%; object-fit: cover; }

.toast {
  position: fixed; bottom: 90px; left: 50%; transform: translateX(-50%);
  padding: 10px 20px; background: rgba(251, 0, 121, 0.15);
  border: 1px solid rgba(251, 0, 121, 0.3); border-radius: 20px;
  color: #FB0079; font-size: 13px; z-index: 200; max-width: 90%;
  text-align: center; backdrop-filter: blur(10px);
}
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
