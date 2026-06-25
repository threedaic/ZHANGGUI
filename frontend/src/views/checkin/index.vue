<template>
  <div class="checkin-page">
    <!-- 日期 + 班次 -->
    <div class="shift-card">
      <div class="shift-date">{{ formatDate(status?.date) }}</div>
      <div class="shift-info" v-if="status?.scheduled_shift">
        <span class="shift-tag" :class="{ overnight: status?.is_overnight }">
          {{ getShiftDisplayName(status?.scheduled_shift) }}
        </span>
        <span class="shift-time" v-if="status?.shift_start_time">
          {{ formatTime(status.shift_start_time) }} - {{ formatTime(status?.shift_end_time) }}
        </span>
        <span class="overnight-badge" v-if="status?.is_overnight">跨天</span>
      </div>
      <div class="shift-info" v-else>
        <span class="shift-rest">今日未排班</span>
      </div>
    </div>

    <!-- 本周统计（紧跟排班下方，一眼可见） -->
    <div class="weekly-card" v-if="status?.weekly_stats">
      <div class="weekly-title">本周考勤</div>
      <div class="weekly-stats">
        <div class="wstat wstat-present">
          <span class="wstat-num">{{ status.weekly_stats.present }}</span>
          <span class="wstat-label">出勤</span>
        </div>
        <div class="wstat wstat-late">
          <span class="wstat-num">{{ status.weekly_stats.late }}</span>
          <span class="wstat-label">迟到</span>
        </div>
        <div class="wstat wstat-early">
          <span class="wstat-num">{{ status.weekly_stats.early }}</span>
          <span class="wstat-label">早退</span>
        </div>
        <div class="wstat wstat-absent">
          <span class="wstat-num">{{ status.weekly_stats.absent }}</span>
          <span class="wstat-label">旷工</span>
        </div>
        <div class="wstat wstat-leave">
          <span class="wstat-num">{{ status.weekly_stats.leave }}</span>
          <span class="wstat-label">请假</span>
        </div>
      </div>
    </div>

    <!-- 打卡时间显示 -->
    <div class="time-display" v-if="status && (status.clock_in || status.clock_out)">
      <div class="time-block" :class="{ active: status.clock_in && !status.clock_out }">
        <span class="time-block-label">上班</span>
        <span class="time-block-value" :class="{ late: status.late_minutes > 0 }">
          {{ status.clock_in ? formatTime(status.clock_in) : '--:--' }}
        </span>
        <span class="time-block-tag" v-if="status.late_minutes > 0">迟到{{ status.late_minutes }}分</span>
      </div>
      <div class="time-arrow">→</div>
      <div class="time-block" :class="{ active: status.clock_out }">
        <span class="time-block-label">下班</span>
        <span class="time-block-value" :class="{ early: status.early_minutes > 0 }">
          {{ status.clock_out ? formatTime(status.clock_out) : '--:--' }}
        </span>
        <span class="time-block-tag" v-if="status.early_minutes > 0">早退{{ status.early_minutes }}分</span>
      </div>
    </div>

    <!-- 大打卡按钮 -->
    <div class="checkin-btn-area">
      <button
        class="checkin-btn"
        :class="{
          'btn-clock-in': status?.next_action === 'clock_in',
          'btn-clock-out': status?.next_action === 'clock_out',
          'btn-done': status?.next_action === 'done',
        }"
        :disabled="loading || status?.next_action === 'done'"
        @click="handleCheckin"
      >
        <div class="btn-ring" v-if="loading"></div>
        <span class="btn-text">{{ btnText }}</span>
        <span class="btn-subtext" v-if="status?.next_action !== 'done' && !loading">点击打卡</span>
        <span class="btn-subtext" v-if="loading">提交中...</span>
      </button>
    </div>

    <!-- WiFi 状态 -->
    <div class="wifi-status" v-if="config?.require_wifi">
      <span class="wifi-icon" :class="{ connected: wifiConnected }">
        <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M2 6c4-4 8-4 12 0M4.5 8.5c2.5-2.5 5-2.5 7.5 0M7 11c1-1 1-1 2 0"/>
          <circle cx="8" cy="13.5" r="0.8" fill="currentColor"/>
        </svg>
      </span>
      <span class="wifi-text">{{ wifiConnected ? 'WiFi已连接' : 'WiFi检测中（浏览器限制，不影响打卡）' }}</span>
    </div>

    <!-- 照片预览 -->
    <div class="photo-preview" v-if="lastPhotoUrl">
      <img :src="lastPhotoUrl" alt="打卡照片" />
      <span class="photo-label">打卡照片留档</span>
    </div>

    <!-- 隐藏的拍照 input -->
    <input
      ref="photoInput"
      type="file"
      accept="image/*"
      capture="user"
      style="display: none"
      @change="onPhotoSelected"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { showToast, showSuccessToast } from 'vant'
