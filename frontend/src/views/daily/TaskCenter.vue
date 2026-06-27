<template>
  <div class="task-center-page">
    <div class="page-header">
      <h1 class="page-title">任务中心</h1>
    </div>

    <!-- 类型筛选 chip：全部 / 我的 / 可认领 / 检查单 -->
    <div class="filter-chips">
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        class="filter-chip"
        :class="{ active: filter === opt.value }"
        @click="filter = opt.value"
      >
        {{ opt.label }}
        <span v-if="opt.count !== undefined && opt.count > 0" class="chip-count">{{ opt.count }}</span>
      </button>
    </div>

    <!-- 统一列表：检查单 + 我的任务 + 可认领任务 -->
    <div class="task-list">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="displayItems.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="#444" stroke-width="1.5">
          <path d="M14 18h20v22H14z" rx="3"/><path d="M19 10v8M29 10v8"/><path d="M14 24h20"/>
        </svg>
        <span>{{ filter === 'mine' ? '暂无指派给你的任务' : filter === 'pool' ? '暂无可认领任务' : filter === 'butler' ? '暂无待办检查单' : '暂无任务' }}</span>
      </div>
      <div v-else>
        <div
          v-for="item in displayItems"
          :key="item.uid"
          class="task-item"
          :class="[`priority-${item.priority}`, `kind-${item.kind}`]"
          @click="onItemClick(item)"
        >
          <div class="task-left">
            <div class="task-priority-dot" :class="item.priority"></div>
            <div class="task-info">
              <span class="task-title">{{ item.title }}</span>
              <span class="task-meta">
                <span class="meta-tag kind-tag" :class="item.kind">{{ item.kind_label }}</span>
                <span v-if="item.due_text" class="meta-tag">{{ item.due_text }}</span>
                <span v-if="item.progress_text" class="meta-tag">{{ item.progress_text }}</span>
                <span v-if="item.assignee_name" class="meta-tag">执行人 {{ item.assignee_name }}</span>
              </span>
            </div>
          </div>
          <div class="task-right">
            <span v-if="item.kind === 'pool'" class="status-chip pool">可认领</span>
            <span v-else-if="item.kind === 'butler'" class="status-chip butler">{{ item.status_label }}</span>
            <span v-else class="status-chip" :class="item.status">{{ item.status_label }}</span>
          </div>
        </div>
      </div>

      <!-- 分页（仅我的任务/全部模式生效） -->
      <div v-if="showPagination" class="pagination">
        <button :disabled="page <= 1" @click="page--; loadTasks()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button :disabled="page * pageSize >= total" @click="page++; loadTasks()">下一页</button>
      </div>
    </div>

    <!-- 任务详情弹窗 -->
    <Transition name="slide-up">
      <div v-if="detailTask" class="detail-overlay" @click.self="detailTask = null">
        <div class="detail-panel">
          <div class="detail-header">
            <h3>{{ detailTask.title }}</h3>
            <button class="close-btn" @click="detailTask = null">×</button>
          </div>
          <div class="detail-body">
            <div class="detail-field">
              <span class="field-label">状态</span>
              <span class="status-chip" :class="detailTask.status">{{ detailTask.status_label }}</span>
            </div>
            <div class="detail-field">
              <span class="field-label">优先级</span>
              <span>{{ detailTask.priority_label }}</span>
            </div>
            <div class="detail-field">
              <span class="field-label">类型</span>
              <span>{{ detailTask.task_type_label }}</span>
            </div>
            <div class="detail-field" v-if="detailTask.assignee_name">
              <span class="field-label">指派给</span>
              <span>{{ detailTask.assignee_name }}</span>
            </div>
            <div class="detail-field">
              <span class="field-label">创建人</span>
              <span>{{ detailTask.created_by_name }}</span>
            </div>
            <div class="detail-field" v-if="detailTask.due_date">
              <span class="field-label">截止日期</span>
              <span>{{ detailTask.due_date }}</span>
            </div>
            <div class="detail-field" v-if="detailTask.description">
              <span class="field-label">描述</span>
              <span class="desc-text">{{ detailTask.description }}</span>
            </div>
            <div class="detail-field" v-if="detailTask.require_photo || detailTask.require_note || detailTask.requirements">
              <span class="field-label">完成要求</span>
              <div class="requirement-list">
                <div v-if="detailTask.require_photo" class="req-tag">需上传照片</div>
                <div v-if="detailTask.require_note" class="req-tag">需填写完成说明</div>
                <div v-if="detailTask.requirements" class="req-text">{{ detailTask.requirements }}</div>
              </div>
            </div>
            <div class="detail-field" v-if="detailTask.completion_note && !canEditNote">
              <span class="field-label">完成说明</span>
              <span class="desc-text">{{ detailTask.completion_note }}</span>
            </div>

            <!-- 执行反馈：员工接收任务后即可编辑，失焦自动保存 -->
            <div v-if="canEditNote" class="detail-field">
              <span class="field-label">
                执行反馈
                <span class="note-status" :class="noteStatusClass">{{ noteStatusText }}</span>
              </span>
              <textarea
                v-model="noteDraft"
                class="note-textarea"
                rows="4"
                maxlength="2000"
                placeholder="随时记录执行进度、问题、说明等（失焦自动保存）"
                @blur="saveNote"
              ></textarea>
            </div>

            <!-- 照片 -->
            <div v-if="detailTask.attachments?.length" class="photo-section">
              <span class="field-label">照片</span>
              <div class="photo-grid">
                <div v-for="att in detailTask.attachments" :key="att.id" class="photo-thumb">
                  <img :src="att.file_url" alt="" @click="previewPhoto = att.file_url" />
                </div>
              </div>
            </div>

            <!-- 操作 -->
            <div class="action-bar" v-if="detailTask.status !== 'completed' && detailTask.status !== 'cancelled'">
              <button v-if="detailTask.task_type === 'pool' && !detailTask.assignee_id" class="btn-claim" @click="handleClaim">
                认领任务
              </button>
              <button v-if="canStart(detailTask)" class="btn-start" @click="handleStatus('in_progress')">
                开始处理
              </button>
              <button v-if="canComplete(detailTask)" class="btn-complete" @click="handleStatus('completed')">
                完成任务
              </button>
              <label class="btn-upload">
                上传照片
                <input type="file" accept="image/*" @change="handleUpload" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 照片预览 -->
    <Transition name="fade">
      <div v-if="previewPhoto" class="photo-preview" @click="previewPhoto = null">
        <img :src="previewPhoto" alt="" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { taskAPI, type TaskItem } from '@/api/task'
