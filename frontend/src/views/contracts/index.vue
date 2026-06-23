<template>
  <div class="contracts-page">
    <!-- 页头 -->
    <header class="page-header">
      <h1>合同系统</h1>
      <button class="btn-primary" @click="showCreateDialog = true">+ 新建合同</button>
    </header>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <select v-model="filterStatus" class="filter-select" @change="fetchContracts">
        <option value="">全部状态</option>
        <option value="draft">草稿</option>
        <option value="pending_sign">待签署</option>
        <option value="signed">已签署</option>
        <option value="expired">已到期</option>
        <option value="terminated">已终止</option>
      </select>
      <select v-model="filterPosition" class="filter-select" @change="fetchContracts">
        <option value="">全部岗位</option>
        <option v-for="p in positions" :key="p" :value="p">{{ p }}</option>
      </select>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <!-- 空状态 -->
    <div v-else-if="contracts.length === 0" class="empty-state">
      <p>暂无合同记录</p>
      <p class="empty-hint">点击「新建合同」开始</p>
    </div>

    <!-- 合同列表 -->
    <div v-else class="contract-list">
      <div
        v-for="c in contracts"
        :key="c.id"
        class="contract-card"
        @click="openDetail(c.id)"
      >
        <div class="card-top">
          <span class="employee-name">{{ c.employee_name }}</span>
          <span class="status-tag" :class="'status-' + c.status">
            {{ statusLabel(c.status) }}
          </span>
        </div>
        <div class="card-mid">
          <span class="position-grade">{{ c.position }} · {{ c.grade }}</span>
          <span class="salary">
            {{ formatMoney(c.monthly_salary) }}
          </span>
        </div>
        <div class="card-bottom">
          <span class="contract-no">{{ c.contract_no }}</span>
          <span class="date-range">{{ c.start_date }} ~ {{ c.end_date || '--' }}</span>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div v-if="totalPages > 1" class="pagination">
      <button :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
      <span>{{ page }} / {{ totalPages }}</span>
      <button :disabled="page >= totalPages" @click="goPage(page + 1)">下一页</button>
    </div>

    <!-- 新建合同弹窗 -->
    <div v-if="showCreateDialog" class="modal-overlay" @click.self="showCreateDialog = false">
      <div class="modal">
        <h2>新建合同</h2>

        <!-- Step 1: 选员工 -->
        <div class="form-group">
          <label>员工</label>
          <select v-model="createForm.employee_id" class="form-input">
            <option value="">请选择员工</option>
            <option v-for="emp in employees" :key="emp.id" :value="emp.id">
              {{ emp.name }} ({{ emp.role }})
            </option>
          </select>
        </div>

        <!-- Step 2: 岗位 + 职档 -->
        <div class="form-row">
          <div class="form-group">
            <label>岗位</label>
            <select v-model="createForm.position" class="form-input" @change="onPositionGradeChange">
              <option value="">请选择</option>
              <option v-for="p in positions" :key="p" :value="p">{{ p }}</option>
            </select>
          </div>
          <div class="form-group">
            <label>职档</label>
            <select v-model="createForm.grade" class="form-input" @change="onPositionGradeChange">
              <option value="">请选择</option>
              <option v-for="g in grades" :key="g" :value="g">{{ g }}</option>
            </select>
          </div>
        </div>

        <!-- 参考薪资矩阵 -->
        <div v-if="matrixRefSalary > 0" class="matrix-ref">
          薪资矩阵参考: {{ formatMoney(matrixRefSalary) }}
        </div>
        <div v-else-if="createForm.position && createForm.grade" class="matrix-ref matrix-na">
          该岗位/职档组合暂不可用
        </div>

        <!-- Step 3: 填月薪 -->
        <div class="form-group">
          <label>月薪总额</label>
          <input
            v-model.number="createForm.monthly_salary"
            type="number"
            class="form-input"
            placeholder="输入月薪（>= 3000）"
            min="3000"
          />
          <div v-if="createForm.monthly_salary >= 3000" class="salary-breakdown">
            <span>基本工资: {{ formatMoney(3000) }}</span>
            <span>补贴: {{ formatMoney(Math.max(0, createForm.monthly_salary - 3000 - 400)) }}</span>
            <span>餐补: {{ formatMoney(400) }}</span>
            <span class="breakdown-total">合计: {{ formatMoney(createForm.monthly_salary) }}</span>
          </div>
        </div>

        <!-- 日期 -->
        <div class="form-row">
          <div class="form-group">
            <label>开始日期</label>
            <input v-model="createForm.start_date" type="date" class="form-input" />
          </div>
          <div class="form-group">
            <label>结束日期</label>
            <input v-model="createForm.end_date" type="date" class="form-input" />
          </div>
        </div>

        <div class="modal-actions">
          <button class="btn-secondary" @click="showCreateDialog = false">取消</button>
          <button class="btn-primary" :disabled="!canCreate" @click="submitCreate">确认创建</button>
        </div>
      </div>
    </div>

    <!-- 合同详情弹窗 -->
    <div v-if="detailContract" class="modal-overlay" @click.self="detailContract = null">
      <div class="modal detail-modal">
        <div class="detail-header">
          <h2>合同详情</h2>
          <span class="status-tag" :class="'status-' + detailContract.status">
            {{ statusLabel(detailContract.status) }}
          </span>
        </div>

        <div class="detail-section">
          <h3>基本信息</h3>
          <dl>
            <dt>合同编号</dt><dd>{{ detailContract.contract_no }}</dd>
            <dt>员工</dt><dd>{{ detailContract.employee_name }}</dd>
            <dt>岗位 / 职档</dt><dd>{{ detailContract.position }} · {{ detailContract.grade }}</dd>
            <dt>合同期限</dt><dd>{{ detailContract.start_date }} ~ {{ detailContract.end_date || '无固定期限' }}</dd>
          </dl>
        </div>

        <div class="detail-section">
          <h3>薪资明细</h3>
          <dl class="salary-detail">
            <dt>月薪总额</dt><dd class="money">{{ formatMoney(detailContract.monthly_salary) }}</dd>
            <dt>基本工资</dt><dd class="money">{{ formatMoney(detailContract.base_salary) }}</dd>
            <dt>补贴</dt><dd class="money">{{ formatMoney(detailContract.allowance) }}</dd>
            <dt>餐补</dt><dd class="money">{{ formatMoney(detailContract.meal_allowance) }}</dd>
          </dl>
        </div>

        <div v-if="detailContract.esign_flow_id" class="detail-section">
          <h3>电子签</h3>
          <dl>
            <dt>流程 ID</dt><dd>{{ detailContract.esign_flow_id }}</dd>
            <dt>签署时间</dt><dd>{{ detailContract.signed_at || '--' }}</dd>
          </dl>
        </div>

        <div v-if="detailContract.template_data" class="detail-section">
          <h3>模板填充字段</h3>
          <pre class="template-preview">{{ JSON.stringify(detailContract.template_data, null, 2) }}</pre>
        </div>

        <div class="modal-actions">
          <button
            v-if="detailContract.status === 'draft'"
            class="btn-danger"
            @click="confirmDelete(detailContract.id)"
          >
            删除
          </button>
          <button
            v-if="detailContract.status === 'draft' || detailContract.status === 'pending_sign'"
            class="btn-primary"
            :disabled="sendingSign"
            @click="sendSign(detailContract.id)"
          >
            {{ sendingSign ? '发起中...' : '发起电子签' }}
          </button>
          <button class="btn-secondary" @click="detailContract = null">关闭</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { contractsAPI, type ContractItem, type ContractDetail, type EmployeeBrief, type SalaryMatrixItem } from '@/api/contracts'

