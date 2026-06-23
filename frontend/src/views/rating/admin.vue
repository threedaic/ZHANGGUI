<template>
  <div class="rating-admin">
    <!-- 汇总卡片 -->
    <div class="summary-row">
      <div class="summary-card">
        <span class="label">总评价数</span>
        <span class="value">{{ summary.total_count }}</span>
      </div>
      <div class="summary-card">
        <span class="label">均分</span>
        <span class="value highlight">{{ summary.avg_overall }}</span>
      </div>
      <div class="summary-card">
        <span class="label">低分预警</span>
        <span class="value danger">{{ summary.low_score_count }}</span>
      </div>
    </div>

    <!-- 维度得分 -->
    <div class="section">
      <h3>各维度得分</h3>
      <div class="dimension-grid">
        <div v-for="(score, key) in summary.dimension_scores" :key="key" class="dimension-item">
          <span class="dim-label">{{ dimLabels[key] }}</span>
          <div class="dim-bar-wrap">
            <div class="dim-bar" :style="{ width: (score / 5) * 100 + '%' }"></div>
          </div>
          <span class="dim-score">{{ score }}</span>
        </div>
      </div>
    </div>

    <!-- 低分告警 -->
    <div class="section">
      <h3>低分告警 <span v-if="alerts.length" class="badge">{{ alerts.length }}</span></h3>
      <div v-if="alerts.length === 0" class="empty">暂无低分告警</div>
      <div v-for="a in alerts" :key="a.id" class="alert-card" :class="{ responded: a.store_response }">
        <div class="alert-head">
          <span class="table-badge">{{ a.table_no }}桌</span>
          <span class="score-badge">{{ a.overall_score }}</span>
          <span class="time">{{ formatTime(a.created_at) }}</span>
        </div>
        <p v-if="a.comment" class="alert-comment">{{ a.comment }}</p>
        <div v-if="a.store_response" class="alert-response">
          已回复：{{ a.store_response }}
        </div>
        <div v-else class="alert-action">
          <el-input
            v-model="replyTexts[a.id]"
            placeholder="输入回复内容..."
            size="small"
            @keyup.enter="handleReply(a.id)"
          />
          <el-button type="primary" size="small" @click="handleReply(a.id)">回复</el-button>
        </div>
      </div>
    </div>

    <!-- 评分列表 -->
    <div class="section">
      <h3>评分记录</h3>
      <div class="rating-list">
        <div v-for="r in ratings" :key="r.id" class="rating-item">
          <div class="rating-head">
            <span class="table-badge">{{ r.table_no }}桌</span>
            <span class="score" :class="{ low: r.is_low_score }">{{ r.overall_score }}</span>
            <span class="time">{{ formatTime(r.created_at) }}</span>
            <span v-if="r.is_low_score" class="tag-low">低分</span>
          </div>
          <p v-if="r.comment" class="rating-comment">{{ r.comment }}</p>
        </div>
      </div>
      <el-pagination
        v-if="total > 0"
        layout="prev, pager, next"
        :total="total"
        :page-size="20"
        :current-page="currentPage"
        @current-change="loadRatings"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getRatingSummary,
  getRatingAlerts,
  getRatings,
  respondToRating,
  type RatingItem,
  type RatingSummary,
} from '@/api/rating'

const dimLabels: Record<string, string> = {
  food_quality: '餐品品质',
  food_speed: '出餐速度',
  drink_quality: '酒水品质',
  drink_speed: '出酒速度',
  service_attitude: '服务态度',
  service_speed: '服务速度',
  cleanliness: '环境卫生',
}

const summary = reactive<RatingSummary>({
  total_count: 0,
  avg_overall: 0,
  low_score_count: 0,
  dimension_scores: {},
})

const alerts = ref<RatingItem[]>([])
const ratings = ref<RatingItem[]>([])
const total = ref(0)
const currentPage = ref(1)
const replyTexts = ref<Record<string, string>>({})

function formatTime(ts: string): string {
  if (!ts) return ''
  try {
    const d = new Date(ts)
    const m = String(d.getMonth() + 1).padStart(2, '0')
    const day = String(d.getDate()).padStart(2, '0')
    const h = String(d.getHours()).padStart(2, '0')
    const min = String(d.getMinutes()).padStart(2, '0')
    return `${m}-${day} ${h}:${min}`
  } catch {
    return ts
  }
}

async function loadSummary() {
  try {
    const res = await getRatingSummary()
    if (res.data.code === 0) {
      Object.assign(summary, res.data.data)
    }
  } catch {
    /* ignore */
  }
}

async function loadAlerts() {
  try {
    const res = await getRatingAlerts()
    if (res.data.code === 0) {
      alerts.value = res.data.data || []
    }
  } catch {
    /* ignore */
  }
}