import { getTodayStatus, type ButlerTodayStatus } from '@/api/butler'

const router = useRouter()
const auth = useAuthStore()

// ============ 数据 ============
type DisplayItem = {
  uid: string
  kind: 'mine' | 'pool' | 'butler'
  kind_label: string
  title: string
  priority: string
  status?: string
  status_label: string
  due_text?: string
  progress_text?: string
  assignee_name?: string
  // 但书：原 task 对象（用于打开详情）
  task_id?: string
  // butler 跳转目标
  butler_session_id?: string | null
  butler_type?: 'opening' | 'closing'
}

const loading = ref(false)
const myTasks = ref<TaskItem[]>([])
const poolTasks = ref<TaskItem[]>([])
const butlerStatus = ref<ButlerTodayStatus | null>(null)
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filter = ref<'' | 'mine' | 'pool' | 'butler'>('')
const detailTask = ref<any>(null)
const previewPhoto = ref<string | null>(null)

// ============ 计数 ============
const pendingCount = computed(() => myTasks.value.filter(t => t.status === 'pending').length)
const poolCount = computed(() => poolTasks.value.length)
const butlerCount = computed(() => butlerStatus.value?.pending?.length || 0)

// ============ 执行反馈草稿与保存状态 ============
const noteDraft = ref('')
const noteStatus = ref<'idle' | 'saving' | 'saved'>('idle')
const noteStatusText = computed(() => ({ idle: '', saving: '保存中...', saved: '已保存' }[noteStatus.value]))
const noteStatusClass = computed(() => ({ saving: 'saving', saved: 'saved' }[noteStatus.value] || ''))

