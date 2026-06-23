<template>
  <div class="stocktake-detail-page">
    <div class="page-header">
      <h1 class="page-title">{{ stocktake?.period || '盘点单' }} #{{ stocktakeId }}</h1>
    </div>

    <div v-if="loading" class="loading-state">加载中...</div>
    <template v-else-if="stocktake">
      <!-- 进度概览 -->
      <div class="progress-bar">
        <div class="progress-stats">
          <div class="ps-item">
            <span class="ps-num">{{ stocktake.checked_count }}/{{ stocktake.total_count }}</span>
            <span class="ps-label">已核/总数</span>
          </div>
          <div class="ps-item">
            <span class="ps-num matched">{{ stocktake.matched_count }}</span>
            <span class="ps-label">匹配</span>
          </div>
          <div class="ps-item">
            <span class="ps-num missing">{{ stocktake.missing_count }}</span>
            <span class="ps-label">缺失</span>
          </div>
          <div class="ps-item">
            <span class="ps-num extra">{{ stocktake.extra_count }}</span>
            <span class="ps-label">多出</span>
          </div>
        </div>
        <div class="progress-track">
          <div class="progress-fill" :style="{ width: progressPct + '%' }"></div>
        </div>
        <div class="progress-text">{{ progressPct }}% · {{ statusLabel(stocktake.status) }}</div>
      </div>

      <!-- 扫码区 -->
      <div v-if="stocktake.status !== 'completed'" class="scan-section">
        <p class="section-title">扫码核对</p>
        <div class="scan-input-row">
          <input
            v-model="scanLabel"
            class="scan-input"
            placeholder="扫瓶身码或手动输入"
            @keyup.enter="handleScan"
            :disabled="scanning"
          />
          <button class="scan-btn" @click="handleScan" :disabled="scanning || !scanLabel.trim()">
            {{ scanning ? '...' : '核对' }}
          </button>
        </div>
        <div v-if="lastResult" class="scan-result" :class="lastResult.check_status">
          <span class="result-icon">{{ resultIcon(lastResult.check_status) }}</span>
          <div class="result-body">
            <span class="result-status">{{ resultLabel(lastResult.check_status) }}</span>
            <span class="result-msg">{{ lastResult.message }}</span>
            <span class="result-wine" v-if="lastResult.wine_name">{{ lastResult.wine_name }} · {{ lastResult.customer_name }}</span>
          </div>
        </div>
      </div>

      <!-- 完成盘点按钮 -->
      <div v-if="stocktake.status !== 'completed'" class="complete-section">
        <button class="complete-btn" @click="handleComplete" :disabled="completing">
          {{ completing ? '处理中...' : '完成盘点' }}
        </button>
        <p class="complete-hint">点击后未核对的酒将标记为"缺失"</p>
      </div>

      <!-- 明细列表 -->
      <div class="items-section">
        <div class="items-header">
          <span class="section-title">明细列表</span>
          <div class="filter-tabs">
            <button
              v-for="f in filters"
              :key="f.value"
              class="filter-tab"
              :class="{ active: currentFilter === f.value }"
              @click="currentFilter = f.value; loadItems()"
            >{{ f.label }}</button>
          </div>
        </div>

        <div v-if="itemsLoading" class="loading-state">加载中...</div>
        <div v-else-if="items.length === 0" class="empty-state">无记录</div>
        <div v-else class="items-list">
          <div
            v-for="it in items"
            :key="it.id"
            class="item-card"
            :class="it.check_status"
          >
            <div class="item-head">
              <span class="item-wine">{{ it.wine_name }}</span>
              <span class="item-status" :class="it.check_status">{{ itemStatusLabel(it.check_status) }}</span>
            </div>
            <div class="item-body">
              <div class="item-row">
                <span class="label">客人</span>
                <span class="value">{{ it.customer_name }} · {{ it.phone }}</span>
              </div>
              <div class="item-row">
                <span class="label">瓶码</span>
                <span class="value code">{{ it.bottle_label }}</span>
              </div>
              <div class="item-row" v-if="it.expected_ml !== null">
                <span class="label">应剩</span>
                <span class="value">{{ it.expected_ml }}ml</span>
              </div>
              <div class="item-row" v-if="it.actual_ml !== null">
                <span class="label">实剩</span>
                <span class="value" :class="{ mismatch: it.check_status === 'mismatch' }">{{ it.actual_ml }}ml</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { stocktakeAPI, type Stocktake, type StocktakeItem, type StocktakeScanResult } from '@/api/wine'

