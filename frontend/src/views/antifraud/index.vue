<template>
  <div class="antifraud-page">
    <!-- 顶部操作栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <h2 class="page-title">防飞单监控</h2>
      </div>
      <div class="toolbar-right">
        <el-date-picker
          v-model="scanDate"
          type="date"
          placeholder="选择日期"
          format="YYYY-MM-DD"
          value-format="YYYY-MM-DD"
          size="small"
          class="date-picker"
        />
        <el-button
          type="primary"
          size="small"
          :loading="scanning"
          class="scan-btn"
          @click="handleScan"
        >
          立即扫描
        </el-button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <div class="stat-value">{{ stats.total_sessions || 0 }}</div>
        <div class="stat-label">总开台</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" :style="{ color: '#FB0079' }">{{ stats.anomaly_count || 0 }}</div>
        <div class="stat-label">异常会话</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" :style="{ color: '#FB0079' }">{{ stats.high_risk_count || 0 }}</div>
        <div class="stat-label">高危预警</div>
      </div>
      <div class="stat-card">
        <div class="stat-value" :style="{ color: '#FB0079' }">{{ stats.critical_count || 0 }}</div>
        <div class="stat-label">严重预警</div>
      </div>
    </div>

    <!-- 预警列表 -->
    <div class="alerts-section">
      <div class="section-header">
        <span class="section-title">预警列表</span>
        <el-select
          v-model="filterRiskLevel"
          placeholder="风险等级"
          size="small"
          clearable
          class="filter-select"
          @change="loadAlerts"
        >
          <el-option label="严重" value="critical" />
          <el-option label="高危" value="high" />
          <el-option label="中危" value="medium" />
          <el-option label="低危" value="low" />
        </el-select>
      </div>

      <!-- 桌面端表格 -->
      <div class="table-wrap desktop-only">
        <table class="alert-table">
          <thead>
            <tr>
              <th>桌号</th>
              <th>员工</th>
              <th>开台时间</th>
              <th>风险分</th>
              <th>风险等级</th>
              <th>状态</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="alerts.length === 0 && !loading">
              <td colspan="7" class="empty-cell">暂无预警数据</td>
            </tr>
            <tr
              v-for="item in alerts"
              :key="item.session_id"
              :class="{ 'row-selected': selectedId === item.session_id }"
              @click="selectAlert(item.session_id)"
            >
              <td class="table-no">{{ item.table_no }}</td>
              <td>{{ item.employee_name }}</td>
              <td class="time-cell">{{ formatTime(item.opened_at) }}</td>
              <td>
                <span class="risk-score" :style="{ color: riskColor(item.risk_score) }">
                  {{ item.risk_score }}
                </span>
              </td>
              <td>
                <span class="risk-tag" :class="'tag-' + item.risk_level">
                  {{ riskLabel(item.risk_level) }}
                </span>
              </td>
              <td>
                <span class="status-tag" :class="item.status === 'open' ? 'status-open' : 'status-closed'">
                  {{ item.status === 'open' ? '进行中' : '已关台' }}
                </span>
              </td>
              <td>
                <el-button link size="small" class="detail-btn" @click.stop="selectAlert(item.session_id)">
                  详情
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- 移动端卡片 -->
      <div class="mobile-only">
        <div v-if="alerts.length === 0 && !loading" class="empty-card">暂无预警数据</div>
        <div
          v-for="item in alerts"
          :key="item.session_id"
          class="alert-card"
          :class="{ 'card-selected': selectedId === item.session_id }"
          @click="selectAlert(item.session_id)"
        >
          <div class="card-top">
            <span class="card-table">{{ item.table_no }}</span>
            <span class="risk-tag" :class="'tag-' + item.risk_level">{{ riskLabel(item.risk_level) }}</span>
          </div>
          <div class="card-mid">
            <span>{{ item.employee_name }}</span>
            <span class="risk-score" :style="{ color: riskColor(item.risk_score) }">{{ item.risk_score }}分</span>
          </div>
          <div class="card-bottom">
            <span class="time-cell">{{ formatTime(item.opened_at) }}</span>
            <span class="status-tag" :class="item.status === 'open' ? 'status-open' : 'status-closed'">
              {{ item.status === 'open' ? '进行中' : '已关台' }}
            </span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div class="pagination-wrap" v-if="totalPages > 1">
        <el-pagination
          v-model:current-page="currentPage"
          :page-size="pageSize"
          :total="total"
          layout="prev, pager, next"
          size="small"
          @current-change="loadAlerts"
        />
      </div>
    </div>

    <!-- 详情弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="预警详情"
      width="560px"
      class="detail-dialog"
      destroy-on-close
    >
      <div v-if="detail" class="detail-content">
        <!-- 基本信息 -->
        <div class="detail-section">
          <div class="detail-row">
            <span class="detail-label">桌号</span>
            <span class="detail-value">{{ detail.table_no }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">员工</span>
            <span class="detail-value">{{ detail.employee_name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">开台时间</span>
            <span class="detail-value">{{ formatTime(detail.opened_at) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">关台时间</span>
            <span class="detail-value">{{ formatTime(detail.closed_at) || '进行中' }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">客人数</span>
            <span class="detail-value">{{ detail.guest_count }} 人</span>
          </div>
        </div>

        <!-- 金额对比 -->
        <div class="detail-section">
          <div class="section-subtitle">金额对比</div>
          <div class="amount-compare">
            <div class="amount-item">
              <div class="amount-label">POS 金额</div>
              <div class="amount-value">{{ detail.crmeb_total_amount.toFixed(0) }}</div>
            </div>
            <div class="amount-divider">vs</div>
            <div class="amount-item">
              <div class="amount-label">企微收款</div>
              <div class="amount-value">{{ detail.wework_pay_amount.toFixed(0) }}</div>
            </div>
          </div>
        </div>

        <!-- 风险分 -->
        <div class="detail-section">
          <div class="section-subtitle">
            综合风险分
            <span class="risk-score-lg" :style="{ color: riskColor(detail.risk_score) }">
              {{ detail.risk_score }} / 100
            </span>
          </div>

          <!-- 5 规则明细 -->
          <div class="rules-list">
            <div
              v-for="rule in detail.rules"
              :key="rule.rule_name"
              class="rule-item"
              :class="{ 'rule-triggered': rule.score > 5 }"
            >
              <div class="rule-header">
                <span class="rule-name">{{ rule.rule_label }}</span>
                <span class="rule-score" :style="{ color: rule.score > 10 ? '#FB0079' : rule.score > 5 ? '#FB0079' : '#C8C8C8' }">
                  {{ rule.score }} / {{ rule.max_score }}
                </span>
              </div>
              <div class="rule-bar">
                <div
                  class="rule-bar-fill"
                  :style="{
                    width: (rule.score / rule.max_score * 100) + '%',
                    backgroundColor: rule.score > 10 ? '#FB0079' : rule.score > 5 ? '#FB0079' : '#333333',
                  }"
                />
              </div>
              <div class="rule-detail">{{ rule.detail }}</div>
            </div>
          </div>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { antifraudAPI } from '@/api/antifraud'
import type { ScanResult, AlertListItem, SessionRisk } from '@/api/antifraud'

const scanDate = ref('')
const scanning = ref(false)
const loading = ref(false)
const stats = ref<Partial<ScanResult>>({})
const alerts = ref<AlertListItem[]>([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const totalPages = ref(0)
const filterRiskLevel = ref('')
const selectedId = ref<string | null>(null)
const detailVisible = ref(false)
const detail = ref<SessionRisk | null>(null)

function riskColor(score: number): string {
  if (score >= 80) return '#FB0079'
  if (score >= 50) return '#FB0079'
  if (score >= 30) return '#C8C8C8'
  return '#7A7C80'
}

function riskLabel(level: string): string {
  const map: Record<string, string> = {
    critical: '严重',
    high: '高危',
    medium: '中危',
    low: '低危',
  }
  return map[level] || level
}

function formatTime(isoStr: string | null): string {
  if (!isoStr) return ''
  try {
    const d = new Date(isoStr)
    const month = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const hours = String(d.getHours()).padStart(2, '0')
    const minutes = String(d.getMinutes()).padStart(2, '0')
    return `${month}-${day} ${hours}:${minutes}`
  } catch {
    return isoStr
  }
}

async function handleScan() {
  scanning.value = true
  try {
    const res = await antifraudAPI.scan(scanDate.value || undefined)
    if (res.data.code === 0) {
      stats.value = res.data.data
      ElMessage.success(
        `扫描完成: ${res.data.data.total_sessions} 桌, ${res.data.data.anomaly_count} 异常`
      )
      await loadAlerts()
    }
  } catch {
    ElMessage.error('扫描失败')
  } finally {
    scanning.value = false
  }
}

async function loadAlerts() {
  loading.value = true
  try {
    const res = await antifraudAPI.getAlerts({
      risk_level: filterRiskLevel.value || undefined,
      page: currentPage.value,
      page_size: pageSize.value,
    })
    if (res.data.code === 0) {
      const d = res.data.data
      alerts.value = d.items
      total.value = d.total
      totalPages.value = d.total_pages
    }
  } catch {
    ElMessage.error('加载预警列表失败')
  } finally {
    loading.value = false
  }
}

async function selectAlert(sessionId: string) {
  selectedId.value = sessionId
  try {
    const res = await antifraudAPI.getAlertDetail(sessionId)
    if (res.data.code === 0) {
      detail.value = res.data.data
      detailVisible.value = true
    }
  } catch {
    ElMessage.error('加载预警详情失败')
  }
}

onMounted(() => {
  loadAlerts()
})
</script>

<style scoped>
.antifraud-page {
  padding: 16px;
  min-height: 100vh;
  background: #000000;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-left {
  display: flex;
  align-items: center;
}
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.page-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0;
}

.date-picker :deep(.el-input__wrapper) {
  background: #111111;
  border-color: #333333;
  box-shadow: none;
}
.date-picker :deep(.el-input__inner) {
  color: #C8C8C8;
}

.scan-btn {
  background: #FB0079 !important;
  border-color: #FB0079 !important;
  font-family: 'Source Han Sans SC', sans-serif;
}
.scan-btn:hover {
  background: #FB0079 !important;
  border-color: #FB0079 !important;
}

.stats-row {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}
.stat-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.stat-value {
  font-family: 'Poppins', sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: #FFFFFF;
  line-height: 1.2;
}
.stat-label {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.alerts-section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.section-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.filter-select :deep(.el-input__wrapper) {
  background: #111111;
  border-color: #333333;
  box-shadow: none;
}

.table-wrap {
  overflow-x: auto;
}
.alert-table {
  width: 100%;
  border-collapse: collapse;
}
.alert-table th {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  color: #7A7C80;
  font-weight: 400;
  text-align: left;
  padding: 8px 12px;
  background: #333333;
  border-bottom: 1px solid #222222;
}
.alert-table th:first-child { border-radius: 8px 0 0 0; }
.alert-table th:last-child { border-radius: 0 8px 0 0; }
.alert-table td {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #C8C8C8;
  padding: 10px 12px;
  border-bottom: 1px solid #222222;
  cursor: pointer;
}
.alert-table tr:hover td {
  background: #111111;
}
.row-selected td {
  background: rgba(251, 0, 121, 0.08);
}
.table-no {
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-weight: 600;
  color: #FFFFFF;
}
.time-cell {
  font-family: 'Poppins', sans-serif;
  font-size: 12px;
  color: #7A7C80;
}
.empty-cell {
  text-align: center;
  color: #7A7C80;
  padding: 40px 12px;
  cursor: default !important;
}
.detail-btn {
  color: #FB0079 !important;
  font-family: 'Source Han Sans SC', sans-serif;
}

.risk-score {
  font-family: 'Poppins', sans-serif;
  font-weight: 600;
  font-size: 13px;
}
.risk-tag {
  display: inline-block;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
}
.tag-critical {
  background: #FB0079;
  color: #FFFFFF;
}
.tag-high {
  background: rgba(255, 104, 162, 0.2);
  color: #FB0079;
}
.tag-medium {
  background: #333333;
  color: #C8C8C8;
}
.tag-low {
  background: #222222;
  color: #7A7C80;
}
.status-tag {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
}
.status-open {
  background: #333333;
  color: #C8C8C8;
}
.status-closed {
  background: #222222;
  color: #7A7C80;
}

.mobile-only { display: none; }
.alert-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 12px 14px;
  margin-bottom: 8px;
  cursor: pointer;
}
.alert-card:active { background: #111111; }
.card-selected { border-color: #FB0079; }
.card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.card-table {
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-weight: 600;
  font-size: 14px;
  color: #FFFFFF;
}
.card-mid {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #C8C8C8;
  margin-bottom: 4px;
}
.card-bottom {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.empty-card {
  text-align: center;
  color: #7A7C80;
  padding: 40px 12px;
}

.pagination-wrap {
  display: flex;
  justify-content: center;
  margin-top: 12px;
}
.pagination-wrap :deep(.el-pager li) {
  background: #111111;
  color: #C8C8C8;
  border: 1px solid #333333;
}
.pagination-wrap :deep(.el-pager li.is-active) {
  background: #FB0079;
  color: #FFFFFF;
  border-color: #FB0079;
}
.pagination-wrap :deep(.btn-prev),
.pagination-wrap :deep(.btn-next) {
  background: #111111;
  color: #C8C8C8;
  border: 1px solid #333333;
}

.detail-dialog :deep(.el-dialog) {
  background: #000000;
  border: 1px solid #333333;
  border-radius: 14px;
}
.detail-dialog :deep(.el-dialog__header) {
  padding: 16px 20px 0;
}
.detail-dialog :deep(.el-dialog__title) {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.detail-dialog :deep(.el-dialog__body) {
  padding: 12px 20px 20px;
}

.detail-content {
  font-family: 'Source Han Sans SC', sans-serif;
}
.detail-section {
  margin-bottom: 16px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 6px 0;
  border-bottom: 1px solid #222222;
}
.detail-label {
  font-size: 13px;
  color: #7A7C80;
}
.detail-value {
  font-size: 13px;
  color: #FFFFFF;
  font-weight: 500;
}
.section-subtitle {
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.risk-score-lg {
  font-family: 'Poppins', sans-serif;
  font-size: 18px;
  font-weight: 600;
}

.amount-compare {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
}
.amount-item {
  text-align: center;
}
.amount-label {
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 4px;
}
.amount-value {
  font-family: 'Poppins', sans-serif;
  font-size: 20px;
  font-weight: 600;
  color: #FB0079;
}
.amount-divider {
  font-family: 'Poppins', sans-serif;
  font-size: 12px;
  color: #7A7C80;
}

.rules-list {
  margin-top: 8px;
}
.rule-item {
  padding: 10px 0;
  border-bottom: 1px solid #222222;
}
.rule-item:last-child {
  border-bottom: none;
}
.rule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 4px;
}
.rule-name {
  font-size: 13px;
  color: #C8C8C8;
}
.rule-score {
  font-family: 'Poppins', sans-serif;
  font-size: 14px;
  font-weight: 600;
}
.rule-bar {
  height: 4px;
  background: #222222;
  border-radius: 2px;
  margin-bottom: 4px;
  overflow: hidden;
}
.rule-bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}
.rule-detail {
  font-size: 12px;
  color: #7A7C80;
  line-height: 1.4;
}
.rule-triggered .rule-name {
  color: #FFFFFF;
}

@media (max-width: 767px) {
  .antifraud-page {
    padding: 12px;
  }
  .stats-row {
    grid-template-columns: repeat(2, 1fr);
  }
  .stat-value {
    font-size: 20px;
  }
  .desktop-only { display: none; }
  .mobile-only { display: block; }
  .toolbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
  .toolbar-right {
    width: 100%;
    justify-content: space-between;
  }
}

@media (min-width: 768px) {
  .desktop-only { display: block; }
  .mobile-only { display: none; }
}
</style>
