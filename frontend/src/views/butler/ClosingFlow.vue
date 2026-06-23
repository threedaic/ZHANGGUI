<template>
  <div class="flow-page">
    <div class="page-header">
      <div class="header-info" v-if="session">
        <h1>{{ session.session_type === 'closing' ? '闭店检查' : '开店检查' }}</h1>
        <span class="status-badge" :class="session.status">
          {{ session.status === 'completed' ? '已完成' : session.status === 'in_progress' ? '进行中' : '异常' }}
        </span>
      </div>
    </div>

    <!-- Progress bar -->
    <div class="progress-section" v-if="session">
      <div class="progress-text">{{ session.completed_items }} / {{ session.total_items }}</div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: progressPercent + '%' }"></div>
      </div>
    </div>

    <!-- Template groups -->
    <div v-if="session" class="templates">
      <div v-for="tpl in session.templates" :key="tpl.id" class="template-group">
        <h3 class="template-title" @click="toggleGroup(tpl.id)">
          <span>{{ tpl.name }}</span>
          <span class="toggle-icon">{{ expandedGroups.has(tpl.id) ? '&#9660;' : '&#9654;' }}</span>
        </h3>

        <div v-if="expandedGroups.has(tpl.id) || expandedGroups.size === 0" class="items-list">
          <div
            v-for="item in (tpl.results || [])"
            :key="item.id"
            class="check-item"
            :class="itemClass(item.review_status)"
          >
            <div class="item-info">
              <span class="item-type-badge" :class="item.item_type">
                {{ item.item_type === 'photo' ? '拍照' : '打勾' }}
              </span>
              <span class="item-name">{{ item.item_name }}</span>
            </div>

            <!-- Pending state -->
            <div v-if="item.review_status === 'pending'" class="item-action">
              <button
                v-if="item.item_type === 'checkbox'"
                class="btn-done"
                @click="doConfirm(item.id)"
              >
                确认完成
              </button>
              <div v-else class="photo-upload">
                <input
                  type="file"
                  accept="image/*"
                  capture="environment"
                  :ref="(el: any) => fileInputs[item.id] = el"
                  @change="(e: any) => doUpload(item.id, e)"
                  style="display:none"
                />
                <button class="btn-photo" @click="triggerUpload(item.id)">拍照上传</button>
              </div>
            </div>

            <!-- Rejected: 需重新提交 -->
            <div v-else-if="item.review_status === 'manual_rejected'" class="item-rejected">
              <div class="reject-tip">已被驳回，请重新拍照</div>
              <div v-if="item.review_comment" class="reject-reason">原因: {{ item.review_comment }}</div>
              <input
                type="file"
                accept="image/*"
                capture="environment"
                :ref="(el: any) => resubmitInputs[item.id] = el"
                @change="(e: any) => doResubmit(item.id, e)"
                style="display:none"
              />
              <button class="btn-resubmit" @click="triggerResubmit(item.id)">重新拍照</button>
            </div>

            <!-- Manual reviewing: 等待店长复核 -->
            <div v-else-if="item.review_status === 'manual_reviewing'" class="item-reviewing">
              <div class="review-tip">
                <span class="done-icon done-review">&#9888;</span>
                <span>等待店长复核</span>
              </div>
              <div v-if="item.ai_result" class="ai-result-box">
                <div class="ai-result-header">
                  <span class="ai-badge" :class="aiPassClass(item.ai_result)">AI 判定</span>
                  <span class="ai-confidence">置信度 {{ (item.ai_result.confidence * 100).toFixed(0) }}%</span>
                </div>
                <div class="ai-reason">{{ item.ai_result.reason }}</div>
              </div>
              <div v-if="item.photo_url" class="photo-preview">
                <img :src="item.photo_url" alt="检查照片" @click="previewPhoto(item.photo_url)" />
              </div>
              <!-- 店长/老板可在此复核 -->
              <div v-if="canReview" class="review-actions">
                <button class="btn-reject" @click="doReview(item.id, 'reject')">驳回</button>
                <button class="btn-approve" @click="doReview(item.id, 'pass')">通过</button>
              </div>
            </div>

            <!-- Done state -->
            <div v-else class="item-done-badge">
              <span v-if="item.review_status === 'passed' || item.review_status === 'auto_passed' || item.review_status === 'manual_passed'" class="done-icon done-ok">&#10003;</span>
              <span v-if="item.review_status === 'auto_passed'" class="done-label">AI 自动通过</span>
              <span v-else-if="item.review_status === 'manual_passed'" class="done-label">店长已通过</span>
              <span v-else>已完成</span>
              <div v-if="item.photo_url && item.review_status !== 'pending'" class="photo-thumb">
                <img :src="item.photo_url" alt="检查照片" @click="previewPhoto(item.photo_url)" />
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add ad-hoc item -->
    <div v-if="session && session.status === 'in_progress'" class="adhoc-section">
      <button class="btn-adhoc" @click="showAdHoc = !showAdHoc">+ 添加临时项</button>
      <div v-if="showAdHoc" class="adhoc-form">
        <input v-model="adhocName" placeholder="输入检查项名称" class="adhoc-input" />
        <div class="adhoc-type">
          <label><input type="radio" v-model="adhocType" value="checkbox" /> 打勾</label>
          <label><input type="radio" v-model="adhocType" value="photo" /> 拍照</label>
        </div>
        <button class="btn-save" @click="doAddAdHoc" :disabled="!adhocName.trim()">添加</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import { useRoute } from 'vue-router'
