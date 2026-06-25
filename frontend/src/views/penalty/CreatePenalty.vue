<template>
  <div class="create-penalty-page">
    <!-- 奖励/惩罚切换 -->
    <div class="mode-switch">
      <button
        class="mode-btn penalty"
        :class="{ active: mode === 'penalty' }"
        @click="switchMode('penalty')"
      >
        惩罚单
      </button>
      <button
        class="mode-btn reward"
        :class="{ active: mode === 'reward' }"
        @click="switchMode('reward')"
      >
        奖励单
      </button>
    </div>

    <div class="form-group">
      <label class="form-label">员工</label>
      <select v-model="form.employee_id" class="form-select">
        <option :value="''" disabled>请选择员工</option>
        <option v-for="emp in employees" :key="emp.id" :value="emp.id">
          {{ emp.name }} ({{ emp.role || 'staff' }})
        </option>
      </select>
    </div>

    <div class="form-group">
      <label class="form-label">{{ mode === 'reward' ? '奖励' : '处罚' }}类型</label>
      <div class="type-grid">
        <button
          v-for="t in filteredTypes"
          :key="t.value"
          class="type-option"
          :class="{ selected: form.penalty_type === t.value }"
          @click="form.penalty_type = t.value"
        >
          {{ t.label }}
        </button>
      </div>
    </div>

    <div class="form-group">
      <label class="form-label">{{ mode === 'reward' ? '奖励' : '罚款' }}金额 (¥)</label>
      <input
        v-model.number="form.amount"
        type="number"
        class="form-input"
        placeholder="0"
        min="0"
        step="0.01"
      />
    </div>

    <div class="form-group">
      <label class="form-label">事由说明</label>
      <textarea
        v-model="form.reason"
        class="form-textarea"
        :placeholder="mode === 'reward' ? '请说明奖励事由...' : '请详细说明处罚事由...'"
        maxlength="2000"
      ></textarea>
    </div>

    <button
      class="btn-submit"
      :class="mode"
      :disabled="!valid || submitting"
      @click="handleSubmit"
    >
      {{ submitting ? '发布中...' : (mode === 'reward' ? '发布奖励通知' : '发布处罚通知') }}
    </button>
    <div class="hint">发布后员工将收到签收提醒，需签名确认。</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { penaltyAPI, type PenaltyTypeOption } from '@/api/penalties'
import { storeAPI } from '@/api/store'

const router = useRouter()
const submitting = ref(false)
const mode = ref<'penalty' | 'reward'>('penalty')

interface EmployeeOption {
  id: string
  name: string
  role: string
}

const employees = ref<EmployeeOption[]>([])
const allTypes = ref<PenaltyTypeOption[]>([])

const form = ref({
  employee_id: '' as string,
  penalty_type: 'penalty_complaint',
  amount: 0,
  reason: '',
})

// 按模式过滤类型
const filteredTypes = computed(() => {
  return allTypes.value.filter((t) => {
    if (mode.value === 'reward') return t.value.startsWith('reward_')
    return t.value.startsWith('penalty_')
  })
})

const valid = computed(() => {
  return form.value.employee_id !== ''
    && form.value.penalty_type
    && form.value.amount >= 0
    && form.value.reason.trim().length > 0
})

function switchMode(m: 'penalty' | 'reward') {
  mode.value = m
  // 切换模式时自动选第一个类型
  const types = filteredTypes.value
  if (types.length > 0) {
    form.value.penalty_type = types[0].value
  }
}

async function loadEmployees() {
  try {
    const res = await storeAPI.listEmployees()
    if (res.data.code === 0 && Array.isArray(res.data.data)) {
      employees.value = res.data.data.map((e) => ({
        id: e.id,
        name: e.name,
        role: e.role || 'staff',
      }))
    }
  } catch (e) {
    console.error('[CreatePenalty] loadEmployees failed:', e instanceof Error ? e.message : String(e))
  }
}

async function loadTypes() {
  try {
    const res = await penaltyAPI.getTypes()
    allTypes.value = res.data.data || []
    // 默认选第一个惩罚类型
    const firstPenalty = allTypes.value.find((t) => t.value.startsWith('penalty_'))
    if (firstPenalty) {
      form.value.penalty_type = firstPenalty.value
    }
  } catch { /* */ }
}

async function handleSubmit() {
  if (!valid.value) return
  submitting.value = true
  try {
    await penaltyAPI.create({
      employee_id: form.value.employee_id,
      penalty_type: form.value.penalty_type,
      amount: form.value.amount,
      reason: form.value.reason.trim(),
    })
    router.replace('/management/penalties')
  } catch { /* */ }
  submitting.value = false
}

onMounted(() => {
  loadEmployees()
  loadTypes()
})
</script>

<style scoped>
.create-penalty-page {
  padding: 0 16px;
  padding-bottom: 24px;
}

/* 奖励/惩罚切换 */
.mode-switch {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}

.mode-btn {
  flex: 1;
  padding: 12px;
  border: 1px solid #333333;
  border-radius: 10px;
  background: #111111;
  color: #7A7C80;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.mode-btn.penalty.active {
  border-color: #FB0079;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
}

.mode-btn.reward.active {
  border-color: #4CAF50;
  color: #4CAF50;
  background: rgba(76, 175, 80, 0.08);
}

.form-group {
  margin-bottom: 20px;
}

.form-label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
  margin-bottom: 8px;
}

.form-select,
.form-input {
  width: 100%;
  padding: 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
  font-family: inherit;
}

.form-select:focus,
.form-input:focus {
  border-color: #FB0079;
}

.form-textarea {
  width: 100%;
  height: 120px;
  padding: 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
  resize: none;
  font-family: inherit;
}

.form-textarea:focus {
  border-color: #FB0079;
}

.type-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}

.type-option {
  padding: 10px 8px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #7A7C80;
  font-size: 12px;
  cursor: pointer;
  text-align: center;
}

.type-option.selected {
  border-color: #FB0079;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.08);
}

.btn-submit {
  width: 100%;
  padding: 14px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 8px;
}

.btn-submit.reward {
  background: #4CAF50;
}

.btn-submit:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.hint {
  text-align: center;
  font-size: 12px;
  color: #7A7C80;
  margin-top: 12px;
}
</style>
