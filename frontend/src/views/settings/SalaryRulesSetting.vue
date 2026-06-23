<template>
  <div class="salary-rules-page">
    <div class="page-header">
      <span class="page-title">通用参数</span>
    </div>

    <div class="section">
      <div class="section-header">
        <span>通用参数</span>
      </div>
      <div class="section-body">
        <div class="form-row">
          <span>发薪日</span>
          <input v-model.number="form.payroll_day_of_month" type="number" min="1" max="28" class="input input-sm" /> 日
        </div>
        <div class="form-row">
          <span>KPI 系数下限</span>
          <input v-model.number="form.kpi_coefficient_min" type="number" min="0.1" max="2" step="0.05" class="input input-sm" />
        </div>
        <div class="form-row">
          <span>KPI 系数上限</span>
          <input v-model.number="form.kpi_coefficient_max" type="number" min="0.5" max="3" step="0.05" class="input input-sm" />
        </div>
        <button class="save-btn" :disabled="saving" @click="saveSettings">
          {{ saving ? '保存中...' : '保存通用参数' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { storeAPI, type StoreSettingsData } from '@/api/store'

const form = reactive({
  payroll_day_of_month: 5,
  kpi_coefficient_min: 0.60,
  kpi_coefficient_max: 1.50,
})

const saving = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const s = res.data.data
    form.payroll_day_of_month = s.payroll_day_of_month
    form.kpi_coefficient_min = s.kpi_coefficient_min
    form.kpi_coefficient_max = s.kpi_coefficient_max
  } catch { /* silent */ }
}

async function saveSettings() {
  saving.value = true
  try {
    await storeAPI.updateSettings({
      payroll_day_of_month: form.payroll_day_of_month,
      kpi_coefficient_min: form.kpi_coefficient_min,
      kpi_coefficient_max: form.kpi_coefficient_max,
    })
  } catch { /* silent */ }
  saving.value = false
}

onMounted(loadData)
</script>

<style scoped>
.salary-rules-page {
  padding: 16px;
  min-height: 100vh;
  background: #000000;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #C8C8C8;
}

.section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
}
.section-body {
  padding: 0 16px 16px;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
  font-size: 13px;
  color: #C8C8C8;
}
.form-row:last-child { border-bottom: none; }

.input {
  width: 60px;
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  text-align: center;
}
.input-sm { width: 50px; }
.input:focus { outline: none; border-color: #FB0079; }

.save-btn {
  width: 100%;
  margin-top: 14px;
  padding: 12px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
  transition: opacity 0.2s;
}
.save-btn:disabled { opacity: 0.5; cursor: not-allowed; }
</style>