import { getSession, confirmItem, uploadPhoto, addAdHocItem, manualReview, resubmitPhoto } from '@/api/butler'
import type { SessionDetail } from '@/api/butler'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const auth = useAuthStore()
const session = ref<SessionDetail | null>(null)
const expandedGroups = ref<Set<string>>(new Set())
const fileInputs = reactive<Record<string, HTMLInputElement | null>>({})
const resubmitInputs = reactive<Record<string, HTMLInputElement | null>>({})
const showAdHoc = ref(false)
const adhocName = ref('')
const adhocType = ref('checkbox')

const canReview = computed(() => {
  const role = auth.info.role || 'staff'
  return role === 'boss' || role === 'store_manager'
})

const progressPercent = computed(() => {
  if (!session.value || session.value.total_items === 0) return 0
  return Math.round((session.value.completed_items / session.value.total_items) * 100)
})

onMounted(() => {
  loadSession()
})

async function loadSession() {
  const id = String(route.params.id || route.params.sessionId || '')
  try {
    const res: any = await getSession(id)
    session.value = res.data?.data || res.data
    // Auto-expand all groups
    if (session.value) {
      for (const tpl of session.value.templates) {
        expandedGroups.value.add(tpl.id)
      }
    }
  } catch (e) {
    console.error(e)
  }
}

function toggleGroup(id: string) {
  if (expandedGroups.value.has(id)) {
    expandedGroups.value.delete(id)
  } else {
    expandedGroups.value.add(id)
  }
}

function triggerUpload(resultId: string) {
  fileInputs[resultId]?.click()
}

function triggerResubmit(resultId: string) {
  resubmitInputs[resultId]?.click()
}

function itemClass(status: string) {
  if (status === 'pending') return 'pending'
  if (status === 'manual_rejected') return 'rejected'
  if (status === 'manual_reviewing') return 'reviewing'
  return 'done'
}

function aiPassClass(ai: any) {
  if (ai?.pass === true) return 'ai-pass'
  if (ai?.pass === false) return 'ai-fail'
  return 'ai-unknown'
}

function previewPhoto(url: string) {
  // 简单实现：新窗口打开
  window.open(url, '_blank')
}

async function doConfirm(resultId: string) {
  if (!session.value) return
  try {
    await confirmItem(session.value.id, resultId)
    await loadSession()
  } catch (e: any) {
    alert(e?.response?.data?.message || '操作失败')
  }
}

