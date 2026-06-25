<template>
  <div class="rule-page">
    <div class="page-header">
      <span class="page-title">存酒配置</span>
    </div>

    <!-- 保质期 -->
    <div class="section">
      <div class="section-header"><span>保质期</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>存酒保质期</span>
          <input v-model.number="form.shelf_life_days" type="number" min="30" max="365" class="input" />
          <span class="unit">天</span>
        </div>
        <div class="form-row">
          <span>到期提醒</span>
          <input v-model.number="form.expiry_remind_days" type="number" min="1" max="60" class="input" />
          <span class="unit">天前</span>
        </div>
        <div class="form-row-hint">到期前 N 天提醒客人来取酒，默认提前 30 天。保质期默认 180 天。</div>
      </div>
    </div>

    <!-- 取酒规则 -->
    <div class="section">
      <div class="section-header"><span>取酒规则</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>取酒需店长确认</span>
          <input type="checkbox" v-model="form.retrieve_require_confirm" class="toggle" />
        </div>
        <div class="form-row">
          <span>存酒打印标签</span>
          <input type="checkbox" v-model="form.label_print_enabled" class="toggle" />
        </div>
        <div class="form-row-hint">开启后存酒时自动打印瓶身标签，需在打印设置中配置标签打印机。</div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="save">
      {{ saving ? '保存中...' : '保存存酒配置' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI } from '@/api/store'

const form = reactive({
  shelf_life_days: 180,
  expiry_remind_days: 30,
  retrieve_require_confirm: false,
  label_print_enabled: true,
})

const saving = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const cfg = res.data.data.extra_config?.wine || {}
    if (cfg.shelf_life_days != null) form.shelf_life_days = cfg.shelf_life_days
    if (cfg.expiry_remind_days != null) form.expiry_remind_days = cfg.expiry_remind_days
    if (cfg.retrieve_require_confirm != null) form.retrieve_require_confirm = cfg.retrieve_require_confirm
    if (cfg.label_print_enabled != null) form.label_print_enabled = cfg.label_print_enabled
  } catch { /* silent */ }
}

async function save() {
  saving.value = true
  try {
    await storeAPI.updateSettings({ extra_config: { wine: { ...form } } } as any)
    ElMessage.success('存酒配置已保存')
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
.section-body { padding: 0 16px 16px; }
.form-row { display: flex; align-items: center; gap: 12px; padding: 10px 0; border-bottom: 1px solid #222222; font-size: 13px; color: #C8C8C8; }
.form-row:last-child { border-bottom: none; }
.form-row-hint { padding: 6px 0; font-size: 11px; color: #7A7C80; line-height: 1.5; }
.unit { color: #7A7C80; font-size: 12px; }
.input { width: 60px; padding: 6px 8px; background: #1a1a1a; border: 1px solid #333333; border-radius: 6px; color: #C8C8C8; font-size: 13px; text-align: center; margin-left: auto; }
.input:focus { outline: none; border-color: #FB0079; }
.toggle { accent-color: #FB0079; margin-left: auto; width: 18px; height: 18px; }
.save-btn { width: 100%; margin-top: 14px; padding: 14px; background: #FB0079; border: none; border-radius: 8px; font-family: "Source Han Sans SC", sans-serif; font-size: 14px; font-weight: 600; color: #FFFFFF; cursor: pointer; transition: opacity 0.2s; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