import { attendanceAPI } from '@/api/attendance'
import type { CheckinStatus, CheckinConfig } from '@/api/attendance'

const status = ref<CheckinStatus | null>(null)
const config = ref<CheckinConfig | null>(null)
const loading = ref(false)
const photoInput = ref<HTMLInputElement | null>(null)
const pendingPhotoBlob = ref<Blob | null>(null)
const lastPhotoUrl = ref<string | null>(null)
const wifiConnected = ref(false)

// 班次名称映射：英文code → 中文
const SHIFT_NAME_MAP: Record<string, string> = {
  day: '白班',
  night: '晚班',
  rest: '休息',
  leave: '请假',
  EVENNING: '晚班',
  EVENING: '晚班',
  evening: '晚班',
  EVENing: '晚班',
  morning: '早班',
  afternoon: '午班',
}

function getShiftDisplayName(shift?: string | null): string {
  if (!shift) return ''
  // 先精确匹配，再小写匹配
  return SHIFT_NAME_MAP[shift] || SHIFT_NAME_MAP[shift.toLowerCase()] || shift
}

const btnText = computed(() => {
  if (loading.value) return ''
  if (!status.value) return '加载中'
  if (status.value.next_action === 'clock_in') return '上班打卡'
  if (status.value.next_action === 'clock_out') return '下班打卡'
  return '今日已完成'
})

function formatDate(d?: string) {
  if (!d) return ''
  const dt = new Date(d)
  const week = ['日', '一', '二', '三', '四', '五', '六']
  return `${dt.getMonth() + 1}月${dt.getDate()}日 周${week[dt.getDay()]}`
}

function formatTime(t?: string | null) {
  if (!t) return '--:--'
  // 兼容多种格式："2026-06-24 14:05:00+00:00" / "14:05:00" / "14:05"
  const m = t.match(/(\d{2}):(\d{2})/)
  return m ? `${m[1]}:${m[2]}` : '--:--'
}

async function loadStatus() {
  try {
    const res = await attendanceAPI.getCheckinStatus()
    if (res.data.code === 0) {
      status.value = res.data.data
    }
  } catch (e) {
    console.error('[Checkin] loadStatus failed:', e)
  }
}

async function loadConfig() {
  try {
    const res = await attendanceAPI.getCheckinConfig()
    if (res.data.code === 0) {
      config.value = res.data.data
    }
  } catch (e) {
    console.error('[Checkin] loadConfig failed:', e)
  }
}

function detectWifi() {
  try {
    const conn = (navigator as any).connection
    if (conn) {
      wifiConnected.value = conn.type === 'wifi' || conn.effectiveType === 'wifi'
    }
  } catch { /* */ }
}

async function handleCheckin() {
  if (loading.value || !status.value) return
  if (status.value.next_action === 'done') return

  if (config.value?.require_photo) {
    pendingPhotoBlob.value = null
    photoInput.value?.click()
    return
  }
  await submitCheckin(null)
}

async function onPhotoSelected(e: Event) {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return

  try {
    loading.value = true
    const compressed = await compressPhoto(file)
    pendingPhotoBlob.value = compressed
    if (lastPhotoUrl.value) URL.revokeObjectURL(lastPhotoUrl.value)
    lastPhotoUrl.value = URL.createObjectURL(compressed)
    await submitCheckin(compressed)
  } catch (err) {
    console.error('[Checkin] photo compress failed:', err)
    showToast('照片处理失败，请重试')
  } finally {
    loading.value = false
  }
}

