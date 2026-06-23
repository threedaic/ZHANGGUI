<template>
  <div class="roster-page">
    <div class="page-header">
      <h1 class="page-title">存酒名单</h1>
      <span class="page-subtitle">按客人手机号归集</span>
    </div>

    <!-- 搜索 + 筛选 -->
    <div class="filter-bar">
      <input
        v-model="searchKeyword"
        class="search-input"
        placeholder="搜索姓名 / 手机号 / 酒名"
      />
      <select v-model="statusFilter" class="status-select">
        <option value="stored">在存</option>
        <option value="retrieved">已取</option>
        <option value="">全部</option>
      </select>
    </div>

    <!-- 汇总 -->
    <div class="summary-bar" v-if="!loading">
      <span class="sum-item">共 {{ people.length }} 位客人</span>
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
      <p class="empty-text">暂无存酒记录</p>
    </div>
    <div v-else class="loading-state">
      <p class="loading-text">加载中...</p>
    </div>

    <!-- ========== 客人详情弹窗 ========== -->
    <el-dialog v-model="showPersonDialog" :title="selectedPerson?.customer_name || '客人存酒'" width="90%" :close-on-click-modal="true">
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
        <button class="btn-cancel" @click="showPersonDialog = false">关闭</button>
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

const people = ref<PersonGroup[]>([])
const loading = ref(false)
const searchKeyword = ref('')
const statusFilter = ref<'stored' | 'retrieved' | ''>('stored')

const filteredPeople = computed<PersonGroup[]>(() => {
  const kw = searchKeyword.value.trim()
  if (!kw) return people.value
  return people.value.filter(p =>
    p.phone.includes(kw) ||
    p.customer_name.includes(kw) ||
    p.bottles.some(b => b.wine_name.includes(kw))
  )
})

const totalBottles = computed(() => people.value.reduce((s, p) => s + p.total, 0))
const totalTypes = computed(() => {
  const set = new Set<string>()
  for (const p of people.value) {
    for (const b of p.bottles) set.add(b.wine_name)
  }
  return set.size
})

async function loadPeople() {
  loading.value = true
  try {
    const params: { status?: string; page: number; page_size: number } = {
      page: 1,
      page_size: 100,
    }
    if (statusFilter.value) params.status = statusFilter.value
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

// 客人详情
const showPersonDialog = ref(false)
const selectedPerson = ref<PersonGroup | null>(null)

const personWineGroups = computed<WineGroup[]>(() => {
  if (!selectedPerson.value) return []
  const map = new Map<string, WineGroup>()
  for (const b of selectedPerson.value.bottles) {
    if (!map.has(b.wine_name)) map.set(b.wine_name, { wine_name: b.wine_name, bottles: [] })
    map.get(b.wine_name)!.bottles.push(b)
  }
  return Array.from(map.values()).sort((a, b) => b.bottles.length - a.bottles.length)
})

function openPerson(p: PersonGroup) {
  selectedPerson.value = p
  showPersonDialog.value = true
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
.filter-bar { display: flex; gap: 8px; margin-bottom: 12px; }
.search-input { flex: 1; height: 40px; padding: 0 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 13px; outline: none; }
.search-input:focus { border-color: #FB0079; }
.search-input::placeholder { color: #7A7C80; }
.status-select { width: 80px; height: 40px; padding: 0 8px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #C8C8C8; font-size: 13px; outline: none; }
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
/* 客人详情弹窗 */
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
.btn-cancel { height: 40px; padding: 0 24px; background: #111111; color: #C8C8C8; border: 1px solid #333333; border-radius: 8px; font-size: 14px; cursor: pointer; }
</style>