const canEditNote = computed(() => {
  if (!detailTask.value) return false
  const t = detailTask.value
  if (t.status === 'completed' || t.status === 'cancelled') return false
  if (t.task_type === 'pool' && !t.assignee_id) return false
  const role = auth.role
  const isAdmin = ['boss', 'store_manager', 'system_admin', 'admin'].includes(role)
  return isAdmin || t.assignee_id === auth.info.employee_id || t.created_by === auth.info.user_id
})

// ============ chip 筛选 ============
const filterOptions = computed(() => [
  { value: '' as const, label: '全部', count: pendingCount.value + poolCount.value + butlerCount.value },
  { value: 'mine' as const, label: '我的', count: pendingCount.value },
  { value: 'pool' as const, label: '可认领', count: poolCount.value },
  { value: 'butler' as const, label: '检查单', count: butlerCount.value },
])

// ============ 转换：把三类原始数据 → DisplayItem ============
function taskToItem(t: TaskItem, kind: 'mine' | 'pool'): DisplayItem {
  const kindLabelMap = { mine: '指派任务', pool: '认领池' }
  const statusLabelMap: Record<string, string> = {
    pending: '待处理', in_progress: '进行中', completed: '已完成', cancelled: '已取消',
  }
  return {
    uid: `${kind}-${t.id}`,
    kind,
    kind_label: kindLabelMap[kind],
    title: t.title,
    priority: t.priority,
    status: t.status,
    status_label: t.status_label || statusLabelMap[t.status] || t.status,
    due_text: t.due_date ? `截止 ${t.due_date}` : undefined,
    assignee_name: t.assignee_name || undefined,
    task_id: t.id,
  }
}

function butlerToItem(p: ButlerTodayStatus['pending'][number]): DisplayItem {
  const total = p.total || 0
  const completed = p.completed || 0
  return {
    uid: `butler-${p.type}-${p.session_id || 'new'}`,
    kind: 'butler',
    kind_label: p.type === 'opening' ? '开店检查' : '闭店检查',
    title: p.label,
    priority: 'high',
    status_label: total === 0 ? '待开始' : (completed >= total ? '已完成' : '进行中'),
    progress_text: total > 0 ? `${completed}/${total}` : undefined,
    due_text: p.type === 'opening' ? '今日 11:30 前' : '今日 23:30 前',
    butler_session_id: p.session_id,
    butler_type: p.type,
  }
}

// ============ 当前显示列表 ============
const displayItems = computed<DisplayItem[]>(() => {
  const mineItems = myTasks.value.map(t => taskToItem(t, 'mine'))
  const poolItems = poolTasks.value.map(t => taskToItem(t, 'pool'))
  const butlerItems = (butlerStatus.value?.pending || []).map(butlerToItem)

  if (filter.value === 'mine') return mineItems
  if (filter.value === 'pool') return poolItems
  if (filter.value === 'butler') return butlerItems
  // 全部：检查单优先 → 我的 → 可认领
  return [...butlerItems, ...mineItems, ...poolItems]
})

const showPagination = computed(() => filter.value === 'mine' && total.value > pageSize)

// ============ 加载 ============
async function loadMyTasks() {
  try {
    const params: any = { page: page.value, page_size: pageSize }
    const res = await taskAPI.myTasks(params)
    myTasks.value = res.data.data.items || []
    total.value = res.data.data.total || 0
  } catch {}
}