// ---- 常量 ----
const positions = ['店长', '吧员', '服务员', '厨师', '保洁']
const grades = ['学徒', '正式', '副职', '正职']

const statusLabel = (s: string) => {
  const map: Record<string, string> = {
    draft: '草稿',
    pending_sign: '待签署',
    signed: '已签署',
    expired: '已到期',
    terminated: '已终止',
  }
  return map[s] || s
}

const formatMoney = (v: number) => {
  return '¥' + v.toLocaleString('zh-CN', { minimumFractionDigits: 0, maximumFractionDigits: 2 })
}

// ---- 列表状态 ----
const loading = ref(true)
const contracts = ref<ContractItem[]>([])
const page = ref(1)
const pageSize = ref(20)
const total = ref(0)
const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)))
const filterStatus = ref('')
const filterPosition = ref('')

async function fetchContracts() {
  loading.value = true
  try {
    const res = await contractsAPI.listContracts({
      page: page.value,
      page_size: pageSize.value,
      status: filterStatus.value || undefined,
      position: filterPosition.value || undefined,
    })
    const data = res.data.data
    contracts.value = data.items
    total.value = data.total
  } catch {
    contracts.value = []
    total.value = 0
  } finally {
    loading.value = false
  }
}

function goPage(p: number) {
  page.value = p
  fetchContracts()
}

