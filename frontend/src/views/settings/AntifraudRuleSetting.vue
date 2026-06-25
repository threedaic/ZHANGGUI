<template>
  <div class="rule-page">
    <div class="page-header">
      <span class="page-title">防飞单规则</span>
    </div>

    <!-- 总开关 -->
    <div class="section">
      <div class="section-header"><span>检测开关</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>防飞单检测</span>
          <input type="checkbox" v-model="form.enabled" class="toggle" />
        </div>
        <div class="form-row">
          <span>预警企微推送</span>
          <input type="checkbox" v-model="form.alert_push_enabled" class="toggle" />
        </div>
        <div class="form-row-hint">开启后异常会话自动推送到企微群机器人（需在推送设置配置群机器人）。</div>
      </div>
    </div>

    <!-- 阈值 -->
    <div class="section">
      <div class="section-header"><span>预警阈值</span><span class="section-hint">总分 0-100</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>异常阈值</span>
          <input v-model.number="form.anomaly_threshold" type="number" min="0" max="100" class="input" />
          <span class="unit">分</span>
        </div>
        <div class="form-row">
          <span>严重阈值</span>
          <input v-model.number="form.critical_threshold" type="number" min="0" max="100" class="input" />
          <span class="unit">分</span>
        </div>
        <div class="form-row-hint">超过异常阈值标记为异常，超过严重阈值标记为严重。默认 50 / 80。</div>
      </div>
    </div>

    <!-- 检测规则开关 -->
    <div class="section">
      <div class="section-header"><span>检测规则</span><span class="section-hint">每条 0-20 分</span></div>
      <div class="section-body">
        <div v-for="r in RULE_LIST" :key="r.code" class="form-row">
          <span>{{ r.label }}</span>
          <input type="checkbox" v-model="form.rules[r.code]" class="toggle" />
        </div>
        <div class="form-row-hint">关闭某条规则后该规则不计入总分。</div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="save">
      {{ saving ? '保存中...' : '保存防飞单规则' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI } from '@/api/store'

const RULE_LIST = [
  { code: 'cancellation', label: '作废异常' },
  { code: 'account_diff', label: '账差检测' },
  { code: 'amount_deviation', label: '金额偏离' },
  { code: 'time_gap', label: '时间裂隙' },
  { code: 'employee_deviation', label: '员工偏差' },
] as const

const form = reactive({
  enabled: true,
  alert_push_enabled: true,
  anomaly_threshold: 50,
  critical_threshold: 80,
  rules: {
    cancellation: true,
    account_diff: true,
    amount_deviation: true,
    time_gap: true,
    employee_deviation: true,
  } as Record<string, boolean>,
})

const saving = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const cfg = res.data.data.extra_config?.antifraud || {}
    if (cfg.enabled != null) form.enabled = cfg.enabled
    if (cfg.alert_push_enabled != null) form.alert_push_enabled = cfg.alert_push_enabled
    if (cfg.anomaly_threshold != null) form.anomaly_threshold = cfg.anomaly_threshold
    if (cfg.critical_threshold != null) form.critical_threshold = cfg.critical_threshold
    if (cfg.rules) Object.assign(form.rules, cfg.rules)
  } catch { /* silent */ }
}

async function save() {
  saving.value = true
  try {
    await storeAPI.updateSettings({ extra_config: { antifraud: { ...form } } } as any)
    ElMessage.success('防飞单规则已保存')
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
.save-btn { width: 100%; margin-top: 14px; padding: 14px; background: #FB0079; border: none; border-radius: 8px; font-family: "Source Han Sans SC", sans-serif; font-size: 14px; font-weight: 600; color: #FFFFFF; cursor: pointer; transition: opacity 0.2s; }
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
