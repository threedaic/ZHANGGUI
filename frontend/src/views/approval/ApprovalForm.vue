<template>
  <div class="approval-form">
    <h3>发起审批</h3>

    <div class="form-row">
      <label>审批类型 <span class="required">*</span></label>
      <select v-model="form.type" class="form-select" @change="onTypeChange">
        <option value="leave">请假</option>
        <option value="makeup">补卡</option>
        <option value="swap">调班</option>
        <option value="expense">报销</option>
      </select>
    </div>

    <!-- 请假子类型 -->
    <div v-if="form.type === 'leave'">
      <div class="form-row">
        <label>请假类型 <span class="required">*</span></label>
        <select v-model="extra.leave_type" class="form-select">
          <option v-for="(v, k) in leaveTypes" :key="k" :value="k">{{ v.label }}</option>
        </select>
      </div>
    </div>

    <div v-if="showDateRange" class="form-row">
      <label>开始日期 <span class="required">*</span></label>
      <el-date-picker
        v-model="form.start_date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择开始日期"
        class="form-picker"
        :clearable="false"
      />
    </div>

    <div v-if="showDateRange" class="form-row">
      <label>结束日期 <span class="required">*</span></label>
      <el-date-picker
        v-model="form.end_date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择结束日期"
        class="form-picker"
        :clearable="false"
        :disabled-date="(d: Date) => form.start_date ? d < new Date(form.start_date) : false"
      />
    </div>

    <div v-if="form.type === 'leave' && form.start_date && form.end_date" class="leave-days-tip">
      共 <strong>{{ leaveDays }}</strong> 天
    </div>

    <div v-if="form.type === 'makeup'" class="form-row">
      <label>补卡日期 <span class="required">*</span></label>
      <el-date-picker
        v-model="extra.date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择补卡日期"
        class="form-picker"
        :clearable="false"
      />
    </div>

    <div v-if="form.type === 'makeup'" class="form-row">
      <label>上班时间 <span class="tip-text">（与下班时间至少填一项）</span></label>
      <el-time-picker
        v-model="extra.clock_in"
        value-format="HH:mm"
        format="HH:mm"
        placeholder="选择上班时间"
        class="form-picker"
      />
    </div>

    <div v-if="form.type === 'makeup'" class="form-row">
      <label>下班时间 <span class="tip-text">（与上班时间至少填一项）</span></label>
      <el-time-picker
        v-model="extra.clock_out"
        value-format="HH:mm"
        format="HH:mm"
        placeholder="选择下班时间"
        class="form-picker"
      />
    </div>

    <div v-if="form.type === 'makeup'" class="form-tip">
      补卡说明：用于打卡异常、漏卡等情况，审批通过后会自动更新考勤记录。
    </div>

    <div v-if="form.type === 'swap'" class="form-row">
      <label>调班对象 <span class="required">*</span></label>
      <select v-model="extra.to_employee_id" class="form-select">
        <option :value="null" disabled>请选择员工</option>
        <option v-for="emp in employeeOptions" :key="emp.id" :value="emp.id">
          {{ emp.name }}{{ emp.role ? `（${roleLabel(emp.role)}）` : '' }}
        </option>
      </select>
    </div>

    <div v-if="form.type === 'swap'" class="form-row">
      <label>调班日期 <span class="required">*</span></label>
      <el-date-picker
        v-model="extra.date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择调班日期"
        class="form-picker"
        :clearable="false"
      />
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>金额（元） <span class="required">*</span></label>
      <input v-model="extra.amount" type="number" step="0.01" min="0.01" class="form-input" placeholder="0.00" />
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>报销分类 <span class="required">*</span></label>
      <select v-model="extra.category" class="form-select">
        <option value="" disabled>请选择分类</option>
        <option value="travel">差旅费</option>
        <option value="meal">餐饮招待</option>
        <option value="office">办公用品</option>
        <option value="transport">交通费</option>
        <option value="communication">通讯费</option>
        <option value="marketing">营销推广</option>
        <option value="maintenance">维修维护</option>
        <option value="other">其他</option>
      </select>
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>发生日期 <span class="required">*</span></label>
      <el-date-picker
        v-model="extra.expense_date"
        type="date"
        value-format="YYYY-MM-DD"
        placeholder="选择费用发生日期"
        class="form-picker"
        :clearable="false"
      />
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>付款方式</label>
      <select v-model="extra.payment_method" class="form-select">
        <option value="personal">个人垫付</option>
        <option value="company">对公支付</option>
        <option value="advance">备用金</option>
      </select>
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>票据号 <span class="tip-text">（选填）</span></label>
      <input v-model="extra.invoice_no" class="form-input" placeholder="发票/收据编号" />
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>附件凭证 <span class="tip-text">（最多5张，单张≤10MB）</span></label>
      <div class="image-uploader">
        <div v-for="(img, idx) in extra.images" :key="idx" class="image-item">
          <img :src="resolveImageUrl(img)" alt="凭证" @click="previewImage(img)" />
          <button class="image-remove" @click="removeImage(idx)" type="button">×</button>
        </div>
        <label v-if="(extra.images || []).length < 5" class="image-add">
          <input type="file" accept="image/jpeg,image/png,image/webp,image/gif" @change="onImageSelected" hidden />
          <span v-if="uploading" class="uploading">上传中...</span>
          <span v-else>＋</span>
        </label>
      </div>
    </div>

    <div v-if="form.type === 'expense'" class="form-row">
      <label>指定审批人 <span class="tip-text">（可选，不选则由店长/老板处理）</span></label>
      <select v-model="form.approver_id" class="form-select">
        <option :value="null">不指定（默认店长/老板）</option>
        <option v-for="a in approverOptions" :key="a.id" :value="a.id">
          {{ a.name }}（{{ roleLabel(a.role) }}）
        </option>
      </select>
    </div>

    <div class="form-row">
      <label>原因 <span class="required">*</span></label>
      <textarea v-model="form.reason" class="form-textarea" rows="3" placeholder="请输入原因（必填）"></textarea>
    </div>

    <button class="submit-btn" :disabled="submitting" @click="handleSubmit">
      {{ submitting ? '提交中...' : '提交审批' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, reactive } from 'vue'
import {
  approvalAPI,
  type ApprovalCreateData,
  type LeaveType,
  type ApproverOption,
} from '@/api/approval'
import { storeAPI } from '@/api/store'
import type { EmployeeBrief } from '@/api/types'

const emit = defineEmits(['submitted'])

const form = ref<ApprovalCreateData>({
  type: 'leave',
  start_date: '',
  end_date: '',
  reason: '',
  extra: {},
  approver_id: null,
})

const extra = ref<any>({
  leave_type: 'comp_off',
  date: '',
  clock_in: '',
  clock_out: '',
  to_employee_id: null,
  amount: null,
  category: '',
  expense_date: '',
  payment_method: 'personal',
  invoice_no: '',
  images: [] as string[],
})
const submitting = ref(false)
const uploading = ref(false)

const leaveTypes = ref<Record<string, LeaveType>>({})
const employeeOptions = ref<EmployeeBrief[]>([])
const approverOptions = ref<ApproverOption[]>([])

const showDateRange = computed(() => ['leave', 'expense'].includes(form.value.type))

const leaveDays = computed(() => {
  if (!form.value.start_date || !form.value.end_date) return 0
  const s = new Date(form.value.start_date)
  const e = new Date(form.value.end_date)
  if (isNaN(s.getTime()) || isNaN(e.getTime())) return 0
  return Math.floor((e.getTime() - s.getTime()) / 86400000) + 1
})

function roleLabel(role: string) {
  const map: Record<string, string> = {
    boss: '老板',
    store_manager: '店长',
    bar_leader: '吧台长',
    staff: '员工',
  }
  return map[role] || role
}

onMounted(async () => {
  // 请假类型（静态字典，几乎不会失败）
  try {
    const typesRes: any = await approvalAPI.getLeaveTypes()
    leaveTypes.value = typesRes.data.data?.types || {}
  } catch (e) {
    // 静默失败
  }

  // 员工列表（调班用，独立容错）
  try {
    const empRes: any = await storeAPI.listEmployees()
    employeeOptions.value = empRes.data.data || []
  } catch (e) {
    // 静默失败
  }

  // 审批人列表（报销用，独立容错）
  try {
    const apprRes: any = await approvalAPI.listApprovers()
    approverOptions.value = apprRes.data.data || []
  } catch (e) {
    // 静默失败
  }
})

function onTypeChange() {
  // 切换类型时重置部分字段
  if (form.value.type !== 'leave') {
    extra.value.leave_type = 'comp_off'
  }
  if (form.value.type !== 'expense') {
    form.value.approver_id = null
  }
}

function resolveImageUrl(url: string) {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return url  // vite 代理会转发 /uploads 到后端
}

function previewImage(url: string) {
  window.open(resolveImageUrl(url), '_blank')
}

function removeImage(idx: number) {
  extra.value.images.splice(idx, 1)
}

async function onImageSelected(e: Event) {
  const input = e.target as HTMLInputElement
  if (!input.files || !input.files[0]) return
  const file = input.files[0]
  if (file.size > 10 * 1024 * 1024) {
    alert('图片大小不能超过 10MB')
    input.value = ''
    return
  }
  uploading.value = true
  try {
    const res: any = await approvalAPI.uploadImage(file)
    const url = res.data?.data?.url
    if (url) {
      if (!extra.value.images) extra.value.images = []
      extra.value.images.push(url)
    }
  } catch (err: any) {
    alert(err.response?.data?.message || '上传失败')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function handleSubmit() {
  // 通用：原因必填
  if (!form.value.reason || !form.value.reason.trim()) {
    alert('请填写原因')
    return
  }

  if (form.value.type === 'leave') {
    if (!form.value.start_date || !form.value.end_date) {
      alert('请填写请假起止日期')
      return
    }
    if (form.value.start_date > form.value.end_date) {
      alert('开始日期不能晚于结束日期')
      return
    }
    if (!extra.value.leave_type) {
      alert('请选择请假类型')
      return
    }
  } else if (form.value.type === 'makeup') {
    if (!extra.value.date) {
      alert('请选择补卡日期')
      return
    }
    if (!extra.value.clock_in && !extra.value.clock_out) {
      alert('请至少填写上班或下班时间')
      return
    }
  } else if (form.value.type === 'swap') {
    if (!extra.value.to_employee_id) {
      alert('请选择调班对象')
      return
    }
    if (!extra.value.date) {
      alert('请选择调班日期')
      return
    }
  } else if (form.value.type === 'expense') {
    if (extra.value.amount === null || extra.value.amount === '' || isNaN(Number(extra.value.amount))) {
      alert('请填写报销金额')
      return
    }
    if (Number(extra.value.amount) <= 0) {
      alert('报销金额必须大于 0')
      return
    }
    if (!extra.value.category) {
      alert('请选择报销分类')
      return
    }
    if (!extra.value.expense_date) {
      alert('请选择费用发生日期')
      return
    }
    if (!extra.value.images || extra.value.images.length === 0) {
      alert('请至少上传一张附件凭证')
      return
    }
  }

  submitting.value = true
  try {
    await approvalAPI.create({
      ...form.value,
      extra: { ...extra.value },
    })
    emit('submitted')
  } catch (e: any) {
    alert(e.response?.data?.message || '提交失败')
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped>
.approval-form {
  padding: 16px;
}

.approval-form h3 {
  margin: 0 0 16px;
  color: #FFFFFF;
  font-size: 16px;
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

.required {
  color: #FB0079;
  margin-left: 2px;
}

.tip-text {
  color: #7A7C80;
  font-size: 11px;
  margin-left: 4px;
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: 8px;
  border: 1px solid #333333;
  border-radius: 8px;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
  box-sizing: border-box;
}

.form-textarea {
  resize: none;
}

/* Element Plus 日期/时间选择器暗色适配 */
.form-picker {
  width: 100%;
}

.form-picker :deep(.el-input__wrapper) {
  background: #111111;
  border: 1px solid #333333;
  box-shadow: none;
  border-radius: 8px;
  padding: 4px 8px;
}

.form-picker :deep(.el-input__wrapper:hover) {
  border-color: #FB0079;
}

.form-picker :deep(.el-input__wrapper.is-focus) {
  border-color: #FB0079;
  box-shadow: 0 0 0 1px #FB0079 inset;
}

.form-picker :deep(.el-input__inner) {
  color: #FFFFFF;
  font-size: 13px;
}

.form-picker :deep(.el-input__inner::placeholder) {
  color: #7A7C80;
}

.form-picker :deep(.el-input__prefix),
.form-picker :deep(.el-input__suffix) {
  color: #7A7C80;
}

.form-tip {
  font-size: 11px;
  color: #7A7C80;
  padding: 6px 8px;
  background: rgba(251, 0, 121, 0.05);
  border-radius: 6px;
  margin-bottom: 12px;
}

.leave-days-tip {
  font-size: 12px;
  color: #C8C8C8;
  padding: 8px 10px;
  background: rgba(33, 150, 243, 0.08);
  border-radius: 6px;
  margin-bottom: 12px;
}

.leave-days-tip strong {
  color: #2196f3;
  font-size: 14px;
}

.submit-btn {
  width: 100%;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.submit-btn:disabled {
  opacity: 0.4;
}

/* 图片上传器 */
.image-uploader {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 4px;
}

.image-item {
  position: relative;
  width: 72px;
  height: 72px;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #333333;
}

.image-item img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  cursor: pointer;
}

.image-remove {
  position: absolute;
  top: 2px;
  right: 2px;
  width: 18px;
  height: 18px;
  border: none;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.7);
  color: #FFFFFF;
  font-size: 14px;
  line-height: 1;
  cursor: pointer;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
}

.image-add {
  width: 72px;
  height: 72px;
  border: 1px dashed #444444;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #7A7C80;
  font-size: 24px;
  background: #111111;
}

.image-add:hover {
  border-color: #FB0079;
  color: #FB0079;
}

.image-add .uploading {
  font-size: 11px;
}
</style>
