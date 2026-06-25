<template>
  <div class="rule-page">
    <div class="page-header">
      <span class="page-title">订桌规则</span>
    </div>

    <!-- 预约上限 -->
    <div class="section">
      <div class="section-header"><span>预约上限</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>每日预订上限</span>
          <input v-model.number="form.daily_booking_limit" type="number" min="0" max="200" class="input" />
          <span class="unit">桌</span>
        </div>
        <div class="form-row-hint">超过上限后客人无法再预约当天桌位，0 表示不限制。</div>
      </div>
    </div>

    <!-- 自动确认 -->
    <div class="section">
      <div class="section-header"><span>确认方式</span><span class="section-hint">点一下就行</span></div>
      <div class="section-body">
        <div class="mode-grid">
          <button class="mode-card" :class="{ active: !form.auto_confirm }" @click="form.auto_confirm = false">
            <span class="mode-name">手动确认</span>
            <span class="mode-desc">预约后需店长确认</span>
          </button>
          <button class="mode-card" :class="{ active: form.auto_confirm }" @click="form.auto_confirm = true">
            <span class="mode-name">自动确认</span>
            <span class="mode-desc">预约即生效</span>
          </button>
        </div>
      </div>
    </div>

    <!-- 时段与提前量 -->
    <div class="section">
      <div class="section-header"><span>时段与提前量</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>默认时段</span>
          <input v-model="form.default_time_slot" class="input input-long" placeholder="如 19:00-21:00" />
        </div>
        <div class="form-row">
          <span>最短提前预约</span>
          <input v-model.number="form.min_advance_hours" type="number" min="0" max="72" class="input" />
          <span class="unit">小时</span>
        </div>
        <div class="form-row">
          <span>取消截止</span>
          <input v-model.number="form.cancel_deadline_hours" type="number" min="0" max="48" class="input" />
          <span class="unit">小时前</span>
        </div>
        <div class="form-row-hint">取消截止：开桌前多少小时内仍可取消预约。</div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="save">
      {{ saving ? '保存中...' : '保存订桌规则' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI } from '@/api/store'

const form = reactive({
  daily_booking_limit: 30,
  auto_confirm: false,
  default_time_slot: '19:00-21:00',
  min_advance_hours: 1,
  cancel_deadline_hours: 2,
})

const saving = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const cfg = res.data.data.extra_config?.booking || {}
    if (cfg.daily_booking_limit != null) form.daily_booking_limit = cfg.daily_booking_limit
    if (cfg.auto_confirm != null) form.auto_confirm = cfg.auto_confirm
    if (cfg.default_time_slot) form.default_time_slot = cfg.default_time_slot
    if (cfg.min_advance_hours != null) form.min_advance_hours = cfg.min_advance_hours
    if (cfg.cancel_deadline_hours != null) form.cancel_deadline_hours = cfg.cancel_deadline_hours
  } catch { /* silent */ }
}

async function save() {
  saving.value = true
  try {
    await storeAPI.updateSettings({ extra_config: { booking: { ...form } } } as any)
    ElMessage.success('订桌规则已保存')
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
.input-long { width: 140px; text-align: left; }
.input:focus { outline: none; border-color: #FB0079; }
.mode-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.mode-card { display: flex; flex-direction: column; align-items: center; gap: 4px; padding: 14px 6px; background: #1a1a1a; border: 1px solid #333333; border-radius: 10px; cursor: pointer; transition: all 0.2s; }
.mode-card.active { background: #FB0079; border-color: #FB0079; box-shadow: 0 2px 10px rgba(251, 0, 121, 0.35); }
.mode-name { font-size: 15px; font-weight: 700; color: #FFFFFF; }
.mode-desc { font-size: 11px; color: #7A7C80; }
.mode-card.active .mode-desc { color: rgba(255,255,255,0.85); }
.save-btn { width: 100%; margin-top: 14px; padding: 14px; background: #FB0079; border: none; border-radius: 8px; font-family: "Source Han Sans SC", sans-serif; font-size: 14px; font-weight: 600; color: #FFFFFF; cursor: pointer; transition: opacity 0.2s; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