async function doUpload(resultId: string, event: any) {
  const file = event.target?.files?.[0]
  if (!file || !session.value) return
  try {
    await uploadPhoto(session.value.id, resultId, file)
    await loadSession()
  } catch (e: any) {
    alert(e?.response?.data?.message || '上传失败')
  }
  event.target.value = ''
}

async function doResubmit(resultId: string, event: any) {
  const file = event.target?.files?.[0]
  if (!file || !session.value) return
  try {
    await resubmitPhoto(session.value.id, resultId, file)
    await loadSession()
  } catch (e: any) {
    alert(e?.response?.data?.message || '重新提交失败')
  }
  event.target.value = ''
}

async function doReview(resultId: string, action: 'pass' | 'reject') {
  if (!session.value) return
  let comment: string | undefined
  if (action === 'reject') {
    comment = prompt('请输入驳回原因（可选）：') || undefined
  }
  try {
    await manualReview(session.value.id, resultId, action, comment)
    await loadSession()
  } catch (e: any) {
    alert(e?.response?.data?.message || '复核失败')
  }
}

async function doAddAdHoc() {
  if (!session.value || !adhocName.value.trim()) return
  try {
    await addAdHocItem(session.value.id, adhocName.value.trim(), adhocType.value as any)
    adhocName.value = ''
    showAdHoc.value = false
    await loadSession()
  } catch (e: any) {
    alert(e?.response?.data?.message || '添加失败')
  }
}


</script>

<style scoped>
.flow-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 16px;
  padding-bottom: 80px;
  min-height: 100vh;
  background: $color-black;
  color: $brand-white;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
}

.header-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;
}

.header-info h1 {
  font-size: 18px;
  margin: 0;
  color: $brand-white;
  font-weight: 600;
}

.status-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
}

.status-badge.completed { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.status-badge.in_progress { background: rgba(251, 0, 121, 0.15); color: $brand-primary; }

.progress-section {
  margin-bottom: 20px;
  padding: 16px;
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
}

.progress-text {
  font-size: 28px;
  font-weight: 700;
  color: $brand-white;
  margin-bottom: 8px;
  font-family: $font-family-number;
  text-shadow: 0 0 8px rgba(251, 0, 121, 0.5);
}

.progress-bar {
  height: 6px;
  background: rgba(255, 255, 255, 0.08);
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, $brand-primary, rgba(251, 0, 121, 0.6));
  border-radius: 3px;
  transition: width 0.3s;
  box-shadow: 0 0 16px rgba(251, 0, 121, 0.25);
}

.template-group {
  margin-bottom: 16px;
}

.template-title {
  font-size: 15px;
  color: $brand-white;
  padding: 12px 16px;
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: $radius-md;
  margin: 0 0 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.toggle-icon {
  font-size: 12px;
  color: $brand-primary;
}

.check-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  background: rgba(17, 17, 17, 0.5);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.04);
  border-radius: $radius-md;
  margin-bottom: 8px;
  border-left: 3px solid rgba(255, 255, 255, 0.1);
  transition: all 0.2s;
}

.check-item:hover {
  border-left-color: $brand-primary;
}

.check-item.done {
  border-left-color: #4caf50;
  opacity: 0.75;
}

.check-item.rejected {
  border-left-color: #f44336;
  background: rgba(244, 67, 54, 0.08);
}

.check-item.reviewing {
  border-left-color: #ffc107;
  background: rgba(255, 193, 7, 0.05);
}

.check-item.pending {
  border-left-color: $brand-primary;
}

.item-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
}

.item-type-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
  white-space: nowrap;
}

