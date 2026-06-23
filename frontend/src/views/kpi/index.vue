<template>
  <div class="kpi-page">
    <!-- 月份选择器 -->
    <div class="period-bar">
      <el-select
        v-model="currentPeriod"
        placeholder="选择月份"
        class="period-select"
        @change="loadResults"
      >
        <el-option
          v-for="p in periodOptions"
          :key="p.value"
          :label="p.label"
          :value="p.value"
        />
      </el-select>
      <el-button type="primary" class="calc-btn" @click="handleCalculate" :loading="calculating">
        自动计算
      </el-button>
    </div>

    <!-- Tab 切换 -->
    <el-tabs v-model="activeTab" class="kpi-tabs">
      <el-tab-pane label="KPI 结果" name="results">
        <!-- 汇总卡片 -->
        <div class="summary-card" v-if="summary">
          <div class="summary-item">
            <span class="summary-label">门店均分</span>
            <span class="summary-value">{{ summary.store_avg }}</span>
          </div>
          <div class="summary-divider"></div>
          <div class="summary-item">
            <span class="summary-label">考核人数</span>
            <span class="summary-value">{{ summary.store_count }}</span>
          </div>
        </div>

        <!-- 结果列表 -->
        <div class="result-list" v-if="summary && summary.results.length">
          <div
            v-for="item in summary.results"
            :key="item.id"
            class="result-card"
            :class="{ 'status-pending': item.status === 'pending', 'status-confirmed': item.status === 'confirmed' }"
          >
            <!-- 排名徽章 -->
            <div class="rank-badge" v-if="item.rank_in_store">
              <span class="rank-num">{{ item.rank_in_store }}</span>
            </div>

            <div class="card-header">
              <div class="emp-info">
                <span class="emp-name">{{ item.employee_name }}</span>
                <span class="emp-role">{{ item.employee_role }}</span>
              </div>
              <div class="score-main">
                <span class="score-num">{{ item.total_score }}</span>
                <span class="score-label">总分</span>
              </div>
            </div>

            <!-- 维度明细 -->
            <div class="dimension-list" v-if="item.dimensions && item.dimensions.length">
              <div class="dim-item" v-for="d in item.dimensions" :key="d.dimension">
                <span class="dim-label">{{ translateDim(d.dimension) }}</span>
                <div class="dim-bar-wrap">
                  <div
                    class="dim-bar"
                    :style="{ width: Math.min(d.normalized_score, 100) + '%' }"
                  ></div>
                </div>
                <span class="dim-score">{{ d.normalized_score.toFixed(1) }}</span>
              </div>
            </div>

            <!-- 系数 & 状态 -->
            <div class="card-footer">
              <span class="coefficient" :class="coefficientClass(item.coefficient)">
                系数 {{ item.coefficient.toFixed(2) }}
              </span>
              <span class="status-tag" :class="'tag-' + item.status">
                {{ item.status === 'pending' ? '待确认' : '已确认' }}
              </span>
              <el-button
                v-if="item.status === 'pending' && canManage"
                type="primary"
                size="small"
                class="confirm-btn"
                @click="handleConfirm(item)"
              >
                确认
              </el-button>
            </div>

            <!-- 申诉入口 -->
            <div class="appeal-entry" v-if="item.status === 'confirmed' && isStaff">
              <el-button text size="small" @click="openAppealDialog(item)">有异议？发起申诉</el-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div class="empty-state" v-else>
          <p class="empty-text">暂无 KPI 数据</p>
          <p class="empty-hint">选择月份后点击「自动计算」生成 KPI 结果</p>
        </div>
      </el-tab-pane>

      <!-- 申诉管理（店长/老板） -->
      <el-tab-pane label="申诉管理" name="appeals" v-if="canManage">
        <div class="appeal-filter">
          <el-select v-model="appealStatus" placeholder="状态筛选" @change="loadAppeals" clearable>
            <el-option label="待处理" value="pending" />
            <el-option label="已通过" value="approved" />
            <el-option label="已驳回" value="rejected" />
          </el-select>
        </div>

        <div class="appeal-list" v-if="appeals.length">
          <div v-for="a in appeals" :key="a.id" class="appeal-card">
            <div class="appeal-header">
              <span class="appeal-emp">{{ a.employee_name }}</span>
              <span class="appeal-period">{{ a.period }}</span>
              <span class="appeal-status" :class="'appeal-' + a.status">
                {{ appealStatusLabel(a.status) }}
              </span>
            </div>
            <div class="appeal-body">
              <p class="appeal-dim" v-if="a.dimension">维度：{{ translateDim(a.dimension) }}</p>
              <p class="appeal-reason">{{ a.reason }}</p>
              <p class="appeal-evidence" v-if="a.evidence">{{ a.evidence }}</p>
            </div>
            <div class="appeal-footer" v-if="a.status === 'pending'">
              <el-button size="small" @click="reviewAppeal(a, 'rejected')">驳回</el-button>
              <el-button size="small" type="primary" @click="reviewAppeal(a, 'approved')">通过</el-button>
            </div>
            <div class="appeal-resolution" v-if="a.resolution">
              <span class="res-label">审批意见：</span>{{ a.resolution }}
            </div>
          </div>
        </div>

        <div class="empty-state" v-else>
          <p class="empty-text">暂无申诉</p>
        </div>
      </el-tab-pane>

      <!-- 我的申诉（员工） -->
      <el-tab-pane label="我的申诉" name="myAppeals" v-if="isStaff">
        <div v-if="myAppeals.length" class="appeal-list">
          <div v-for="a in myAppeals" :key="a.id" class="appeal-card">
            <div class="appeal-header">
              <span class="appeal-period">{{ a.period }}</span>
              <span class="appeal-status" :class="'appeal-' + a.status">
                {{ appealStatusLabel(a.status) }}
              </span>
            </div>
            <div class="appeal-body">
              <p class="appeal-dim" v-if="a.dimension">维度：{{ translateDim(a.dimension) }}</p>
              <p class="appeal-reason">{{ a.reason }}</p>
            </div>
            <div class="appeal-resolution" v-if="a.resolution">
              <span class="res-label">审批意见：</span>{{ a.resolution }}
            </div>
          </div>
        </div>
        <div class="empty-state" v-else>
          <p class="empty-text">暂无申诉记录</p>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 确认对话框 -->
    <el-dialog v-model="confirmVisible" title="确认 KPI 结果" class="kpi-dialog">
      <div class="confirm-info">
        <p><strong>{{ confirmTarget?.employee_name }}</strong> | 总分 {{ confirmTarget?.total_score }}</p>
        <el-form label-position="top">
          <el-form-item label="绩效系数">
            <el-input-number
              v-model="confirmCoefficient"
              :min="0.5"
              :max="2.0"
              :step="0.05"
              :precision="2"
            />
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="confirmReason" type="textarea" :rows="2" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="confirmVisible = false">取消</el-button>
        <el-button type="primary" @click="submitConfirm">确认</el-button>
      </template>
    </el-dialog>

    <!-- 申诉对话框 -->
    <el-dialog v-model="appealVisible" title="发起 KPI 申诉" class="kpi-dialog">
      <div class="appeal-form">
        <p class="appeal-result-info">
          {{ appealTarget?.employee_name }} | {{ appealTarget?.period }} | 总分 {{ appealTarget?.total_score }}
        </p>
        <el-form label-position="top">
          <el-form-item label="申诉维度（可选）">
            <el-select v-model="appealDimension" placeholder="选择维度" clearable>
              <el-option
                v-for="d in appealTarget?.dimensions || []"
                :key="d.dimension"
                :label="translateDim(d.dimension)"
                :value="d.dimension"
              />
            </el-select>
          </el-form-item>
          <el-form-item label="申诉原因" required>
            <el-input
              v-model="appealReason"
              type="textarea"
              :rows="4"
              maxlength="500"
              show-word-limit
              placeholder="请说明申诉原因"
            />
          </el-form-item>
          <el-form-item label="证据/附件（可选）">
            <el-input v-model="appealEvidence" type="textarea" :rows="2" placeholder="补充说明" />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="appealVisible = false">取消</el-button>
        <el-button type="primary" @click="submitAppeal" :disabled="!appealReason">提交申诉</el-button>
      </template>
    </el-dialog>

    <!-- 审批对话框 -->
    <el-dialog v-model="reviewVisible" title="审批申诉" class="kpi-dialog" width="360px">
      <div class="review-info">
        <p><strong>{{ reviewTarget?.employee_name }}</strong> 对 {{ reviewTarget?.period }} 的 KPI 结果提出申诉</p>
        <p class="review-reason">{{ reviewTarget?.reason }}</p>
      </div>
      <el-form label-position="top">
        <el-form-item label="审批意见">
          <el-input v-model="reviewResolution" type="textarea" :rows="2" placeholder="选填" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="reviewVisible = false">取消</el-button>
        <el-button @click="submitReview('rejected')">驳回</el-button>
        <el-button type="primary" @click="submitReview('approved')">通过</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  kpiResultAPI,
  kpiAppealAPI,
  kpiScoreAPI,
  type KPIResultDetail,
  type KPIAppealItem,
} from '@/api/kpi'

