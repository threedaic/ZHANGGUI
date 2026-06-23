<template>
  <div class="printer-page">
    <div class="page-header">
      <h1 class="page-title">打印机配置</h1>
      <span class="page-subtitle">存酒出标签 / 取酒出小票</span>
    </div>

    <!-- 两台打印机开关 -->
    <div class="printer-list" v-if="!loading">
      <!-- 标签打印机 -->
      <div class="printer-card" :class="{ on: form.label_printer_enabled }">
        <div class="pc-header">
          <div class="pc-left">
            <span class="pc-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
                <path d="M6 4h12v6H6z"/><path d="M6 14h12v6H6z"/><rect x="9" y="16" width="6" height="2"/>
              </svg>
            </span>
            <div class="pc-info">
              <span class="pc-name">标签打印机</span>
              <span class="pc-desc">存酒时自动打印瓶身标签</span>
            </div>
          </div>
          <button
            class="toggle-btn"
            :class="{ on: form.label_printer_enabled }"
            @click="togglePrinter('label_printer_enabled', !form.label_printer_enabled)"
            :disabled="saving"
          >
            <span class="toggle-icon">{{ form.label_printer_enabled ? '✓' : '✗' }}</span>
            <span class="toggle-text">{{ form.label_printer_enabled ? '打印' : '不打印' }}</span>
          </button>
        </div>
      </div>

      <!-- 取酒单打印机 -->
      <div class="printer-card" :class="{ on: form.receipt_printer_enabled }">
        <div class="pc-header">
          <div class="pc-left">
            <span class="pc-icon">
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
                <path d="M5 4h14v8H5z"/><path d="M5 16h14v4H5z"/><path d="M8 8h8"/><path d="M8 18h6"/>
              </svg>
            </span>
            <div class="pc-info">
              <span class="pc-name">取酒单打印机</span>
              <span class="pc-desc">取酒时自动打印取酒小票</span>
            </div>
          </div>
          <button
            class="toggle-btn"
            :class="{ on: form.receipt_printer_enabled }"
            @click="togglePrinter('receipt_printer_enabled', !form.receipt_printer_enabled)"
            :disabled="saving"
          >
            <span class="toggle-icon">{{ form.receipt_printer_enabled ? '✓' : '✗' }}</span>
            <span class="toggle-text">{{ form.receipt_printer_enabled ? '打印' : '不打印' }}</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 加载中 -->
    <div v-else class="loading-state">
      <p class="loading-text">加载中...</p>
    </div>

    <!-- 高级配置（折叠） -->
    <div class="advanced-section" v-if="!loading">
      <button class="advanced-toggle" @click="showAdvanced = !showAdvanced">
        <span>{{ showAdvanced ? '收起' : '展开' }}高级配置</span>
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none" :style="{ transform: showAdvanced ? 'rotate(90deg)' : '' }">
          <path d="M5 3l4 4-4 4" stroke="#7A7C80" stroke-width="1.2" stroke-linecap="round"/>
        </svg>
      </button>
      <div class="advanced-content" v-if="showAdvanced">
        <div class="form-section">
          <p class="section-title">打印机品牌</p>
          <select v-model="form.printer_brand" class="form-input" :disabled="saving">
            <option value="yilianyun">易联云</option>
            <option value="feie">飞鹅</option>
            <option value="xpyun">芯烨</option>
            <option value="gainscha">佳博</option>
            <option value="jolimark">佳博（骏码）</option>
          </select>
        </div>
        <div class="form-section">
          <p class="section-title">设备 SN</p>
          <input v-model="form.printer_sn" class="form-input" placeholder="打印机 SN 编号" :disabled="saving" />
        </div>
        <div class="form-section">
          <p class="section-title">账号 / Client ID</p>
          <input v-model="form.printer_user" class="form-input" placeholder="API 账号" :disabled="saving" />
        </div>
        <div class="form-section">
          <p class="section-title">Ukey / Client Secret</p>
          <input v-model="form.printer_ukey" class="form-input" placeholder="API 密钥" type="password" :disabled="saving" />
        </div>
        <div class="form-row">
          <div class="form-section">
            <p class="section-title">标签宽度 mm</p>
            <input v-model.number="form.printer_label_width" type="number" class="form-input" :disabled="saving" />
          </div>
          <div class="form-section">
            <p class="section-title">标签高度 mm</p>
            <input v-model.number="form.printer_label_height" type="number" class="form-input" :disabled="saving" />
          </div>
        </div>
        <button class="save-btn" @click="saveAdvanced" :disabled="saving">{{ saving ? '保存中...' : '保存高级配置' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI, type StoreSettingsData } from '@/api/store'

const loading = ref(false)
const saving = ref(false)
const showAdvanced = ref(false)

const form = reactive<{
  label_printer_enabled: boolean
  receipt_printer_enabled: boolean
  printer_brand: string
  printer_sn: string
  printer_user: string
  printer_ukey: string
  printer_label_width: number
  printer_label_height: number
}>({
  label_printer_enabled: false,
  receipt_printer_enabled: false,
  printer_brand: 'yilianyun',
  printer_sn: '',
  printer_user: '',
  printer_ukey: '',
  printer_label_width: 80,
  printer_label_height: 50,
})

async function loadSettings() {
  loading.value = true
  try {
    const { data: res } = await storeAPI.getSettings()
    if (res.code === 0 && res.data) {
      const s = res.data as StoreSettingsData
      form.label_printer_enabled = s.label_printer_enabled ?? false
      form.receipt_printer_enabled = s.receipt_printer_enabled ?? false
      form.printer_brand = s.printer_brand || 'yilianyun'
      form.printer_sn = s.printer_sn || ''
      form.printer_user = s.printer_user || ''
      form.printer_ukey = s.printer_ukey || ''
      form.printer_label_width = s.printer_label_width ?? 80
      form.printer_label_height = s.printer_label_height ?? 50
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '加载配置失败')
  } finally {
    loading.value = false
  }
}

async function togglePrinter(field: 'label_printer_enabled' | 'receipt_printer_enabled', value: boolean) {
  saving.value = true
  const oldValue = form[field]
  form[field] = value
  try {
    const { data: res } = await storeAPI.updateSettings({ [field]: value } as Partial<StoreSettingsData>)
    if (res.code === 0) {
      ElMessage.success(value ? '已开启打印' : '已关闭打印')
    } else {
      form[field] = oldValue
      ElMessage.error(res.message || '保存失败')
    }
  } catch (e: any) {
    form[field] = oldValue
    ElMessage.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function saveAdvanced() {
  saving.value = true
  try {
    const { data: res } = await storeAPI.updateSettings({
      printer_brand: form.printer_brand,
      printer_sn: form.printer_sn,
      printer_user: form.printer_user,
      printer_ukey: form.printer_ukey,
      printer_label_width: form.printer_label_width,
      printer_label_height: form.printer_label_height,
    } as Partial<StoreSettingsData>)
    if (res.code === 0) {
      ElMessage.success('高级配置已保存')
      showAdvanced.value = false
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped>
.printer-page { padding: 16px; background: #000000; min-height: 100vh; padding-bottom: calc(56px + 24px); }
.page-header { margin-bottom: 20px; }
.page-title { font-family: "Source Han Sans SC", sans-serif; font-size: 22px; font-weight: 700; color: #FFFFFF; margin: 0; }
.page-subtitle { font-size: 12px; color: #7A7C80; }
.printer-list { display: flex; flex-direction: column; gap: 12px; margin-bottom: 24px; }
.printer-card { padding: 16px; background: #111111; border: 1px solid #333333; border-radius: 12px; transition: border-color 0.2s; }
.printer-card.on { border-color: #FB0079; }
.pc-header { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
.pc-left { display: flex; align-items: center; gap: 12px; flex: 1; }
.pc-icon { display: flex; align-items: center; justify-content: center; color: #C8C8C8; }
.printer-card.on .pc-icon { color: #FB0079; }
.pc-info { display: flex; flex-direction: column; gap: 2px; }
.pc-name { font-size: 15px; font-weight: 600; color: #FFFFFF; }
.pc-desc { font-size: 12px; color: #7A7C80; }
.toggle-btn { display: flex; align-items: center; gap: 6px; padding: 8px 14px; background: #1a1a1a; border: 1px solid #333333; border-radius: 999px; color: #7A7C80; font-size: 13px; cursor: pointer; transition: all 0.2s; min-width: 96px; justify-content: center; }
.toggle-btn.on { background: #FB0079; border-color: #FB0079; color: #FFFFFF; }
.toggle-btn:disabled { opacity: 0.6; cursor: not-allowed; }
.toggle-icon { font-size: 14px; font-weight: 700; }
.toggle-text { font-size: 12px; }
.loading-state { display: flex; justify-content: center; padding: 60px 16px; }
.loading-text { font-size: 14px; color: #7A7C80; }
.advanced-section { margin-top: 8px; }
.advanced-toggle { display: flex; align-items: center; gap: 6px; padding: 10px 0; background: none; border: none; color: #7A7C80; font-size: 13px; cursor: pointer; }
.advanced-content { display: flex; flex-direction: column; gap: 14px; padding: 16px; background: #111111; border: 1px solid #333333; border-radius: 12px; margin-top: 8px; }
.form-section { display: flex; flex-direction: column; gap: 6px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
.section-title { font-size: 12px; color: #7A7C80; margin: 0; }
.form-input { height: 40px; padding: 0 12px; background: #0a0a0a; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 13px; outline: none; width: 100%; box-sizing: border-box; }
.form-input:focus { border-color: #FB0079; }
.form-input:disabled { opacity: 0.6; }
.save-btn { height: 44px; background: #FB0079; color: #FFFFFF; border: none; border-radius: 8px; font-size: 14px; font-weight: 600; cursor: pointer; margin-top: 4px; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