function compressPhoto(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => {
      const img = new Image()
      img.onload = () => {
        const maxSize = 800
        let { width, height } = img
        if (width > maxSize || height > maxSize) {
          if (width > height) {
            height = Math.round((height * maxSize) / width)
            width = maxSize
          } else {
            width = Math.round((width * maxSize) / height)
            height = maxSize
          }
        }
        const canvas = document.createElement('canvas')
        canvas.width = width
        canvas.height = height
        const ctx = canvas.getContext('2d')
        if (!ctx) return reject(new Error('canvas ctx null'))
        ctx.drawImage(img, 0, 0, width, height)
        canvas.toBlob(
          (blob) => { if (blob) resolve(blob); else reject(new Error('canvas toBlob null')) },
          'image/jpeg', 0.8,
        )
      }
      img.onerror = reject
      img.src = reader.result as string
    }
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

async function submitCheckin(photo: Blob | null) {
  loading.value = true
  try {
    const res = await attendanceAPI.checkin({
      photo: photo || undefined,
    })
    if (res.data.code === 0) {
      const result = res.data.data
      const actionText = result.action === 'clock_in' ? '上班' : '下班'
      let msg = `${actionText}打卡成功 ${formatTime(result.clock_time)}`
      if (result.status === 'late') msg += `（迟到${result.late_minutes}分钟）`
      else if (result.status === 'early') msg += `（早退${result.early_minutes}分钟）`
      showSuccessToast(msg)
      await loadStatus()
    } else {
      showToast(res.data.message || '打卡失败')
    }
  } catch (err: any) {
    const msg = err?.response?.data?.message || err?.message || '打卡失败'
    showToast(msg)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadStatus()
  loadConfig()
  detectWifi()
})
</script>

<style scoped>
.checkin-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

/* 日期+班次 */
.shift-card {
  width: 100%;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.shift-date {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 6px;
}
.shift-info {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.shift-tag {
  font-size: 12px;
  font-weight: 600;
  color: #FFFFFF;
  background: #FB0079;
  padding: 3px 10px;
  border-radius: 4px;
}
.shift-tag.overnight { background: #6C2BD9; }
.shift-time { font-size: 13px; color: #C8C8C8; }
.overnight-badge {
  font-size: 10px;
  color: #6C2BD9;
  border: 1px solid #6C2BD9;
  padding: 1px 6px;
  border-radius: 3px;
}
.shift-rest { font-size: 13px; color: #7A7C80; }

/* 打卡时间显示 */
.time-display {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-bottom: 8px;
}
.time-block {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 12px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  position: relative;
}
.time-block.active {
  border-color: #34C759;
  background: rgba(52, 199, 89, 0.08);
}
.time-block-label {
  font-size: 11px;
  color: #7A7C80;
}
.time-block-value {
  font-size: 28px;
  font-weight: 800;
  color: #FFFFFF;
  font-family: 'Poppins', sans-serif;
  letter-spacing: 1px;
}
.time-block-value.late { color: #FB0079; }
.time-block-value.early { color: #FF9500; }
.time-block-tag {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(251, 0, 121, 0.15);
  color: #FB0079;
}
.time-arrow {
  color: #333333;
  font-size: 18px;
}

/* 大按钮 */
.checkin-btn-area {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  padding: 16px 0;
}
.checkin-btn {
  width: 170px;
  height: 170px;
  border-radius: 50%;
  border: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  cursor: pointer;
  position: relative;
  transition: transform 0.15s ease;
  -webkit-tap-highlight-color: transparent;
}
.checkin-btn:active { transform: scale(0.95); }
.checkin-btn:disabled { cursor: not-allowed; opacity: 0.4; }
.btn-clock-in {
  background: radial-gradient(circle at 50% 40%, #FB0079, #C40061);
  box-shadow: 0 8px 32px rgba(251, 0, 121, 0.35);
}
.btn-clock-out {
  background: radial-gradient(circle at 50% 40%, #222222, #000000);
  border: 2px solid #FB0079;
  box-shadow: 0 8px 32px rgba(251, 0, 121, 0.2);
}
.btn-done {
  background: #1a1a1a;
  border: 1px solid #333333;
}
.btn-text {
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
}
.btn-clock-out .btn-text { color: #FB0079; }
.btn-done .btn-text { color: #7A7C80; }
.btn-subtext {
  font-size: 11px;
  color: rgba(255, 255, 255, 0.7);
}
.btn-done .btn-subtext { color: #555555; }
.btn-ring {
  position: absolute;
  width: 100%;
  height: 100%;
  border-radius: 50%;
  border: 3px solid rgba(255, 255, 255, 0.2);
  border-top-color: #FFFFFF;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* 本周统计 */
.weekly-card {
  width: 100%;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.weekly-title {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 10px;
}
.weekly-stats {
  display: flex;
  gap: 6px;
}
.wstat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}
.wstat-num {
  font-size: 20px;
  font-weight: 800;
  font-family: 'Poppins', sans-serif;
}
.wstat-label {
  font-size: 10px;
  color: #7A7C80;
}
.wstat-present .wstat-num { color: #34C759; }
.wstat-late .wstat-num { color: #FB0079; }
.wstat-early .wstat-num { color: #FF9500; }
.wstat-absent .wstat-num { color: #FF3B30; }
.wstat-leave .wstat-num { color: #8E8E93; }

/* WiFi */
.wifi-status {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}
.wifi-icon { color: #7A7C80; }
.wifi-icon.connected { color: #34C759; }
.wifi-text { font-size: 11px; color: #7A7C80; }

/* 照片预览 */
.photo-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
}
.photo-preview img {
  width: 100px;
  height: 100px;
  object-fit: cover;
  border-radius: 8px;
  border: 1px solid #333333;
}
.photo-label { font-size: 11px; color: #7A7C80; }
</style>
