<template>
  <div class="roster-page">
    <div class="page-header">
      <h1 class="page-title">存酒名单</h1>
      <span class="page-subtitle">按客人手机号归集</span>
    </div>

    <!-- Tab 切换 -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'stored' }"
        @click="switchTab('stored')"
      >在存</button>
      <button
        class="tab-btn"
        :class="{ active: activeTab === 'retrieved' }"
        @click="switchTab('retrieved')"
      >已取</button>
    </div>

    <!-- 搜索 -->
    <div class="filter-bar">
      <input
        v-model="searchKeyword"
        class="search-input"
        placeholder="搜索姓名 / 手机号 / 酒名"
      />
    </div>

    <!-- 汇总 -->
    <div class="summary-bar" v-if="!loading">
      <span class="sum-item">共 {{ filteredPeople.length }} 位客人</span>
      <span class="sum-item">{{ totalBottles }} 瓶</span>
      <span class="sum-item">{{ totalTypes }} 种酒</span>
    </div>

    <!-- 客人列表 -->
    <div class="people-list" v-if="filteredPeople.length > 0">
      <div
        v-for="p in filteredPeople"
        :key="p.phone"
        class="person-card"
        @click="openPerson(p)"
      >
        <div class="pc-top">
          <span class="pc-name">{{ p.customer_name }}</span>
          <span class="pc-phone">{{ p.phone }}</span>
        </div>
        <div class="pc-bottom">
          <span class="pc-types">{{ p.wineTypes }} 种酒</span>
          <span class="pc-total">共 {{ p.total }} 瓶</span>
          <span class="pc-stored" v-if="p.storedCount > 0">在存 {{ p.storedCount }}</span>
          <span class="pc-retrieved" v-if="p.retrievedCount > 0">已取 {{ p.retrievedCount }}</span>
          <span class="pc-arrow">
            <svg width="14" height="14" viewBox="0 0 14 14" fill="none"><path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/></svg>
          </span>
        </div>
      </div>
    </div>
    <div v-else-if="!loading" class="empty-state">
      <p class="empty-text">{{ activeTab === 'stored' ? '暂无在存酒水' : '暂无已取记录' }}</p>
    </div>
    <div v-else class="loading-state">
      <p class="loading-text">加载中...</p>
    </div>

    <!-- ========== 在存详情弹窗 ========== -->
    <el-dialog v-model="showStoredDialog" :title="selectedPerson?.customer_name || '客人存酒'" width="90%" :close-on-click-modal="true">
      <div class="person-detail" v-if="selectedPerson">
        <div class="person-meta">
          <span class="pm-name">{{ selectedPerson.customer_name }}</span>
          <span class="pm-phone">{{ selectedPerson.phone }}</span>
          <span class="pm-total">共 {{ selectedPerson.total }} 瓶 / {{ selectedPerson.wineTypes }} 种</span>
        </div>
        <div class="person-wine-list">
          <div
            v-for="g in personWineGroups"
            :key="g.wine_name"
            class="pw-item"
          >
            <div class="pw-top">
              <span class="pw-name">{{ g.wine_name }}</span>
              <span class="pw-qty">×{{ g.bottles.length }}</span>
            </div>
            <div class="pw-sub">
              <span class="pw-ml">{{ remainingLabel(g.bottles[0].remaining_ml, g.bottles[0].initial_ml) }}</span>
              <span class="pw-date">存于 {{ formatDate(g.bottles[0].date_stored) }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showStoredDialog = false">关闭</button>
      </template>
    </el-dialog>

    <!-- ========== 已取详情弹窗（按取酒事件分组） ========== -->
    <el-dialog v-model="showRetrievedDialog" :title="selectedPerson?.customer_name + ' - 取酒记录'" width="90%" :close-on-click-modal="true">
      <div class="person-detail" v-if="selectedPerson">
        <div class="person-meta">
          <span class="pm-name">{{ selectedPerson.customer_name }}</span>
          <span class="pm-phone">{{ selectedPerson.phone }}</span>
          <span class="pm-total">共取 {{ selectedPerson.total }} 瓶</span>
        </div>
        <div class="event-list">
          <div
            v-for="(evt, idx) in retrievalEvents"
            :key="idx"
            class="event-card"
          >
            <!-- 事件头部：时间 + 桌号 + 取酒人 -->
            <div class="evt-header">
              <div class="evt-header-left">
                <span class="evt-time">{{ formatDateTime(evt.retrieved_at) }}</span>
                <span class="evt-table" v-if="evt.table_no">{{ evt.table_no }}桌</span>
              </div>
              <div class="evt-retriever">
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none"><circle cx="6" cy="3.5" r="2" stroke="#FB0079" stroke-width="1"/><path d="M2 10c0-2.2 1.8-4 4-4s4 1.8 4 4" stroke="#FB0079" stroke-width="1" fill="none"/></svg>
                <span v-if="evt.retriever_name">{{ evt.retriever_name }}<span class="evt-emp-code" v-if="evt.retriever_employee_code"> ({{ evt.retriever_employee_code }})</span></span>
                <span v-else class="evt-no-retriever">取酒人未知</span>
              </div>
            </div>

            <!-- 酒水汇总：酒名 × 数量 -->
            <div class="evt-wines">
              <div
                v-for="wg in evt.wineGroups"
                :key="wg.wine_name"
                class="evt-wine-row"
              >
                <span class="evt-wine-name">{{ wg.wine_name }}</span>
                <span class="evt-wine-qty">×{{ wg.count }}</span>
                <span class="evt-wine-ml">{{ wg.initial_ml }}ml → {{ wg.remaining_ml }}ml</span>
              </div>
            </div>

            <!-- 展开瓶码详情 -->
            <div class="evt-expand" @click="toggleEvent(idx)">
              <span class="evt-expand-text">
                {{ expandedEvents.has(idx) ? '收起瓶码' : '查看瓶码 (' + evt.bottles.length + '瓶)' }}
              </span>
              <svg :class="['evt-expand-arrow', { rotated: expandedEvents.has(idx) }]" width="12" height="12" viewBox="0 0 12 12" fill="none"><path d="M4 5l2 2 2-2" stroke="#7A7C80" stroke-width="1" stroke-linecap="round"/></svg>
            </div>
            <div class="evt-bottle-list" v-if="expandedEvents.has(idx)">
              <div
                v-for="b in evt.bottles"
                :key="b.bottle_label"
                class="evt-bottle-item"
              >
                <span class="evt-bottle-wine">{{ b.wine_name }}</span>
                <span class="evt-bottle-label">{{ b.bottle_label }}</span>
                <span class="evt-bottle-cabinet" v-if="b.cabinet_no">柜{{ b.cabinet_no }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showRetrievedDialog = false">关闭</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { wineAPI, type WineInfo } from '@/api/wine'

interface PersonGroup {
  phone: string
  customer_name: string
  bottles: WineInfo[]
  total: number
  wineTypes: number
  storedCount: number
  retrievedCount: number
}

interface WineGroup {
  wine_name: string
  bottles: WineInfo[]
}

/** 一次取酒事件 */
interface WineSummary {
  wine_name: string
  count: number
  initial_ml: number
  remaining_ml: number
}

interface RetrievalEvent {
  retrieved_at: string
  table_no: string | null
  retriever_name: string | null
  retriever_employee_code: string | null
  bottles: WineInfo[]
  wineGroups: WineSummary[]
}

const activeTab = ref<'stored' | 'retrieved'>('stored')
const people = ref<PersonGroup[]>([])
const loading = ref(false)
const searchKeyword = ref('')

const filteredPeople = computed<PersonGroup[]>(() => {
  const kw = searchKeyword.value.trim()
  if (!kw) return people.value
  return people.value.filter(p =>
    p.phone.includes(kw) ||
    p.customer_name.includes(kw) ||
    p.bottles.some(b => b.wine_name.includes(kw))
  )
})

const totalBottles = computed(() => filteredPeople.value.reduce((s, p) => s + p.total, 0))
const totalTypes = computed(() => {
  const set = new Set<string>()
  for (const p of filteredPeople.value) {
    for (const b of p.bottles) set.add(b.wine_name)
  }
  return set.size
})

function switchTab(tab: 'stored' | 'retrieved') {
  activeTab.value = tab
  searchKeyword.value = ''
  loadPeople()
}

async function loadPeople() {
  loading.value = true
  try {
    const params: { status?: string; page: number; page_size: number } = {
      page: 1,
      page_size: 100,
    }
    if (activeTab.value) params.status = activeTab.value
    const { data: res } = await wineAPI.list(params)
    const items = res.code === 0 ? (res.data.items || []) : []
    // 按手机号归人
    const map = new Map<string, PersonGroup>()
    for (const w of items) {
      const key = w.phone || '未知'
      if (!map.has(key)) {
        map.set(key, {
          phone: w.phone || '未知',
          customer_name: w.customer_name || '未知',
          bottles: [],
          total: 0,
          wineTypes: 0,
          storedCount: 0,
          retrievedCount: 0,
        })
      }
      const person = map.get(key)!
      person.bottles.push(w)
    }
    const list: PersonGroup[] = []
    for (const p of map.values()) {
      p.total = p.bottles.length
      const wineNameSet = new Set(p.bottles.map(b => b.wine_name))
      p.wineTypes = wineNameSet.size
      p.storedCount = p.bottles.filter(b => b.status === 'stored').length
      p.retrievedCount = p.bottles.filter(b => b.status === 'retrieved').length
      list.push(p)
    }
    list.sort((a, b) => b.total - a.total)
    people.value = list
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '加载失败')
    people.value = []
  } finally {
    loading.value = false
  }
}

// 弹窗
const showStoredDialog = ref(false)
const showRetrievedDialog = ref(false)
const selectedPerson = ref<PersonGroup | null>(null)
const expandedEvents = ref(new Set<number>())

const personWineGroups = computed<WineGroup[]>(() => {
  if (!selectedPerson.value) return []
  const map = new Map<string, WineGroup>()
  for (const b of selectedPerson.value.bottles) {
    if (!map.has(b.wine_name)) map.set(b.wine_name, { wine_name: b.wine_name, bottles: [] })
    map.get(b.wine_name)!.bottles.push(b)
  }
  return Array.from(map.values()).sort((a, b) => b.bottles.length - a.bottles.length)
})

/** 按取酒事件分组（同一个人 + 同一分钟 + 同一桌号 = 一次事件） */
const retrievalEvents = computed<RetrievalEvent[]>(() => {
  if (!selectedPerson.value) return []
  const bottles = selectedPerson.value.bottles

  // 按 retrieved_by + retrieved_at(分钟精度) + table_no 分组
  const eventMap = new Map<string, WineInfo[]>()
  for (const b of bottles) {
    const timeKey = b.retrieved_at ? b.retrieved_at.substring(0, 16) : 'unknown'
    const key = `${b.retrieved_by || 'unknown'}|${timeKey}|${b.table_no || ''}`
    if (!eventMap.has(key)) eventMap.set(key, [])
    eventMap.get(key)!.push(b)
  }

  const events: RetrievalEvent[] = []
  for (const group of eventMap.values()) {
    // 按酒名汇总
    const wineMap = new Map<string, { count: number; initial_ml: number; remaining_ml: number }>()
    for (const b of group) {
      const name = b.wine_name
      if (!wineMap.has(name)) wineMap.set(name, { count: 0, initial_ml: b.initial_ml || 0, remaining_ml: b.remaining_ml || 0 })
      wineMap.get(name)!.count++
    }
    const wineGroups: WineSummary[] = []
    for (const [wine_name, info] of wineMap.entries()) {
      wineGroups.push({ wine_name, ...info })
    }
    wineGroups.sort((a, b) => b.count - a.count)

    const first = group[0]
    events.push({
      retrieved_at: first.retrieved_at || '',
      table_no: first.table_no,
      retriever_name: first.retriever_name || null,
      retriever_employee_code: first.retriever_employee_code || null,
      bottles: group,
      wineGroups,
    })
  }

  // 按时间倒序
  events.sort((a, b) => (b.retrieved_at || '').localeCompare(a.retrieved_at || ''))
  return events
})

function toggleEvent(idx: number) {
  if (expandedEvents.value.has(idx)) {
    expandedEvents.value.delete(idx)
  } else {
    expandedEvents.value.add(idx)
  }
}

function openPerson(p: PersonGroup) {
  selectedPerson.value = p
  expandedEvents.value = new Set()
  if (activeTab.value === 'stored') {
    showStoredDialog.value = true
  } else {
    showRetrievedDialog.value = true
  }
}

function formatDate(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '-'
  const d = new Date(iso)
  if (isNaN(d.getTime())) return iso
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const h = String(d.getHours()).padStart(2, '0')
  const min = String(d.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${day} ${h}:${min}`
}

function remainingLabel(remaining: number | null, initial: number | null): string {
  const r = remaining || 0
  const i = initial || 0
  if (r <= 0) return '已取完'
  if (r === i) return '满瓶'
  const pct = r / i
  if (pct >= 0.7) return '约3/4瓶'
  if (pct >= 0.45) return '约1/2瓶'
  return '约1/4瓶'
}

onMounted(() => {
  loadPeople()
})
</script>

<style scoped>
.roster-page { padding: 16px; background: #000000; min-height: 100vh; padding-bottom: calc(64px + 24px); }
.page-header { margin-bottom: 16px; }
.page-title { font-family: "Source Han Sans SC", sans-serif; font-size: 22px; font-weight: 700; color: #FFFFFF; margin: 0; }
.page-subtitle { font-size: 12px; color: #7A7C80; }

/* Tab 切换 */
.tab-bar { display: flex; gap: 4px; margin-bottom: 12px; background: #111111; border-radius: 8px; padding: 4px; }
.tab-btn {
  flex: 1; height: 36px; border: none; border-radius: 6px; font-size: 14px; font-weight: 600;
  cursor: pointer; transition: all 0.2s;
  background: transparent; color: #7A7C80;
}
.tab-btn.active { background: #FB0079; color: #FFFFFF; }

.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input { flex: 1; height: 40px; padding: 0 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 13px; outline: none; }
.search-input:focus { border-color: #FB0079; }
.search-input::placeholder { color: #7A7C80; }
.summary-bar { display: flex; gap: 16px; padding: 10px 12px; background: #111111; border-radius: 8px; margin-bottom: 12px; }
.sum-item { font-size: 12px; color: #C8C8C8; }
.sum-item:first-child { color: #FB0079; font-weight: 600; }
.people-list { display: flex; flex-direction: column; gap: 8px; }
.person-card { padding: 12px 14px; background: #111111; border: 1px solid #333333; border-radius: 10px; cursor: pointer; transition: border-color 0.2s; }
.person-card:hover { border-color: #FB0079; }
.pc-top { display: flex; align-items: center; gap: 10px; margin-bottom: 6px; }
.pc-name { font-size: 15px; font-weight: 600; color: #FFFFFF; }
.pc-phone { font-size: 12px; color: #7A7C80; font-family: 'Poppins', sans-serif; }
.pc-bottom { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.pc-types { font-size: 12px; color: #C8C8C8; }
.pc-total { font-size: 12px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; }
.pc-stored { font-size: 11px; color: #FB0079; padding: 1px 8px; border-radius: 4px; background: rgba(251,0,121,0.1); }
.pc-retrieved { font-size: 11px; color: #7A7C80; padding: 1px 8px; border-radius: 4px; background: rgba(122,124,128,0.1); }
.pc-arrow { margin-left: auto; display: flex; align-items: center; }
.empty-state, .loading-state { display: flex; justify-content: center; padding: 60px 16px; }
.empty-text, .loading-text { font-size: 14px; color: #7A7C80; }
/* 详情弹窗 */
.person-detail { display: flex; flex-direction: column; gap: 12px; }
.person-meta { display: flex; align-items: center; gap: 12px; padding: 10px 12px; background: #111111; border-radius: 8px; flex-wrap: wrap; }
.pm-name { font-size: 16px; font-weight: 600; color: #FFFFFF; }
.pm-phone { font-size: 13px; color: #7A7C80; font-family: 'Poppins', sans-serif; }
.pm-total { font-size: 12px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; margin-left: auto; }
.person-wine-list { display: flex; flex-direction: column; gap: 6px; max-height: 50vh; overflow-y: auto; }
.pw-item { padding: 10px 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; }
.pw-top { display: flex; align-items: center; gap: 8px; margin-bottom: 4px; }
.pw-name { font-size: 14px; color: #FFFFFF; flex: 1; }
.pw-qty { font-size: 13px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; }
.pw-sub { display: flex; align-items: center; gap: 12px; }
.pw-ml { font-size: 12px; color: #C8C8C8; }
.pw-date { font-size: 11px; color: #7A7C80; }

/* ========== 已取：取酒事件卡片 ========== */
.event-list { display: flex; flex-direction: column; gap: 10px; max-height: 55vh; overflow-y: auto; }
.event-card { background: #111111; border: 1px solid #333333; border-radius: 10px; overflow: hidden; }

.evt-header { padding: 10px 12px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; border-bottom: 1px solid #222222; }
.evt-header-left { display: flex; align-items: center; gap: 8px; }
.evt-time { font-size: 13px; color: #FFFFFF; font-weight: 600; font-family: 'Poppins', sans-serif; }
.evt-table { font-size: 11px; color: #FB0079; background: rgba(251,0,121,0.1); padding: 1px 6px; border-radius: 4px; }
.evt-retriever { display: flex; align-items: center; gap: 4px; font-size: 12px; color: #FB0079; }
.evt-emp-code { color: #C8C8C8; font-family: 'Poppins', sans-serif; font-size: 11px; }
.evt-no-retriever { color: #7A7C80; font-style: italic; }

.evt-wines { padding: 8px 12px; display: flex; flex-direction: column; gap: 4px; }
.evt-wine-row { display: flex; align-items: center; gap: 8px; }
.evt-wine-name { font-size: 13px; color: #FFFFFF; flex: 1; }
.evt-wine-qty { font-size: 13px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; }
.evt-wine-ml { font-size: 11px; color: #7A7C80; font-family: 'Poppins', sans-serif; }

.evt-expand { display: flex; align-items: center; justify-content: center; gap: 4px; padding: 6px 12px; cursor: pointer; border-top: 1px solid #1A1A1A; }
.evt-expand:hover { background: #1A1A1A; }
.evt-expand-text { font-size: 11px; color: #7A7C80; }
.evt-expand-arrow { transition: transform 0.2s; }
.evt-expand-arrow.rotated { transform: rotate(180deg); }

.evt-bottle-list { padding: 6px 12px 10px; display: flex; flex-direction: column; gap: 3px; border-top: 1px solid #1A1A1A; }
.evt-bottle-item { display: flex; align-items: center; gap: 8px; padding: 3px 0; }
.evt-bottle-wine { font-size: 11px; color: #C8C8C8; flex: 1; }
.evt-bottle-label { font-size: 11px; color: #7A7C80; font-family: 'Poppins', sans-serif; background: #1A1A1A; padding: 1px 6px; border-radius: 4px; }
.evt-bottle-cabinet { font-size: 10px; color: #7A7C80; }

.btn-cancel { height: 40px; padding: 0 24px; background: #111111; color: #C8C8C8; border: 1px solid #333333; border-radius: 8px; font-size: 14px; cursor: pointer; }
</style>
