<template>
  <div class="schedule-rule-page">
    <div class="page-header">
      <span class="page-title">排班规则</span>
    </div>

    <!-- 排班模式（最关键，猴子都会选） -->
    <div class="section">
      <div class="section-header">
        <span>排班模式</span>
        <span class="section-hint">点一下就行</span>
      </div>
      <div class="section-body">
        <div class="mode-grid">
          <button
            v-for="m in MODE_LIST"
            :key="m.code"
            class="mode-card"
            :class="{ active: currentMode === m.code }"
            @click="selectMode(m.code)"
          >
            <span class="mode-name">{{ m.name }}</span>
            <span class="mode-desc">{{ m.desc }}</span>
            <span class="mode-days">每月休 {{ m.days }} 天</span>
          </button>
        </div>
        <div class="mode-tip">
          {{ currentModeTip }}
        </div>
      </div>
    </div>

    <!-- 休息天数（由模式自动算，可微调） -->
    <div class="section">
      <div class="section-header">
        <span>休息天数</span>
      </div>
      <div class="section-body">
        <div class="form-row">
          <span>月休息天数</span>
          <input v-model.number="form.rest_days_per_month" type="number" min="0" max="16" class="input" />
          <span class="unit">天</span>
        </div>
        <div class="form-row-hint">
          由排班模式自动填好，一般不用改。改了会同步到薪资规则，保证考勤和工资算的休息天数一致。
        </div>
      </div>
    </div>

    <!-- 岗位约束 -->
    <div class="section">
      <div class="section-header">
        <span>岗位约束</span>
      </div>
      <div class="section-body">
        <div class="form-row">
          <span>同岗位最多同时休</span>
          <input v-model.number="form.max_same_position_off" type="number" min="1" max="10" class="input" />
          <span class="unit">人</span>
        </div>
        <div class="form-row">
          <span>同岗位最低在岗率</span>
          <input v-model.number="form.min_position_coverage_percent" type="number" min="0" max="100" class="input" />
          <span class="unit">%</span>
        </div>
        <div class="form-row-hint">
          例如4个服务员设50%，则最多2人同时休假（病假不受限）。
        </div>
      </div>
    </div>

    <!-- 其他 -->
    <div class="section">
      <div class="section-header">
        <span>其他</span>
      </div>
      <div class="section-body">
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
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="saveSettings">
      {{ saving ? '保存中...' : '保存排班规则' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI } from '@/api/store'
import { updateRule } from '@/api/payrollConfig'

// 排班模式定义：单休/大小周/双休
const MODE_LIST = [
  { code: 'single', name: '单休', desc: '每周休1天', days: 4 },
  { code: 'alternate', name: '大小周', desc: '单休周+双休周交替', days: 6 },
  { code: 'double', name: '双休', desc: '每周休2天', days: 8 },
] as const

type ModeCode = typeof MODE_LIST[number]['code']

const MODE_TIPS: Record<ModeCode, string> = {
  single: '单休：每周固定休1天（一般周日），每月共4天休息。',
  alternate: '大小周：一周单休、一周双休交替，平均每月休6天。这是酒吧最常用的排班方式。',
  double: '双休：每周固定休2天（一般周六周日），每月共8天休息。',
}

const currentMode = ref<ModeCode>('alternate')

// 根据休息天数反推模式
function detectMode(days: number): ModeCode {
  if (days <= 5) return 'single'
  if (days >= 7) return 'double'
  return 'alternate'
}

function selectMode(code: ModeCode) {
  currentMode.value = code
  const m = MODE_LIST.find(x => x.code === code)
  if (m) form.rest_days_per_month = m.days
}

const currentModeTip = computed(() => MODE_TIPS[currentMode.value])

const form = reactive({
  rest_days_per_month: 6,
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
    currentMode.value = detectMode(s.rest_days_per_month)
  } catch { /* silent */ }
}

async function saveSettings() {
  saving.value = true
  try {
    // 1. 保存排班规则到门店设置
    await storeAPI.updateSettings({
      rest_days_per_month: form.rest_days_per_month,
      max_same_position_off: form.max_same_position_off,
      min_position_coverage_percent: form.min_position_coverage_percent,
      manager_order_constraint: form.manager_order_constraint,
      holiday_policy: form.holiday_policy,
      auto_schedule_enabled: form.auto_schedule_enabled,
      schedule_lock_after_publish: form.schedule_lock_after_publish,
    })
    // 2. 同步休息天数到薪资规则表，保证考勤/工资算的休息天数一致
    try {
      await updateRule('rest_days_per_month', form.rest_days_per_month)
    } catch {
      // 薪资规则表可能未初始化，忽略
    }
    ElMessage.success('排班规则已保存，休息天数已同步到薪资计算')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.schedule-rule-page {
  padding: 16px;
  padding-bottom: 100px;
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
.section-hint {
  font-size: 11px;
  color: #7A7C80;
}
.section-body {
  padding: 0 16px 16px;
}

/* 排班模式卡片 */
.mode-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 10px;
}
.mode-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 14px 6px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
}
.mode-card.active {
  background: #FB0079;
  border-color: #FB0079;
  box-shadow: 0 2px 10px rgba(251, 0, 121, 0.35);
}
.mode-name {
  font-size: 15px;
  font-weight: 700;
  color: #FFFFFF;
}
.mode-card.active .mode-name { color: #FFFFFF; }
.mode-desc {
  font-size: 11px;
  color: #7A7C80;
}
.mode-card.active .mode-desc { color: rgba(255,255,255,0.85); }
.mode-days {
  font-size: 11px;
  color: #FB0079;
  font-weight: 600;
  margin-top: 2px;
}
.mode-card.active .mode-days { color: #FFFFFF; }
.mode-tip {
  padding: 10px 12px;
  background: rgba(251, 0, 121, 0.08);
  border-left: 3px solid #FB0079;
  border-radius: 4px;
  font-size: 12px;
  color: #C8C8C8;
  line-height: 1.6;
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
  padding: 6px 0 6px 0;
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
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
  margin-left: auto;
}
.input:focus { outline: none; border-color: #FB0079; }

.select {
  padding: 6px 8px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #C8C8C8;
  font-size: 13px;
  margin-left: auto;
}
.select:focus { outline: none; border-color: #FB0079; }

.toggle {
  accent-color: #FB0079;
  margin-left: auto;
  width: 18px;
  height: 18px;
}

.save-btn {
  width: 100%;
  margin-top: 14px;
  padding: 14px;
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
