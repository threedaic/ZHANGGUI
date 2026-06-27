<template>
  <div class="butler-manage-page">
    <div class="page-header">
      <h1 class="page-title">开闭店管理</h1>
    </div>
    <p class="page-tip">店长配置检查单、查看员工执行进度与历史记录</p>

    <!-- 当前进行中的会话 -->
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="activeSession" class="active-session-card" @click="goToSession(activeSession.id)">
      <div class="card-header">
        <span class="badge" :class="activeSession.session_type">
          {{ activeSession.session_type === 'closing' ? '闭店进行中' : '开店进行中' }}
        </span>
        <span class="progress-text">{{ activeSession.completed_items }}/{{ activeSession.total_items }}</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
      <div class="card-footer">
        <span class="card-tip">点击查看执行详情</span>
        <span class="card-time">开始于 {{ formatTime(activeSession.started_at) }}</span>
      </div>
    </div>

    <!-- 未配置提示 -->
    <div v-else-if="!hasAnyTemplate" class="empty-config-card">
      <div class="empty-icon">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
          <rect x="8" y="6" width="32" height="36" rx="3"/>
          <line x1="16" y1="16" x2="32" y2="16"/>
          <line x1="16" y1="24" x2="32" y2="24"/>
          <line x1="16" y1="32" x2="24" y2="32"/>
        </svg>
      </div>
      <div class="empty-text">
        <div class="empty-title">本店尚未配置开闭店检查单</div>
        <div class="empty-desc">请先配置开店/闭店检查项，员工才能开始执行检查</div>
      </div>
      <button class="btn-setup" @click="goConfig">立即配置</button>
    </div>

    <!-- 管理功能入口 -->
    <div class="section-title">配置与管理</div>
    <div class="card-grid">
      <button class="func-card" @click="goHistory">
        <span class="card-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
            <circle cx="14" cy="14" r="10"/>
            <path d="M14 8v6l4 2"/>
          </svg>
        </span>
        <span class="card-label">历史记录</span>
        <span class="card-desc">查看所有检查会话</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
        </span>
      </button>

      <button v-if="isBoss" class="func-card" @click="goDashboard">
        <span class="card-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
            <rect x="3" y="3" width="10" height="10" rx="2"/>
            <rect x="15" y="3" width="10" height="10" rx="2"/>
            <rect x="3" y="15" width="10" height="10" rx="2"/>
            <rect x="15" y="15" width="10" height="10" rx="2"/>
          </svg>
        </span>
        <span class="card-label">数据看板</span>
        <span class="card-desc">多店开闭店概览</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
        </span>
      </button>

      <button class="func-card" @click="goConfig">
        <span class="card-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
            <path d="M4 14h20M14 4v20"/>
          </svg>
        </span>
        <span class="card-label">检查单配置</span>
        <span class="card-desc">修改检查项（底部入口）</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
        </span>
      </button>

      <button class="func-card" @click="goWecomBot">
        <span class="card-icon">
          <svg width="28" height="28" viewBox="0 0 28 28" fill="none" stroke="#FB0079" stroke-width="1.5" stroke-linecap="round">
            <path d="M14 4c-5 0-9 3.5-9 8 0 2.5 1.3 4.7 3.3 6.2L7 22l3.7-2c1 .3 2.1.5 3.3.5 5 0 9-3.5 9-8s-4-8.5-9-8.5z"/>
            <circle cx="10" cy="12" r="1" fill="#FB0079"/>
            <circle cx="18" cy="12" r="1" fill="#FB0079"/>
          </svg>
        </span>
        <span class="card-label">推送设置</span>
        <span class="card-desc">{{ botEnabled ? '已开启 · 点击配置' : '未开启 · 点击开启' }}</span>
        <span class="card-arrow">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
        </span>
      </button>
    </div>

    <!-- 执行人顺位配置 -->
    <div class="section-title">执行人顺位</div>
    <div class="assignee-config-card">
      <div class="assignee-tabs">
        <button
          class="assignee-tab"
          :class="{ active: assigneeTab === 'opening' }"
          @click="assigneeTab = 'opening'"
        >开店检查</button>
        <button
          class="assignee-tab"
          :class="{ active: assigneeTab === 'closing' }"
          @click="assigneeTab = 'closing'"
        >闭店检查</button>
      </div>

      <div v-if="assigneeLoading" class="assignee-empty">加载中...</div>

      <div v-else-if="assigneeList.length === 0" class="assignee-empty">
        还没配置顺位，请添加执行人
      </div>

      <ul v-else class="assignee-list">
        <li v-for="(item, idx) in assigneeList" :key="item.employee_id" class="assignee-row">
          <span class="assignee-priority">{{ idx + 1 }}</span>
          <div class="assignee-info">
            <span class="assignee-name">{{ item.employee_name }}</span>
            <span class="assignee-role">{{ roleLabel(item.employee_role) }}</span>
            <span v-if="idx === 0" class="assignee-default">默认</span>
            <span v-else class="assignee-fallback">请假时顺延</span>
          </div>
          <div class="assignee-actions">
            <button
              v-if="idx > 0"
              class="icon-btn"
              title="上移"
              @click="moveAssignee(idx, -1)"
            >↑</button>
            <button
              v-if="idx < assigneeList.length - 1"
              class="icon-btn"
              title="下移"
              @click="moveAssignee(idx, 1)"
            >↓</button>
            <button
              class="icon-btn danger"
              title="移除"
              @click="removeAssignee(idx)"
            >×</button>
          </div>
        </li>
      </ul>

      <div class="assignee-add">
        <select v-model="addEmployeeId" class="assignee-select">
          <option value="">+ 添加顺位执行人</option>
          <option
            v-for="emp in availableEmployees"
            :key="emp.employee_id"
            :value="emp.employee_id"
          >{{ emp.name }}（{{ roleLabel(emp.role) }}）</option>
        </select>
        <button
          v-if="addEmployeeId"
          class="btn-add"
          @click="addAssignee"
        >添加</button>
      </div>

      <button
        v-if="assigneeList.length > 0"
        class="btn-save"
        :disabled="assigneeSaving"
        @click="saveAssignee"
      >{{ assigneeSaving ? '保存中...' : '保存顺位配置' }}</button>
    </div>

    <!-- 最近会话列表 -->
    <div class="section-title">最近检查</div>
    <div v-if="recentSessions.length === 0" class="empty-list">暂无检查记录</div>
    <div v-else class="session-list">
      <div
        v-for="s in recentSessions"
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
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { listTemplates, listSessions, listAssigneeRules, saveAssigneeRules, listAssignableEmployees } from '@/api/butler'
import type { SessionDetail, ChecklistTemplate, AssigneeRule, AssignableEmployee } from '@/api/butler'
import { useAuthStore } from '@/stores/auth'
import apiClient from '@/api/client'

