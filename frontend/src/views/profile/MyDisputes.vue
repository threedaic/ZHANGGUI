<script setup lang="ts">
// 我的工资申诉（员工视角）
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getMyDisputes, createDispute, type WageDispute } from '@/api/disputes'
import { getMyPayroll, type MyPayrollItem } from '@/api/payroll'

const route = useRoute()
const router = useRouter()
const disputes = ref<WageDispute[]>([])
const loading = ref(false)
const showForm = ref(false)

// 申诉表单
const form = ref({
  wage_id: '',
  dispute_type: 'less' as string,
  expected_amount: undefined as number | undefined,
  reason: '',
})

const disputeTypeOptions = [
  { value: 'less', label: '少发了', desc: '实际到手比应得少' },
  { value: 'more', label: '多发了', desc: '实际到手比应得多' },
  { value: 'wrong_formula', label: '公式算错', desc: '工资计算公式有误' },
  { value: 'other', label: '其他', desc: '其他工资相关问题' },
]

const statusMap: Record<string, { label: string; color: string }> = {
  pending: { label: '待处理', color: '#f59e0b' },
  confirmed: { label: '已确认有误', color: '#10b981' },
  rejected: { label: '已驳回', color: '#ef4444' },
  adjusted: { label: '已调整', color: '#6366f1' },
}

const typeMap: Record<string, string> = {
  less: '少发',
  more: '多发',
  wrong_formula: '公式错误',
  other: '其他',
}

async function load() {
  loading.value = true
  try {
    const res = await getMyDisputes()
    disputes.value = res.data.data ?? []
  } catch {
    disputes.value = []
  } finally {
    loading.value = false
  }
}

async function submitDispute() {
  if (!form.value.wage_id || !form.value.reason) return
  try {
    await createDispute({
      wage_id: form.value.wage_id,
      dispute_type: form.value.dispute_type,
      expected_amount: form.value.expected_amount,
      reason: form.value.reason,
    })
    showForm.value = false
    form.value = { wage_id: '', dispute_type: 'less', expected_amount: undefined, reason: '' }
    await load()
  } catch {}
}

function formatDate(s: string | null) {
  if (!s) return '-'
  return new Date(s).toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' })
}

onMounted(() => {
  load()
  // 如果从工资详情页跳转过来，自动打开申诉表单
  if (route.query.wage_id) {
    form.value.wage_id = route.query.wage_id as string
    showForm.value = true
  }
})
</script>

