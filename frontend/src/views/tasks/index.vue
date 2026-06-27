<template>
  <div class="tasks-page">
    <div class="page-header">
      <h1 class="page-title">任务管理</h1>
      <span class="page-subtitle">分配 · 跟踪 · 完成</span>
    </div>

    <!-- Tab 切换 -->
    <div class="tabs">
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

    <!-- 新建任务 -->
    <div v-if="isManager" class="create-section">
      <button class="create-btn" @click="showCreate = !showCreate">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
        新建任务
      </button>
    </div>

    <!-- 新建表单 -->
    <Transition name="slide">
      <div v-if="showCreate" class="create-form">
        <div class="form-group">
          <label>任务标题</label>
          <input v-model="newTask.title" placeholder="如：清理后厨冰箱" maxlength="200" />
        </div>
        <div class="form-group">
          <label>任务描述（可选）</label>
          <textarea v-model="newTask.description" placeholder="补充说明..." rows="2" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>类型</label>
            <div class="radio-group">
              <button :class="{ selected: newTask.task_type === 'direct' }" @click="newTask.task_type = 'direct'">指派</button>
              <button :class="{ selected: newTask.task_type === 'pool' }" @click="newTask.task_type = 'pool'">认领</button>
            </div>
          </div>
          <div class="form-group">
            <label>优先级</label>
            <div class="radio-group">
              <button :class="{ selected: newTask.priority === 'high' }" @click="newTask.priority = 'high'">紧急</button>
              <button :class="{ selected: newTask.priority === 'medium' }" @click="newTask.priority = 'medium'">普通</button>
              <button :class="{ selected: newTask.priority === 'low' }" @click="newTask.priority = 'low'">低</button>
            </div>
          </div>
        </div>
        <div v-if="newTask.task_type === 'direct'" class="form-group">
          <label>指派给</label>
          <select v-model="newTask.assignee_id">
            <option value="">请选择员工</option>
            <option v-for="emp in employees" :key="emp.id" :value="emp.id">
              {{ emp.name }}（{{ emp.role_label }}）
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>截止日期（可选）</label>
          <input type="date" v-model="newTask.due_date" />
        </div>
        <div class="form-group">
          <label>完成要求</label>
          <div class="checkbox-group">
            <label class="checkbox-item">
              <input type="checkbox" v-model="newTask.require_photo" />
              <span>需上传照片</span>
            </label>
            <label class="checkbox-item">
              <input type="checkbox" v-model="newTask.require_note" />
              <span>需填写完成说明</span>
            </label>
          </div>
          <textarea v-model="newTask.requirements" placeholder="完成要求说明（可选），如：清洁后拍照上传并说明使用的清洁剂" rows="2" class="mt-8" />
        </div>
        <div class="form-actions">
          <button class="btn-cancel" @click="showCreate = false">取消</button>
          <button class="btn-submit" :disabled="!newTask.title" @click="handleCreate">创建任务</button>
        </div>
      </div>
    </Transition>

    <!-- 任务列表 -->
    <div v-if="activeTab !== 'templates'" class="task-list">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="#555" stroke-width="1.5">
            <path d="M9 11h22v18H9z" rx="2"/><path d="M15 7v4M25 7v4"/><path d="M13 17h14M13 23h8"/>
          </svg>
        </div>
        <span>{{ activeTab === 'pool' ? '暂无可认领的任务' : '暂无任务' }}</span>
      </div>
      <div v-else>
        <div
          v-for="task in tasks"
          :key="task.id"
          class="task-card"
          :class="[`priority-${task.priority}`, `status-${task.status}`]"
          @click="openDetail(task)"
        >
          <div class="task-top">
            <span class="task-type-badge">{{ task.task_type_label }}</span>
            <span class="task-status-badge" :class="task.status">{{ task.status_label }}</span>
          </div>
          <div class="task-title">{{ task.title }}</div>
          <div class="task-meta">
            <span v-if="task.assignee_name">执行人 {{ task.assignee_name }}</span>
            <span v-else-if="task.task_type === 'pool'">待认领</span>
            <span v-if="task.due_date">截止 {{ task.due_date }}</span>
            <span v-if="task.attachments_count" class="att-count">附件 {{ task.attachments_count }}</span>
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

    <!-- 周期模板 -->
    <div v-if="activeTab === 'templates'" class="template-list">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="templates.length === 0" class="empty-state">
        <div class="empty-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="#555" stroke-width="1.5">
            <circle cx="20" cy="20" r="14"/><path d="M20 12v8l5 3"/>
          </svg>
        </div>
        <span>暂无周期模板</span>
        <span class="empty-hint">创建模板可自动生成周期任务</span>
      </div>
      <div v-else>
        <div v-for="tpl in templates" :key="tpl.id" class="tpl-card">
          <div class="tpl-top">
            <span class="tpl-recurrence">{{ tpl.recurrence_type_label }}</span>
            <span class="tpl-status" :class="{ enabled: tpl.enabled }">{{ tpl.enabled ? '已启用' : '已停用' }}</span>
          </div>
          <div class="tpl-title">{{ tpl.title }}</div>
          <div class="tpl-meta">
            <span>执行人 {{ tpl.assignee_name }}</span>
            <span v-if="tpl.due_time">截止 {{ tpl.due_time }}</span>
          </div>
          <div class="tpl-actions">
            <button @click.stop="handleToggleTemplate(tpl)">{{ tpl.enabled ? '停用' : '启用' }}</button>
            <button class="danger" @click.stop="handleDeleteTemplate(tpl)">删除</button>
          </div>
        </div>
      </div>

      <!-- 新建模板 -->
      <div v-if="isManager" class="create-section" style="margin-top: 16px;">
        <button class="create-btn" @click="showCreateTemplate = !showCreateTemplate">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M7 2v10M2 7h10" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"/>
          </svg>
          新建周期模板
        </button>
      </div>

      <Transition name="slide">
        <div v-if="showCreateTemplate" class="create-form">
          <div class="form-group">
            <label>模板标题</label>
            <input v-model="newTpl.title" placeholder="如：每周大扫除" maxlength="200" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label>周期</label>
              <div class="radio-group">
                <button :class="{ selected: newTpl.recurrence_type === 'daily' }" @click="newTpl.recurrence_type = 'daily'">每天</button>
                <button :class="{ selected: newTpl.recurrence_type === 'weekly' }" @click="newTpl.recurrence_type = 'weekly'">每周</button>
                <button :class="{ selected: newTpl.recurrence_type === 'monthly' }" @click="newTpl.recurrence_type = 'monthly'">每月</button>
              </div>
            </div>
            <div class="form-group">
              <label>优先级</label>
              <div class="radio-group">
                <button :class="{ selected: newTpl.priority === 'high' }" @click="newTpl.priority = 'high'">紧急</button>
                <button :class="{ selected: newTpl.priority === 'medium' }" @click="newTpl.priority = 'medium'">普通</button>
                <button :class="{ selected: newTpl.priority === 'low' }" @click="newTpl.priority = 'low'">低</button>
              </div>
            </div>
          </div>
          <div class="form-group">
            <label>执行人</label>
            <select v-model="newTpl.assignee_id">
              <option value="">请选择员工</option>
              <option v-for="emp in employees" :key="emp.id" :value="emp.id">
                {{ emp.name }}（{{ emp.role_label }}）
              </option>
            </select>
          </div>
          <div class="form-group">
            <label>截止时间（可选）</label>
            <input type="time" v-model="newTpl.due_time" />
          </div>
          <div class="form-group" v-if="newTpl.recurrence_type === 'weekly'">
            <label>每周几</label>
            <div class="radio-group">
              <button v-for="(d, i) in ['日','一','二','三','四','五','六']" :key="i"
                :class="{ selected: weeklyDay === i }"
                @click="weeklyDay = i">{{ d }}</button>
            </div>
          </div>
          <div class="form-group" v-if="newTpl.recurrence_type === 'monthly'">
            <label>每月几号</label>
            <input type="number" v-model.number="monthlyDay" min="1" max="31" placeholder="1-31" />
          </div>
          <div class="form-group">
            <label>完成要求</label>
            <div class="checkbox-group">
              <label class="checkbox-item">
                <input type="checkbox" v-model="newTpl.require_photo" />
                <span>需上传照片</span>
              </label>
              <label class="checkbox-item">
                <input type="checkbox" v-model="newTpl.require_note" />
                <span>需填写完成说明</span>
              </label>
            </div>
            <textarea v-model="newTpl.requirements" placeholder="完成要求说明（可选）" rows="2" class="mt-8" />
          </div>
          <div class="form-actions">
            <button class="btn-cancel" @click="showCreateTemplate = false">取消</button>
            <button class="btn-submit" :disabled="!newTpl.title || !newTpl.assignee_id" @click="handleCreateTemplate">创建模板</button>
          </div>
        </div>
      </Transition>
    </div>

    <!-- 任务详情弹窗 -->
    <Transition name="slide">
      <div v-if="detailTask" class="detail-overlay" @click.self="detailTask = null">
        <div class="detail-panel">
          <div class="detail-header">
            <h2>{{ detailTask.title }}</h2>
            <button class="close-btn" @click="detailTask = null">×</button>
          </div>
          <div class="detail-body">
            <div class="detail-row">
              <span class="detail-label">状态</span>
              <span class="task-status-badge" :class="detailTask.status">{{ detailTask.status_label }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">优先级</span>
              <span>{{ detailTask.priority_label }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">类型</span>
              <span>{{ detailTask.task_type_label }}</span>
            </div>
            <div class="detail-row" v-if="detailTask.assignee_name">
              <span class="detail-label">执行人</span>
              <span>{{ detailTask.assignee_name }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">创建人</span>
              <span>{{ detailTask.created_by_name }}</span>
            </div>
            <div class="detail-row" v-if="detailTask.due_date">
              <span class="detail-label">截止日期</span>
              <span>{{ detailTask.due_date }}</span>
            </div>
            <div class="detail-row" v-if="detailTask.description">
              <span class="detail-label">描述</span>
              <span class="detail-desc">{{ detailTask.description }}</span>
            </div>
            <div class="detail-row" v-if="detailTask.require_photo || detailTask.require_note || detailTask.requirements">
              <span class="detail-label">完成要求</span>
              <div class="requirement-list">
                <div v-if="detailTask.require_photo" class="req-item">需上传照片</div>
                <div v-if="detailTask.require_note" class="req-item">需填写完成说明</div>
                <div v-if="detailTask.requirements" class="req-text">{{ detailTask.requirements }}</div>
              </div>
            </div>
            <div class="detail-row" v-if="detailTask.completion_note">
              <span class="detail-label">完成说明</span>
              <span class="detail-desc">{{ detailTask.completion_note }}</span>
            </div>
            <div class="detail-row">
              <span class="detail-label">创建时间</span>
              <span>{{ detailTask.created_at?.slice(0, 16).replace('T', ' ') }}</span>
            </div>

            <!-- 照片墙 -->
            <div v-if="detailTask.attachments?.length" class="photo-wall">
              <span class="detail-label">照片凭证</span>
              <div class="photo-grid">
                <div v-for="att in detailTask.attachments" :key="att.id" class="photo-item">
                  <img :src="att.file_url" :alt="att.file_name || ''" @click="previewPhoto = att.file_url" />
                </div>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="detail-actions" v-if="detailTask.status !== 'completed' && detailTask.status !== 'cancelled'">
              <button v-if="detailTask.task_type === 'pool' && !detailTask.assignee_id" class="btn-claim" @click="handleClaim">
                认领此任务
              </button>
              <button v-if="canUpdateStatus(detailTask, 'in_progress')" class="btn-progress" @click="handleStatusUpdate('in_progress')">
                开始处理
              </button>
              <button v-if="canUpdateStatus(detailTask, 'completed')" class="btn-complete" @click="handleStatusUpdate('completed')">
                标记完成
              </button>
              <button v-if="canCancel(detailTask)" class="btn-cancel-task" @click="handleStatusUpdate('cancelled')">
                取消任务
              </button>
              <label class="btn-upload">
                上传照片
                <input type="file" accept="image/jpeg,image/png,image/webp" hidden @change="handleUploadPhoto" />
              </label>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- 照片预览 -->
    <Transition name="fade">
      <div v-if="previewPhoto" class="photo-preview" @click="previewPhoto = null">
        <img :src="previewPhoto" alt="预览" />
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import { taskAPI, type TaskItem, type TemplateItem, type EmployeeOption } from '@/api/task'

const auth = useAuthStore()
const isManager = computed(() => ['boss', 'store_manager', 'system_admin', 'admin'].includes(auth.role))

// ===================== State =====================

const activeTab = ref<'all' | 'my' | 'pool' | 'templates'>('all')
const loading = ref(false)
const tasks = ref<TaskItem[]>([])
const templates = ref<TemplateItem[]>([])
const employees = ref<EmployeeOption[]>([])
const page = ref(1)
const pageSize = 20
const total = ref(0)
const detailTask = ref<any>(null)
const previewPhoto = ref<string | null>(null)
const showCreate = ref(false)
const showCreateTemplate = ref(false)

const newTask = ref({
  title: '',
  description: '',
  task_type: 'direct' as 'direct' | 'pool',
  priority: 'medium' as string,
  assignee_id: '',
  due_date: '',
  require_photo: false,
  require_note: false,
  requirements: '',
})

const newTpl = ref({
  title: '',
  description: '',
  recurrence_type: 'weekly' as 'daily' | 'weekly' | 'monthly',
  priority: 'medium',
  assignee_id: '',
  due_time: '',
  require_photo: false,
  require_note: false,
  requirements: '',
})

const weeklyDay = ref(1)
const monthlyDay = ref(1)

const pendingCount = computed(() => tasks.value.filter(t => t.status === 'pending').length)

const tabs = computed(() => [
  { key: 'all', label: '全部任务', badge: 0 },
  { key: 'my', label: '我的任务', badge: 0 },
  { key: 'pool', label: '认领池', badge: 0 },
  { key: 'templates', label: '周期模板', badge: 0 },
])

// ===================== Load Data =====================

async function loadTasks() {
  loading.value = true
  try {
    let res
    if (activeTab.value === 'my') {
      res = await taskAPI.myTasks({ page: page.value, page_size: pageSize })
    } else if (activeTab.value === 'pool') {
      res = await taskAPI.pool({ page: page.value, page_size: pageSize })
    } else {
      res = await taskAPI.list({ page: page.value, page_size: pageSize })
    }
    tasks.value = res.data.data.items || []
    total.value = res.data.data.total || 0
  } catch {} finally {
    loading.value = false
  }
}

async function loadTemplates() {
  loading.value = true
  try {
    const res = await taskAPI.listTemplates()
    templates.value = res.data.data || []
  } catch {} finally {
    loading.value = false
  }
}

async function loadEmployees() {
  try {
    const res = await taskAPI.listEmployees()
    employees.value = res.data.data || []
  } catch {}
}

watch(activeTab, () => {
  page.value = 1
  if (activeTab.value === 'templates') {
    loadTemplates()
  } else {
    loadTasks()
  }
})

onMounted(() => {
  loadTasks()
  loadEmployees()
})

// ===================== Actions =====================

async function handleCreate() {
  if (!newTask.value.title) return
  try {
    const data: any = {
      title: newTask.value.title,
      description: newTask.value.description,
      task_type: newTask.value.task_type,
      priority: newTask.value.priority,
      require_photo: newTask.value.require_photo,
      require_note: newTask.value.require_note,
      requirements: newTask.value.requirements || undefined,
    }
    if (newTask.value.task_type === 'direct' && newTask.value.assignee_id) {
      data.assignee_id = newTask.value.assignee_id
    }
    if (newTask.value.due_date) {
      data.due_date = newTask.value.due_date
    }
    await taskAPI.create(data)
    ElMessage.success('任务创建成功')
    showCreate.value = false
    newTask.value = { title: '', description: '', task_type: 'direct', priority: 'medium', assignee_id: '', due_date: '', require_photo: false, require_note: false, requirements: '' }
    loadTasks()
  } catch {}
}

async function openDetail(task: TaskItem) {
  try {
    const res = await taskAPI.get(task.id)
    detailTask.value = res.data.data
  } catch {}
}

async function handleClaim() {
  if (!detailTask.value) return
  try {
    await taskAPI.claim(detailTask.value.id)
    ElMessage.success('认领成功')
    detailTask.value = null
    loadTasks()
  } catch {}
}

async function handleStatusUpdate(status: string) {
  if (!detailTask.value) return
  const labels: Record<string, string> = { in_progress: '开始处理', completed: '标记完成', cancelled: '取消' }

  // 完成校验
  let completionNote: string | undefined
  if (status === 'completed') {
    const task = detailTask.value
    // 校验：require_photo=true 必须先上传照片
    if (task.require_photo && !task.attachments?.length) {
      ElMessage.warning('此任务要求完成时上传照片，请先上传至少一张照片')
      return
    }
    // 校验：require_note=true 必须填完成说明
    if (task.require_note) {
      try {
        const { value } = await ElMessageBox.prompt('请填写完成说明', '完成说明', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          inputType: 'textarea',
          inputPlaceholder: '请填写本次任务的完成说明',
          inputValidator: (val) => (val && val.trim().length > 0) || '完成说明不能为空',
        })
        completionNote = value.trim()
      } catch { return }
    } else {
      try {
        await ElMessageBox.confirm(`确定要${labels[status] || status}吗？`, '确认操作')
      } catch { return }
    }
  } else {
    try {
      await ElMessageBox.confirm(`确定要${labels[status] || status}吗？`, '确认操作')
    } catch { return }
  }

  try {
    await taskAPI.updateStatus(detailTask.value.id, status, completionNote)
    ElMessage.success('操作成功')
    detailTask.value = null
    loadTasks()
  } catch {}
}

function canUpdateStatus(task: any, status: string): boolean {
  if (status === 'in_progress') return task.status === 'pending'
  if (status === 'completed') return task.status === 'in_progress' || task.status === 'pending'
  return false
}

function canCancel(task: any): boolean {
  return isManager.value && (task.status === 'pending' || task.status === 'in_progress')
}

async function handleUploadPhoto(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0]
  if (!file || !detailTask.value) return
  try {
    await taskAPI.uploadAttachment(detailTask.value.id, file, 'progress')
    ElMessage.success('照片上传成功')
    const res = await taskAPI.get(detailTask.value.id)
    detailTask.value = res.data.data
  } catch {}
  ;(e.target as HTMLInputElement).value = ''
}

async function handleToggleTemplate(tpl: TemplateItem) {
  try {
    await taskAPI.toggleTemplate(tpl.id)
    ElMessage.success(tpl.enabled ? '已停用' : '已启用')
    loadTemplates()
  } catch {}
}

async function handleDeleteTemplate(tpl: TemplateItem) {
  try {
    await ElMessageBox.confirm(`确定删除模板「${tpl.title}」吗？`, '确认删除')
  } catch { return }
  try {
    await taskAPI.deleteTemplate(tpl.id)
    ElMessage.success('已删除')
    loadTemplates()
  } catch {}
}

async function handleCreateTemplate() {
  if (!newTpl.value.title || !newTpl.value.assignee_id) return
  const rule: Record<string, any> = {}
  if (newTpl.value.recurrence_type === 'weekly') {
    rule.days_of_week = [weeklyDay.value]
    rule.interval = 1
  } else if (newTpl.value.recurrence_type === 'monthly') {
    rule.day_of_month = monthlyDay.value
    rule.interval = 1
  } else {
    rule.interval = 1
  }
  try {
    await taskAPI.createTemplate({
      title: newTpl.value.title,
      description: newTpl.value.description,
      recurrence_type: newTpl.value.recurrence_type,
      priority: newTpl.value.priority,
      assignee_id: newTpl.value.assignee_id,
      due_time: newTpl.value.due_time || undefined,
      recurrence_rule: rule,
      require_photo: newTpl.value.require_photo,
      require_note: newTpl.value.require_note,
      requirements: newTpl.value.requirements || undefined,
    })
    ElMessage.success('模板创建成功')
    showCreateTemplate.value = false
    newTpl.value = { title: '', description: '', recurrence_type: 'weekly', priority: 'medium', assignee_id: '', due_time: '', require_photo: false, require_note: false, requirements: '' }
    loadTemplates()
  } catch {}
}
</script>

<style scoped lang="scss">
.tasks-page {
  padding: 16px;
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
.page-subtitle {
  font-size: 12px;
  color: #666;
}

/* Tabs */
.tabs {
  display: flex;
  gap: 4px;
  background: #141414;
  border-radius: 12px;
  padding: 4px;
  margin-bottom: 16px;
  border: 1px solid rgba(255,255,255,0.06);
}
.tab-btn {
  flex: 1;
  padding: 8px 0;
  font-size: 12px;
  font-weight: 500;
  color: #888;
  background: transparent;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  position: relative;
}
.tab-btn.active {
  color: #fff;
  background: rgba(251, 0, 121, 0.15);
}
.tab-badge {
  position: absolute;
  top: 2px;
  right: 4px;
  font-size: 9px;
  min-width: 14px;
  height: 14px;
  line-height: 14px;
  text-align: center;
  background: #FB0079;
  color: #fff;
  border-radius: 7px;
  padding: 0 3px;
}

/* Create */
.create-section {
  margin-bottom: 12px;
}
.create-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: 13px;
  font-weight: 500;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
  border: 1px solid rgba(251, 0, 121, 0.2);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.create-btn:active {
  transform: scale(0.96);
}

/* Form */
.create-form {
  background: #141414;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.form-group {
  margin-bottom: 12px;
}
.form-group label {
  display: block;
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
  font-weight: 500;
}
.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 8px 12px;
  font-size: 14px;
  color: #fff;
  background: #1a1a1a;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}
.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  border-color: #FB0079;
}
.form-group select {
  appearance: none;
  cursor: pointer;
}
.form-group textarea {
  resize: vertical;
}
.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.radio-group {
  display: flex;
  gap: 4px;
}
.radio-group button {
  flex: 1;
  padding: 6px 0;
  font-size: 12px;
  color: #888;
  background: #1a1a1a;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}
.radio-group button.selected {
  color: #fff;
  background: rgba(251, 0, 121, 0.15);
  border-color: rgba(251, 0, 121, 0.3);
}
.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}
.checkbox-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #ccc;
  cursor: pointer;
}
.checkbox-item input[type="checkbox"] {
  width: 16px;
  height: 16px;
  accent-color: #FB0079;
  cursor: pointer;
}
.mt-8 { margin-top: 8px; }
.requirement-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.req-item {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  font-size: 12px;
  color: #FF6BAA;
  background: rgba(251, 0, 121, 0.1);
  border: 1px solid rgba(251, 0, 121, 0.25);
  border-radius: 12px;
  width: fit-content;
}
.req-text {
  font-size: 13px;
  color: #aaa;
  line-height: 1.5;
  white-space: pre-wrap;
}
.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 4px;
}
.btn-cancel {
  flex: 1;
  padding: 8px;
  font-size: 13px;
  color: #888;
  background: transparent;
  border: 1px solid rgba(255,255,255,0.1);
  border-radius: 8px;
  cursor: pointer;
}
.btn-submit {
  flex: 2;
  padding: 8px;
  font-size: 13px;
  font-weight: 600;
  color: #fff;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: opacity 0.2s;
}
.btn-submit:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Task Cards */
.task-list {
  min-height: 200px;
}
.task-card {
  background: #141414;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: all 0.2s;
}
.task-card:active {
  transform: scale(0.98);
}
.task-card.priority-high {
  border-left: 3px solid #ff3b30;
}
.task-card.status-completed {
  opacity: 0.5;
}
.task-card.status-cancelled {
  opacity: 0.35;
}
.task-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.task-type-badge {
  font-size: 10px;
  color: #888;
  background: rgba(255,255,255,0.05);
  padding: 2px 6px;
  border-radius: 4px;
}
.task-status-badge {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 4px;
}
.task-status-badge.pending {
  color: #ff9500;
  background: rgba(255, 149, 0, 0.1);
}
.task-status-badge.in_progress {
  color: #007aff;
  background: rgba(0, 122, 255, 0.1);
}
.task-status-badge.completed {
  color: #34c759;
  background: rgba(52, 199, 89, 0.1);
}
.task-status-badge.cancelled {
  color: #888;
  background: rgba(136,136,136,0.1);
}
.task-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 6px;
}
.task-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #666;
}
.att-count {
  color: #FB0079;
}

