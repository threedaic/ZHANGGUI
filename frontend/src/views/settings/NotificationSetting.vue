<template>
  <div class="notification-setting-page">
    <h1 class="page-title">推送设置</h1>
    <p class="page-tip">统一管理所有模块的推送通知，每项可单独设置开关、推送方式和时间</p>

    <!-- 群机器人全局配置 -->
    <div class="bot-config-card">
      <div class="bot-header">
        <div class="bot-title-area">
          <span class="bot-title">企微群机器人</span>
          <span class="bot-desc">群推送通道总开关，关闭后所有"群推送"选项不生效</span>
        </div>
        <label class="switch">
          <input v-model="botEnabled" type="checkbox" @change="handleBotToggle" />
          <span class="slider" />
        </label>
      </div>
      <template v-if="botEnabled">
        <div class="bot-form">
          <label class="form-label">Webhook 地址</label>
          <input
            v-model="webhookUrl"
            type="text"
            class="form-input"
            placeholder="粘贴群机器人的 Webhook 地址"
          />
          <div class="bot-actions">
            <button class="btn btn-test" :disabled="testing" @click="handleTest">
              {{ testing ? '测试中...' : '测试发送' }}
            </button>
            <button class="btn btn-save-webhook" :disabled="savingWebhook" @click="handleSaveWebhook">
              {{ savingWebhook ? '保存中...' : '保存地址' }}
            </button>
          </div>
          <div v-if="testResult" class="test-result" :class="testResult.ok ? 'success' : 'fail'">
            {{ testResult.msg }}
          </div>
        </div>
      </template>
    </div>

    <!-- 推送项列表 -->
    <div class="section-title">推送项目（{{ list.length }} 项）</div>
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="setting-list">
      <div v-for="item in list" :key="item.setting_key" class="setting-card" :class="{ disabled: !item.enabled }">
        <div class="setting-header">
          <div class="setting-name-area">
            <span class="setting-name">{{ settingName(item.setting_key) }}</span>
            <span class="setting-category">{{ settingCategory(item.setting_key) }}</span>
          </div>
          <van-switch v-model="item.enabled" size="18px" />
        </div>
        <div class="setting-body">
          <div class="setting-row">
            <label class="row-label">应用通知</label>
            <select v-model="item.channel" class="form-select">
              <option value="in_app">仅站内信</option>
              <option value="wecom">仅企微应用</option>
              <option value="all">站内信+企微应用</option>
            </select>
          </div>
          <div class="setting-row">
            <label class="row-label">群机器人</label>
            <label class="switch-mini">
              <input v-model="item.push_to_group" type="checkbox" />
              <span class="slider-mini" />
            </label>
            <span class="row-hint">{{ item.push_to_group ? '推送到群' : '不推群' }}</span>
          </div>
          <div class="setting-row">
            <label class="row-label">接收角色</label>
            <div class="role-checks">
              <label><input v-model="item.target_roles" type="checkbox" value="boss" /> 老板</label>
              <label><input v-model="item.target_roles" type="checkbox" value="store_manager" /> 店长</label>
              <label><input v-model="item.target_roles" type="checkbox" value="staff" /> 员工</label>
            </div>
          </div>
          <div class="setting-row">
            <label class="row-label">推送时间</label>
            <input v-model="item.schedule_time" type="time" class="form-input time-input" />
            <button v-if="item.schedule_time" class="clear-time-btn" @click="item.schedule_time = null">清除</button>
            <span class="row-hint">{{ item.schedule_time ? '定时触发' : '实时推送' }}</span>
          </div>
        </div>
      </div>
    </div>

    <button class="save-btn" :disabled="saving" @click="handleSave">保存全部设置</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import apiClient from '@/api/client'
import { notificationAPI, type NotificationSetting } from '@/api/notifications'

const list = ref<NotificationSetting[]>([])
const loading = ref(false)
const saving = ref(false)

// 群机器人全局配置
const botEnabled = ref(false)
const webhookUrl = ref('')
const savingWebhook = ref(false)
const testing = ref(false)
const testResult = ref<{ ok: boolean; msg: string } | null>(null)

