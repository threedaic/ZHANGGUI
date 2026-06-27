<template>
  <div class="task-center-page">
    <div class="page-header">
      <h1 class="page-title">任务中心</h1>
    </div>

    <!-- 功能入口（独立区块） -->
    <div class="section-label">功能</div>
    <div class="feature-entries">
      <button class="feature-card" @click="router.push('/daily/butler')">
        <div class="feature-icon">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round">
            <rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/>
            <rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>
          </svg>
        </div>
        <div class="feature-text">
          <span class="feature-name">开闭店检查</span>
          <span class="feature-desc">开店 / 闭店流程清单</span>
        </div>
        <svg class="feature-arrow" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
          <path d="M9 18l6-6-6-6"/>
        </svg>
      </button>
    </div>

    <!-- 我的任务 -->
    <div class="section-label">
      <span>我的任务</span>
      <span v-if="pendingCount > 0" class="section-badge">{{ pendingCount }} 待处理</span>
    </div>

    <!-- 状态筛选（chip 行） -->
    <div class="filter-chips">
      <button
        v-for="opt in filterOptions"
        :key="opt.value"
        class="filter-chip"
        :class="{ active: filter === opt.value }"
        @click="filter = opt.value"
      >{{ opt.label }}</button>
    </div>

    <!-- 任务列表 -->
    <div class="task-list">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="tasks.length === 0" class="empty-state">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none" stroke="#444" stroke-width="1.5">
          <path d="M14 18h20v22H14z" rx="3"/><path d="M19 10v8M29 10v8"/><path d="M14 24h20"/>
        </svg>
        <span>{{ filter ? '没有符合条件的任务' : '暂无任务' }}</span>
      </div>
      <div v-else>
        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-item"
          :class="[`priority-${task.priority}`, `status-${task.status}`]"
          @click="openDetail(task)"
        >
          <div class="task-left">
            <div class="task-priority-dot" :class="task.priority"></div>
            <div class="task-info">
              <span class="task-title">{{ task.title }}</span>
              <span class="task-meta">
                <span v-if="task.due_date" class="meta-tag">截止 {{ task.due_date }}</span>
                <span class="meta-tag">{{ task.task_type_label }}</span>
                <span v-if="task.attachments_count" class="meta-tag">附件 {{ task.attachments_count }}</span>
              </span>
            </div>
          </div>
          <div class="task-right">
            <span class="status-chip" :class="task.status">{{ task.status_label }}</span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="total > pageSize" class="pagination">
        <button :disabled="page <= 1" @click="page--; loadTasks()">上一页</button>
        <span>{{ page }} / {{ Math.ceil(total / pageSize) }}</span>
        <button :disabled="page * pageSize >= total" @click="page++; loadTasks()">下一页</button>
      </div>
    </div>

    <!-- 认领池入口（仅当有可认领任务时显示） -->
    <div v-if="poolCount > 0" class="pool-entry" @click="goPool">
      <div class="pool-left">
        <div class="pool-dot"></div>
        <div class="pool-text">
          <span class="pool-title">有 {{ poolCount }} 个任务可认领</span>
          <span class="pool-desc">点击查看认领池</span>
        </div>
      </div>
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round">
        <path d="M9 18l6-6-6-6"/>
      </svg>
    </div>

    <!-- 认领池抽屉 -->
    <Transition name="slide-up">
      <div v-if="poolOpen" class="detail-overlay" @click.self="poolOpen = false">
        <div class="detail-panel pool-panel">
          <div class="detail-header">
            <h3>认领池（{{ poolTasks.length }}）</h3>
            <button class="close-btn" @click="poolOpen = false">×</button>
          </div>
          <div class="detail-body">
            <div v-if="poolLoading" class="loading-state">加载中...</div>
            <div v-else-if="poolTasks.length === 0" class="empty-state">
              <span>暂无可认领任务</span>
            </div>
            <div v-else>
              <div
                v-for="task in poolTasks"
                :key="task.id"
                class="task-item"
                :class="[`priority-${task.priority}`]"
                @click="openDetail(task)"
              >
                <div class="task-left">
                  <div class="task-priority-dot" :class="task.priority"></div>
                  <div class="task-info">
                    <span class="task-title">{{ task.title }}</span>
                    <span class="task-meta">
                      <span v-if="task.due_date" class="meta-tag">截止 {{ task.due_date }}</span>
                      <span class="meta-tag">{{ task.task_type_label }}</span>
                    </span>
                  </div>
                </div>
                <div class="task-right">
                  <span class="pool-claim-chip">可认领</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>

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

const router = useRouter()
const auth = useAuthStore()

