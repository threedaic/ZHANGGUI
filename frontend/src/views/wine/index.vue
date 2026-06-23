<template>
  <div class="wine-page">
    <!-- 两个大按钮 -->
    <div class="action-block">
      <button class="big-btn store-btn" @click="showStoreDialog = true">
        <span class="big-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M13 6h14l3 8H10l3-8z"/><path d="M17 14v14c0 4-6 4-6 0V14"/><rect x="22" y="14" width="7" height="17" rx="2"/>
          </svg>
        </span>
        <span class="big-label">存酒</span>
        <span class="big-sub">登记客人存酒</span>
      </button>
      <button class="big-btn retrieve-btn" @click="showRetrieveDialog = true">
        <span class="big-icon">
          <svg width="40" height="40" viewBox="0 0 40 40" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
            <path d="M8 20a12 12 0 0 1 20-8"/><path d="M32 20a12 12 0 0 1-20 8"/><path d="M28 8v6h-6"/><path d="M12 32v-6h6"/>
          </svg>
        </span>
        <span class="big-label">取酒</span>
        <span class="big-sub">搜索客人取酒</span>
      </button>
    </div>

    <!-- ========== 存酒弹窗 ========== -->
    <el-dialog v-model="showStoreDialog" title="存酒" width="90%" :close-on-click-modal="false">
      <div class="store-form">
        <!-- 客人信息 -->
        <div class="form-section">
          <p class="section-title">客人信息</p>
          <input v-model="storeCustomer" class="form-input" placeholder="客人姓名" />
          <input v-model="storePhone" class="form-input" placeholder="手机号" type="tel" maxlength="11" />
        </div>

        <!-- 酒单列表 -->
        <div class="form-section" v-for="(item, idx) in storeItems" :key="idx">
          <div class="wine-item-header">
            <span class="section-title">第{{ idx + 1 }}种酒</span>
            <button v-if="storeItems.length > 1" class="wine-remove" @click="removeWineItem(idx)">删除</button>
          </div>

          <!-- 容量 -->
          <div class="capacity-grid">
            <button
              v-for="cap in capacities"
              :key="cap.value"
              class="capacity-btn"
              :class="{ active: item.remaining_ml === cap.value }"
              @click="item.remaining_ml = cap.value"
            >{{ cap.label }}</button>
          </div>

          <!-- 数量 -->
          <div class="qty-row">
            <button class="qty-btn" @click="decItemQty(idx)">-</button>
            <span class="qty-num">{{ item.quantity }}</span>
            <button class="qty-btn" @click="incItemQty(idx)">+</button>
            <span class="qty-label">瓶</span>
          </div>

          <!-- 酒名 -->
          <el-select
            v-model="item.wine_name"
            class="form-select"
            filterable
            allow-create
            default-first-option
            placeholder="输入或选择酒名"
          >
            <el-option v-for="w in presetWines" :key="w" :label="w" :value="w" />
          </el-select>
        </div>

        <!-- 添加酒种 -->
        <button class="add-wine-btn" @click="addWineItem" v-if="storeItems.length < 10">
          + 添加酒种
        </button>

        <!-- 备注 -->
        <div class="form-section">
          <textarea v-model="storeNotes" class="form-textarea" placeholder="备注（可选）" rows="2" />
        </div>
      </div>
      <template #footer>
        <button class="btn-cancel" @click="showStoreDialog = false">取消</button>
        <button class="btn-confirm" @click="onStore" :disabled="storing">{{ storing ? '存酒中...' : '确认存酒' }}</button>
      </template>
    </el-dialog>

    <!-- ========== 取酒弹窗 ========== -->
    <el-dialog v-model="showRetrieveDialog" title="取酒" width="90%" :close-on-click-modal="false">
      <div class="retrieve-form">
        <p class="section-title">搜索客人（手机号尾号 / 姓名）</p>
        <input
          v-model="retrieveKeyword"
          class="form-input"
          placeholder="输入手机号或姓名"
          @input="onRetrieveSearch"
        />
        <!-- 搜索结果（按客人归人，再按酒名分组） -->
        <div class="retrieve-list" v-if="retrievePeople.length > 0">
          <div
            v-for="person in retrievePeople"
            :key="person.phone"
            class="retrieve-person"
          >
            <div class="rp-header">
              <span class="rp-name">{{ person.customer_name }}</span>
              <span class="rp-phone">{{ person.phone }}</span>
              <span class="rp-total">{{ person.bottles.length }} 瓶</span>
            </div>
            <div class="rp-wines">
              <div
                v-for="g in person.groups"
                :key="g.wine_name"
                class="retrieve-item"
                :class="{ selected: selectedGroup?.wine_name === g.wine_name && selectedGroup?.phone === person.phone }"
                @click="selectRetrieveGroup(person, g)"
              >
                <div class="ri-top">
                  <span class="ri-name">{{ g.wine_name }}</span>
                  <span class="ri-ml">×{{ g.bottles.length }}瓶</span>
                </div>
                <div class="ri-sub">
                  <span class="ri-ml-text">{{ remainingLabel(g.bottles[0].remaining_ml, g.bottles[0].initial_ml) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="retrieve-empty" v-else-if="retrieveSearched">
          <p>未找到该客人的存酒</p>
        </div>
        <!-- 选中后显示取酒表单 -->
        <div class="retrieve-actions" v-if="selectedGroup">
          <p class="section-title">取几瓶</p>
          <div class="qty-row">
            <button class="qty-btn" @click="decRetrieveQty">-</button>
            <span class="qty-num">{{ retrieveQty }}</span>
            <button class="qty-btn" @click="incRetrieveQty">+</button>
            <span class="qty-label">瓶 / 共{{ selectedGroup.bottles.length }}瓶</span>
          </div>
          <input v-model="retrieveTableNo" class="form-input" placeholder="桌号（可选）" style="margin-top:8px" />
        </div>
      </div>
      <template #footer>
        <button
          class="btn-cancel"
          @click="showRetrieveDialog = false; resetRetrieve()"
        >取消</button>
        <button
          class="btn-confirm"
          @click="onRetrieve"
          :disabled="retrieving || !selectedGroup || retrieveQty <= 0"
        >{{ retrieving ? '取酒中...' : `确认取酒（${retrieveQty}瓶）` }}</button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { wineAPI, type WineInfo } from '@/api/wine'

const capacities = [
  { label: '满瓶', value: 750 },
  { label: '3/4瓶', value: 562 },
  { label: '1/2瓶', value: 375 },
  { label: '1/4瓶', value: 187 },
]

const presetWines = [
  '百威啤酒', '喜力啤酒', '科罗娜', '1664白啤', '福佳白',
  '青岛啤酒', '雪花啤酒', '燕京啤酒', '哈尔滨啤酒',
  '轩尼诗VSOP', '轩尼诗XO', '马爹利名士', '马爹利蓝带',
  '芝华士12年', '芝华士18年', '尊尼获加黑牌', '尊尼获加蓝牌',
  '皇家礼炮21年', '麦卡伦12年', '格兰菲迪12年',
  '绝对伏特加', '灰雁伏特加', '添加利金酒',
  '百加得白朗姆', '摩根船长', '野格',
  '杰克丹尼', '占边波本', '金宾',
  '奔富407', '奔富389', '拉菲传奇',
]

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

// ==================== 存酒 ====================
const showStoreDialog = ref(false)
const storing = ref(false)
const storeCustomer = ref('')
const storePhone = ref('')
const storeNotes = ref('')

interface WineItem {
  wine_name: string
  remaining_ml: number
  quantity: number
}

const storeItems = ref<WineItem[]>([
  { wine_name: '', remaining_ml: 750, quantity: 1 },
])

function addWineItem() {
  storeItems.value.push({ wine_name: '', remaining_ml: 750, quantity: 1 })
}
function removeWineItem(idx: number) {
  storeItems.value.splice(idx, 1)
}
function incItemQty(idx: number) {
  if (storeItems.value[idx].quantity < 99) storeItems.value[idx].quantity++
}
function decItemQty(idx: number) {
  if (storeItems.value[idx].quantity > 1) storeItems.value[idx].quantity--
}
function resetStoreForm() {
  storeCustomer.value = ''; storePhone.value = ''; storeNotes.value = ''
  storeItems.value = [{ wine_name: '', remaining_ml: 750, quantity: 1 }]
}

async function onStore() {
  if (!storeCustomer.value.trim()) { ElMessage.warning('请输入客人姓名'); return }
  if (!/^1[3-9]\d{9}$/.test(storePhone.value.trim())) { ElMessage.warning('请输入正确手机号'); return }
  for (let i = 0; i < storeItems.value.length; i++) {
    if (!storeItems.value[i].wine_name.trim()) {
      ElMessage.warning(`第${i + 1}种酒的酒名不能为空`); return
    }
  }
  storing.value = true
  try {
    const { data: res } = await wineAPI.batchStore({
      customer_name: storeCustomer.value.trim(),
      phone: storePhone.value.trim(),
      wines: storeItems.value.map(it => ({
        wine_name: it.wine_name.trim(),
        remaining_ml: it.remaining_ml,
        quantity: it.quantity,
      })),
      notes: storeNotes.value.trim() || undefined,
    })
    if (res.code === 0) {
      const total = storeItems.value.reduce((s, it) => s + it.quantity, 0)
      ElMessage.success(`存酒成功！共 ${total} 瓶`)
      showStoreDialog.value = false; resetStoreForm()
    } else {
      ElMessage.error(res.message || '存酒失败')
    }
  } catch (e: any) { ElMessage.error(e?.response?.data?.message || '存酒失败') }
  finally { storing.value = false }
}

// ==================== 取酒 ====================
const showRetrieveDialog = ref(false)
const retrieveKeyword = ref('')
const retrievePeople = ref<RetrievePerson[]>([])
const retrieveSearched = ref(false)
const selectedGroup = ref<{ wine_name: string; customer_name: string; phone: string; bottles: WineInfo[] } | null>(null)
const retrieveQty = ref(1)
const retrieveTableNo = ref('')
const retrieving = ref(false)

interface RetrievePerson {
  phone: string
  customer_name: string
  bottles: WineInfo[]
  groups: Array<{ wine_name: string; bottles: WineInfo[] }>
}

function resetRetrieve() {
  retrieveKeyword.value = ''; retrievePeople.value = []
  retrieveSearched.value = false
  selectedGroup.value = null; retrieveQty.value = 1
  retrieveTableNo.value = ''
}

let retrieveTimer: ReturnType<typeof setTimeout> | null = null

function onRetrieveSearch() {
  if (retrieveTimer) clearTimeout(retrieveTimer)
  const kw = retrieveKeyword.value.trim()
  if (kw.length < 1) { retrievePeople.value = []; retrieveSearched.value = false; return }
  retrieveTimer = setTimeout(async () => {
    try {
      // 不传 search_type → 后端 OR 匹配姓名/手机号/酒名/瓶码
      const { data: res } = await wineAPI.list({ keyword: kw, status: 'stored', page_size: 100 })
      const items = res.code === 0 ? (res.data.items || []) : []
      // 按手机号归人，再按酒名分组
      const map = new Map<string, RetrievePerson>()
      for (const w of items) {
        if (!w.bottle_label) continue
        const key = w.phone || '未知'
        if (!map.has(key)) {
          map.set(key, {
            phone: w.phone || '未知',
            customer_name: w.customer_name || '未知',
            bottles: [],
            groups: [],
          })
        }
        map.get(key)!.bottles.push(w)
      }
      // 每人按酒名分组
      for (const person of map.values()) {
        const gmap = new Map<string, { wine_name: string; bottles: WineInfo[] }>()
        for (const b of person.bottles) {
          if (!gmap.has(b.wine_name)) gmap.set(b.wine_name, { wine_name: b.wine_name, bottles: [] })
          gmap.get(b.wine_name)!.bottles.push(b)
        }
        person.groups = Array.from(gmap.values()).sort((a, b) => b.bottles.length - a.bottles.length)
      }
      retrievePeople.value = Array.from(map.values()).sort((a, b) => b.bottles.length - a.bottles.length)
    } catch { retrievePeople.value = [] }
    retrieveSearched.value = true
  }, 300)
}

function selectRetrieveGroup(person: RetrievePerson, g: { wine_name: string; bottles: WineInfo[] }) {
  selectedGroup.value = {
    wine_name: g.wine_name,
    customer_name: person.customer_name,
    phone: person.phone,
    bottles: g.bottles,
  }
  retrieveQty.value = 1
}

function incRetrieveQty() {
  if (selectedGroup.value && retrieveQty.value < selectedGroup.value.bottles.length) retrieveQty.value++
}
function decRetrieveQty() {
  if (retrieveQty.value > 1) retrieveQty.value--
}

async function onRetrieve() {
  if (!selectedGroup.value) { ElMessage.warning('请先选择要取的酒'); return }
  if (retrieveQty.value <= 0 || retrieveQty.value > selectedGroup.value.bottles.length) {
    ElMessage.warning('取酒数量不正确'); return
  }
  retrieving.value = true
  const bottles = selectedGroup.value.bottles.slice(0, retrieveQty.value)
  let successCount = 0
  let lastError = ''
  try {
    for (const b of bottles) {
      try {
        // 确保 retrieve_ml > 0，避免 422
        const retrieveMl = b.remaining_ml || b.initial_ml || 750
        const { data: res } = await wineAPI.retrieve({
          bottle_label: b.bottle_label!,
          retrieve_ml: retrieveMl,
          table_no: retrieveTableNo.value.trim() || undefined,
        })
        if (res.code === 0) successCount++
        else lastError = res.message || '取酒失败'
      } catch (e: any) {
        lastError = e?.response?.data?.message || '取酒失败'
      }
    }
    if (successCount === bottles.length) {
      ElMessage.success(`取酒成功！共 ${successCount} 瓶`)
      showRetrieveDialog.value = false; resetRetrieve()
    } else if (successCount > 0) {
      ElMessage.warning(`部分成功：${successCount}/${bottles.length} 瓶，${lastError}`)
      showRetrieveDialog.value = false; resetRetrieve()
    } else {
      ElMessage.error(lastError || '取酒失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '取酒失败')
  }
  finally { retrieving.value = false }
}

// ==================== Lifecycle ====================
onMounted(() => {
  // 主页只展示两个按钮，无需预加载数据
})
</script>

<style scoped>
.wine-page { padding: 16px; background: #000000; min-height: 100vh; display: flex; align-items: center; justify-content: center; }
.action-block { display: flex; flex-direction: column; gap: 20px; width: 100%; max-width: 360px; }
.big-btn { display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 8px; height: 160px; border: none; border-radius: 20px; cursor: pointer; transition: transform 0.15s, box-shadow 0.2s; font-family: 'Source Han Sans SC', sans-serif; }
.big-btn:active { transform: scale(0.98); }
.store-btn { background: linear-gradient(135deg, #FB0079 0%, #d10063 100%); color: #FFFFFF; box-shadow: 0 8px 24px rgba(251,0,121,0.3); }
.retrieve-btn { background: #111111; color: #FFFFFF; border: 1px solid #333333; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.retrieve-btn:active { border-color: #FB0079; }
.big-icon { display: flex; align-items: center; justify-content: center; }
.big-label { font-size: 24px; font-weight: 700; letter-spacing: 2px; }
.big-sub { font-size: 12px; opacity: 0.8; }
.store-form { display: flex; flex-direction: column; gap: 16px; }
.form-section { display: flex; flex-direction: column; gap: 8px; }
.section-title { font-size: 13px; color: #C8C8C8; margin: 0; }
.capacity-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
.capacity-btn { height: 44px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #C8C8C8; font-family: 'Poppins', 'Source Han Sans SC', sans-serif; font-size: 14px; cursor: pointer; }
.capacity-btn.active { background: #FB0079; border-color: #FB0079; color: #FFFFFF; }
.qty-row { display: flex; align-items: center; gap: 12px; }
.qty-btn { width: 40px; height: 40px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #C8C8C8; font-size: 18px; cursor: pointer; display: flex; align-items: center; justify-content: center; }
.qty-num { font-family: 'Poppins', sans-serif; font-size: 22px; color: #FB0079; min-width: 30px; text-align: center; }
.qty-label { font-size: 14px; color: #7A7C80; }
.wine-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.wine-remove { background: none; border: none; color: #FB0079; font-size: 12px; cursor: pointer; padding: 2px 6px; }
.add-wine-btn { width: 100%; height: 40px; margin: 8px 0; background: none; border: 1px dashed #333; border-radius: 8px; color: #C8C8C8; font-size: 13px; cursor: pointer; }
.form-input { height: 44px; padding: 0 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 14px; outline: none; width: 100%; box-sizing: border-box; }
.form-input:focus { border-color: #FB0079; }
.form-input::placeholder { color: #7A7C80; }
.form-select { width: 100%; }
.form-textarea { padding: 10px 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 14px; outline: none; resize: none; width: 100%; box-sizing: border-box; }
.form-textarea:focus { border-color: #FB0079; }
.btn-cancel { height: 40px; padding: 0 24px; background: #111111; color: #C8C8C8; border: 1px solid #333333; border-radius: 8px; font-size: 14px; cursor: pointer; }
.btn-confirm { height: 40px; padding: 0 24px; background: #FB0079; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; }
.btn-confirm:disabled { opacity: 0.5; cursor: not-allowed; }
.retrieve-form { display: flex; flex-direction: column; gap: 12px; }
.retrieve-list { display: flex; flex-direction: column; gap: 10px; max-height: 50vh; overflow-y: auto; }
.retrieve-person { background: #0a0a0a; border: 1px solid #222222; border-radius: 10px; overflow: hidden; }
.rp-header { display: flex; align-items: center; gap: 10px; padding: 10px 12px; background: #111111; border-bottom: 1px solid #222222; }
.rp-name { font-size: 14px; font-weight: 600; color: #FFFFFF; }
.rp-phone { font-size: 12px; color: #7A7C80; font-family: 'Poppins', sans-serif; }
.rp-total { margin-left: auto; font-size: 12px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; }
.rp-wines { display: flex; flex-direction: column; gap: 4px; padding: 6px; }
.retrieve-item { padding: 10px 12px; background: #111111; border: 1px solid #333333; border-radius: 8px; cursor: pointer; display: flex; flex-direction: column; gap: 4px; }
.retrieve-item.selected { border-color: #FB0079; background: rgba(251,0,121,0.08); }
.ri-top { display: flex; align-items: center; gap: 8px; }
.ri-sub { display: flex; align-items: center; gap: 12px; }
.ri-name { font-size: 14px; color: #FFFFFF; flex: 1; }
.ri-ml { font-size: 12px; color: #FB0079; font-family: 'Poppins', sans-serif; font-weight: 600; }
.ri-ml-text { font-size: 11px; color: #C8C8C8; }
.retrieve-empty { text-align: center; padding: 20px; color: #7A7C80; font-size: 13px; }
.retrieve-actions { margin-top: 4px; }
</style>