// ---- 员工列表 ----
const employees = ref<EmployeeBrief[]>([])

async function fetchEmployees() {
  try {
    const res = await contractsAPI.listEmployees()
    employees.value = res.data.data
  } catch {
    employees.value = []
  }
}

// ---- 薪资矩阵 ----
const salaryMatrix = ref<SalaryMatrixItem[]>([])

async function fetchMatrix() {
  try {
    const res = await contractsAPI.getSalaryMatrix()
    salaryMatrix.value = res.data.data
  } catch {
    salaryMatrix.value = []
  }
}

const matrixRefSalary = computed(() => {
  const form = createForm.value
  if (!form.position || !form.grade) return 0
  const entry = (salaryMatrix.value as Record<string, unknown>[]).find(
    (m: unknown) => {
      const record = m as Record<string, unknown>
      return record.position === form.position && record.grade === form.grade
    }
  )
  return Number((entry as Record<string, unknown>)?.monthly_salary) || 0
})

// ---- 新建合同 ----
const showCreateDialog = ref(false)
const createForm = ref({
  employee_id: '' as string,
  position: '',
  grade: '',
  monthly_salary: 0,
  start_date: '',
  end_date: '' as string,
})

const canCreate = computed(() => {
  return (
    createForm.value.employee_id &&
    createForm.value.position &&
    createForm.value.grade &&
    createForm.value.monthly_salary >= 3000 &&
    createForm.value.start_date
  )
})

function onPositionGradeChange() {
  // 自动填入矩阵参考薪资
  if (matrixRefSalary.value > 0) {
    createForm.value.monthly_salary = matrixRefSalary.value
  }
}

async function submitCreate() {
  if (!canCreate.value) return
  try {
    await contractsAPI.createContract({
      employee_id: createForm.value.employee_id as string,
      position: createForm.value.position,
      grade: createForm.value.grade,
      monthly_salary: createForm.value.monthly_salary,
      start_date: createForm.value.start_date,
      end_date: createForm.value.end_date || null,
    })
    showCreateDialog.value = false
    createForm.value = { employee_id: '', position: '', grade: '', monthly_salary: 0, start_date: '', end_date: '' }
    fetchContracts()
  } catch (err: any) {
    alert(err?.response?.data?.message || '创建失败')
  }
}

// ---- 合同详情 ----
const detailContract = ref<ContractDetail | null>(null)

async function openDetail(id: string) {
  try {
    const res = await contractsAPI.getContract(id)
    detailContract.value = res.data.data
  } catch (err: any) {
    alert(err?.response?.data?.message || '获取详情失败')
  }
}

// ---- 删除 ----
async function confirmDelete(id: string) {
  if (!confirm('确认删除该合同？仅草稿状态可删除。')) return
  try {
    await contractsAPI.deleteContract(id)
    detailContract.value = null
    fetchContracts()
  } catch (err: any) {
    alert(err?.response?.data?.message || '删除失败')
  }
}

// ---- 电子签 ----
const sendingSign = ref(false)

async function sendSign(id: string) {
  sendingSign.value = true
  try {
    const res = await contractsAPI.sendForSign(id)
    alert(res.data.data.message || '电子签流程已发起')
    // 刷新详情
    const detail = await contractsAPI.getContract(id)
    detailContract.value = detail.data.data
    fetchContracts()
  } catch (err: any) {
    alert(err?.response?.data?.message || '发起失败')
  } finally {
    sendingSign.value = false
  }
}

// ---- 生命周期 ----
onMounted(() => {
  fetchContracts()
  fetchEmployees()
  fetchMatrix()
})
</script>

<style scoped>
/* ===== 页面布局 ===== */
.contracts-page {
  padding: 16px;
  max-width: 480px;
  margin: 0 auto;
}

/* ===== 页头 ===== */
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h1 {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 20px;
  font-weight: 900;
  color: #FFFFFF;
  margin: 0;
}

