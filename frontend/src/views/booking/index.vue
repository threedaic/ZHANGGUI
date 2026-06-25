<template>
  <div class="booking-page">
    <!-- 统计卡片 -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ stats.total_tables }}</span>
        <span class="stat-label">总桌</span>
      </div>
      <div class="stat-card stat-card--booked">
        <span class="stat-value stat-value--pink">{{ stats.booked }}</span>
        <span class="stat-label">已订</span>
      </div>
      <div class="stat-card stat-card--free">
        <span class="stat-value stat-value--dawn">{{ stats.free }}</span>
        <span class="stat-label">空闲</span>
      </div>
    </div>

    <!-- 日期选择：横向卡片框选 -->
    <div class="date-strip">
      <div class="date-strip-inner">
        <div
          v-for="d in dateOptions"
          :key="d.value"
          class="date-chip"
          :class="{ 'date-chip--active': d.value === statsDate }"
          @click="selectDate(d.value)"
        >
          <span class="date-chip-week">{{ d.weekday }}</span>
          <span class="date-chip-date">{{ d.label }}</span>
        </div>
      </div>
    </div>

    <!-- 桌位平面图：按区域分组 -->
    <div class="floor-plan" v-if="zoneGroups.length > 0">
      <div v-for="zone in zoneGroups" :key="zone.name" class="zone-block">
        <div class="zone-header">
          <span class="zone-name">{{ zone.name }}</span>
          <span class="zone-summary">
            <span class="zone-free">{{ zone.freeCount }}空闲</span>
            <span class="zone-divider">/</span>
            <span class="zone-total">{{ zone.tables.length }}桌</span>
          </span>
        </div>
        <div class="zone-grid">
          <div
            v-for="t in zone.tables"
            :key="t.id"
            class="table-cell"
            :class="{
              'table-cell--booked': t._booked,
              'table-cell--free': !t._booked && t.status === 'active',
              'table-cell--inactive': t.status === 'inactive',
            }"
            @click="onTableClick(t)"
          >
            <span class="table-cell-no">{{ t.table_no }}</span>
            <span class="table-cell-capa">{{ t.capacity }}人</span>
            <div v-if="t._booking" class="table-cell-guest">
              {{ t._booking.customer_name }}
            </div>
            <span v-else-if="t.status === 'inactive'" class="table-cell-label">停用</span>
            <span v-else class="table-cell-label table-cell-label--free">空闲</span>
          </div>
        </div>
      </div>
    </div>
    <div v-else class="empty-state">
      <p class="empty-text">暂无桌位数据</p>
    </div>

    <!-- 新增预约弹窗 -->
    <div v-if="showBookingForm" class="modal-overlay" @click.self="closeBookingForm">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">新增预约</span>
          <button class="modal-close" @click="closeBookingForm">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M4 4l10 10M14 4l-10 10" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">客人姓名 *</label>
            <input v-model="bookingForm.customer_name" class="form-input" placeholder="请输入姓名" />
          </div>
          <div class="form-group">
            <label class="form-label">手机号</label>
            <input v-model="bookingForm.phone" class="form-input" placeholder="选填" />
          </div>
          <div class="form-group">
            <label class="form-label">日期 *</label>
            <input v-model="bookingForm.date" type="date" class="form-input" />
          </div>
          <div class="form-group">
            <label class="form-label">时段</label>
            <input v-model="bookingForm.time_slot" class="form-input" placeholder="如 19:00-21:00" />
          </div>
          <div class="form-group">
            <label class="form-label">人数</label>
            <input v-model.number="bookingForm.guests_count" type="number" class="form-input" min="1" />
          </div>
          <div class="form-group">
            <label class="form-label">桌位</label>
            <select v-model="bookingForm.table_id" class="form-input">
              <option value="">自动分配</option>
              <option v-for="t in activeTables" :key="t.id" :value="t.id">
                {{ t.area }} {{ t.table_no }} ({{ t.capacity }}人)
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">备注</label>
            <textarea v-model="bookingForm.notes" class="form-textarea" rows="2" placeholder="选填" />
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="closeBookingForm">取消</button>
          <button class="btn-submit" @click="submitBooking" :disabled="submitting">确认</button>
        </div>
      </div>
    </div>

    <!-- 预约详情弹窗 -->
    <div v-if="detailBooking" class="modal-overlay" @click.self="detailBooking = null">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">预约详情</span>
          <button class="modal-close" @click="detailBooking = null">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M4 4l10 10M14 4l-10 10" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="detail-row">
            <span class="detail-label">姓名</span>
            <span class="detail-value">{{ detailBooking.customer_name }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">手机</span>
            <span class="detail-value">{{ detailBooking.phone }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">日期</span>
            <span class="detail-value">{{ detailBooking.date }}</span>
          </div>
          <div class="detail-row" v-if="detailBooking.time_slot">
            <span class="detail-label">时段</span>
            <span class="detail-value">{{ detailBooking.time_slot }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">桌位</span>
            <span class="detail-value">
              {{ detailBooking.table_area || '' }} {{ detailBooking.table_no || '未分配' }} / {{ detailBooking.guests_count }}人
            </span>
          </div>
          <div class="detail-row">
            <span class="detail-label">状态</span>
            <span class="booking-status" :class="`status--${detailBooking.status}`">{{ statusLabel(detailBooking.status) }}</span>
          </div>
          <div class="detail-row">
            <span class="detail-label">预定人</span>
            <span class="detail-value">{{ detailBooking.created_by_name || '-' }}</span>
          </div>
          <div class="detail-row" v-if="detailBooking.notes">
            <span class="detail-label">备注</span>
            <span class="detail-value">{{ detailBooking.notes }}</span>
          </div>
        </div>
        <div class="modal-footer" v-if="detailBooking.status === 'confirmed'">
          <button class="btn-cancel" style="flex:2" @click="handleCancel(detailBooking.id); detailBooking = null">取消预约</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onActivated } from 'vue'
import { tableAPI, bookingAPI } from '@/api/booking'
import type { TableItem, BookingItem, BookingStats } from '@/api/booking'

// ==================== State ====================

const today = new Date().toISOString().slice(0, 10)
const statsDate = ref(today)
const stats = ref<BookingStats>({ date: today, total_tables: 0, booked: 0, free: 0 })
const bookings = ref<BookingItem[]>([])
const tables = ref<TableItem[]>([])
const submitting = ref(false)
const showBookingForm = ref(false)
const selectedTableId = ref<string | null>(null)
const detailBooking = ref<BookingItem | null>(null)

const bookingForm = ref({
  customer_name: '',
  phone: '',
  date: today,
  time_slot: '',
  guests_count: 4,
  table_id: '' as string,
  notes: '',
})

// ==================== Computed ====================

const isToday = computed(() => statsDate.value === today)

const activeTables = computed(() => tables.value.filter(t => t.status === 'active'))

// 日期选项：今天起未来7天
const dateOptions = computed(() => {
  const weekdays = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const opts: { value: string; weekday: string; label: string }[] = []
  const now = new Date()
  for (let i = 0; i < 7; i++) {
    const d = new Date(now)
    d.setDate(d.getDate() + i)
    const value = formatDate(d)
    let weekday: string
    if (i === 0) weekday = '今天'
    else if (i === 1) weekday = '明天'
    else if (i === 2) weekday = '后天'
    else weekday = weekdays[d.getDay()]
    const label = `${d.getMonth() + 1}/${d.getDate()}`
    opts.push({ value, weekday, label })
  }
  return opts
})

// 每个桌位附加是否被预约信息
interface TableWithBooking extends TableItem {
  _booked: boolean
  _booking: BookingItem | null
}

const tablesWithStatus = computed<TableWithBooking[]>(() => {
  const bookedIds = new Set(
    bookings.value
      .filter(b => b.status === 'confirmed' && b.date === statsDate.value)
      .map(b => b.table_id)
  )
  return tables.value.map(t => ({
    ...t,
    _booked: bookedIds.has(t.id),
    _booking: bookings.value.find(b => b.status === 'confirmed' && b.table_id === t.id) || null,
  }))
})

const zoneGroups = computed(() => {
  const zoneOrder = ['大桌', '八人桌', '六人桌', '四人桌', '卡座', '包间', '吧台']
  const map: Record<string, TableWithBooking[]> = {}
  for (const t of tablesWithStatus.value) {
    const area = t.area || '其他'
    if (!map[area]) map[area] = []
    map[area].push(t)
  }
  return zoneOrder
    .filter(name => map[name] && map[name].length > 0)
    .map(name => ({
      name,
      tables: map[name],
      freeCount: map[name].filter(t => !t._booked && t.status === 'active').length,
    }))
    .concat(
      Object.keys(map)
        .filter(k => !zoneOrder.includes(k))
        .map(name => ({
          name,
          tables: map[name],
          freeCount: map[name].filter(t => !t._booked && t.status === 'active').length,
        }))
    )
})

// ==================== Methods ====================

function formatDate(date: Date): string {
  return date.toISOString().slice(0, 10)
}

function selectDate(value: string) {
  statsDate.value = value
  reloadAll()
}

function statusLabel(status: string): string {
  const map: Record<string, string> = {
    confirmed: '已确认',
    cancelled: '已取消',
    completed: '已完成',
    no_show: '未到店',
  }
  return map[status] || status
}

async function reloadAll() {
  loadStats()
  loadBookings()
}

async function loadStats() {
  try {
    const res = await bookingAPI.stats(statsDate.value)
    stats.value = res.data.data
  } catch { /* ignore */ }
}

async function loadBookings() {
  try {
    const res = await bookingAPI.list({ date: statsDate.value, page_size: 200 })
    bookings.value = res.data.data.items
  } catch { /* ignore */ }
}

async function loadTables() {
  try {
    const res = await tableAPI.list({ page_size: 200 })
    tables.value = res.data.data.items
  } catch { /* ignore */ }
}

function onTableClick(t: TableWithBooking) {
  if (t.status === 'inactive') return
  if (t._booked && t._booking) {
    detailBooking.value = t._booking
  } else {
    openBookingForm(t.id)
  }
}

async function submitBooking() {
  if (!bookingForm.value.customer_name || !bookingForm.value.date) {
    alert('请填写必填项')
    return
  }
  submitting.value = true
  try {
    const params: any = { ...bookingForm.value }
    if (!params.table_id) delete params.table_id
    await bookingAPI.create(params)
    closeBookingForm()
    // 等待所有数据刷新完再关闭 loading
    await Promise.all([loadStats(), loadBookings(), loadTables()])
  } catch (e: any) {
    const msg = e?.response?.data?.message || '预约失败'
    alert(msg)
  } finally {
    submitting.value = false
  }
}

async function handleCancel(id: string) {
  if (!confirm('确认取消该预约？')) return
  try {
    const res = await bookingAPI.cancel(id)
    detailBooking.value = null
    await Promise.all([loadStats(), loadBookings()])
  } catch (e: any) {
    console.error('[Cancel] 取消失败:', e instanceof Error ? e.message : String(e))
    const msg = e.response?.data?.message || e.message || '未知错误'
    alert('取消失败: ' + msg)
  }
}

function openBookingForm(tableId: string | null) {
  selectedTableId.value = tableId
  bookingForm.value = {
    customer_name: '',
    phone: '',
    date: statsDate.value,
    time_slot: '',
    guests_count: tableId
      ? tables.value.find(t => t.id === tableId)?.capacity || 4
      : 4,
    table_id: tableId || '',
    notes: '',
  }
  showBookingForm.value = true
}

function closeBookingForm() {
  showBookingForm.value = false
  selectedTableId.value = null
}

function showBookingDetail(b: BookingItem) {
  detailBooking.value = b
}

// ==================== Lifecycle ====================

onMounted(() => {
  loadStats()
  loadBookings()
  loadTables()
})

onActivated(() => {
  loadStats()
  loadBookings()
  loadTables()
})
</script>

<style scoped>
/* Page */
.booking-page {
  padding: 16px;
  padding-bottom: 80px;
  min-height: 100vh;
  background: #000000;
}

/* Stats */
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
}
.stat-card {
  flex: 1;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.stat-card--booked {
  border-color: rgba(251, 0, 121, 0.5);
}
.stat-card--free {
  border-color: rgba(255, 104, 162, 0.5);
}
.stat-value {
  display: block;
  font-family: 'Poppins', sans-serif;
  font-size: 28px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}
.stat-value--pink {
  color: #FB0079;
}
.stat-value--dawn {
  color: #00E676;
}
.stat-label {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 12px;
  color: #7A7C80;
}

/* Date Strip - 横向卡片框选 */
.date-strip {
  margin-bottom: 20px;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  scrollbar-width: none;
}
.date-strip::-webkit-scrollbar {
  display: none;
}
.date-strip-inner {
  display: flex;
  gap: 8px;
  padding: 2px 0;
}
.date-chip {
  flex-shrink: 0;
  min-width: 64px;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 10px 8px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, background 0.2s, transform 0.1s;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}
.date-chip:active {
  transform: scale(0.95);
}
.date-chip--active {
  border-color: #FB0079;
  background: #111111;
  box-shadow: 0 0 8px rgba(251, 0, 121, 0.25);
}
.date-chip-week {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 12px;
  font-weight: 600;
  color: #C8C8C8;
}
.date-chip--active .date-chip-week {
  color: #FB0079;
}
.date-chip-date {
  font-family: 'Poppins', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}
.date-chip--active .date-chip-date {
  color: #FB0079;
}

/* Floor Plan */
.floor-plan {
  margin-bottom: 24px;
}
.zone-block {
  margin-bottom: 16px;
}
.zone-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
  padding: 0 2px;
}
.zone-name {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.zone-summary {
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
}
.zone-free {
  color: #00E676;
}
.zone-divider {
  color: #7A7C80;
  margin: 0 4px;
}
.zone-total {
  color: #7A7C80;
}

.zone-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
  gap: 8px;
}

/* Table Cell */
.table-cell {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px 8px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s;
  min-height: 60px;
  display: flex;
  flex-direction: column;
  justify-content: center;
}
.table-cell:active {
  transform: scale(0.97);
}
.table-cell--booked {
  border-color: #FB0079;
  box-shadow: 0 0 8px rgba(251, 0, 121, 0.25);
  background: #111111;
}
.table-cell--inactive {
  opacity: 0.4;
  cursor: default;
}
.table-cell-no {
  font-family: 'Poppins', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.table-cell--booked .table-cell-no {
  color: #FB0079;
}
.table-cell-capa {
  font-size: 10px;
  color: #7A7C80;
  margin-top: 2px;
}
.table-cell-guest {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 10px;
  color: #FB0079;
  margin-top: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.table-cell-label {
  font-size: 10px;
  color: #7A7C80;
  margin-top: 2px;
}
.table-cell-label--free {
  color: #00E676;
}

/* Section */
.section {
  margin-bottom: 16px;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.section-title {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0;
}

/* Empty */
.empty-state {
  padding: 40px 0;
  text-align: center;
}
.empty-text {
  font-size: 13px;
  color: #7A7C80;
}

/* Booking Card */
.booking-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 8px;
  cursor: pointer;
}
.booking-card:active {
  background: #1a1a1a;
}
.booking-card-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}
.booking-name {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
}
.booking-status {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 6px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
}
.status--confirmed {
  background: rgba(251, 0, 121, 0.2);
  color: #FB0079;
}
.status--cancelled {
  background: #333333;
  color: #C8C8C8;
}
.status--completed {
  background: rgba(255, 104, 162, 0.2);
  color: #FB0079;
}
.status--no_show {
  background: #333333;
  color: #7A7C80;
}
.booking-card-body {
  display: flex;
  flex-wrap: wrap;
  gap: 8px 16px;
}
.booking-info {
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-size: 12px;
  color: #C8C8C8;
}

/* Detail */
.detail-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
}
.detail-label {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 13px;
  color: #7A7C80;
}
.detail-value {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 13px;
  color: #FFFFFF;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 14px 14px 0 0;
  width: 100%;
  max-width: 450px;
  max-height: 85vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #222222;
}
.modal-title {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.modal-close {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
}
.modal-body {
  padding: 16px;
}
.modal-footer {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #222222;
}

/* Form */
.form-group {
  margin-bottom: 14px;
}
.form-label {
  display: block;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 6px;
}
.form-input,
.form-textarea {
  width: 100%;
  padding: 10px 12px;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #FFFFFF;
  outline: none;
  box-sizing: border-box;
}
.form-input:focus,
.form-textarea:focus {
  border-color: #FB0079;
}
.form-textarea {
  resize: vertical;
}
select.form-input {
  appearance: none;
}

/* Buttons */
.btn-cancel {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  color: #C8C8C8;
  cursor: pointer;
}
.btn-submit {
  flex: 1;
  padding: 12px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
}
.btn-submit:disabled {
  background: #333333;
  color: #7A7C80;
  cursor: not-allowed;
}
</style>