async function loadRatings(page = 1) {
  currentPage.value = page
  try {
    const res = await getRatings(page, 20)
    if (res.data.code === 0) {
      const d = res.data.data
      ratings.value = d.items
      total.value = d.total
    }
  } catch {
    /* ignore */
  }
}

async function handleReply(id: string) {
  const text = replyTexts.value[id]
  if (!text || !text.trim()) return
  try {
    const res = await respondToRating(id, text.trim())
    if (res.data.code === 0) {
      ElMessage.success('回复成功')
      replyTexts.value[id] = ''
      await loadAlerts()
      await loadRatings(currentPage.value)
    }
  } catch {
    ElMessage.error('回复失败')
  }
}

onMounted(() => {
  loadSummary()
  loadAlerts()
  loadRatings()
})
</script>

<style scoped>
.rating-admin {
  padding: 16px;
  min-height: 100vh;
  background: #000000;
}

/* 汇总卡片 */
.summary-row {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}
.summary-card {
  flex: 1;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.summary-card .label {
  display: block;
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 4px;
}
.summary-card .value {
  font-family: Poppins, sans-serif;
  font-size: 24px;
  font-weight: 600;
  color: #FFFFFF;
}
.summary-card .value.highlight {
  color: #FB0079;
}
.summary-card .value.danger {
  color: #FB0079;
}

/* 区块 */
.section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 12px;
}
.section h3 {
  font-size: 14px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 12px 0;
  display: flex;
  align-items: center;
  gap: 8px;
}
.badge {
  font-family: Poppins, sans-serif;
  font-size: 12px;
  background: #FB0079;
  color: #FFFFFF;
  border-radius: 999px;
  padding: 2px 8px;
}

/* 维度得分 */
.dimension-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.dimension-item {
  display: flex;
  align-items: center;
  gap: 8px;
}
.dim-label {
  width: 72px;
  font-size: 12px;
  color: #C8C8C8;
  text-align: right;
  flex-shrink: 0;
}
.dim-bar-wrap {
  flex: 1;
  height: 6px;
  background: #333333;
  border-radius: 3px;
  overflow: hidden;
}
.dim-bar {
  height: 100%;
  background: #FB0079;
  border-radius: 3px;
  transition: width 0.3s;
}
.dim-score {
  font-family: Poppins, sans-serif;
  font-size: 12px;
  color: #FB0079;
  width: 28px;
  text-align: left;
}

/* 低分告警 */
.alert-card {
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 8px;
}
.alert-card.responded {
  opacity: 0.6;
}
.alert-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.table-badge {
  font-size: 12px;
  color: #C8C8C8;
  background: #333333;
  border-radius: 6px;
  padding: 2px 8px;
}
.score-badge {
  font-family: Poppins, sans-serif;
  font-size: 18px;
  font-weight: 600;
  color: #FB0079;
}
.time {
  font-size: 11px;
  color: #7A7C80;
  margin-left: auto;
}
.alert-comment {
  font-size: 13px;
  color: #C8C8C8;
  margin: 0 0 8px 0;
  line-height: 1.5;
}
.alert-response {
  font-size: 12px;
  color: #7A7C80;
  background: #111111;
  border-radius: 6px;
  padding: 8px;
}
.alert-action {
  display: flex;
  gap: 8px;
  align-items: center;
}
.alert-action :deep(.el-input__inner) {
  background: #222222;
  border-color: #333333;
  color: #FFFFFF;
  font-size: 13px;
}
.alert-action :deep(.el-button--primary) {
  background: #FB0079;
  border-color: #FB0079;
  white-space: nowrap;
}

/* 评分列表 */
.rating-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.rating-item {
  background: #1a1a1a;
  border-radius: 8px;
  padding: 10px 12px;
}
.rating-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.rating-head .score {
  font-family: Poppins, sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.rating-head .score.low {
  color: #FB0079;
}
.tag-low {
  font-size: 10px;
  background: #FB0079;
  color: #000000;
  border-radius: 4px;
  padding: 1px 6px;
  margin-left: auto;
}
.rating-comment {
  font-size: 13px;
  color: #C8C8C8;
  margin: 6px 0 0 0;
  line-height: 1.4;
}

.empty {
  text-align: center;
  padding: 24px;
  color: #7A7C80;
  font-size: 13px;
}

/* pagination */
:deep(.el-pagination) {
  justify-content: center;
  margin-top: 12px;
}
:deep(.el-pagination .btn-prev),
:deep(.el-pagination .btn-next),
:deep(.el-pagination .el-pager li) {
  background: #111111 !important;
  color: #C8C8C8 !important;
  border: 1px solid #333333 !important;
}
:deep(.el-pagination .el-pager li.is-active) {
  background: #FB0079 !important;
  color: #FFFFFF !important;
  border-color: #FB0079 !important;
}
</style>
