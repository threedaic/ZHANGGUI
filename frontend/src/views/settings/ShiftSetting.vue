<template>
  <div class="schedule-setting-page">
    <h1 class="page-title">排班设置</h1>
    <p class="page-tip">班次时间 + 排班规则，一站式搞定</p>

    <!-- ============ 第一块：班次定义 ============ -->
    <div class="section">
      <div class="section-header">
        <span>班次定义</span>
        <span class="section-hint">几点到几点是什么班</span>
      </div>
      <div class="section-body">
        <div class="shift-list">
          <div v-for="(item, index) in shiftList" :key="index" class="shift-item">
            <div class="field-row">
              <label>名称</label>
              <input v-model="item.shift_name" type="text" placeholder="如：白班" />
            </div>
            <div class="field-row">
              <label>代码</label>
              <input v-model="item.shift_code" type="text" placeholder="如：day" />
            </div>
            <div class="field-row">
              <label>上班时间</label>
              <input v-model="item.start_time" type="text" placeholder="12:00" />
            </div>
            <div class="field-row">
              <label>下班时间</label>
              <input v-model="item.end_time" type="text" placeholder="20:00" />
            </div>
            <div class="field-row">
              <label>颜色</label>
              <input v-model="item.color" type="color" />
            </div>
            <div class="field-row inline">
              <label>
                <input v-model="item.is_overnight" type="checkbox" />
                跨天
              </label>
              <label>
                <input v-model="item.is_active" type="checkbox" />
                启用
              </label>
            </div>
            <button class="remove-btn" @click="removeShift(index)">删除</button>
          </div>
        </div>
        <button class="add-btn" @click="addShift">+ 添加班次</button>
        <button class="save-btn" :disabled="savingShift" @click="saveShifts">
          {{ savingShift ? '保存中...' : '保存班次' }}
        </button>
      </div>
    </div>

    <!-- ============ 第二块：排班规则 ============ -->
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
        <div class="mode-tip">{{ currentModeTip }}</div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><span>休息天数</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>月休息天数</span>
          <input v-model.number="ruleForm.rest_days_per_month" type="number" min="0" max="16" class="input" />
          <span class="unit">天</span>
        </div>
        <div class="form-row-hint">
          由排班模式自动填好，一般不用改。改了会同步到薪资规则，保证考勤和工资算的休息天数一致。
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><span>岗位约束</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>同岗位最多同时休</span>
          <input v-model.number="ruleForm.max_same_position_off" type="number" min="1" max="10" class="input" />
          <span class="unit">人</span>
        </div>
        <div class="form-row">
          <span>同岗位最低在岗率</span>
          <input v-model.number="ruleForm.min_position_coverage_percent" type="number" min="0" max="100" class="input" />
          <span class="unit">%</span>
        </div>
        <div class="form-row-hint">
          例如4个服务员设50%，则最多2人同时休假（病假不受限）。
        </div>
      </div>
    </div>

    <div class="section">
      <div class="section-header"><span>其他</span></div>
      <div class="section-body">
        <div class="form-row">
          <span>管理顺位约束</span>
          <input type="checkbox" v-model="ruleForm.manager_order_constraint" class="toggle" />
        </div>
        <div class="form-row">
          <span>节假日策略</span>
          <select v-model="ruleForm.holiday_policy" class="select">
            <option value="comp_leave">安排值班+补休</option>
            <option value="overtime_pay">直接发加班费</option>
          </select>
        </div>
        <div class="form-row">
          <span>发布后锁定排班</span>
          <input type="checkbox" v-model="ruleForm.schedule_lock_after_publish" class="toggle" />
        </div>
        <div class="form-row">
          <span>自动排班</span>
          <input type="checkbox" v-model="ruleForm.auto_schedule_enabled" class="toggle" />
        </div>
      </div>
    </div>

    <button class="save-btn" :disabled="savingRule" @click="saveRules">
      {{ savingRule ? '保存中...' : '保存排班规则' }}
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { attendanceAPI, type ShiftConfig } from '@/api/attendance'
import { storeAPI } from '@/api/store'
import { updateRule } from '@/api/payrollConfig'

// ==================== 班次定义 ====================
const shiftList = ref<Partial<ShiftConfig>[]>([])
const savingShift = ref(false)

function addShift() {
  shiftList.value.push({
    shift_code: '',
    shift_name: '',
    start_time: '',
    end_time: '',
    is_overnight: false,
    color: '#FB0079',
    sort_order: shiftList.value.length,
    is_active: true,
  } as Partial<ShiftConfig>)
}

function removeShift(index: number) {
  shiftList.value.splice(index, 1)
}