/* Template Cards */
.tpl-card {
  background: #141414;
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 8px;
}
.tpl-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.tpl-recurrence {
  font-size: 10px;
  color: #FB0079;
  background: rgba(251,0,121,0.1);
  padding: 2px 6px;
  border-radius: 4px;
}
.tpl-status {
  font-size: 10px;
  color: #888;
}
.tpl-status.enabled {
  color: #34c759;
}
.tpl-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}
.tpl-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: #666;
  margin-bottom: 8px;
}
.tpl-actions {
  display: flex;
  gap: 8px;
}
.tpl-actions button {
  padding: 4px 10px;
  font-size: 11px;
  color: #888;
  background: rgba(255,255,255,0.05);
  border: 1px solid rgba(255,255,255,0.08);
  border-radius: 6px;
  cursor: pointer;
}
.tpl-actions button.danger {
  color: #ff3b30;
  border-color: rgba(255,59,48,0.2);
}

/* Empty & Loading */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 40px 0;
  color: #555;
  font-size: 13px;
}
.empty-hint {
  font-size: 11px;
  color: #444;
}
.loading-state {
  text-align: center;
  padding: 40px 0;
  color: #666;
  font-size: 13px;
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

/* Detail Panel */
.detail-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.7);
  z-index: 200;
  display: flex;
  align-items: flex-end;
  justify-content: center;
}
.detail-panel {
  width: 100%;
  max-width: 600px;
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
.detail-header h2 {
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
.detail-row {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.03);
  font-size: 13px;
  color: #ccc;
}
.detail-label {
  font-size: 12px;
  color: #666;
  min-width: 60px;
  flex-shrink: 0;
}
.detail-desc {
  color: #aaa;
  font-size: 12px;
  white-space: pre-wrap;
}

/* Photo */
.photo-wall {
  margin-top: 12px;
}
.photo-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-top: 8px;
}
.photo-item {
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
}
.photo-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* Detail Actions */
.detail-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(255,255,255,0.06);
}
.detail-actions button,
.detail-actions label {
  padding: 8px 16px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  border: none;
}
.btn-claim {
  color: #fff;
  background: #007aff;
}
.btn-progress {
  color: #fff;
  background: #007aff;
}
.btn-complete {
  color: #fff;
  background: #34c759;
}
.btn-cancel-task {
  color: #fff;
  background: #ff3b30;
}
.btn-upload {
  color: #888;
  background: rgba(255,255,255,0.06);
  border: 1px solid rgba(255,255,255,0.1) !important;
}

/* Photo Preview */
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
.slide-enter-active,
.slide-leave-active {
  transition: all 0.25s ease;
}
.slide-enter-from,
.slide-leave-to {
  opacity: 0;
  transform: translateY(12px);
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