async function loadPool() {
  try {
    const res = await taskAPI.pool({ page: 1, page_size: 50 })
    poolTasks.value = res.data.data.items || []
  } catch {}
}

async function loadButler() {
  try {
    const res = await getTodayStatus()
    if (res.data.code === 0) butlerStatus.value = res.data.data
  } catch {}
}

async function loadAll() {
  loading.value = true
  await Promise.all([loadMyTasks(), loadPool(), loadButler()])
  loading.value = false
}

watch(filter, () => { page.value = 1 })

onMounted(() => {
  loadAll()
})

// ============ 点击行为分流 ============
function onItemClick(item: DisplayItem) {
  if (item.kind === 'butler') {
    // 跳 butler 页（如已有 session 直接进会话；否则进 butler 首页会自动创建）
    router.push('/daily/butler')
    return
  }
  if (item.task_id) openDetail(item.task_id)
}

async function openDetail(taskId: string) {
  try {
    const res = await taskAPI.get(taskId)
    detailTask.value = res.data.data
    noteDraft.value = res.data.data.completion_note || ''
    noteStatus.value = 'idle'
  } catch {}
}

// 失焦自动保存执行反馈
async function saveNote() {
  if (!detailTask.value || !canEditNote.value) return
  const taskId = detailTask.value.id
  const newText = noteDraft.value.trim()
  const oldText = (detailTask.value.completion_note || '').trim()
  if (newText === oldText) return
  noteStatus.value = 'saving'
  try {
    const res = await taskAPI.saveNote(taskId, newText)
    detailTask.value = res.data.data
    noteStatus.value = 'saved'
    setTimeout(() => { if (noteStatus.value === 'saved') noteStatus.value = 'idle' }, 2000)
    loadMyTasks()
  } catch {
    noteStatus.value = 'idle'
  }
}

async function handleClaim() {
  if (!detailTask.value) return
  try {
    await taskAPI.claim(detailTask.value.id)
    ElMessage.success('认领成功')
    detailTask.value = null
    loadMyTasks()
    loadPool()
  } catch {}
}

async function handleStatus(status: string) {
  if (!detailTask.value) return
  const labels: Record<string, string> = { in_progress: '开始处理', completed: '完成任务' }
  const task = detailTask.value

  if (status === 'completed') {
    if (task.require_photo && !task.attachments?.length) {
      ElMessage.warning('此任务要求完成时上传照片，请先上传至少一张照片')
      return
    }
    if (task.require_note) {
      const draft = noteDraft.value.trim()
      const stored = (task.completion_note || '').trim()
      if (!draft && !stored) {
        ElMessage.warning('请先填写「执行反馈」再完成任务')
        return
      }
      if (draft && draft !== stored) {
        try { await taskAPI.saveNote(task.id, draft) }
        catch {
          ElMessage.error('保存反馈失败，请重试')
          return
        }
      }
    }
    try {
      await ElMessageBox.confirm(`确定${labels[status]}吗？`, '确认')
    } catch { return }
  } else {
    try {
      await ElMessageBox.confirm(`确定${labels[status]}吗？`, '确认')
    } catch { return }
  }

  try {
    await taskAPI.updateStatus(task.id, status)
    ElMessage.success('操作成功')
    detailTask.value = null
    loadMyTasks()
  } catch {}
}

function canStart(task: any): boolean {
  return task.status === 'pending' && task.assignee_id
}

function canComplete(task: any): boolean {
  return task.status === 'in_progress' || (task.status === 'pending' && task.assignee_id)
}

async function handleUpload(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !detailTask.value) return
  try {
    await taskAPI.uploadAttachment(detailTask.value.id, file, 'progress')
    ElMessage.success('上传成功')
    const res = await taskAPI.get(detailTask.value.id)
    detailTask.value = res.data.data
  } catch {}
  ;(e.target as HTMLInputElement).value = ''
}
</script>

<style scoped lang="scss">
.task-center-page {
  padding: 16px;
  padding-bottom: 100px;
  max-width: 600px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 16px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}

