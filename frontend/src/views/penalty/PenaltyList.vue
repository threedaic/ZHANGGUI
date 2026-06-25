<template>
  <div class="penalty-list-page">
    <div class="page-header">
      <h2 class="page-title">奖惩通知</h2>
      <button class="btn-create" @click="router.push('/management/penalties/create')">+ 新建</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="items.length === 0" class="empty">暂无奖惩通知</div>
    <div v-else class="penalty-list">
      <div
        v-for="item in items"
        :key="item.id"
        class="penalty-card"
        :class="statusClass(item.status)"
        @click="openDetail(item)"
      >
        <div class="card-top">
          <span class="penalty-type-badge">{{ item.penalty_type_name }}</span>
          <span class="penalty-amount">¥{{ item.amount }}</span>
        </div>
        <div class="card-reason">{{ item.reason }}</div>
        <div class="card-bottom">
          <div class="card-meta">
            <span>员工: {{ item.employee_name }}</span>
            <span>发布人: {{ item.issued_by_name }}</span>
            <span>{{ formatDate(item.created_at) }}</span>
          </div>
          <div class="card-status-row">
            <span class="status-tag" :class="item.status">
              {{ statusLabel(item.status) }}
            </span>
            <span v-if="item.sign_task_status" class="sign-status">
              {{ signStatusLabel(item.sign_task_status) }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- 详情弹窗 -->
    <div v-if="detailVisible" class="modal-mask" @click.self="closeDetail">
      <div class="modal-body" ref="exportRef">
        <div class="modal-header">
          <span class="modal-title">奖惩通知详情</span>
          <button class="btn-close" @click="closeDetail">×</button>
        </div>

        <div v-if="current" class="modal-content">
          <div class="doc-title">
            {{ current.penalty_type_name }}通知书
          </div>

          <div class="doc-grid">
            <div class="doc-row"><span class="doc-label">员工姓名</span><span class="doc-value">{{ current.employee_name }}</span></div>
            <div class="doc-row"><span class="doc-label">处罚类型</span><span class="doc-value">{{ current.penalty_type_name }}</span></div>
            <div class="doc-row"><span class="doc-label">金额</span><span class="doc-value amount">¥{{ current.amount }}</span></div>
            <div class="doc-row"><span class="doc-label">事由</span><span class="doc-value">{{ current.reason }}</span></div>
            <div class="doc-row"><span class="doc-label">发布人</span><span class="doc-value">{{ current.issued_by_name }}</span></div>
            <div class="doc-row"><span class="doc-label">发布时间</span><span class="doc-value">{{ formatDateTime(current.issued_at) }}</span></div>
          </div>

          <div v-if="current.sign_task_status === 'signed'" class="sign-section">
            <div class="section-title">员工已签收</div>
            <div class="doc-row"><span class="doc-label">签收时间</span><span class="doc-value">{{ formatDateTime(current.signed_at) }}</span></div>
            <div class="signature-block">
              <div class="doc-label">员工手写签名</div>
              <img v-if="current.signature_data" :src="current.signature_data" class="signature-img" alt="签名" />
              <div v-else class="no-signature">（无签名图）</div>
            </div>
            <div v-if="current.sign_notes" class="doc-row">
              <span class="doc-label">备注</span><span class="doc-value">{{ current.sign_notes }}</span>
            </div>
          </div>

          <div v-else-if="current.sign_task_status === 'disputed'" class="dispute-section">
            <div class="section-title warn">员工提出异议</div>
            <div class="doc-row"><span class="doc-label">异议时间</span><span class="doc-value">{{ formatDateTime(current.disputed_at) }}</span></div>
            <div class="doc-row"><span class="doc-label">异议理由</span><span class="doc-value">{{ current.dispute_reason }}</span></div>
          </div>

          <div v-else-if="current.sign_task_status === 'pending'" class="pending-section">
            <div class="section-title muted">等待员工签收中...</div>
          </div>
        </div>

        <div class="modal-footer">
          <button class="btn-export" @click="exportPng">导出图片</button>
          <button class="btn-cancel" @click="closeDetail">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { penaltyAPI, type PenaltyItem } from '@/api/penalties'

const router = useRouter()
const items = ref<PenaltyItem[]>([])
const loading = ref(false)

// 详情弹窗
const detailVisible = ref(false)
const current = ref<PenaltyItem | null>(null)
const exportRef = ref<HTMLElement | null>(null)

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    draft: '草稿',
    issued: '已发布',
    acknowledged: '已签收',
  }
  return map[status] || status
}