/* ===== 按钮 ===== */
.btn-primary {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  font-family: 'Source Han Sans SC', sans-serif;
  cursor: pointer;
}
.btn-primary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-secondary {
  background: #333333;
  color: #C8C8C8;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}
.btn-danger {
  background: transparent;
  color: #FB0079;
  border: 1px solid #FB0079;
  border-radius: 8px;
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}

/* ===== 筛选栏 ===== */
.filter-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.filter-select {
  flex: 1;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 8px 12px;
  color: #C8C8C8;
  font-size: 13px;
  font-family: 'Source Han Sans SC', sans-serif;
}

/* ===== 加载/空状态 ===== */
.loading-state,
.empty-state {
  text-align: center;
  padding: 80px 16px;
  color: #7A7C80;
  font-size: 13px;
}
.empty-hint {
  margin-top: 8px;
  font-size: 11px;
}

/* ===== 合同卡片 ===== */
.contract-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.contract-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.contract-card:hover {
  border-color: #FB0079;
}
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.employee-name {
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.card-mid {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 8px;
}
.position-grade {
  font-size: 13px;
  color: #C8C8C8;
}
.salary {
  font-family: 'Poppins', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FB0079;
}
.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.contract-no {
  font-size: 11px;
  color: #7A7C80;
}
.date-range {
  font-size: 11px;
  color: #7A7C80;
}

/* ===== 状态标签 ===== */
.status-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.status-signed {
  background: #FB0079;
  color: #FFFFFF;
}
.status-pending_sign {
  background: #333333;
  color: #C8C8C8;
}
.status-draft {
  background: #333333;
  color: #7A7C80;
}
.status-expired {
  background: rgba(251, 0, 121, 0.15);
  color: #FFFFFF;
}
.status-terminated {
  background: #333333;
  color: #7A7C80;
}

/* ===== 分页 ===== */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}
.pagination button {
  background: #333333;
  color: #C8C8C8;
  border: none;
  border-radius: 8px;
  padding: 6px 12px;
  font-size: 13px;
  cursor: pointer;
}
.pagination button:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.pagination span {
  color: #C8C8C8;
  font-size: 13px;
  font-family: 'Poppins', sans-serif;
}

/* ===== 弹窗 ===== */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
  padding: 16px;
}
.modal {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 14px;
  padding: 24px;
  width: 100%;
  max-width: 420px;
  max-height: 80vh;
  overflow-y: auto;
}
.modal h2 {
  font-size: 18px;
  font-weight: 900;
  color: #FFFFFF;
  margin: 0 0 20px 0;
}

/* ===== 表单 ===== */
.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 4px;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.form-input {
  width: 100%;
  background: #222222;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 10px 12px;
  color: #FFFFFF;
  font-size: 14px;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  box-sizing: border-box;
}
.form-input:focus {
  outline: none;
  border-color: #FB0079;
}
select.form-input {
  appearance: none;
}
.form-row {
  display: flex;
  gap: 12px;
}
.form-row .form-group {
  flex: 1;
}

/* ===== 薪资分解 ===== */
.salary-breakdown {
  background: #222222;
  border-radius: 8px;
  padding: 10px;
  margin-top: 8px;
  font-size: 12px;
  color: #C8C8C8;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.salary-breakdown span {
  display: block;
  line-height: 1.8;
}
.breakdown-total {
  border-top: 1px solid #333333;
  margin-top: 4px;
  padding-top: 4px;
  color: #FB0079;
  font-weight: 600;
}

.matrix-ref {
  font-size: 12px;
  color: #C8C8C8;
  padding: 8px 12px;
  background: #222222;
  border-radius: 8px;
  margin-bottom: 12px;
}
.matrix-na {
  color: #FB0079;
}

/* ===== 弹窗按钮 ===== */
.modal-actions {
  display: flex;
  gap: 8px;
  margin-top: 20px;
  justify-content: flex-end;
}

/* ===== 详情弹窗 ===== */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.detail-header h2 {
  margin-bottom: 0;
}
.detail-section {
  background: #222222;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.detail-section h3 {
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
  margin: 0 0 10px 0;
}
.detail-section dl {
  margin: 0;
}
.detail-section dt {
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 2px;
}
.detail-section dd {
  font-size: 14px;
  color: #FFFFFF;
  margin: 0 0 10px 0;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
}
.detail-section dd:last-child {
  margin-bottom: 0;
}
.money {
  text-align: right;
  font-weight: 600;
  color: #FB0079;
}
.total-row {
  border-top: 1px solid #333333;
  padding-top: 8px;
  margin-top: 4px;
  font-size: 16px;
}

.template-preview {
  background: #000000;
  border-radius: 8px;
  padding: 12px;
  font-size: 11px;
  color: #C8C8C8;
  overflow-x: auto;
  white-space: pre-wrap;
  max-height: 200px;
  font-family: 'Fira Code', 'Consolas', monospace;
}
</style>