// ---- 权限判断 ----
const userRole = ref('staff')

function loadUserRole() {
  const info = localStorage.getItem('user_info')
  if (info) {
    try {
      const parsed = JSON.parse(info)
      userRole.value = parsed.role || 'staff'
    } catch { /* ignore */ }
  }
}

const canManage = computed(() => ['boss', 'store_manager'].includes(userRole.value))
const isStaff = computed(() => !canManage.value)

// ---- 月份选择 ----
const currentPeriod = ref('')
const periodOptions = computed(() => {
  const now = new Date()
  const year = now.getFullYear()
  const month = now.getMonth() + 1
  const opts = []
  for (let i = 0; i < 12; i++) {
    let m = month - i
    let y = year
    if (m <= 0) {
      m += 12
      y -= 1
    }
    const value = `${y}-${String(m).padStart(2, '0')}`
    opts.push({ value, label: value })
  }
  return opts
})
if (periodOptions.value.length > 0 && !currentPeriod.value) {
  currentPeriod.value = periodOptions.value[0].value
}

// ---- Tab ----
const activeTab = ref('results')

// ---- KPI 结果 ----
const summary = ref<any>(null)
const calculating = ref(false)

const dimensionLabels: Record<string, string> = {
  attendance: '出勤率',
  rating: '服务评分',
  revenue: '营业贡献',
  teamwork: '团队协作',
  compliance: '合规执行',
  drink_sales: '酒水销售',
  customer_count: '客流量',
}

