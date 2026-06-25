<template>
  <div class="rule-page">
    <div class="page-header">
      <span class="page-title">评分码</span>
    </div>

    <!-- 低分预警 -->
    <div class="section">
      <div class="section-header"><span>低分预警</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>低分预警开关</span>
          <input type="checkbox" v-model="form.low_score_alert_enabled" class="toggle" />
        </div>
        <div class="form-row">
          <span>低分阈值</span>
          <input v-model.number="form.low_score_threshold" type="number" min="1" max="5" step="0.5" class="input" />
          <span class="unit">分</span>
        </div>
        <div class="form-row-hint">均分低于此值触发预警并推送给店长。默认 2 分。</div>
      </div>
    </div>

    <!-- 评分码生成 -->
    <div class="section">
      <div class="section-header">
        <span>桌面评分码</span>
        <span class="section-hint">扫码即评分</span>
      </div>
      <div class="section-body">
        <div v-if="tables.length === 0" class="empty">暂无桌位，请先在桌号管理添加</div>
        <div v-else class="qr-grid">
          <div v-for="t in tables" :key="t.id" class="qr-card" @click="openQr(t)">
            <img v-if="qrCache[t.table_no]" :src="qrCache[t.table_no]" class="qr-img" :alt="t.table_no" />
            <div v-else class="qr-placeholder">生成中</div>
            <span class="qr-table">{{ t.table_no }}桌</span>
            <span class="qr-area">{{ t.area }}</span>
          </div>
        </div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="save">
      {{ saving ? '保存中...' : '保存评分规则' }}
    </button>

    <!-- 二维码大图弹窗 -->
    <div v-if="activeTable" class="modal-overlay" @click.self="activeTable = null">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">{{ activeTable.area }} {{ activeTable.table_no }}桌</span>
          <button class="modal-close" @click="activeTable = null">×</button>
        </div>
        <div class="modal-body">
          <img v-if="activeTable && qrCache[activeTable.table_no]" :src="qrCache[activeTable.table_no]" class="qr-big" :alt="activeTable.table_no" />
          <div v-else class="qr-placeholder big">生成中</div>
          <p class="qr-tip">客人扫此码即可评分</p>
          <p class="qr-url">{{ activeTable ? ratingUrl(activeTable.table_no) : '' }}</p>
        </div>
        <div class="modal-footer">
          <button class="btn-cancel" @click="activeTable = null">关闭</button>
          <button class="btn-submit" @click="copyUrl(activeTable.table_no)">复制链接</button>
          <button class="btn-submit" @click="downloadQr(activeTable.table_no)">下载二维码</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import QRCode from 'qrcode'
import { storeAPI } from '@/api/store'
import { tableAPI } from '@/api/booking'
import type { TableItem } from '@/api/booking'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()

const form = reactive({
  low_score_alert_enabled: true,
  low_score_threshold: 2.0,
})

const saving = ref(false)
const tables = ref<TableItem[]>([])
const activeTable = ref<TableItem | null>(null)
// 二维码图片缓存：table_no -> dataURL
const qrCache = ref<Record<string, string>>({})
// 评分码域名（优先用后端配置，兜底用当前域名）
const baseUrl = ref(window.location.origin)

function ratingUrl(tableNo: string): string {
  const storeId = auth.info.store_id || ''
  return `${baseUrl.value}/rating-h5.html?store_id=${storeId}&table_no=${encodeURIComponent(tableNo)}`
}

// 本地生成二维码（不依赖外部服务）
async function genQr(tableNo: string): Promise<string> {
  if (qrCache.value[tableNo]) return qrCache.value[tableNo]
  const url = ratingUrl(tableNo)
  const dataUrl = await QRCode.toDataURL(url, {
    width: 200,
    margin: 2,
    color: { dark: '#000000', light: '#FFFFFF' },
  })
  qrCache.value[tableNo] = dataUrl
  return dataUrl
}

function openQr(t: TableItem) {
  activeTable.value = t
}

async function copyUrl(tableNo: string) {
  try {
    await navigator.clipboard.writeText(ratingUrl(tableNo))
    ElMessage.success('链接已复制')
  } catch {
    ElMessage.error('复制失败')
  }
}

