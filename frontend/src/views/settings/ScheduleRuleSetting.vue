<template>
  <div class="schedule-rule-page">
    <div class="page-header">
      <span class="page-title">排班规则</span>
    </div>

    <div class="section">
      <div class="section-header">
        <span>排班规则</span>
      </div>
      <div class="section-body">
        <div class="form-row">
          <span>月休息天数</span>
          <input v-model.number="form.rest_days_per_month" type="number" min="0" max="30" class="input" />
        </div>
        <div class="form-row">
          <span>同岗位最多同时休</span>
          <input v-model.number="form.max_same_position_off" type="number" min="1" max="10" class="input" />
        </div>
        <div class="form-row">
          <span>同岗位最低在岗率</span>
          <input v-model.number="form.min_position_coverage_percent" type="number" min="0" max="100" class="input" />
          <span class="unit">%</span>
        </div>
        <div class="form-row-hint">
          同岗位员工请假后，在岗人数不得低于此比例（病假不受此限制）。例如4个服务员设50%，则最多2人同时休假。
        </div>
        <div class="form-row">
          <span>管理顺位约束</span>
          <input type="checkbox" v-model="form.manager_order_constraint" class="toggle" />
        </div>
        <div class="form-row">
          <span>节假日策略</span>
          <select v-model="form.holiday_policy" class="select">
            <option value="comp_leave">安排值班+补休</option>
            <option value="overtime_pay">直接发加班费</option>
          </select>
        </div>
        <div class="form-row">
          <span>发布后锁定排班</span>
          <input type="checkbox" v-model="form.schedule_lock_after_publish" class="toggle" />
        </div>
        <div class="form-row">
          <span>自动排班</span>
          <input type="checkbox" v-model="form.auto_schedule_enabled" class="toggle" />
        </div>

        <button class="save-btn" :disabled="saving" @click="saveSettings">
          {{ saving ? '保存中...' : '保存排班规则' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { storeAPI, type StoreSettingsData } from '@/api/store'

const form = reactive({
  rest_days_per_month: 4,
  max_same_position_off: 1,
  min_position_coverage_percent: 50,
  manager_order_constraint: true,
  holiday_policy: 'comp_leave',
  auto_schedule_enabled: false,
  schedule_lock_after_publish: true,
})

const saving = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getSettings()
    const s = res.data.data
    form.rest_days_per_month = s.rest_days_per_month
    form.max_same_position_off = s.max_same_position_off
    form.min_position_coverage_percent = s.min_position_coverage_percent
    form.manager_order_constraint = s.manager_order_constraint
    form.holiday_policy = s.holiday_policy
    form.auto_schedule_enabled = s.auto_schedule_enabled
    form.schedule_lock_after_publish = s.schedule_lock_after_publish
  } catch { /* silent */ }
}

async function saveSettings() {
  saving.value = true
  try {
    await storeAPI.updateSettings({
      rest_days_per_month: form.rest_days_per_month,
      max_same_position_off: form.max_same_position_off,
      min_position_coverage_percent: form.min_position_coverage_percent,
      manager_order_constraint: form.manager_order_constraint,
      holiday_policy: form.holiday_policy,
      auto_schedule_enabled: form.auto_schedule_enabled,
      schedule_lock_after_publish: form.schedule_lock_after_publish,
    })
  } catch { /* silent */ }
  saving.value = false
}

onMounted(loadData)
</script>

<style scoped>
.schedule-rule-page {
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

.form-row-hint {
  padding: 6px 0 6px 12px;
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
  border-bottom: 1px solid #222222;
}

.unit {
  color: #7A7C80;
  font-size: 12px;
}

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
.input:focus { outline: none; border-color: #FB0079; }

.select {
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
}
.select:focus { outline: none; border-color: #FB0079; }

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