function translateDim(dim: string): string {
  return dimensionLabels[dim] || dim
}

function coefficientClass(coef: number): string {
  if (coef >= 1.2) return 'coef-high'
  if (coef >= 1.0) return 'coef-normal'
  return 'coef-low'
}

async function loadResults() {
  if (!currentPeriod.value) return
  try {
    const res = await kpiResultAPI.list(currentPeriod.value)
    summary.value = res.data.data
  } catch {
    summary.value = null
  }
}

async function handleCalculate() {
  calculating.value = true
  try {
    await kpiScoreAPI.calculate({ period: currentPeriod.value })
    ElMessage.success('计算完成')
    await loadResults()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '计算失败')
  } finally {
    calculating.value = false
  }
}

// ---- 确认 ----
const confirmVisible = ref(false)
const confirmTarget = ref<KPIResultDetail | null>(null)
const confirmCoefficient = ref(1.0)
const confirmReason = ref('')

function handleConfirm(item: KPIResultDetail) {
  confirmTarget.value = item
  confirmCoefficient.value = item.coefficient
  confirmReason.value = item.coefficient_reason || ''
  confirmVisible.value = true
}

async function submitConfirm() {
  if (!confirmTarget.value) return
  try {
    await kpiResultAPI.confirm(confirmTarget.value.id, {
      coefficient: confirmCoefficient.value,
      coefficient_reason: confirmReason.value || undefined,
    })
    ElMessage.success('确认成功')
    confirmVisible.value = false
    await loadResults()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '确认失败')
  }
}

// ---- 申诉（员工发起） ----
const appealVisible = ref(false)
const appealTarget = ref<KPIResultDetail | null>(null)
const appealDimension = ref<string | null>(null)
const appealReason = ref('')
const appealEvidence = ref('')

function openAppealDialog(item: KPIResultDetail) {
  appealTarget.value = item
  appealDimension.value = null
  appealReason.value = ''
  appealEvidence.value = ''
  appealVisible.value = true
}

async function submitAppeal() {
  if (!appealTarget.value || !appealReason.value) return
  try {
    await kpiAppealAPI.create({
      result_id: appealTarget.value.id,
      dimension: appealDimension.value || undefined,
      reason: appealReason.value,
      evidence: appealEvidence.value || undefined,
    })
    ElMessage.success('申诉已提交，等待店长审批')
    appealVisible.value = false
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '提交失败')
  }
}

