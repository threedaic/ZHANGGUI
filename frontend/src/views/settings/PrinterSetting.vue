<template>
  <div class="printer-page">
    <h2 class="page-title">云打印机配置</h2>
    <p class="page-desc">存酒时打印标签，客人自助取酒时出取酒小票。支持飞鹅/易联云等云打印机。</p>

    <div class="form-card">
      <!-- 启用 -->
      <div class="form-item">
        <label class="form-label">启用云打印</label>
        <el-switch v-model="form.printer_enabled" active-color="#FB0079" />
      </div>

      <!-- 品牌 -->
      <div class="form-item">
        <label class="form-label">打印机品牌</label>
        <el-select v-model="form.printer_brand" class="form-select" placeholder="选择品牌">
          <el-option label="飞鹅" value="feie" />
          <el-option label="易联云" value="yilianyun" />
          <el-option label="芯烨" value="xpyun" />
          <el-option label="佳博" value="gainscha" />
          <el-option label="映美" value="jolimark" />
        </el-select>
        <span class="form-hint">{{ brandHint }}</span>
      </div>

      <!-- API 地址 -->
      <div class="form-item">
        <label class="form-label">API 地址</label>
        <input v-model="form.printer_api_url" class="form-input" :placeholder="brandApiPlaceholder" />
        <span class="form-hint">留空使用品牌默认地址</span>
      </div>

      <!-- 设备编号 -->
      <div class="form-item">
        <label class="form-label">设备编号 (SN)</label>
        <input v-model="form.printer_sn" class="form-input" placeholder="打印机背面贴纸上的设备号" />
      </div>

      <!-- 账号 -->
      <div class="form-item">
        <label class="form-label">账号</label>
        <input v-model="form.printer_user" class="form-input" placeholder="云打印平台注册账号" />
      </div>

      <!-- 密钥 -->
      <div class="form-item">
        <label class="form-label">密钥 (UKEY / API Key)</label>
        <input v-model="form.printer_ukey" class="form-input" type="password" placeholder="云打印平台密钥" />
        <span class="form-hint">密钥将明文存储，请妥善保管</span>
      </div>

      <!-- 标签宽度 -->
      <div class="form-item">
        <label class="form-label">标签纸宽度</label>
        <el-select v-model="form.printer_label_width" class="form-select">
          <el-option label="80mm（标准）" :value="80" />
          <el-option label="60mm" :value="60" />
          <el-option label="58mm" :value="58" />
        </el-select>
      </div>

      <div class="form-item">
        <label class="form-label">标签纸高度</label>
        <el-select v-model="form.printer_label_height" class="form-select">
          <el-option label="60mm（宽敞）" :value="60" />
          <el-option label="50mm（标准）" :value="50" />
          <el-option label="40mm（紧凑）" :value="40" />
        </el-select>
        <span class="form-hint">高度决定纵向间距和留白</span>
      </div>

      <!-- 保存 -->
      <div class="form-actions">
        <button class="btn-primary" @click="save" :disabled="saving">
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import apiClient from '@/api/client'

const form = reactive({
  printer_enabled: false,
  printer_brand: 'yilianyun',
  printer_api_url: '',
  printer_sn: '',
  printer_user: '',
  printer_ukey: '',
  printer_label_width: 80,
  printer_label_height: 50,
})
const saving = ref(false)

const brandLabelMap: Record<string, { user: string; key: string; api: string }> = {
  feie: { user: '账号 (USER)', key: '密钥 (UKEY)', api: 'http://api.feieyun.cn/Api/Open/printMsg' },
  yilianyun: { user: '应用ID (Client ID)', key: '应用密钥 (Client Secret)', api: 'https://open-api.10ss.net/printer/print' },
  xpyun: { user: '账号', key: '用户密钥', api: 'http://open.xpyun.net/api/openapi/xprinter/print' },
  gainscha: { user: 'API Key', key: '商户编码', api: 'https://api.poscom.cn/apisc/print' },
  jolimark: { user: '应用ID (App ID)', key: '应用密钥 (App Secret)', api: 'https://cloud.jolimark.com/api/print' },
}

const brandHint = computed(() => {
  const m = brandLabelMap[form.printer_brand]
  return m ? '账号=' + m.user + '，密钥=' + m.key : ''
})
const brandApiPlaceholder = computed(() => {
  return brandLabelMap[form.printer_brand]?.api || ''
})

onMounted(async () => {
  try {
    const { data: res } = await apiClient.get('/stores/settings')
    const d = res.data
    form.printer_enabled = d.printer_enabled ?? false
    form.printer_brand = d.printer_brand || 'yilianyun'
    form.printer_api_url = d.printer_api_url || ''
    form.printer_sn = d.printer_sn || ''
    form.printer_user = d.printer_user || ''
    form.printer_ukey = d.printer_ukey || ''
    form.printer_label_width = d.printer_label_width || 80
    form.printer_label_height = d.printer_label_height || 50
  } catch {
    /* ignore */
  }
})

async function save() {
  saving.value = true
  try {
    const { data: res } = await apiClient.put('/stores/settings', {
      printer_enabled: form.printer_enabled,
      printer_brand: form.printer_brand,
      printer_api_url: form.printer_api_url,
      printer_sn: form.printer_sn,
      printer_user: form.printer_user,
      printer_ukey: form.printer_ukey,
      printer_label_width: form.printer_label_width,
      printer_label_height: form.printer_label_height,
    })
    if (res.code === 0) {
      ElMessage.success('打印机配置已保存')
    } else {
      ElMessage.error(res.message || '保存失败')
    }
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.printer-page { padding: 16px; background: #000000; min-height: 100vh; }
.page-title { font-size: 18px; font-weight: 600; color: #FFFFFF; margin-bottom: 4px; }
.page-desc { font-size: 12px; color: #7A7C80; margin-bottom: 20px; line-height: 1.6; }
.form-card { background: #111111; border: 1px solid #333333; border-radius: 12px; padding: 20px 16px; }
.form-item { margin-bottom: 16px; }
.form-item:last-child { margin-bottom: 0; }
.form-label { display: block; font-size: 13px; color: #C8C8C8; margin-bottom: 8px; }
.form-input { width: 100%; height: 44px; padding: 0 12px; background: #000000; border: 1px solid #333333; border-radius: 8px; color: #FFFFFF; font-size: 14px; outline: none; box-sizing: border-box; }
.form-input:focus { border-color: #FB0079; }
.form-input::placeholder { color: #7A7C80; }
.form-select { width: 100%; }
.form-hint { display: block; font-size: 11px; color: #7A7C80; margin-top: 4px; }
.form-actions { margin-top: 24px; }
.btn-primary { width: 100%; height: 48px; background: #FB0079; color: #FFFFFF; border: none; border-radius: 8px; font-size: 15px; font-weight: 600; cursor: pointer; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