function downloadQr(tableNo: string) {
  const dataUrl = qrCache.value[tableNo]
  if (!dataUrl) {
    ElMessage.error('二维码未生成')
    return
  }
  const a = document.createElement('a')
  a.href = dataUrl
  a.download = `评分码-${tableNo}桌.png`
  a.click()
  ElMessage.success('已下载')
}

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const cfg = res.data.data.extra_config?.rating || {}
    if (cfg.low_score_alert_enabled != null) form.low_score_alert_enabled = cfg.low_score_alert_enabled
    if (cfg.low_score_threshold != null) form.low_score_threshold = cfg.low_score_threshold
  } catch { /* silent */ }
  // 拿后端配置的线上域名（解决本地开发二维码打不开问题）
  try {
    const res = await storeAPI.getInfo()
    const url = res.data.data.frontend_base_url
    if (url) baseUrl.value = url
  } catch { /* silent */ }
  try {
    const res = await tableAPI.list({ page_size: 200 })
    tables.value = res.data.data.items.filter(t => t.status === 'active')
    // 预生成所有桌位二维码
    await Promise.all(tables.value.map(t => genQr(t.table_no)))
  } catch { /* silent */ }
}

async function save() {
  saving.value = true
  try {
    await storeAPI.updateSettings({ extra_config: { rating: { ...form } } } as any)
    ElMessage.success('评分规则已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.rule-page { padding: 16px; padding-bottom: 100px; min-height: 100vh; background: #000000; }
.page-header { display: flex; align-items: center; gap: 12px; margin-bottom: 20px; }
.page-title { font-size: 16px; font-weight: 600; color: #C8C8C8; }
.section { background: #111111; border: 1px solid #333333; border-radius: 12px; margin-bottom: 12px; overflow: hidden; }
.section-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; font-size: 14px; font-weight: 500; color: #C8C8C8; }
.section-hint { font-size: 11px; color: #7A7C80; }
.section-body { padding: 0 16px 16px; }
.form-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #222222; font-size: 13px; color: #C8C8C8; }
.form-row:last-child { border-bottom: none; }
.form-row-hint { padding: 6px 0; font-size: 11px; color: #7A7C80; line-height: 1.5; }
.unit { color: #7A7C80; font-size: 12px; }
.input { width: 60px; padding: 6px 8px; background: #1a1a1a; border: 1px solid #333333; border-radius: 6px; color: #C8C8C8; font-size: 13px; text-align: center; margin-left: auto; }
.input:focus { outline: none; border-color: #FB0079; }
.toggle { accent-color: #FB0079; margin-left: auto; width: 18px; height: 18px; }
.empty { padding: 20px 0; text-align: center; font-size: 13px; color: #7A7C80; }
.qr-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(96px, 1fr)); gap: 10px; padding-top: 8px; }
.qr-card { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 10px 6px; background: #1a1a1a; border: 1px solid #333333; border-radius: 10px; cursor: pointer; transition: border-color 0.2s; }
.qr-card:hover { border-color: #FB0079; }
.qr-img { width: 72px; height: 72px; border-radius: 6px; background: #fff; }
.qr-placeholder { width: 72px; height: 72px; border-radius: 6px; background: #1a1a1a; border: 1px solid #333333; display: flex; align-items: center; justify-content: center; font-size: 11px; color: #7A7C80; }
.qr-placeholder.big { width: 200px; height: 200px; }
.qr-table { font-size: 13px; font-weight: 600; color: #FFFFFF; }
.qr-area { font-size: 10px; color: #7A7C80; }
.save-btn { width: 100%; margin-top: 14px; padding: 14px; background: #FB0079; border: none; border-radius: 8px; font-family: "Source Han Sans SC", sans-serif; font-size: 14px; font-weight: 600; color: #FFFFFF; cursor: pointer; transition: opacity 0.2s; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.modal-overlay { position: fixed; top: 0; left: 0; right: 0; bottom: 0; background: rgba(0,0,0,0.7); display: flex; align-items: center; justify-content: center; z-index: 1000; }
.modal { background: #111111; border: 1px solid #333333; border-radius: 14px; width: 90%; max-width: 320px; }
.modal-header { display: flex; justify-content: space-between; align-items: center; padding: 14px 16px; border-bottom: 1px solid #222222; }
.modal-title { font-size: 15px; font-weight: 600; color: #FFFFFF; }
.modal-close { background: none; border: none; color: #7A7C80; font-size: 22px; cursor: pointer; }
.modal-body { padding: 20px; display: flex; flex-direction: column; align-items: center; gap: 10px; }
.qr-big { width: 200px; height: 200px; border-radius: 8px; background: #fff; }
.qr-tip { font-size: 13px; color: #C8C8C8; }
.qr-url { font-size: 10px; color: #7A7C80; word-break: break-all; text-align: center; }
.modal-footer { display: flex; gap: 8px; padding: 12px 16px; border-top: 1px solid #222222; }
.btn-cancel { flex: 1; padding: 10px; background: #1a1a1a; border: 1px solid #333333; border-radius: 8px; color: #C8C8C8; font-size: 13px; cursor: pointer; }
.btn-submit { flex: 1; padding: 10px; background: #FB0079; border: none; border-radius: 8px; color: #FFFFFF; font-size: 13px; font-weight: 600; cursor: pointer; }
</style>
