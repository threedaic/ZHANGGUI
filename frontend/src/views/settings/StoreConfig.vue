<template>
  <div class="store-page">
    <div class="page-hint">仅老板可见，配置后全店生效</div>

    <!-- 门店信息 -->
    <div class="section">
      <div class="section-header" @click="sections.store = !sections.store">
        <span>门店信息</span>
        <span class="toggle">{{ sections.store ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.store" class="section-body">
        <div class="info-row">
          <span class="info-label">门店名</span>
          <span class="info-value">{{ storeInfo.name }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">编码</span>
          <span class="info-value">{{ storeInfo.store_code }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">地址</span>
          <span class="info-value">{{ storeInfo.address || '未设置' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">城市</span>
          <span class="info-value">{{ storeInfo.city || '未设置' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">日订桌上限</span>
          <span class="info-value">{{ storeInfo.daily_booking_limit || 30 }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">企微状态</span>
          <span class="info-value" :class="{ 'status-ok': storeInfo.wework_status === 'configured' }">
            {{ weworkStatusLabel }}
          </span>
        </div>
      </div>
    </div>

    <!-- 排班规则 -->
    <div class="section">
      <div class="section-header" @click="sections.schedule = !sections.schedule">
        <span>排班规则</span>
        <span class="toggle">{{ sections.schedule ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.schedule" class="section-body">
        <div class="form-row">
          <span>月休息天数</span>
          <input v-model.number="form.rest_days_per_month" type="number" min="0" max="30" class="input" />
        </div>
        <div class="form-row">
          <span>同岗位最多同时休</span>
          <input v-model.number="form.max_same_position_off" type="number" min="1" max="10" class="input" />
        </div>
        <div class="form-row">
          <span>管理顺位约束</span>
          <van-switch v-model="form.manager_order_constraint" size="22px" active-color="#FB0079" />
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
          <van-switch v-model="form.schedule_lock_after_publish" size="22px" active-color="#FB0079" />
        </div>
        <div class="form-row">
          <span>自动排班</span>
          <van-switch v-model="form.auto_schedule_enabled" size="22px" active-color="#FB0079" />
        </div>

        <button class="save-btn" :disabled="saving" @click="saveSettings">
          {{ saving ? '保存中...' : '保存排班规则' }}
        </button>
      </div>
    </div>

    <!-- 通用参数 -->
    <div class="section">
      <div class="section-header" @click="sections.general = !sections.general">
        <span>通用参数</span>
        <span class="toggle">{{ sections.general ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.general" class="section-body">
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
        <button class="save-btn" :disabled="saving" @click="saveSettings">保存通用参数</button>
      </div>
    </div>

    <!-- 企微配置 -->
    <div class="section">
      <div class="section-header" @click="sections.wework = !sections.wework">
        <span>企业微信配置</span>
        <span class="toggle">{{ sections.wework ? '收起' : '展开' }}</span>
      </div>
      <div v-if="sections.wework" class="section-body">
        <div class="form-row">
          <span>企业 ID</span>
          <input v-model="wework.corp_id" class="input input-long" placeholder="ww..." />
        </div>
        <div class="form-row">
          <span>应用 ID</span>
          <input v-model="wework.agent_id" class="input" placeholder="1000001" />
        </div>
        <div class="form-row">
          <span>应用密钥</span>
          <input v-model="wework.secret" type="password" class="input input-long" placeholder="应用 Secret" />
        </div>
        <div class="form-row">
          <span>回调 Token</span>
          <input v-model="wework.token" class="input input-long" placeholder="回调验证 Token" />
        </div>
        <div class="form-row">
          <span>回调 AES Key</span>
          <input v-model="wework.aes_key" class="input input-long" placeholder="43位随机字符串" />
        </div>
        <div class="form-row">
          <span>门店部门 ID</span>
          <input v-model="wework.department_id" class="input input-long" placeholder="企微部门数字ID" type="number" />
        </div>
        <div class="form-row hint-row">
          <span class="hint-text">仅同步该部门及子部门成员，留空则同步全公司</span>
        </div>
        <button class="save-btn" :disabled="savingWework" @click="saveWework">
          {{ savingWework ? '保存中...' : '保存企微配置' }}
        </button>
      </div>
    </div>

    <div style="height: 80px"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { storeAPI, type StoreInfo, type StoreSettingsData } from '@/api/store'

const sections = reactive({
  store: true,
  schedule: false,
  general: false,
  wework: false,
})

const storeInfo = ref<StoreInfo>({
  id: '', name: '加载中...', store_code: '', address: null, city: null,
  status: 'active', daily_booking_limit: 30,
  wework_status: null, wework_corp_id: null, wework_agent_id: null,
  wework_department_id: null,
} as StoreInfo)

const form = reactive<StoreSettingsData>({
  rest_days_per_month: 4,
  rest_allowed_weekdays: ['周日','周一','周二','周三','周四'],
  rest_forbidden_weekdays: ['周五','周六'],
  max_same_position_off: 1,
  min_position_coverage_percent: 50,
  manager_order_constraint: true,
  holiday_policy: 'comp_leave',
  auto_schedule_enabled: false,
  schedule_lock_after_publish: true,
  payroll_day_of_month: 5,
  kpi_coefficient_min: 0.60,
  kpi_coefficient_max: 1.50,
})

const wework = reactive({
  corp_id: '',
  agent_id: '',
  secret: '',
  token: '',
  aes_key: '',
  department_id: null as number | null,
})

const saving = ref(false)
const savingWework = ref(false)

const weworkStatusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '未配置', configured: '已配置', error: '配置错误',
  }
  return map[storeInfo.value.wework_status || ''] || '未知'
})

async function loadData() {
  try {
    const [infoRes, settingsRes] = await Promise.all([
      storeAPI.getInfo(),
      storeAPI.getSettings(),
    ])
    const info = infoRes.data.data
    storeInfo.value = info
    if (info.wework_corp_id) wework.corp_id = info.wework_corp_id
    if (info.wework_agent_id) wework.agent_id = info.wework_agent_id
    if (info.wework_department_id) wework.department_id = info.wework_department_id
    const s = settingsRes.data.data
    Object.assign(form, s)
  } catch { /* silent */ }
}

async function saveSettings() {
  saving.value = true
  try {
    await storeAPI.updateSettings({
      rest_days_per_month: form.rest_days_per_month,
      max_same_position_off: form.max_same_position_off,
      manager_order_constraint: form.manager_order_constraint,
      holiday_policy: form.holiday_policy,
      auto_schedule_enabled: form.auto_schedule_enabled,
      schedule_lock_after_publish: form.schedule_lock_after_publish,
      payroll_day_of_month: form.payroll_day_of_month,
      kpi_coefficient_min: form.kpi_coefficient_min,
      kpi_coefficient_max: form.kpi_coefficient_max,
    })
  } catch { /* silent */ }
  saving.value = false
}

async function saveWework() {
  savingWework.value = true
  try {
    await storeAPI.updateWework({
      wework_corp_id: wework.corp_id || undefined,
      wework_agent_id: wework.agent_id || undefined,
      wework_secret: wework.secret || undefined,
      wework_token: wework.token || undefined,
      wework_aes_key: wework.aes_key || undefined,
      wework_department_id: wework.department_id || undefined,
    })
  } catch { /* silent */ }
  savingWework.value = false
}

onMounted(loadData)
</script>

<style scoped>
.store-page {
  padding: 16px 16px calc(64px + 24px);
  min-height: 100vh;
}

.page-hint {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 16px;
  padding: 8px 12px;
  background: rgba(251, 0, 121, 0.06);
  border-radius: 8px;
}

/* 折叠区块 */
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
  cursor: pointer;
}
.toggle {
  font-size: 12px;
  color: #7A7C80;
}
.section-body {
  padding: 0 16px 16px;
}

/* 信息行 */
.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
}
.info-row:last-child { border-bottom: none; }
.info-label { font-size: 13px; color: #7A7C80; }
.info-value { font-size: 13px; color: #C8C8C8; }
.status-ok { color: #4CAF50; }

/* 表单行 */
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
.input-long { width: 140px; text-align: left; }
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