const router = useRouter()
const auth = useAuthStore()

const loading = ref(true)
const templates = ref<ChecklistTemplate[]>([])
const activeSession = ref<SessionDetail | null>(null)
const recentSessions = ref<SessionDetail[]>([])
const botEnabled = ref(false)

// 执行人顺位
const assigneeTab = ref<'opening' | 'closing'>('opening')
const assigneeLoading = ref(false)
const assigneeSaving = ref(false)
const assigneeList = ref<AssigneeRule[]>([])
const allEmployees = ref<AssignableEmployee[]>([])
const addEmployeeId = ref('')

const isBoss = computed(() => auth.info.role === 'boss')
const hasAnyTemplate = computed(() => templates.value.length > 0)

// 过滤可选员工：已配置的不出现在下拉
const availableEmployees = computed(() => {
  const usedIds = new Set(assigneeList.value.map(a => a.employee_id))
  return allEmployees.value.filter(e => !usedIds.has(e.employee_id))
})

const ROLE_LABELS: Record<string, string> = {
  boss: '老板',
  store_manager: '店长',
  accountant: '财务',
  bar_manager: '吧台主管',
  service_manager: '服务主管',
  kitchen_manager: '厨房主管',
  staff: '员工',
}

function roleLabel(role: string): string {
  return ROLE_LABELS[role] || role
}

