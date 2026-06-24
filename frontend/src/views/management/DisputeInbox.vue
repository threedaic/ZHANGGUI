<script setup lang="ts">
// 工资申诉收件箱（管理端 - 老板/店长视角）
import { ref, onMounted, computed } from 'vue'
import { getDisputes, getDisputeStats, rejectDispute, confirmDispute, type WageDispute, type DisputeStats } from '@/api/disputes'

const disputes = ref<WageDispute[]>([])
const stats = ref<DisputeStats>({ total: 0, pending: 0, confirmed: 0, rejected: 0, adjusted: 0 })
const loading = ref(false)
const activeTab = ref('pending')
const selectedDispute = ref<WageDispute | null>(null)
const showDetail = ref(false)

// 处理表单
const rejectForm = ref({ resolution: '' })
const confirmForm = ref({ adjusted_amount: 0, adjusted_in_period: '', resolution: '' })
const processing = ref(false)

const tabs = [
  { key: 'pending', label: '待处理', color: '#f59e0b' },
  { key: 'confirmed', label: '已确认', color: '#10b981' },
  { key: 'rejected', label: '已驳回', color: '#ef4444' },
  { key: 'adjusted', label: '已调整', color: '#6366f1' },
]

const typeMap: Record<string, string> = {
  less: '少发',
  more: '多发',
  wrong_formula: '公式错误',
  other: '其他',
}

async function load() {
  loading.value = true
  try {
    const [disputesRes, statsRes] = await Promise.all([
      getDisputes(activeTab.value),
      getDisputeStats(),
    ])
    disputes.value = disputesRes.data.data ?? []
    stats.value = statsRes.data.data ?? stats.value
  } catch {
    disputes.value = []
  } finally {
    loading.value = false
  }
}

function openDetail(d: WageDispute) {
  selectedDispute.value = d
  showDetail.value = true
  rejectForm.value = { resolution: '' }
  confirmForm.value = { adjusted_amount: 0, adjusted_in_period: '', resolution: '' }
}

async function handleReject() {
  if (!selectedDispute.value || !rejectForm.value.resolution) return
  processing.value = true
  try {
    await rejectDispute(selectedDispute.value.dispute_id, rejectForm.value.resolution)
    showDetail.value = false
    await load()
  } catch {} finally { processing.value = false }
}

async function handleConfirm() {
  if (!selectedDispute.value || !confirmForm.value.adjusted_amount) return
  processing.value = true
  try {
    await confirmDispute(selectedDispute.value.dispute_id, {
      adjusted_amount: confirmForm.value.adjusted_amount,
      adjusted_in_period: confirmForm.value.adjusted_in_period || undefined,
      resolution: confirmForm.value.resolution || undefined,
    })
    showDetail.value = false
    await load()
  } catch {} finally { processing.value = false }
}