const props = defineProps<{ stocktakeId: string }>()

const stocktake = ref<Stocktake | null>(null)
const items = ref<StocktakeItem[]>([])
const loading = ref(false)
const itemsLoading = ref(false)
const scanning = ref(false)
const completing = ref(false)
const scanLabel = ref('')
const lastResult = ref<StocktakeScanResult | null>(null)
const currentFilter = ref('all')

const filters = [
  { label: '全部', value: 'all' },
  { label: '待核', value: 'pending' },
  { label: '匹配', value: 'matched' },
  { label: '异常', value: 'mismatch' },
  { label: '缺失', value: 'missing' },
]

const progressPct = computed(() => {
  if (!stocktake.value || stocktake.value.total_count === 0) return 0
  return Math.round((stocktake.value.checked_count / stocktake.value.total_count) * 100)
})

async function loadStocktake() {
  loading.value = true
  try {
    const { data: res } = await stocktakeAPI.getById(props.stocktakeId)
    if (res.code === 0) stocktake.value = res.data
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '加载失败')
  } finally { loading.value = false }
}

async function loadItems() {
  itemsLoading.value = true
  try {
    const params: Record<string, unknown> = { page_size: 200 }
    if (currentFilter.value !== 'all') {
      params.check_status = currentFilter.value
    }
    const { data: res } = await stocktakeAPI.listItems(props.stocktakeId, params)
    if (res.code === 0) items.value = res.data.items || []
  } catch { items.value = [] }
  finally { itemsLoading.value = false }
}