// 推送项名称映射（补全所有类型）
const nameMap: Record<string, string> = {
  // 考勤类
  daily_report: '每日考勤日报',
  attendance_alert: '考勤异常提醒',
  shift_status: '班次到岗检查',
  shift_change: '排班变更通知',
  // 审批类
  approval: '审批通知',
  approval_pending: '审批待处理',
  approval_result: '审批结果',
  // 签收类
  sign_remind: '签收提醒',
  sign_dispute: '签收异议',
  // 处罚
  penalty_notice: '处罚通知',
  // 开闭店检查单
  butler_opening_overdue: '开店检查单超时',
  butler_closing_overdue: '闭店检查单超时',
  butler_manual_review: '检查单人工审核',
  // 告警类
  antifraud_alert: '防飞单预警',
  rating_alert: '低分评分预警',
  wine_stocktake_alert: '存酒盘点通知',
  system_error: '系统异常告警',
  // 其他
  reminder: '上班提醒',
}

// 推送项分类映射
const categoryMap: Record<string, string> = {
  daily_report: '考勤',
  attendance_alert: '考勤',
  shift_status: '考勤',
  shift_change: '考勤',
  approval: '审批',
  approval_pending: '审批',
  approval_result: '审批',
  sign_remind: '签收',
  sign_dispute: '签收',
  penalty_notice: '处罚',
  butler_opening_overdue: '开闭店',
  butler_closing_overdue: '开闭店',
  butler_manual_review: '开闭店',
  antifraud_alert: '告警',
  rating_alert: '告警',
  wine_stocktake_alert: '告警',
  system_error: '告警',
  reminder: '其他',
}

function settingName(key: string) {
  return nameMap[key] || key
}

function settingCategory(key: string) {
  return categoryMap[key] || ''
}

async function loadData() {
  loading.value = true
  try {
    // 并行加载推送设置和群机器人配置
    const [settingsRes, storeRes] = await Promise.all([
      notificationAPI.getSettings(),
      apiClient.get('/store/settings').catch(() => null),
    ])
    list.value = settingsRes.data.data

    if (storeRes) {
      const storeData = (storeRes.data as any).data || (storeRes.data as any)
      botEnabled.value = !!storeData?.wecom_bot_enabled
      webhookUrl.value = storeData?.wecom_webhook_url || ''
    }
  } finally {
    loading.value = false
  }
}

async function handleBotToggle() {
  try {
    await apiClient.put('/store/settings', { wecom_bot_enabled: botEnabled.value })
  } catch {
    botEnabled.value = !botEnabled.value
  }
}

async function handleSaveWebhook() {
  if (!webhookUrl.value.trim()) {
    testResult.value = { ok: false, msg: '请输入 Webhook 地址' }
    return
  }
  savingWebhook.value = true
  testResult.value = null
  try {
    await apiClient.put('/store/settings', { wecom_webhook_url: webhookUrl.value.trim() })
    testResult.value = { ok: true, msg: 'Webhook 地址已保存' }
  } catch (e: any) {
    testResult.value = { ok: false, msg: e.response?.data?.message || '保存失败' }
  } finally {
    savingWebhook.value = false
  }
}

async function handleTest() {
  if (!webhookUrl.value.trim()) {
    testResult.value = { ok: false, msg: '请先输入 Webhook 地址' }
    return
  }
  testing.value = true
  testResult.value = null
  try {
    await apiClient.post('/notifications/test-webhook', { webhook_url: webhookUrl.value.trim() })
    testResult.value = { ok: true, msg: '测试消息已发送，请查看企微群' }
  } catch (e: any) {
    testResult.value = { ok: false, msg: e.response?.data?.message || '测试发送失败' }
  } finally {
    testing.value = false
  }
}