function formatDate(s: string | null) {
  if (!s) return '-'
  return new Date(s).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

onMounted(load)
</script>

<template>
  <div class="dispute-inbox">
    <!-- 统计卡片 -->
    <div class="stats-bar">
      <div class="stat-item" :class="{ active: activeTab === 'pending' }" @click="activeTab = 'pending'; load()">
        <span class="stat-num">{{ stats.pending }}</span>
        <span class="stat-label">待处理</span>
      </div>
      <div class="stat-item" :class="{ active: activeTab === 'confirmed' }" @click="activeTab = 'confirmed'; load()">
        <span class="stat-num">{{ stats.confirmed }}</span>
        <span class="stat-label">已确认</span>
      </div>
      <div class="stat-item" :class="{ active: activeTab === 'rejected' }" @click="activeTab = 'rejected'; load()">
        <span class="stat-num">{{ stats.rejected }}</span>
        <span class="stat-label">已驳回</span>
      </div>
      <div class="stat-item" :class="{ active: activeTab === 'adjusted' }" @click="activeTab = 'adjusted'; load()">
        <span class="stat-num">{{ stats.adjusted }}</span>
        <span class="stat-label">已调整</span>
      </div>
    </div>

    <!-- 申诉列表 -->
    <div v-loading="loading" class="list">
      <div v-if="disputes.length === 0 && !loading" class="empty-state">
        {{ activeTab === 'pending' ? '暂无待处理申诉' : '暂无记录' }}
      </div>
      <div v-for="d in disputes" :key="d.dispute_id" class="dispute-card" @click="openDetail(d)">
        <div class="card-header">
          <div class="employee-info">
            <span class="name">{{ d.employee_name }}</span>
            <span class="period">{{ d.period }}</span>
          </div>
          <span class="type-tag">{{ typeMap[d.dispute_type] }}</span>
        </div>
        <div class="card-body">
          <p class="reason">{{ d.reason }}</p>
          <div class="amounts">
            <span>原工资：¥{{ d.original_amount?.toFixed(2) ?? '-' }}</span>
            <span v-if="d.expected_amount">期望：¥{{ d.expected_amount.toFixed(2) }}</span>
          </div>
        </div>
        <div class="card-footer">
          <span class="time">{{ formatDate(d.created_at) }}</span>
          <span v-if="d.status === 'pending'" class="action-hint">点击处理</span>
        </div>
      </div>
    </div>

    <!-- 详情/处理弹窗 -->
    <div v-if="showDetail && selectedDispute" class="modal-overlay" @click.self="showDetail = false">
      <div class="modal-content">
        <div class="detail-header">
          <h3>{{ selectedDispute.employee_name }} 的工资申诉</h3>
          <span class="period-tag">{{ selectedDispute.period }}</span>
        </div>

        <div class="detail-section">
          <div class="info-row"><span class="label">申诉类型</span><span>{{ typeMap[selectedDispute.dispute_type] }}</span></div>
          <div class="info-row"><span class="label">原工资</span><span>¥{{ selectedDispute.original_amount?.toFixed(2) }}</span></div>
          <div v-if="selectedDispute.expected_amount" class="info-row"><span class="label">期望金额</span><span>¥{{ selectedDispute.expected_amount.toFixed(2) }}</span></div>
          <div class="info-row"><span class="label">申诉原因</span></div>
          <p class="reason-text">{{ selectedDispute.reason }}</p>
          <div v-if="selectedDispute.resolution" class="resolution-box">
            <span class="label">处理结果：</span>{{ selectedDispute.resolution }}
          </div>
        </div>

        <!-- 待处理状态：显示处理按钮 -->
        <div v-if="selectedDispute.status === 'pending'" class="action-section">
          <div class="action-tabs">
            <button class="tab-btn reject" :class="{ active: activeTab === 'reject' }" @click="activeTab = 'reject'">驳回</button>
            <button class="tab-btn confirm" :class="{ active: activeTab === 'confirm' }" @click="activeTab = 'confirm'">确认有误</button>
          </div>

          <!-- 驳回表单 -->
          <div v-if="activeTab === 'reject'" class="action-form">
            <div class="form-group">
              <label>驳回原因 <span class="required">*</span></label>
              <textarea v-model="rejectForm.resolution" rows="3" placeholder="说明为什么驳回..." />
            </div>
            <button class="btn-reject" :disabled="!rejectForm.resolution || processing" @click="handleReject">
              {{ processing ? '处理中...' : '确认驳回' }}
            </button>
          </div>

          <!-- 确认有误表单 -->
          <div v-if="activeTab === 'confirm'" class="action-form">
            <div class="form-group">
              <label>调整金额 <span class="required">*</span></label>
              <div class="amount-hint">正数=补发给员工，负数=从下月扣回</div>
              <input v-model.number="confirmForm.adjusted_amount" type="number" placeholder="例：+500 或 -300" />
            </div>
            <div class="form-group">
              <label>调整月份（可选）</label>
              <input v-model="confirmForm.adjusted_in_period" type="text" placeholder="如：2026-07（默认下月）" />
            </div>
            <div class="form-group">
              <label>处理说明</label>
              <textarea v-model="confirmForm.resolution" rows="2" placeholder="备注..." />
            </div>
            <button class="btn-confirm" :disabled="!confirmForm.adjusted_amount || processing" @click="handleConfirm">
              {{ processing ? '处理中...' : '确认调整' }}
            </button>
          </div>
        </div>

        <button class="btn-close" @click="showDetail = false">关闭</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.dispute-inbox { padding: 16px; max-width: 600px; margin: 0 auto; }
.stats-bar { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 16px; }
.stat-item { background: #fff; border-radius: 12px; padding: 12px; text-align: center; cursor: pointer; border: 2px solid transparent; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.stat-item.active { border-color: #FB0079; }
.stat-num { display: block; font-size: 24px; font-weight: 700; color: #1f2937; }
.stat-label { display: block; font-size: 12px; color: #9ca3af; margin-top: 4px; }
.empty-state { text-align: center; padding: 40px; color: #9ca3af; }
.dispute-card { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 10px; cursor: pointer; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.dispute-card:active { background: #f9fafb; }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.employee-info .name { font-weight: 600; font-size: 15px; margin-right: 8px; }
.employee-info .period { font-size: 13px; color: #9ca3af; }
.type-tag { font-size: 12px; background: #fdf2f8; color: #FB0079; padding: 2px 8px; border-radius: 6px; }
.card-body .reason { font-size: 14px; color: #374151; margin: 0 0 8px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.card-body .amounts { display: flex; gap: 16px; font-size: 13px; color: #6b7280; }
.card-footer { display: flex; justify-content: space-between; margin-top: 10px; font-size: 12px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 8px; }
.action-hint { color: #FB0079; font-weight: 500; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 16px; padding: 24px; width: 90%; max-width: 500px; max-height: 85vh; overflow-y: auto; }
.detail-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.detail-header h3 { margin: 0; font-size: 17px; }
.period-tag { font-size: 13px; background: #e5e7eb; padding: 4px 10px; border-radius: 6px; }
.detail-section { margin-bottom: 16px; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }
.info-row .label { color: #9ca3af; }
.reason-text { font-size: 14px; color: #374151; background: #f9fafb; padding: 12px; border-radius: 8px; margin: 8px 0; }
.resolution-box { background: #f0fdf4; padding: 12px; border-radius: 8px; font-size: 14px; margin-top: 12px; }
.resolution-box .label { color: #9ca3af; }
.action-section { border-top: 1px solid #e5e7eb; padding-top: 16px; margin-top: 16px; }
.action-tabs { display: flex; gap: 8px; margin-bottom: 16px; }
.tab-btn { flex: 1; padding: 10px; border: 2px solid #e5e7eb; border-radius: 8px; background: #fff; cursor: pointer; font-size: 14px; font-weight: 500; }
.tab-btn.reject.active { border-color: #ef4444; background: #fef2f2; color: #ef4444; }
.tab-btn.confirm.active { border-color: #10b981; background: #f0fdf4; color: #10b981; }
.form-group { margin-bottom: 12px; }
.form-group label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 6px; }
.form-group .required { color: #ef4444; }
.amount-hint { font-size: 12px; color: #9ca3af; margin-bottom: 4px; }
.form-group input, .form-group textarea { width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; font-size: 14px; box-sizing: border-box; }
.form-group textarea { resize: vertical; }
.btn-reject { width: 100%; background: #ef4444; color: #fff; border: none; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn-reject:disabled { opacity: 0.5; }
.btn-confirm { width: 100%; background: #10b981; color: #fff; border: none; padding: 12px; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn-confirm:disabled { opacity: 0.5; }
.btn-close { width: 100%; background: #f3f4f6; color: #374151; border: none; padding: 10px; border-radius: 8px; font-size: 14px; cursor: pointer; margin-top: 12px; }
</style>