async function saveShifts() {
  savingShift.value = true
  try {
    for (const item of shiftList.value) {
      if (!item.shift_code || !item.shift_name) continue
      await attendanceAPI.saveShiftConfig(item as Partial<ShiftConfig> & { shift_code: string; shift_name: string; start_time: string; end_time: string })
    }
    ElMessage.success('班次已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
  } finally {
    savingShift.value = false
  }
}

async function loadShifts() {
  const res = await attendanceAPI.getShiftConfigs()
  shiftList.value = res.data?.data || []
}

// ==================== 排班规则 ====================
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

function detectMode(days: number): ModeCode {
  if (days <= 5) return 'single'
  if (days >= 7) return 'double'
  return 'alternate'
}

function selectMode(code: ModeCode) {
  currentMode.value = code
  const m = MODE_LIST.find(x => x.code === code)
  if (m) ruleForm.rest_days_per_month = m.days
}

const currentModeTip = computed(() => MODE_TIPS[currentMode.value])

const ruleForm = reactive({
  rest_days_per_month: 6,
  max_same_position_off: 1,
  min_position_coverage_percent: 50,
  manager_order_constraint: true,
  holiday_policy: 'comp_leave',
  auto_schedule_enabled: false,
  schedule_lock_after_publish: true,
})

const savingRule = ref(false)

async function loadRules() {
  try {
    const res = await storeAPI.getSettings()
    const s = res.data.data
    ruleForm.rest_days_per_month = s.rest_days_per_month
    ruleForm.max_same_position_off = s.max_same_position_off
    ruleForm.min_position_coverage_percent = s.min_position_coverage_percent
    ruleForm.manager_order_constraint = s.manager_order_constraint
    ruleForm.holiday_policy = s.holiday_policy
    ruleForm.auto_schedule_enabled = s.auto_schedule_enabled
    ruleForm.schedule_lock_after_publish = s.schedule_lock_after_publish
    currentMode.value = detectMode(s.rest_days_per_month)
  } catch { /* silent */ }
}

async function saveRules() {
  savingRule.value = true
  try {
    await storeAPI.updateSettings({
      rest_days_per_month: ruleForm.rest_days_per_month,
      max_same_position_off: ruleForm.max_same_position_off,
      min_position_coverage_percent: ruleForm.min_position_coverage_percent,
      manager_order_constraint: ruleForm.manager_order_constraint,
      holiday_policy: ruleForm.holiday_policy,
      auto_schedule_enabled: ruleForm.auto_schedule_enabled,
      schedule_lock_after_publish: ruleForm.schedule_lock_after_publish,
    })
    try {
      await updateRule('rest_days_per_month', ruleForm.rest_days_per_month)
    } catch { /* 薪资规则表可能未初始化 */ }
    ElMessage.success('排班规则已保存，休息天数已同步到薪资计算')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    savingRule.value = false
  }
}

onMounted(() => {
  loadShifts()
  loadRules()
})
</script>

<style scoped>
.schedule-setting-page {
  padding: 16px;
  padding-bottom: 100px;
  min-height: 100vh;
  background: #000000;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 4px;
}

.page-tip {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 16px;
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

/* ---- 班次定义 ---- */
.shift-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 8px;
}
.shift-item {
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 12px;
}
.field-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}
.field-row label {
  width: 80px;
  font-size: 12px;
  color: #C8C8C8;
}
.field-row input[type="text"] {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
}
.field-row input[type="color"] {
  width: 40px;
  height: 28px;
  border: none;
  background: transparent;
}
.field-row.inline { gap: 16px; }
.field-row.inline label {
  width: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}
.remove-btn {
  width: 100%;
  margin-top: 8px;
  padding: 6px;
  border: 1px solid #FB0079;
  border-radius: 6px;
  background: transparent;
  color: #FB0079;
  font-size: 12px;
  cursor: pointer;
}
.add-btn {
  width: 100%;
  margin-top: 8px;
  padding: 10px;
  border: none;
  border-radius: 8px;
  background: #333333;
  color: #C8C8C8;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* ---- 排班模式卡片 ---- */
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
.mode-name { font-size: 15px; font-weight: 700; color: #FFFFFF; }
.mode-card.active .mode-name { color: #FFFFFF; }
.mode-desc { font-size: 11px; color: #7A7C80; }
.mode-card.active .mode-desc { color: rgba(255,255,255,0.85); }
.mode-days { font-size: 11px; color: #FB0079; font-weight: 600; margin-top: 2px; }
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

/* ---- 表单行 ---- */
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
  padding: 6px 0;
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
}
.unit { color: #7A7C80; font-size: 12px; }
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

/* ---- 保存按钮 ---- */
.save-btn {
  width: 100%;
  margin-top: 12px;
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