// ---- 申诉管理（店长审批） ----
const appealStatus = ref<string | undefined>('pending')
const appeals = ref<KPIAppealItem[]>([])

function appealStatusLabel(s: string): string {
  const map: Record<string, string> = { pending: '待处理', approved: '已通过', rejected: '已驳回' }
  return map[s] || s
}

async function loadAppeals() {
  try {
    const res = await kpiAppealAPI.list({
      status: appealStatus.value || undefined,
    })
    appeals.value = res.data.data.items
  } catch {
    appeals.value = []
  }
}

const reviewVisible = ref(false)
const reviewTarget = ref<KPIAppealItem | null>(null)
const reviewResolution = ref('')

function reviewAppeal(item: KPIAppealItem, action: string) {
  reviewTarget.value = item
  reviewResolution.value = ''
  reviewVisible.value = true
  // Store action for later
  ;(reviewTarget.value as any)._action = action
}

async function submitReview(action: string) {
  if (!reviewTarget.value) return
  try {
    await kpiAppealAPI.review(reviewTarget.value.id, {
      action,
      resolution: reviewResolution.value || undefined,
    })
    ElMessage.success(action === 'approved' ? '已通过' : '已驳回')
    reviewVisible.value = false
    await loadAppeals()
    await loadResults()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '操作失败')
  }
}

// ---- 我的申诉 ----
const myAppeals = ref<KPIAppealItem[]>([])

async function loadMyAppeals() {
  try {
    const res = await kpiAppealAPI.my()
    myAppeals.value = res.data.data.items
  } catch {
    myAppeals.value = []
  }
}

// ---- 生命周期 ----
onMounted(() => {
  loadUserRole()
  loadResults()
})
</script>

<style scoped>
/* ========== 页面 ========== */
.kpi-page {
  padding: 16px;
  background: #000000;
  min-height: 100vh;
  font-family: 'Source Han Sans SC', 'Poppins', sans-serif;
}

/* ========== 月份选择 ========== */
.period-bar {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.period-select {
  width: 160px;
}

.period-select :deep(.el-input__wrapper) {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  box-shadow: none;
}

.period-select :deep(.el-input__inner) {
  color: #FFFFFF;
}

.calc-btn {
  background: #FB0079 !important;
  border-color: #FB0079 !important;
  border-radius: 8px;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  height: 32px;
  padding: 0 16px;
}

.calc-btn:hover {
  background: #FB0079 !important;
  border-color: #FB0079 !important;
}

/* ========== Tabs ========== */
.kpi-tabs :deep(.el-tabs__header) {
  margin-bottom: 16px;
}

.kpi-tabs :deep(.el-tabs__nav-wrap::after) {
  background: #222222;
  height: 1px;
}

.kpi-tabs :deep(.el-tabs__item) {
  color: #7A7C80;
  font-size: 14px;
  font-weight: 400;
  height: 40px;
  line-height: 40px;
}

.kpi-tabs :deep(.el-tabs__item.is-active) {
  color: #FB0079;
  font-weight: 600;
}

.kpi-tabs :deep(.el-tabs__active-bar) {
  background: #FB0079;
}

/* ========== 汇总卡片 ========== */
.summary-card {
  display: flex;
  align-items: center;
  gap: 0;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px 24px;
  margin-bottom: 12px;
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
}

.summary-label {
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 4px;
}

.summary-value {
  font-family: 'Poppins', sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: #FB0079;
}

.summary-divider {
  width: 1px;
  height: 40px;
  background: #222222;
}

/* ========== 结果卡片 ========== */
.result-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.result-card {
  position: relative;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  overflow: hidden;
}

.result-card.status-pending {
  border-color: rgba(251, 0, 121, 0.5);
}

.rank-badge {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 28px;
  height: 28px;
  background: #FB0079;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.rank-num {
  font-family: 'Poppins', sans-serif;
  font-size: 14px;
  font-weight: 700;
  color: #FFFFFF;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.emp-info {
  display: flex;
  flex-direction: column;
}

.emp-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
}

.emp-role {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 2px;
}