const progressPercent = computed(() => {
  if (!activeSession.value || activeSession.value.total_items === 0) return 0
  return Math.round((activeSession.value.completed_items / activeSession.value.total_items) * 100)
})

onMounted(() => {
  loadData()
  loadAssigneeData()
})

async function loadData() {
  loading.value = true
  try {
    const [tplRes, sessRes, settingsRes] = await Promise.all([
      listTemplates().catch(() => null),
      listSessions({ page: 1, page_size: 10 }).catch(() => null),
      apiClient.get('/stores/settings').catch(() => null),
    ])
    if (tplRes) {
      templates.value = (tplRes.data as any).data || (tplRes.data as any) || []
    }
    if (sessRes) {
      const items = (sessRes.data as any).data?.items || (sessRes.data as any).items || []
      recentSessions.value = items
      const active = items.find((s: SessionDetail) => s.status === 'in_progress')
      if (active) activeSession.value = active
    }
    if (settingsRes) {
      const settingsData = (settingsRes.data as any).data || (settingsRes.data as any)
      botEnabled.value = !!settingsData?.wecom_bot_enabled
    }
  } catch (e) {
    console.error('[ButlerManage] loadData failed:', e)
  } finally {
    loading.value = false
  }
}

// 切换 tab 时重新加载顺位
watch(assigneeTab, () => { loadAssigneeRules() })

async function loadAssigneeData() {
  assigneeLoading.value = true
  try {
    const [empRes] = await Promise.all([
      listAssignableEmployees().catch(() => null),
    ])
    if (empRes) {
      allEmployees.value = (empRes.data as any).data || []
    }
    await loadAssigneeRules()
  } finally {
    assigneeLoading.value = false
  }
}

async function loadAssigneeRules() {
  try {
    const res = await listAssigneeRules(assigneeTab.value)
    assigneeList.value = ((res.data as any).data || []) as AssigneeRule[]
  } catch {
    assigneeList.value = []
  }
}

function moveAssignee(idx: number, delta: number) {
  const newIdx = idx + delta
  if (newIdx < 0 || newIdx >= assigneeList.value.length) return
  const arr = [...assigneeList.value]
  ;[arr[idx], arr[newIdx]] = [arr[newIdx], arr[idx]]
  assigneeList.value = arr
}

function removeAssignee(idx: number) {
  assigneeList.value = assigneeList.value.filter((_, i) => i !== idx)
}

function addAssignee() {
  if (!addEmployeeId.value) return
  const emp = allEmployees.value.find(e => e.employee_id === addEmployeeId.value)
  if (!emp) return
  assigneeList.value.push({
    rule_id: '',
    session_type: assigneeTab.value,
    employee_id: emp.employee_id,
    employee_name: emp.name,
    employee_role: emp.role,
    priority: assigneeList.value.length + 1,
    is_active: true,
  })
  addEmployeeId.value = ''
}

