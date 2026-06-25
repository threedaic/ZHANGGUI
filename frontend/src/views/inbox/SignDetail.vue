<template>
  <div class="sign-detail-page">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="loadError" class="error-state">
      <div class="error-icon">!</div>
      <div class="error-text">{{ loadError }}</div>
      <button class="btn-retry" @click="loadDetail">重试</button>
    </div>
    <template v-else-if="detail">
      <!-- 标题区域 -->
      <div class="detail-header">
        <h2 class="detail-title">{{ detail.title }}</h2>
        <span class="detail-type">{{ typeLabel(detail.type) }}</span>
      </div>

      <!-- 业务数据内容区域 -->
      <div class="detail-content card-section">
        <template v-if="detail.type === 'salary_slip'">
          <div class="salary-section">
            <div class="salary-row">
              <span>实发金额</span>
              <span class="salary-amount">¥{{ formatMoney(extraData?.net_pay) }}</span>
            </div>
            <div class="salary-row">
              <span>工资月份</span>
              <span>{{ detail.extra?.period }}</span>
            </div>
            <div class="salary-row">
              <span>员工</span>
              <span>{{ detail.extra?.employee_name || detail.employee_name }}</span>
            </div>
          </div>
        </template>

        <template v-else-if="detail.type === 'penalty_notice'">
          <div class="penalty-section">
            <div class="info-row">
              <span class="info-label">处罚类型</span>
              <span class="info-value">{{ detail.extra?.penalty_label || detail.extra?.penalty_type_name || penaltyTypeNames[extraData?.penalty_type] || detail.extra?.penalty_type }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">罚款金额</span>
              <span class="info-value amount">¥{{ detail.extra?.amount }}</span>
            </div>
            <div class="info-row reason">
              <span class="info-label">事由</span>
              <span class="info-value">{{ detail.extra?.reason }}</span>
            </div>
          </div>
        </template>

        <template v-else-if="detail.type === 'attendance_confirm'">
          <div class="attendance-section">
            <div class="info-row">
              <span class="info-label">考勤月份</span>
              <span class="info-value">{{ detail.extra?.period }}</span>
            </div>
            <div class="info-row">
              <span class="info-label">员工</span>
              <span class="info-value">{{ detail.employee_name }}</span>
            </div>
          </div>
        </template>

        <div class="info-row">
          <span class="info-label">发布人</span>
          <span class="info-value">{{ detail.issued_by_name }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">发布时间</span>
          <span class="info-value">{{ formatDate(detail.issued_at) }}</span>
        </div>
      </div>

      <!-- 已签收时显示签名 -->
      <div v-if="detail.status === 'signed' && detail.signature_data" class="signed-preview card-section">
        <div class="section-label">已签收</div>
        <img :src="detail.signature_data" class="signature-img" alt="签名" />
        <div class="signed-time">签收时间: {{ formatDate(detail.signed_at) }}</div>
        <div v-if="detail.notes" class="signed-notes">备注: {{ detail.notes }}</div>
      </div>

      <!-- 异议状态 -->
      <div v-if="detail.status === 'disputed'" class="disputed-info card-section">
        <div class="section-label">已提出异议</div>
        <div class="dispute-reason">{{ detail.dispute_reason }}</div>
        <div class="signed-time">提交时间: {{ formatDate(detail.disputed_at) }}</div>
      </div>

      <!-- 待签收：签名 + 操作 -->
      <div v-if="detail.status === 'pending'">
        <SignaturePad ref="signatureRef" />

        <div class="sign-actions">
          <button class="btn-primary" @click="handleSign" :disabled="signing">
            {{ signing ? '签收中...' : '确认签收' }}
          </button>
          <button class="btn-secondary" @click="showDispute = true">
            有异议，反馈
          </button>
        </div>

        <!-- 异议弹窗 -->
        <div v-if="showDispute" class="dispute-dialog">
          <div class="dialog-mask" @click="showDispute = false"></div>
          <div class="dialog-panel">
            <div class="dialog-title">提出异议</div>
            <textarea v-model="disputeReason" class="dispute-input" placeholder="请说明异议原因..." maxlength="500"></textarea>
            <div class="dialog-actions">
              <button class="btn-cancel" @click="showDispute = false">取消</button>
              <button class="btn-submit" @click="handleDispute" :disabled="!disputeReason.trim() || disputing">
                {{ disputing ? '提交中...' : '提交' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { signTaskAPI, type SignTaskItem } from '@/api/sign-tasks'
import SignaturePad from '@/components/SignaturePad.vue'

const route = useRoute()
const router = useRouter()

const detail = ref<SignTaskItem | null>(null)
const loading = ref(false)
const loadError = ref('')
const signing = ref(false)
const disputing = ref(false)
const showDispute = ref(false)
const disputeReason = ref('')
const signatureRef = ref<InstanceType<typeof SignaturePad> | null>(null)

// 将 extra (Record<string, unknown> | null) 转为可索引的记录，便于模板访问
const extraData = computed<Record<string, any> | undefined>(() => detail.value?.extra ?? undefined)

const typeLabels: Record<string, string> = {
  salary_slip: '工资单',
  penalty_notice: '处罚通知',
  attendance_confirm: '考勤确认',
}

const penaltyTypeNames: Record<string, string> = {
  penalty_complaint: '服务投诉',
  penalty_antifraud: '飞单处罚',
  penalty_other: '严重违纪',
}

function typeLabel(type: string): string {
  return typeLabels[type] || type
}

function formatMoney(n: number | undefined): string {
  if (n == null) return '0'
  return n.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

function formatDate(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  return d.toLocaleDateString('zh-CN') + ' ' + d.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function loadDetail() {
  const id = String(route.params.id || '')
  if (!id) {
    loadError.value = '缺少任务ID'
    return
  }
  loading.value = true
  loadError.value = ''
  try {
    const res = await signTaskAPI.getDetail(id)
    detail.value = res.data.data
    if (!detail.value) {
      loadError.value = '未找到该签收任务'
    }
  } catch (e: any) {
    const msg = e?.response?.data?.message || e?.message || '加载失败'
    loadError.value = msg
  } finally {
    loading.value = false
  }
}

async function handleSign() {
  const pad = signatureRef.value
  if (!pad || pad.isEmpty()) {
    loadError.value = '请先手写签名'
    return
  }
  signing.value = true
  loadError.value = ''
  try {
    const dataURL = pad.getDataURL()
    await signTaskAPI.sign(detail.value!.id, dataURL)
    await loadDetail()
  } catch (e: any) {
    loadError.value = '签收失败: ' + (e?.response?.data?.message || e?.message || '未知错误')
  } finally {
    signing.value = false
  }
}

async function handleDispute() {
  if (!disputeReason.value.trim()) return
  disputing.value = true
  loadError.value = ''
  try {
    await signTaskAPI.dispute(detail.value!.id, disputeReason.value.trim())
    showDispute.value = false
    await loadDetail()
  } catch (e: any) {
    loadError.value = '提交异议失败: ' + (e?.response?.data?.message || e?.message || '未知错误')
  } finally {
    disputing.value = false
  }
}

onMounted(loadDetail)

// 路由参数变化时重新加载（同组件跳转场景）
watch(() => route.params.id, (newId) => {
  if (newId) loadDetail()
})
</script>

<style scoped>
.sign-detail-page {
  padding: 0 16px;
  padding-bottom: 24px;
}

.loading {
  text-align: center;
  color: #7A7C80;
  padding: 48px;
}

.error-state {
  text-align: center;
  padding: 48px 16px;
}

.error-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
  border-radius: 50%;
  font-size: 20px;
  font-weight: 700;
  margin-bottom: 12px;
}

.error-text {
  font-size: 14px;
  color: #C8C8C8;
  margin-bottom: 16px;
  word-break: break-all;
}

.btn-retry {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  padding: 8px 24px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}

.detail-header {
  padding: 16px 0;
  display: flex;
  align-items: center;
  gap: 12px;
}

.detail-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.detail-type {
  font-size: 11px;
  color: #7A7C80;
  padding: 2px 8px;
  border: 1px solid #333333;
  border-radius: 4px;
}

.card-section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #1a1a1a;
}

.info-row:last-child {
  border-bottom: none;
}

.info-row.reason {
  flex-direction: column;
  gap: 4px;
}

.info-label {
  font-size: 13px;
  color: #7A7C80;
}

.info-value {
  font-size: 13px;
  color: #C8C8C8;
}

.info-value.amount {
  color: #FB0079;
  font-weight: 600;
}

.salary-section .salary-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid #1a1a1a;
  font-size: 13px;
  color: #C8C8C8;
}

.salary-row:last-child {
  border-bottom: none;
}

.salary-amount {
  color: #FB0079;
  font-weight: 700;
  font-size: 16px;
}

.signed-preview {
  text-align: center;
}

.signature-img {
  max-width: 100%;
  max-height: 120px;
  background: #1a1a1a;
  border-radius: 8px;
  padding: 8px;
}

.signed-time,
.signed-notes {
  font-size: 12px;
  color: #7A7C80;
  margin-top: 8px;
}

.disputed-info {
  border-left: 3px solid #FB0079;
}

.dispute-reason {
  font-size: 13px;
  color: #C8C8C8;
  line-height: 1.6;
  padding: 8px 0;
}

.sign-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 16px 0;
}

.btn-primary {
  width: 100%;
  padding: 14px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-secondary {
  width: 100%;
  padding: 12px;
  background: transparent;
  color: #7A7C80;
  border: 1px solid #333333;
  border-radius: 10px;
  font-size: 13px;
  cursor: pointer;
}

/* Dispute dialog */
.dispute-dialog {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 100;
  display: flex;
  align-items: flex-end;
}

.dialog-mask {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
}

.dialog-panel {
  position: relative;
  width: 100%;
  background: #111111;
  border-radius: 14px 14px 0 0;
  padding: 20px 16px;
  padding-bottom: calc(20px + env(safe-area-inset-bottom));
  z-index: 1;
}

.dialog-title {
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 12px;
}

.dispute-input {
  width: 100%;
  height: 100px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  padding: 12px;
  resize: none;
  outline: none;
  font-family: inherit;
}

.dispute-input:focus {
  border-color: #FB0079;
}

.dialog-actions {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

.btn-cancel {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #7A7C80;
  font-size: 14px;
  cursor: pointer;
}

.btn-submit {
  flex: 1;
  padding: 12px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-submit:disabled {
  opacity: 0.5;
}
</style>