.item-type-badge.photo { background: rgba(33, 150, 243, 0.15); color: #64b5f6; }
.item-type-badge.checkbox { background: rgba(251, 0, 121, 0.15); color: $brand-primary; }

.item-name {
  font-size: 14px;
  color: $brand-white;
}

.item-action {
  flex-shrink: 0;
}

.btn-done, .btn-photo, .btn-save, .btn-resubmit, .btn-approve, .btn-reject {
  padding: 8px 16px;
  border: none;
  border-radius: $radius-sm;
  font-size: 13px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.15s;
}

.btn-done {
  background: #4caf50;
  color: $brand-white;
  box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
}

.btn-photo {
  background: #2196f3;
  color: $brand-white;
  box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
}

.btn-resubmit {
  background: #ff9800;
  color: $brand-white;
  margin-top: 8px;
}

.btn-approve {
  background: #4caf50;
  color: $brand-white;
}

.btn-reject {
  background: #f44336;
  color: $brand-white;
}

.btn-save {
  background: $brand-primary;
  color: $brand-white;
  box-shadow: 0 4px 16px rgba(251, 0, 121, 0.35);
  transition: box-shadow 0.2s, transform 0.1s;
}

.btn-save:active {
  transform: scale(0.97);
  box-shadow: 0 2px 8px rgba(251, 0, 121, 0.25);
}

.btn-save:disabled {
  background: rgba(251, 0, 121, 0.3);
  cursor: not-allowed;
  box-shadow: none;
}

.item-rejected {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 4px;
}

.reject-tip {
  color: #f44336;
  font-size: 12px;
  font-weight: 600;
}

.reject-reason {
  color: #ff8080;
  font-size: 11px;
}

.item-reviewing {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 8px;
  min-width: 200px;
}

.review-tip {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 12px;
  color: #ffc107;
}

.ai-result-box {
  width: 100%;
  padding: 10px;
  background: rgba(255, 193, 7, 0.06);
  border: 1px solid rgba(255, 193, 7, 0.2);
  border-radius: $radius-sm;
  font-size: 11px;
}

.ai-result-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.ai-badge {
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
  font-size: 10px;
}

.ai-badge.ai-pass { background: rgba(76, 175, 80, 0.15); color: #4caf50; }
.ai-badge.ai-fail { background: rgba(244, 67, 54, 0.15); color: #f44336; }
.ai-badge.ai-unknown { background: rgba(255, 193, 7, 0.15); color: #ffc107; }

.ai-confidence {
  color: $brand-text-light;
  font-size: 10px;
}

.ai-reason {
  color: rgba(255, 255, 255, 0.8);
  line-height: 1.5;
}

.photo-preview, .photo-thumb {
  width: 100%;
  margin-top: 6px;
}

.photo-preview img, .photo-thumb img {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  border-radius: $radius-sm;
  cursor: pointer;
}

.photo-thumb img {
  max-height: 60px;
}

.review-actions {
  display: flex;
  gap: 6px;
  width: 100%;
}

.review-actions button {
  flex: 1;
}

.item-done-badge {
  display: flex;
  align-items: flex-end;
  gap: 4px;
  font-size: 12px;
  color: $brand-text-light;
  flex-direction: column;
}

.done-label {
  font-size: 10px;
  color: #4caf50;
}

.done-icon {
  font-size: 14px;
}

.done-ok { color: #4caf50; }
.done-review { color: #ffc107; }

/* Ad-hoc section */
.adhoc-section {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.btn-adhoc {
  background: none;
  border: 1px dashed rgba(255, 255, 255, 0.15);
  color: $brand-text-light;
  padding: 12px 16px;
  border-radius: $radius-md;
  width: 100%;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-adhoc:hover {
  border-color: $brand-primary;
  color: $brand-primary;
}

.adhoc-form {
  margin-top: 10px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px;
  background: rgba(17, 17, 17, 0.6);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 16px;
}

.adhoc-input {
  padding: 12px 14px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: $radius-sm;
  background: rgba(0, 0, 0, 0.3);
  color: $brand-white;
  font-size: 14px;
}

.adhoc-input:focus {
  outline: none;
  border-color: $brand-primary;
}

.adhoc-type {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: $brand-text-light;
}

.adhoc-type input {
  margin-right: 4px;
}
</style>