/* 区块标题 */
.section-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 13px;
  font-weight: 600;
  color: #888;
  letter-spacing: 0.5px;
  margin: 20px 0 10px;
}
.section-label:first-of-type {
  margin-top: 0;
}
.section-badge {
  font-size: 11px;
  font-weight: 600;
  color: #FB0079;
  background: rgba(251,0,121,0.1);
  padding: 3px 8px;
  border-radius: 10px;
}

/* 功能入口卡片 */
.feature-entries {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 8px;
}
.feature-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: #141414;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
  text-align: left;
}
.feature-card:active {
  transform: scale(0.98);
}
.feature-icon {
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(251,0,121,0.1);
  color: #FB0079;
  border-radius: 10px;
  flex-shrink: 0;
}
.feature-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
  min-width: 0;
}
.feature-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}
.feature-desc {
  font-size: 11px;
  color: #666;
}
.feature-arrow {
  color: #555;
  flex-shrink: 0;
}

/* 状态筛选 chip */
.filter-chips {
  display: flex;
  gap: 6px;
  margin-bottom: 12px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
  &::-webkit-scrollbar {
    display: none;
  }
}
.filter-chip {
  flex-shrink: 0;
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 6px 14px;
  font-size: 12px;
  font-weight: 500;
  color: #888;
  background: #141414;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 16px;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.filter-chip.active {
  color: #fff;
  background: #FB0079;
  border-color: #FB0079;
}
.chip-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 16px;
  height: 16px;
  padding: 0 4px;
  font-size: 10px;
  font-weight: 700;
  color: #fff;
  background: rgba(255,255,255,0.18);
  border-radius: 8px;
}
.filter-chip:not(.active) .chip-count {
  background: rgba(251,0,121,0.25);
  color: #FF6BAA;
}

/* 类型标签：mine / pool / butler 三色 */
.kind-tag {
  font-weight: 600;
}
.kind-tag.mine {
  color: #FFB02E;
  background: rgba(255,176,46,0.1);
}
.kind-tag.pool {
  color: #FB0079;
  background: rgba(251,0,121,0.1);
}
.kind-tag.butler {
  color: #4ADE80;
  background: rgba(74,222,128,0.1);
}

/* 检查单卡片样式微调 */
.kind-butler .task-priority-dot {
  background: #4ADE80 !important;
}

/* 状态徽章变体：pool / butler */
.status-chip.pool {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  color: #FB0079;
  background: rgba(251,0,121,0.12);
  border: 1px solid rgba(251,0,121,0.25);
}
.status-chip.butler {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  color: #4ADE80;
  background: rgba(74,222,128,0.12);
  border: 1px solid rgba(74,222,128,0.25);
}

/* Task list */
.task-list {
  min-height: 200px;
}
.task-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px;
  margin-bottom: 8px;
  background: #141414;
  border: 1px solid rgba(255,255,255,0.06);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.task-item:active {
  transform: scale(0.98);
}
.task-item.priority-high {
  border-left: 3px solid #ff3b30;
}
.task-item.status-completed {
  opacity: 0.5;
}