async function handleSave() {
  saving.value = true
  try {
    for (const item of list.value) {
      await notificationAPI.saveSetting(item)
    }
    alert('保存成功')
  } catch (e: any) {
    alert(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(loadData)
</script>

<style scoped>
.notification-setting-page {
  padding: 16px;
  padding-bottom: 24px;
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

/* 群机器人配置卡片 */
.bot-config-card {
  background: #111111;
  border: 1px solid #FB0079;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
}

.bot-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.bot-title-area {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.bot-title {
  font-size: 15px;
  font-weight: 700;
  color: #FFFFFF;
}

.bot-desc {
  font-size: 11px;
  color: #7A7C80;
}

.bot-form {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #333333;
}

.form-label {
  display: block;
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 6px;
}

.form-input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #000000;
  color: #FFFFFF;
  font-size: 13px;
  box-sizing: border-box;
  margin-bottom: 10px;
}

.form-input:focus {
  outline: none;
  border-color: #FB0079;
}

.bot-actions {
  display: flex;
  gap: 8px;
}

.btn {
  flex: 1;
  padding: 8px;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}

.btn:disabled {
  opacity: 0.4;
  cursor: default;
}

.btn-test {
  background: #333333;
  color: #FFFFFF;
}

.btn-save-webhook {
  background: #FB0079;
  color: #FFFFFF;
}

.test-result {
  margin-top: 8px;
  padding: 6px 10px;
  border-radius: 4px;
  font-size: 12px;
}

.test-result.success {
  background: rgba(76, 175, 80, 0.1);
  color: #4CAF50;
}

.test-result.fail {
  background: rgba(251, 0, 121, 0.1);
  color: #FB0079;
}

/* 推送项列表 */
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #7A7C80;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.loading {
  text-align: center;
  color: #7A7C80;
  padding: 32px;
}

.setting-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.setting-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 12px;
  transition: opacity 0.2s;
}

.setting-card.disabled {
  opacity: 0.6;
}

.setting-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.setting-name-area {
  display: flex;
  align-items: center;
  gap: 8px;
}

.setting-name {
  font-size: 14px;
  color: #FFFFFF;
  font-weight: 600;
}

.setting-category {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: rgba(251, 0, 121, 0.12);
  color: #FB0079;
}

.setting-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.setting-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.row-label {
  width: 70px;
  font-size: 12px;
  color: #C8C8C8;
  flex-shrink: 0;
}

.form-select {
  flex: 1;
  padding: 5px 8px;
  border: 1px solid #333333;
  border-radius: 5px;
  background: #000000;
  color: #FFFFFF;
  font-size: 12px;
}

.time-input {
  flex: 1;
  padding: 5px 8px;
  border: 1px solid #333333;
  border-radius: 5px;
  background: #000000;
  color: #FFFFFF;
  font-size: 12px;
  margin-bottom: 0;
}

.clear-time-btn {
  padding: 4px 8px;
  border: 1px solid #333333;
  border-radius: 4px;
  background: #222222;
  color: #C8C8C8;
  font-size: 11px;
  cursor: pointer;
}

.row-hint {
  font-size: 11px;
  color: #7A7C80;
}

.role-checks {
  display: flex;
  gap: 10px;
  flex: 1;
}

.role-checks label {
  display: flex;
  align-items: center;
  gap: 3px;
  color: #C8C8C8;
  font-size: 12px;
}

/* Toggle Switch (大) */
.switch {
  position: relative;
  display: inline-block;
  width: 44px;
  height: 24px;
  flex-shrink: 0;
}

.switch input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #333333;
  border-radius: 24px;
  transition: background 0.2s;
}

.slider::before {
  content: "";
  position: absolute;
  height: 18px;
  width: 18px;
  left: 3px;
  bottom: 3px;
  background: #FFFFFF;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch input:checked + .slider {
  background: #FB0079;
}

.switch input:checked + .slider::before {
  transform: translateX(20px);
}

/* Toggle Switch (小) */
.switch-mini {
  position: relative;
  display: inline-block;
  width: 36px;
  height: 20px;
  flex-shrink: 0;
}

.switch-mini input {
  opacity: 0;
  width: 0;
  height: 0;
}

.slider-mini {
  position: absolute;
  cursor: pointer;
  top: 0; left: 0; right: 0; bottom: 0;
  background: #333333;
  border-radius: 20px;
  transition: background 0.2s;
}

.slider-mini::before {
  content: "";
  position: absolute;
  height: 14px;
  width: 14px;
  left: 3px;
  bottom: 3px;
  background: #FFFFFF;
  border-radius: 50%;
  transition: transform 0.2s;
}

.switch-mini input:checked + .slider-mini {
  background: #4CAF50;
}

.switch-mini input:checked + .slider-mini::before {
  transform: translateX(16px);
}

/* 保存按钮 */
.save-btn {
  width: 100%;
  margin-top: 16px;
  padding: 12px;
  border: none;
  border-radius: 8px;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.save-btn:disabled {
  opacity: 0.4;
}
</style>
