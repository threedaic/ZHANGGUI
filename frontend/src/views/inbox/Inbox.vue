<template>
  <div class="inbox-page">
    <!-- 待签收提醒条 -->
    <div v-if="pendingCount > 0 && activeTab === 'pending'" class="reminder-bar">
      <div class="reminder-info">
        <span class="reminder-icon">!</span>
        <span class="reminder-text">
          您有 <strong>{{ pendingCount }}</strong> 份文件待签收
        </span>
      </div>
      <button class="btn-batch" @click="enterBatchMode" v-if="!batchMode && items.length > 1">
        批量签收
      </button>
      <button class="btn-batch-cancel" @click="exitBatchMode" v-if="batchMode">
        取消
      </button>
    </div>

    <div class="tabs">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'pending' }"
        @click="switchTab('pending')"
      >
        待签收
        <span v-if="pendingCount > 0" class="badge">{{ pendingCount > 99 ? '99+' : pendingCount }}</span>
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'signed' }"
        @click="switchTab('signed')"
      >
        已签收
      </button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'disputed' }"
        @click="switchTab('disputed')"
      >
        异议中
      </button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="items.length === 0" class="empty">
      <div class="empty-icon">✓</div>
      <div v-if="activeTab === 'pending'">暂无待签收任务</div>
      <div v-else-if="activeTab === 'signed'">暂无已签收记录</div>
      <div v-else>暂无异议任务</div>
    </div>
    <div v-else class="inbox-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="inbox-card"
        :class="{
          pending: item.status === 'pending',
          signed: item.status === 'signed',
          disputed: item.status === 'disputed',
          selected: batchSelected.has(item.id),
        }"
        @click="onCardClick(item)"
      >
        <input
          v-if="batchMode && item.status === 'pending'"
          type="checkbox"
          class="batch-checkbox"
          :checked="batchSelected.has(item.id)"
          @click.stop="toggleBatch(item.id)"
        />
        <div class="card-status-dot"></div>
        <div class="card-body">
          <div class="card-header">
            <span class="card-title">{{ item.title }}</span>
            <span class="card-type">{{ typeLabel(item.type) }}</span>
          </div>
          <div class="card-meta">
            <span v-if="item.issued_by_name">发布人: {{ item.issued_by_name }}</span>
            <span v-if="item.status === 'signed' && item.signed_at">已签收 · {{ formatTime(item.signed_at) }}</span>
            <span v-else-if="item.status === 'disputed'">已提出异议 · {{ formatTime(item.disputed_at) }}</span>
            <span v-else>待签收 · {{ formatTime(item.issued_at) }}</span>
          </div>
        </div>
        <div class="card-arrow" v-if="!batchMode">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
            <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
          </svg>
        </div>
      </div>
    </div>

    <!-- 批量签收底部操作栏 -->
    <div v-if="batchMode" class="batch-footer">
      <div class="batch-info">
        已选 {{ batchSelected.size }} 项
        <button class="link-btn" @click="selectAll" v-if="batchSelected.size < items.length">全选</button>
        <button class="link-btn" @click="batchSelected.clear()" v-else>取消全选</button>
      </div>
      <button
        class="btn-batch-sign"
        :disabled="batchSelected.size === 0"
        @click="openBatchSign"
      >
        批量签收
      </button>
    </div>

    <!-- 批量签收弹窗 -->
    <div v-if="showBatchSignModal" class="modal-mask" @click.self="closeBatchSign">
      <div class="modal-content">
        <div class="modal-header">
          <h3>批量签收确认</h3>
          <button class="close-btn" @click="closeBatchSign">×</button>
        </div>
        <div class="modal-body">
          <p class="modal-tip">将对以下 {{ batchSelected.size }} 项文件使用同一份签名进行签收：</p>
          <ul class="batch-list">
            <li v-for="item in selectedItems" :key="item.id">
              <span class="batch-item-type">[{{ typeLabel(item.type) }}]</span>
              {{ item.title }}
            </li>
          </ul>

          <div class="sign-section">
            <label class="sign-label">手写签名</label>
            <div class="signature-pad-wrapper">
              <canvas
                ref="signaturePad"
                class="signature-pad"
                @mousedown="startDraw"
                @mousemove="draw"
                @mouseup="endDraw"
                @mouseleave="endDraw"
                @touchstart.prevent="startDraw"
                @touchmove.prevent="draw"
                @touchend.prevent="endDraw"
              ></canvas>
              <button v-if="hasSignature" class="btn-clear-sig" @click="clearSignature">清除</button>
            </div>
          </div>

          <div class="form-row">
            <label>备注（可选）</label>
            <textarea v-model="batchNotes" rows="2" class="form-textarea" maxlength="200"></textarea>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeBatchSign">取消</button>
          <button class="btn-confirm" :disabled="batchSubmitting || !hasSignature" @click="submitBatchSign">
            {{ batchSubmitting ? '提交中...' : '确认签收' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, nextTick, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { signTaskAPI, type SignTaskItem } from '@/api/sign-tasks'

const router = useRouter()
const activeTab = ref('pending')
const items = ref<SignTaskItem[]>([])
const loading = ref(false)
const pendingCount = ref(0)

// 批量签收
const batchMode = ref(false)
const batchSelected = reactive<Set<string>>(new Set())
const showBatchSignModal = ref(false)
const batchNotes = ref('')
const batchSubmitting = ref(false)

// 签名画板
const signaturePad = ref<HTMLCanvasElement | null>(null)
const isDrawing = ref(false)
const hasSignature = ref(false)
let ctx: CanvasRenderingContext2D | null = null

const typeLabels: Record<string, string> = {
  salary_slip: '工资单',
  penalty_notice: '处罚通知',
  attendance_confirm: '考勤确认',
}

const selectedItems = computed(() => {
  return items.value.filter(i => batchSelected.has(i.id))
})

function typeLabel(type: string): string {
  return typeLabels[type] || type
}

function formatTime(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  if (diff < 172800000) return '1天前'
  return d.toLocaleDateString('zh-CN')
}

async function loadData() {
  loading.value = true
  try {
    const status = activeTab.value
    const res = await signTaskAPI.getInbox({ status, page: 1, page_size: 50 })
    items.value = res.data.data.items || []
  } catch { /* */ }
  loading.value = false
}

async function loadCount() {
  try {
    const res = await signTaskAPI.getCount()
    pendingCount.value = res.data.data.pending
  } catch { /* */ }
}

function switchTab(tab: string) {
  activeTab.value = tab
  exitBatchMode()
  loadData()
}

function onCardClick(item: SignTaskItem) {
  if (batchMode && item.status === 'pending') {
    toggleBatch(item.id)
    return
  }
  router.push(`/daily/inbox/${item.id}`)
}

// ===== 批量签收 =====
function enterBatchMode() {
  batchMode.value = true
  batchSelected.clear()
}

function exitBatchMode() {
  batchMode.value = false
  batchSelected.clear()
  showBatchSignModal.value = false
}

function toggleBatch(id: string) {
  if (batchSelected.has(id)) {
    batchSelected.delete(id)
  } else {
    batchSelected.add(id)
  }
}

function selectAll() {
  items.value.filter(i => i.status === 'pending').forEach(i => batchSelected.add(i.id))
}

async function openBatchSign() {
  showBatchSignModal.value = true
  hasSignature.value = false
  batchNotes.value = ''
  await nextTick()
  initCanvas()
}

function closeBatchSign() {
  showBatchSignModal.value = false
  hasSignature.value = false
}

function initCanvas() {
  const canvas = signaturePad.value
  if (!canvas) return
  // 适配高 DPI
  const dpr = window.devicePixelRatio || 1
  const rect = canvas.getBoundingClientRect()
  canvas.width = rect.width * dpr
  canvas.height = rect.height * dpr
  ctx = canvas.getContext('2d')
  if (ctx) {
    ctx.scale(dpr, dpr)
    ctx.strokeStyle = '#FFFFFF'
    ctx.lineWidth = 2
    ctx.lineCap = 'round'
    ctx.lineJoin = 'round'
  }
}

function getPos(e: MouseEvent | TouchEvent) {
  const canvas = signaturePad.value
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  const clientX = 'touches' in e ? e.touches[0].clientX : e.clientX
  const clientY = 'touches' in e ? e.touches[0].clientY : e.clientY
  return { x: clientX - rect.left, y: clientY - rect.top }
}

function startDraw(e: MouseEvent | TouchEvent) {
  isDrawing.value = true
  const pos = getPos(e)
  if (ctx) {
    ctx.beginPath()
    ctx.moveTo(pos.x, pos.y)
  }
}

function draw(e: MouseEvent | TouchEvent) {
  if (!isDrawing.value || !ctx) return
  const pos = getPos(e)
  ctx.lineTo(pos.x, pos.y)
  ctx.stroke()
  hasSignature.value = true
}

function endDraw() {
  isDrawing.value = false
}

function clearSignature() {
  const canvas = signaturePad.value
  if (canvas && ctx) {
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    hasSignature.value = false
  }
}

async function submitBatchSign() {
  if (!hasSignature.value || !signaturePad.value) {
    alert('请先签名')
    return
  }
  const canvas = signaturePad.value
  // 转为 base64 PNG
  const dataUrl = canvas.toDataURL('image/png')
  const base64 = dataUrl.split(',')[1]

  batchSubmitting.value = true
  try {
    const ids = Array.from(batchSelected)
    const res = await signTaskAPI.batchSign(ids, base64, batchNotes.value || undefined)
    const data = res.data.data
    alert(`成功签收 ${data.success_count} 项${data.failed_count ? `，${data.failed_count} 项失败` : ''}`)
    closeBatchSign()
    exitBatchMode()
    await Promise.all([loadData(), loadCount()])
  } catch (e: any) {
    alert(e.response?.data?.message || '签收失败')
  } finally {
    batchSubmitting.value = false
  }
}

onMounted(() => {
  loadCount()
  loadData()
})
</script>

<style scoped>
.inbox-page {
  padding: 0 16px;
  padding-bottom: 80px;
}

.reminder-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 12px;
  background: rgba(251, 0, 121, 0.08);
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 8px;
  margin: 12px 0;
}

.reminder-info {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #FFFFFF;
}

.reminder-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  background: #FB0079;
  color: #FFFFFF;
  border-radius: 50%;
  font-size: 12px;
  font-weight: 700;
}