.score-main {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

.score-num {
  font-family: 'Poppins', sans-serif;
  font-size: 28px;
  font-weight: 700;
  color: #FB0079;
}

.score-label {
  font-size: 11px;
  color: #7A7C80;
}

/* ========== 维度进度条 ========== */
.dimension-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.dim-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.dim-label {
  width: 64px;
  font-size: 12px;
  color: #C8C8C8;
  flex-shrink: 0;
}

.dim-bar-wrap {
  flex: 1;
  height: 6px;
  background: #222222;
  border-radius: 3px;
  overflow: hidden;
}

.dim-bar {
  height: 100%;
  background: linear-gradient(90deg, #FB0079, #FB0079);
  border-radius: 3px;
  transition: width 0.4s ease;
}

.dim-score {
  width: 36px;
  font-family: 'Poppins', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #C8C8C8;
  text-align: right;
  flex-shrink: 0;
}

/* ========== 底部栏 ========== */
.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 12px;
  border-top: 1px solid #222222;
}

.coefficient {
  font-family: 'Poppins', sans-serif;
  font-size: 13px;
  font-weight: 600;
}

.coef-high {
  color: #FB0079;
}

.coef-normal {
  color: #C8C8C8;
}

.coef-low {
  color: #7A7C80;
}

.status-tag {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
}

.tag-pending {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}

.tag-confirmed {
  background: #333333;
  color: #C8C8C8;
}

.confirm-btn {
  background: #FB0079 !important;
  border-color: #FB0079 !important;
  border-radius: 6px;
  height: 28px;
  font-size: 12px;
}

/* ========== 申诉入口 ========== */
.appeal-entry {
  margin-top: 8px;
  text-align: right;
}

.appeal-entry :deep(.el-button) {
  color: #FB0079;
  font-size: 12px;
}

/* ========== 申诉卡片 ========== */
.appeal-filter {
  margin-bottom: 12px;
}

.appeal-filter :deep(.el-input__wrapper) {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 8px;
  box-shadow: none;
}

.appeal-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.appeal-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
}

.appeal-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.appeal-emp {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}

.appeal-period {
  font-size: 12px;
  color: #C8C8C8;
}

.appeal-status {
  margin-left: auto;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
}

.appeal-pending {
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}

.appeal-approved {
  background: #333333;
  color: #C8C8C8;
}

.appeal-rejected {
  background: #222222;
  color: #7A7C80;
}

.appeal-body {
  margin-bottom: 8px;
}

.appeal-dim {
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 4px;
}

.appeal-reason {
  font-size: 13px;
  color: #C8C8C8;
  line-height: 1.5;
}

.appeal-evidence {
  font-size: 12px;
  color: #7A7C80;
  margin-top: 4px;
}

.appeal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 8px;
  border-top: 1px solid #222222;
}

.appeal-footer :deep(.el-button) {
  border-radius: 6px;
  font-size: 12px;
}

.appeal-footer :deep(.el-button--primary) {
  background: #FB0079;
  border-color: #FB0079;
}

.appeal-resolution {
  padding-top: 8px;
  border-top: 1px solid #222222;
  font-size: 12px;
  color: #7A7C80;
  line-height: 1.5;
}

.res-label {
  color: #C8C8C8;
  font-weight: 600;
}

/* ========== 空状态 ========== */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 64px 16px;
}

.empty-text {
  font-size: 15px;
  color: #C8C8C8;
  margin-bottom: 8px;
}

.empty-hint {
  font-size: 12px;
  color: #7A7C80;
}

/* ========== 对话框 ========== */
.kpi-dialog :deep(.el-dialog) {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 14px;
}

.kpi-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}

.kpi-dialog :deep(.el-form-item__label) {
  color: #C8C8C8;
  font-size: 13px;
}

.kpi-dialog :deep(.el-input__wrapper) {
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  box-shadow: none;
}

.kpi-dialog :deep(.el-input__inner) {
  color: #FFFFFF;
}

.kpi-dialog :deep(.el-textarea__inner) {
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-family: 'Source Han Sans SC', sans-serif;
}

.kpi-dialog :deep(.el-button) {
  border-radius: 8px;
}

.kpi-dialog :deep(.el-button--primary) {
  background: #FB0079;
  border-color: #FB0079;
}

.confirm-info p,
.review-info p,
.appeal-result-info {
  color: #C8C8C8;
  font-size: 13px;
  margin-bottom: 12px;
}

.review-reason {
  color: #C8C8C8;
  font-size: 13px;
  padding: 8px;
  background: #000000;
  border-radius: 8px;
  margin-top: 8px;
  line-height: 1.5;
}
</style>