async function handleScan() {
  const label = scanLabel.value.trim()
  if (!label) return
  scanning.value = true
  try {
    const { data: res } = await stocktakeAPI.scan(props.stocktakeId, { bottle_label: label })
    if (res.code === 0) {
      lastResult.value = res.data
      ElMessage.success(res.data.message)
      scanLabel.value = ''
      // 刷新数据
      await Promise.all([loadStocktake(), loadItems()])
    } else {
      ElMessage.error(res.message || '核对失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '核对失败')
  } finally { scanning.value = false }
}

async function handleComplete() {
  try {
    await ElMessageBox.confirm('完成后未核对的酒将标记为缺失，确定完成盘点吗？', '完成盘点', {
      confirmButtonText: '确定完成',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch { return }

  completing.value = true
  try {
    const { data: res } = await stocktakeAPI.complete(props.stocktakeId)
    if (res.code === 0) {
      ElMessage.success('盘点已完成')
      await loadStocktake()
      await loadItems()
    } else {
      ElMessage.error(res.message || '完成失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '完成失败')
  } finally { completing.value = false }
}

function statusLabel(status: string): string {
  return { pending: '待盘点', in_progress: '盘点中', completed: '已完成' }[status] || status
}

function itemStatusLabel(status: string): string {
  return { pending: '待核', matched: '匹配', missing: '缺失', mismatch: '量不符' }[status] || status
}

function resultIcon(status: string): string {
  return { matched: '✓', missing: '✗', mismatch: '!', extra: '+' }[status] || '?'
}

function resultLabel(status: string): string {
  return { matched: '匹配成功', missing: '缺失', mismatch: '量不符', extra: '多出' }[status] || status
}

onMounted(() => {
  loadStocktake()
  loadItems()
})
</script>

<style scoped>
.stocktake-detail-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
}
.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 30px 0;
  color: #7A7C80;
  font-size: 13px;
}

/* 进度概览 */
.progress-bar {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
}
.progress-stats {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.ps-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.ps-num {
  font-family: 'Poppins', sans-serif;
  font-size: 16px;
  font-weight: 700;
  color: #FFFFFF;
}
.ps-num.matched { color: #6fcf6f; }
.ps-num.missing { color: #FB0079; }
.ps-num.extra { color: #ffa500; }
.ps-label {
  font-size: 10px;
  color: #7A7C80;
}
.progress-track {
  height: 6px;
  background: #1a1a1a;
  border-radius: 3px;
  overflow: hidden;
  margin-bottom: 6px;
}
.progress-fill {
  height: 100%;
  background: #FB0079;
  border-radius: 3px;
  transition: width 0.3s;
}
.progress-text {
  font-size: 11px;
  color: #7A7C80;
  text-align: center;
}

/* 扫码区 */
.scan-section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.section-title {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0 0 10px;
}
.scan-input-row {
  display: flex;
  gap: 8px;
}
.scan-input {
  flex: 1;
  height: 44px;
  padding: 0 14px;
  background: #0a0a0a;
  border: 1px solid #333333;
  border-radius: 10px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
}
.scan-input:focus { border-color: #FB0079; }
.scan-btn {
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 10px;
  padding: 0 20px;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}
.scan-btn:disabled { opacity: 0.4; cursor: not-allowed; }

.scan-result {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin-top: 12px;
  padding: 12px;
  border-radius: 8px;
  background: #0a0a0a;
}
.scan-result.matched { border: 1px solid rgba(111, 207, 111, 0.3); }
.scan-result.missing, .scan-result.mismatch { border: 1px solid rgba(251, 0, 121, 0.3); }
.scan-result.extra { border: 1px solid rgba(255, 165, 0, 0.3); }
.result-icon {
  font-size: 20px;
  font-weight: 700;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  flex-shrink: 0;
}
.scan-result.matched .result-icon { background: rgba(111, 207, 111, 0.2); color: #6fcf6f; }
.scan-result.missing .result-icon, .scan-result.mismatch .result-icon { background: rgba(251, 0, 121, 0.2); color: #FB0079; }
.scan-result.extra .result-icon { background: rgba(255, 165, 0, 0.2); color: #ffa500; }
.result-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.result-status {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}
.result-msg {
  font-size: 12px;
  color: #C8C8C8;
}
.result-wine {
  font-size: 11px;
  color: #7A7C80;
}

/* 完成盘点 */
.complete-section {
  margin-bottom: 16px;
  text-align: center;
}
.complete-btn {
  width: 100%;
  height: 48px;
  background: transparent;
  border: 1px solid #FB0079;
  border-radius: 10px;
  color: #FB0079;
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
}
.complete-btn:disabled { opacity: 0.4; cursor: not-allowed; }
.complete-hint {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 6px;
}

/* 明细列表 */
.items-section { margin-top: 8px; }
.items-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}
.filter-tabs {
  display: flex;
  gap: 4px;
}
.filter-tab {
  background: transparent;
  border: 1px solid #333333;
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 11px;
  color: #7A7C80;
  cursor: pointer;
  font-family: 'Source Han Sans SC', sans-serif;
}
.filter-tab.active {
  background: rgba(251, 0, 121, 0.15);
  border-color: #FB0079;
  color: #FB0079;
}

.items-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.item-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px;
}
.item-card.matched { border-left: 3px solid #6fcf6f; }
.item-card.missing, .item-card.mismatch { border-left: 3px solid #FB0079; }
.item-card.pending { border-left: 3px solid #7A7C80; }
.item-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.item-wine {
  font-family: 'Source Han Sans SC', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.item-status {
  font-size: 10px;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'Source Han Sans SC', sans-serif;
}
.item-status.pending { background: #333; color: #7A7C80; }
.item-status.matched { background: rgba(111, 207, 111, 0.2); color: #6fcf6f; }
.item-status.missing, .item-status.mismatch { background: rgba(251, 0, 121, 0.2); color: #FB0079; }
.item-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.item-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
}
.label { color: #7A7C80; min-width: 36px; }
.value { color: #C8C8C8; }
.value.code { font-family: 'Poppins', monospace; font-size: 11px; color: #FB0079; }
.value.mismatch { color: #FB0079; font-weight: 600; }
</style>