.task-left {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.task-priority-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.task-priority-dot.high { background: #ff3b30; }
.task-priority-dot.medium { background: #ff9500; }
.task-priority-dot.low { background: #34c759; }

.task-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}
.task-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.task-meta {
  display: flex;
  gap: 8px;
}
.meta-tag {
  font-size: 10px;
  color: #666;
}

.task-right {
  flex-shrink: 0;
}
.status-chip {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
}
.status-chip.pending {
  color: #ff9500;
  background: rgba(255,149,0,0.1);
}
.status-chip.in_progress {
  color: #007aff;
  background: rgba(0,122,255,0.1);
}
.status-chip.completed {
  color: #34c759;
  background: rgba(52,199,89,0.1);
}

/* Empty & Loading */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 48px 0;
  color: #555;
  font-size: 13px;
}
.loading-state {
  text-align: center;
  padding: 48px 0;
  color: #666;
}

/* Pagination */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 16px 0;
}
.pagination button {
  padding: 6px 14px;
  font-size: 12px;
  color: #fff;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 6px;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.pagination span {
  font-size: 12px;
  color: #888;
}

/* Detail overlay */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.6);
  z-index: 200;
  display: flex;
  align-items: flex-end;
}
.detail-panel {
  width: 100%;
  max-width: 600px;
  margin: 0 auto;
  max-height: 80vh;
  background: #141414;
  border-radius: 16px 16px 0 0;
  overflow-y: auto;
}
.detail-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px;
  border-bottom: 1px solid rgba(255,255,255,0.06);
  position: sticky;
  top: 0;
  background: #141414;
  z-index: 1;
}
.detail-header h3 {
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  margin: 0;
}
.close-btn {
  width: 28px;
  height: 28px;
  font-size: 18px;
  color: #888;
  background: rgba(255,255,255,0.06);
  border: none;
  border-radius: 50%;
  cursor: pointer;
}
.detail-body {
  padding: 16px;
}
.detail-field {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 13px;
  color: #ccc;
}
.field-label {
  font-size: 12px;
  color: #666;
  min-width: 56px;
  flex-shrink: 0;
}
.desc-text {
  font-size: 12px;
  color: #aaa;
  white-space: pre-wrap;
}
.requirement-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  flex: 1;
}
.req-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 11px;
  color: #FF6BAA;
  background: rgba(251, 0, 121, 0.1);
  border: 1px solid rgba(251, 0, 121, 0.25);
  border-radius: 12px;
  width: fit-content;
}
.req-text {
  font-size: 12px;
  color: #aaa;
  line-height: 1.5;
  white-space: pre-wrap;
}

/* 执行反馈 textarea */
.note-textarea {
  width: 100%;
  min-height: 90px;
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  line-height: 1.55;
  font-family: inherit;
  resize: vertical;
  outline: none;
  transition: border-color 0.15s, background 0.15s;
  box-sizing: border-box;
}
.note-textarea::placeholder {
  color: #555;
}
.note-textarea:focus {
  border-color: #FB0079;
  background: rgba(255, 255, 255, 0.06);
}
.note-status {
  margin-left: 8px;
  font-size: 11px;
  font-weight: 400;
}
.note-status.saving {
  color: #FFB02E;
}
.note-status.saved {
  color: #4ADE80;
}

/* Photo */
.photo-section {
  margin-top: 12px;
}
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 8px;
}
.photo-thumb {
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}
.photo-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Action bar */
.action-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.action-bar button,
.action-bar label {
  padding: 10px 18px;
  font-size: 13px;
  font-weight: 600;
  border-radius: 10px;
  cursor: pointer;
  border: none;
  transition: all 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.action-bar button:active,
.action-bar label:active {
  transform: scale(0.95);
}
.btn-claim {
  color: #fff;
  background: #007aff;
}
.btn-start {
  color: #fff;
  background: #007aff;
}
.btn-complete {
  color: #fff;
  background: #34c759;
}
.btn-upload {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  user-select: none;
  color: #888;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1) !important;
  position: relative;
  transition: background 0.15s, color 0.15s;
}
.btn-upload:hover {
  background: rgba(255,255,255,0.1);
  color: #fff;
}
.btn-upload input[type="file"] {
  position: absolute;
  inset: 0;
  opacity: 0;
  cursor: pointer;
}

/* Photo preview */
.photo-preview {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.9);
  z-index: 300;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}
.photo-preview img {
  max-width: 90%;
  max-height: 90%;
  border-radius: 8px;
}

/* Transitions */
.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.25s ease;
}
.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
}
.slide-up-enter-from .detail-panel,
.slide-up-leave-to .detail-panel {
  transform: translateY(100%);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