async function saveAssignee() {
  if (assigneeList.value.length === 0) {
    ElMessage.warning('请至少添加一个执行人')
    return
  }
  assigneeSaving.value = true
  try {
    const items = assigneeList.value.map((a, idx) => ({
      employee_id: a.employee_id,
      priority: idx + 1,
    }))
    await saveAssigneeRules(assigneeTab.value, items)
    ElMessage.success('顺位保存成功')
    await loadAssigneeRules()
  } catch (e) {
    ElMessage.error('保存失败')
    console.error(e)
  } finally {
    assigneeSaving.value = false
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
  router.push(`/management/butler/session/${id}`)
}

function goConfig() {
  router.push('/management/butler/config')
}

function goHistory() {
  router.push('/management/butler/history')
}

function goDashboard() {
  router.push('/management/butler/dashboard')
}

function goAIConfig() {
  router.push('/settings/ai-config')
}

function goWecomBot() {
  router.push('/settings/notification')
}
</script>

<style scoped>
.butler-manage-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.page-tip {
  font-size: 12px;
  color: #7A7C80;
  margin: 0 0 20px;
}

.loading {
  text-align: center;
  padding: 24px;
  color: #7A7C80;
  font-size: 13px;
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

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-tip {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.5);
}

.card-time {
  font-size: 11px;
  color: #7A7C80;
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

/* 未配置卡片 */
.empty-config-card {
  background: #111111;
  border: 1px dashed #FB0079;
  border-radius: 12px;
  padding: 24px 16px;
  margin-bottom: 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
}

.empty-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.empty-text {
  text-align: center;
}

.empty-title {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.empty-desc {
  font-size: 12px;
  color: #7A7C80;
}

.btn-setup {
  padding: 8px 20px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

/* 功能卡片 */
.section-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 13px;
  font-weight: 500;
  color: #7A7C80;
  margin: 0 0 12px 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.card-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
  margin-bottom: 20px;
}

.func-card {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  padding: 16px 14px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s;
  position: relative;
  text-align: left;
}

.func-card:hover {
  border-color: #FB0079;
}

.card-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  margin-bottom: 4px;
}

.card-label {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.card-desc {
  font-size: 11px;
  color: #7A7C80;
}

.card-arrow {
  position: absolute;
  top: 12px;
  right: 10px;
  display: flex;
  align-items: center;
}

/* 会话列表 */
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

/* ========== 执行人顺位配置 ========== */
.assignee-config-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 20px;
}

.assignee-tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #2A2A2A;
}

.assignee-tab {
  flex: 1;
  padding: 8px 12px;
  font-size: 13px;
  font-weight: 600;
  color: #7A7C80;
  background: transparent;
  border: 1px solid #2A2A2A;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.assignee-tab.active {
  color: #FFFFFF;
  background: rgba(251, 0, 121, 0.1);
  border-color: #FB0079;
}

.assignee-empty {
  text-align: center;
  padding: 20px 0;
  color: #7A7C80;
  font-size: 13px;
}

.assignee-list {
  list-style: none;
  padding: 0;
  margin: 0 0 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.assignee-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #181818;
  border: 1px solid #2A2A2A;
  border-radius: 8px;
}

.assignee-priority {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  font-size: 12px;
  font-weight: 700;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
  border-radius: 50%;
  flex-shrink: 0;
}

.assignee-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  min-width: 0;
}

.assignee-name {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.assignee-role {
  font-size: 11px;
  color: #7A7C80;
}

.assignee-default {
  font-size: 10px;
  font-weight: 700;
  color: #4ADE80;
  background: rgba(74, 222, 128, 0.1);
  padding: 2px 6px;
  border-radius: 4px;
}

.assignee-fallback {
  font-size: 10px;
  color: #FFB02E;
  background: rgba(255, 176, 46, 0.08);
  padding: 2px 6px;
  border-radius: 4px;
}

.assignee-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.icon-btn {
  width: 28px;
  height: 28px;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  background: #222222;
  border: 1px solid #333333;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.icon-btn:hover {
  background: #2A2A2A;
  border-color: #FB0079;
}

.icon-btn.danger:hover {
  border-color: #FF3B30;
  color: #FF3B30;
}

.assignee-add {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}

.assignee-select {
  flex: 1;
  padding: 10px 12px;
  font-size: 13px;
  color: #FFFFFF;
  background: #181818;
  border: 1px solid #2A2A2A;
  border-radius: 8px;
  outline: none;
  cursor: pointer;
}

.assignee-select:focus {
  border-color: #FB0079;
}

.btn-add {
  padding: 10px 16px;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  cursor: pointer;
}

.btn-save {
  width: 100%;
  padding: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #FFFFFF;
  background: linear-gradient(135deg, #FB0079, #ff3d9a);
  border: none;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-save:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-save:not(:disabled):active {
  transform: scale(0.98);
}
</style>