const loading = ref(false)
const tasks = ref<TaskItem[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const filter = ref('')
const pendingCount = ref(0)
const detailTask = ref<any>(null)
const previewPhoto = ref<string | null>(null)

// 执行反馈草稿与保存状态
const noteDraft = ref('')
const noteStatus = ref<'idle' | 'saving' | 'saved'>('idle')
const noteStatusText = computed(() => ({ idle: '', saving: '保存中...', saved: '已保存' }[noteStatus.value]))
const noteStatusClass = computed(() => ({ saving: 'saving', saved: 'saved' }[noteStatus.value] || ''))

// 是否可编辑执行反馈：任务未结束 + 当前用户是执行人/创建人/管理员
const canEditNote = computed(() => {
  if (!detailTask.value) return false
  const t = detailTask.value
  if (t.status === 'completed' || t.status === 'cancelled') return false
  // 待认领的池任务不能编（没执行人）
  if (t.task_type === 'pool' && !t.assignee_id) return false
  const role = auth.role
  const isAdmin = ['boss', 'store_manager', 'system_admin', 'admin'].includes(role)
  return isAdmin || t.assignee_id === auth.info.employee_id || t.created_by === auth.info.user_id
})

// 认领池
const poolCount = ref(0)
const poolOpen = ref(false)
const poolLoading = ref(false)
const poolTasks = ref<TaskItem[]>([])

const filterOptions = [
  { value: '', label: '全部' },
  { value: 'pending', label: '待处理' },
  { value: 'in_progress', label: '进行中' },
  { value: 'completed', label: '已完成' },
]

async function loadTasks() {
  loading.value = true
  try {
    const params: any = { page: page.value, page_size: pageSize }
    if (filter.value) params.status = filter.value
    const res = await taskAPI.myTasks(params)
    tasks.value = res.data.data.items || []
    total.value = res.data.data.total || 0
  } catch {} finally {
    loading.value = false
  }
}

async function loadPendingCount() {
  try {
    const res = await taskAPI.myTasks({ status: 'pending', page: 1, page_size: 1 })
    pendingCount.value = res.data.data.total || 0
  } catch {}
}

async function loadPoolCount() {
  try {
    const res = await taskAPI.pool({ page: 1, page_size: 1 })
    poolCount.value = res.data.data.total || 0
  } catch {}
}

async function openPool() {
  poolOpen.value = true
  poolLoading.value = true
  try {
    const res = await taskAPI.pool({ page: 1, page_size: 50 })
    poolTasks.value = res.data.data.items || []
  } catch {} finally {
    poolLoading.value = false
  }
}

function goPool() {
  openPool()
}

watch(filter, () => {
  page.value = 1
  loadTasks()
})

onMounted(() => {
  loadTasks()
  loadPendingCount()
  loadPoolCount()
})

async function openDetail(task: TaskItem) {
  try {
    const res = await taskAPI.get(task.id)
    detailTask.value = res.data.data
    // 初始化反馈草稿 & 状态
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
  // 内容未变不保存
  if (newText === oldText) return
  noteStatus.value = 'saving'
  try {
    const res = await taskAPI.saveNote(taskId, newText)
    detailTask.value = res.data.data
    noteStatus.value = 'saved'
    // 2 秒后状态归位
    setTimeout(() => {
      if (noteStatus.value === 'saved') noteStatus.value = 'idle'
    }, 2000)
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
    poolOpen.value = false
    loadTasks()
    loadPendingCount()
    loadPoolCount()
  } catch {}
}

async function handleStatus(status: string) {
  if (!detailTask.value) return
  const labels: Record<string, string> = { in_progress: '开始处理', completed: '完成任务' }
  const task = detailTask.value

  if (status === 'completed') {
    // 完成校验：require_photo=true 必须先上传照片
    if (task.require_photo && !task.attachments?.length) {
      ElMessage.warning('此任务要求完成时上传照片，请先上传至少一张照片')
      return
    }
    // 完成校验：require_note=true 必须有反馈（草稿优先）
    if (task.require_note) {
      const draft = noteDraft.value.trim()
      const stored = (task.completion_note || '').trim()
      if (!draft && !stored) {
        ElMessage.warning('请先填写「执行反馈」再完成任务')
        return
      }
      // 草稿与已存不一致时，先把草稿提交
      if (draft && draft !== stored) {
        try {
          await taskAPI.saveNote(task.id, draft)
        } catch {
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
    loadTasks()
    loadPendingCount()
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

/* 认领池入口 */
.pool-entry {
  position: fixed;
  left: 50%;
  transform: translateX(-50%);
  bottom: 76px;
  z-index: 50;
  width: calc(100% - 32px);
  max-width: 568px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: linear-gradient(135deg, #FB0079 0%, #FF6BAA 100%);
  border-radius: 14px;
  cursor: pointer;
  box-shadow: 0 8px 24px rgba(251,0,121,0.3);
  transition: transform 0.2s;
  -webkit-tap-highlight-color: transparent;
}
.pool-entry:active {
  transform: translateX(-50%) scale(0.98);
}
.pool-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.pool-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #fff;
  box-shadow: 0 0 0 4px rgba(255,255,255,0.25);
  flex-shrink: 0;
}
.pool-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}
.pool-title {
  font-size: 14px;
  font-weight: 700;
  color: #fff;
}
.pool-desc {
  font-size: 11px;
  color: rgba(255,255,255,0.85);
}

/* 认领池抽屉 */
.pool-panel .task-item {
  margin-bottom: 8px;
}
.pool-claim-chip {
  font-size: 10px;
  font-weight: 600;
  padding: 3px 8px;
  border-radius: 6px;
  color: #FB0079;
  background: rgba(251,0,121,0.12);
  border: 1px solid rgba(251,0,121,0.25);
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