function signStatusLabel(status: string): string {
  const map: Record<string, string> = {
    pending: '待签收',
    signed: '已签收',
    disputed: '有异议',
  }
  return map[status] || status
}

function statusClass(status: string): string {
  return `status-${status}`
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN')
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
}

function openDetail(item: PenaltyItem) {
  current.value = item
  detailVisible.value = true
}

function closeDetail() {
  detailVisible.value = false
  current.value = null
}

async function exportPng() {
  if (!exportRef.value) return
  // 动态加载 html-to-image（避免首次包体积）
  const { toPng } = await import('html-to-image')
  const dataUrl = await toPng(exportRef.value, {
    backgroundColor: '#000000',
    pixelRatio: 2,
  })
  const link = document.createElement('a')
  const emp = current.value?.employee_name || '员工'
  const type = current.value?.penalty_type_name || '通知'
  const date = new Date().toISOString().slice(0, 10)
  link.download = `${type}通知-${emp}-${date}.png`
  link.href = dataUrl
  link.click()
}

async function loadData() {
  loading.value = true
  try {
    const res = await penaltyAPI.getList({ page: 1, page_size: 50 })
    items.value = res.data.data.items || []
  } catch { /* */ }
  loading.value = false
}

onMounted(loadData)
</script>

<style scoped>
.penalty-list-page {
  padding: 0 16px;
  padding-bottom: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 0;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.btn-create {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 48px;
}

.penalty-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.penalty-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.penalty-card:active {
  border-color: #FB0079;
}

.penalty-card.status-draft {
  border-left: 3px solid #333333;
}

.penalty-card.status-issued {
  border-left: 3px solid #FB0079;
}

.penalty-card.status-acknowledged {
  border-left: 3px solid #FB0079;
}

.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.penalty-type-badge {
  font-size: 11px;
  color: #FB0079;
  padding: 2px 8px;
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 4px;
}

.penalty-amount {
  font-size: 16px;
  font-weight: 700;
  color: #FB0079;
}

.card-reason {
  font-size: 13px;
  color: #C8C8C8;
  line-height: 1.5;
  margin-bottom: 10px;
}

.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
}

.card-meta {
  font-size: 11px;
  color: #7A7C80;
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.card-status-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag.draft {
  background: #333333;
  color: #7A7C80;
}

.status-tag.issued {
  background: rgba(255, 104, 162, 0.15);
  color: #FB0079;
}

.status-tag.acknowledged {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}

.sign-status {
  font-size: 11px;
  color: #7A7C80;
}

/* ============ 详情弹窗 ============ */
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  justify-content: center;
  align-items: flex-start;
  padding: 16px;
  z-index: 9999;
  overflow-y: auto;
}

.modal-body {
  background: #000000;
  border: 1px solid #333333;
  border-radius: 16px;
  width: 100%;
  max-width: 480px;
  margin-top: 24px;
  margin-bottom: 24px;
  overflow: hidden;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #222222;
}

.modal-title {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 700;
}

.btn-close {
  background: transparent;
  border: none;
  color: #7A7C80;
  font-size: 28px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
}

.modal-content {
  padding: 20px 16px;
}

.doc-title {
  text-align: center;
  color: #FFFFFF;
  font-size: 18px;
  font-weight: 700;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px dashed #333333;
}

.doc-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.doc-row {
  display: flex;
  font-size: 14px;
  line-height: 1.6;
}

.doc-label {
  flex: 0 0 90px;
  color: #7A7C80;
}

.doc-value {
  flex: 1;
  color: #FFFFFF;
  word-break: break-all;
}

.doc-value.amount {
  color: #FB0079;
  font-weight: 700;
}

.sign-section,
.dispute-section,
.pending-section {
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px dashed #333333;
}

.section-title {
  color: #FB0079;
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
}

.section-title.warn {
  color: #FF8800;
}

.section-title.muted {
  color: #7A7C80;
}

.signature-block {
  margin-top: 12px;
  background: #FFFFFF;
  border-radius: 8px;
  padding: 8px;
}

.signature-block .doc-label {
  color: #555555;
  margin-bottom: 6px;
  display: block;
  flex: none;
}

.signature-img {
  width: 100%;
  height: auto;
  display: block;
}

.no-signature {
  color: #999999;
  font-size: 12px;
  text-align: center;
  padding: 16px;
}

.modal-footer {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #222222;
}

.btn-export {
  flex: 1;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.btn-cancel {
  flex: 1;
  background: #222222;
  color: #FFFFFF;
  border: none;
  padding: 10px;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
}
</style>