<template>
  <div class="my-disputes">
    <div class="page-header">
      <h3>工资申诉</h3>
      <button class="btn-primary" @click="showForm = true">发起申诉</button>
    </div>

    <!-- 申诉列表 -->
    <div v-loading="loading" class="list">
      <div v-if="disputes.length === 0 && !loading" class="empty-state">
        暂无申诉记录
      </div>
      <div v-for="d in disputes" :key="d.dispute_id" class="dispute-card">
        <div class="card-header">
          <span class="period">{{ d.period }} 月工资</span>
          <span class="status-badge" :style="{ color: statusMap[d.status]?.color }">
            {{ statusMap[d.status]?.label }}
          </span>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">申诉类型</span>
            <span>{{ typeMap[d.dispute_type] }}</span>
          </div>
          <div class="info-row">
            <span class="label">原工资</span>
            <span>¥{{ d.original_amount?.toFixed(2) ?? '-' }}</span>
          </div>
          <div v-if="d.expected_amount" class="info-row">
            <span class="label">期望金额</span>
            <span>¥{{ d.expected_amount.toFixed(2) }}</span>
          </div>
          <div class="info-row">
            <span class="label">申诉原因</span>
            <span class="reason">{{ d.reason }}</span>
          </div>
          <div v-if="d.resolution" class="info-row resolution">
            <span class="label">处理结果</span>
            <span>{{ d.resolution }}</span>
          </div>
          <div v-if="d.adjusted_amount" class="info-row">
            <span class="label">调整金额</span>
            <span :style="{ color: d.adjusted_amount > 0 ? '#10b981' : '#ef4444' }">
              {{ d.adjusted_amount > 0 ? '+' : '' }}¥{{ d.adjusted_amount.toFixed(2) }}
            </span>
          </div>
        </div>
        <div class="card-footer">
          <span class="time">{{ formatDate(d.created_at) }}</span>
          <span v-if="d.reviewer_name" class="reviewer">处理人：{{ d.reviewer_name }}</span>
        </div>
      </div>
    </div>

    <!-- 申诉表单弹窗 -->
    <div v-if="showForm" class="modal-overlay" @click.self="showForm = false">
      <div class="modal-content">
        <h3>发起工资申诉</h3>

        <div class="form-group">
          <label>申诉类型</label>
          <div class="type-options">
            <div
              v-for="opt in disputeTypeOptions"
              :key="opt.value"
              class="type-option"
              :class="{ active: form.dispute_type === opt.value }"
              @click="form.dispute_type = opt.value"
            >
              <span class="opt-label">{{ opt.label }}</span>
              <span class="opt-desc">{{ opt.desc }}</span>
            </div>
          </div>
        </div>

        <div class="form-group">
          <label>期望金额（可选）</label>
          <input v-model.number="form.expected_amount" type="number" placeholder="您认为正确的工资金额" />
        </div>

        <div class="form-group">
          <label>申诉原因 <span class="required">*</span></label>
          <textarea v-model="form.reason" rows="4" placeholder="请详细说明工资哪里有问题..." />
        </div>

        <div class="form-actions">
          <button class="btn-secondary" @click="showForm = false">取消</button>
          <button class="btn-primary" :disabled="!form.reason" @click="submitDispute">提交申诉</button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.my-disputes { padding: 16px; max-width: 600px; margin: 0 auto; }
.page-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.page-header h3 { margin: 0; font-size: 18px; }
.btn-primary { background: #FB0079; color: #fff; border: none; padding: 8px 16px; border-radius: 8px; font-size: 14px; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-secondary { background: #f3f4f6; color: #374151; border: none; padding: 8px 16px; border-radius: 8px; font-size: 14px; cursor: pointer; }
.empty-state { text-align: center; padding: 40px; color: #9ca3af; }
.dispute-card { background: #fff; border-radius: 12px; padding: 16px; margin-bottom: 12px; box-shadow: 0 1px 3px rgba(0,0,0,0.08); }
.card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.period { font-weight: 600; font-size: 15px; }
.status-badge { font-size: 13px; font-weight: 500; }
.info-row { display: flex; justify-content: space-between; padding: 6px 0; font-size: 14px; }
.info-row .label { color: #9ca3af; }
.info-row .reason { max-width: 60%; text-align: right; }
.info-row.resolution { background: #f0fdf4; padding: 8px; border-radius: 8px; margin-top: 8px; }
.card-footer { display: flex; justify-content: space-between; margin-top: 12px; font-size: 12px; color: #9ca3af; border-top: 1px solid #f3f4f6; padding-top: 8px; }
.modal-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.5); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal-content { background: #fff; border-radius: 16px; padding: 24px; width: 90%; max-width: 480px; max-height: 80vh; overflow-y: auto; }
.modal-content h3 { margin: 0 0 20px; font-size: 18px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 14px; font-weight: 500; margin-bottom: 8px; }
.form-group .required { color: #ef4444; }
.form-group input, .form-group textarea { width: 100%; border: 1px solid #e5e7eb; border-radius: 8px; padding: 10px 12px; font-size: 14px; box-sizing: border-box; }
.form-group textarea { resize: vertical; }
.type-options { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.type-option { border: 2px solid #e5e7eb; border-radius: 10px; padding: 12px; cursor: pointer; text-align: center; }
.type-option.active { border-color: #FB0079; background: #fdf2f8; }
.opt-label { display: block; font-weight: 600; font-size: 14px; }
.opt-desc { display: block; font-size: 11px; color: #9ca3af; margin-top: 4px; }
.form-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px; }
</style>