.reminder-text strong {
  color: #FB0079;
  font-size: 15px;
}

.btn-batch, .btn-batch-cancel {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn-batch-cancel {
  background: #333333;
  color: #C8C8C8;
}

.tabs {
  display: flex;
  gap: 24px;
  padding: 12px 0 16px;
  border-bottom: 1px solid #222222;
  margin-bottom: 12px;
}

.tab-btn {
  background: none;
  border: none;
  font-size: 14px;
  font-weight: 600;
  color: #7A7C80;
  cursor: pointer;
  padding: 0 0 6px;
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
}

.tab-btn.active {
  color: #FB0079;
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: #FB0079;
  border-radius: 1px;
}

.badge {
  background: #FB0079;
  color: #FFFFFF;
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 18px;
  text-align: center;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 48px 16px;
  font-size: 13px;
}

.empty-icon {
  font-size: 32px;
  color: #4caf50;
  margin-bottom: 8px;
}

.inbox-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.inbox-card {
  display: flex;
  align-items: center;
  gap: 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 12px;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s;
}

.inbox-card.selected {
  background: rgba(251, 0, 121, 0.08);
  border-color: #FB0079;
}

.inbox-card.pending {
  border-left: 3px solid #FB0079;
}

.inbox-card.disputed {
  border-left: 3px solid #ff9800;
}

.inbox-card.signed {
  border-left: 3px solid #333333;
}

.batch-checkbox {
  width: 18px;
  height: 18px;
  cursor: pointer;
  accent-color: #FB0079;
}

.card-body {
  flex: 1;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.card-type {
  font-size: 11px;
  color: #7A7C80;
  padding: 1px 6px;
  border: 1px solid #333333;
  border-radius: 4px;
  flex-shrink: 0;
}

.card-meta {
  font-size: 12px;
  color: #7A7C80;
  display: flex;
  gap: 12px;
}

.card-arrow {
  flex-shrink: 0;
}

/* 批量签收底部栏 */
.batch-footer {
  position: fixed;
  bottom: 60px;
  left: 0;
  right: 0;
  background: #1A1A1A;
  border-top: 1px solid #333333;
  padding: 12px 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  z-index: 100;
}

.batch-info {
  font-size: 13px;
  color: #FFFFFF;
  display: flex;
  align-items: center;
  gap: 8px;
}

.link-btn {
  background: none;
  border: none;
  color: #FB0079;
  font-size: 12px;
  cursor: pointer;
  padding: 0;
}

.btn-batch-sign {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 10px 24px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-batch-sign:disabled {
  background: #555555;
  cursor: not-allowed;
}

/* 弹窗 */
.modal-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 16px;
}

.modal-content {
  background: #1A1A1A;
  border-radius: 12px;
  width: 100%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #333333;
}

.modal-header h3 {
  margin: 0;
  font-size: 16px;
  color: #FFFFFF;
}

.close-btn {
  background: none;
  border: none;
  color: #7A7C80;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.modal-body {
  padding: 16px;
}

.modal-tip {
  font-size: 13px;
  color: #C8C8C8;
  margin: 0 0 12px;
}

.batch-list {
  list-style: none;
  padding: 0;
  margin: 0 0 16px;
  max-height: 120px;
  overflow-y: auto;
  background: #111111;
  border-radius: 6px;
  padding: 8px;
}

.batch-list li {
  font-size: 12px;
  color: #FFFFFF;
  padding: 4px 0;
  border-bottom: 1px solid #222222;
}

.batch-list li:last-child {
  border-bottom: none;
}

.batch-item-type {
  color: #FB0079;
  margin-right: 4px;
}

.sign-section {
  margin-bottom: 12px;
}

.sign-label {
  display: block;
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 6px;
}

.signature-pad-wrapper {
  position: relative;
  background: #FFFFFF;
  border-radius: 8px;
  overflow: hidden;
}

.signature-pad {
  display: block;
  width: 100%;
  height: 160px;
  cursor: crosshair;
  touch-action: none;
}

.btn-clear-sig {
  position: absolute;
  top: 6px;
  right: 6px;
  background: rgba(0, 0, 0, 0.5);
  color: #FFFFFF;
  border: none;
  padding: 4px 8px;
  border-radius: 4px;
  font-size: 11px;
  cursor: pointer;
}

.form-row {
  margin-bottom: 12px;
}

.form-row label {
  display: block;
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 4px;
}

.form-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
  box-sizing: border-box;
  resize: none;
  font-family: inherit;
}

.modal-footer {
  display: flex;
  gap: 12px;
  padding: 16px;
  border-top: 1px solid #333333;
}

.btn-cancel, .btn-confirm {
  flex: 1;
  padding: 10px;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  border: none;
  cursor: pointer;
}

.btn-cancel {
  background: #333333;
  color: #C8C8C8;
}

.btn-confirm {
  background: #FB0079;
  color: #FFFFFF;
}

.btn-confirm:disabled {
  background: #555555;
  cursor: not-allowed;
}
</style>
