<template>
  <div class="checkin-setting-page">
    <h1 class="page-title">打卡设置</h1>
    <p class="page-tip">配置打卡规则、智能班次归位、WiFi绑定</p>

    <div v-if="loading" class="loading-text">加载中...</div>
    <template v-else>
      <!-- 打卡规则 -->
      <div class="section">
        <h2 class="section-title">打卡规则</h2>
        <div class="setting-card">
          <div class="setting-row">
            <div class="setting-info">
              <span class="setting-label">要求拍照</span>
              <span class="setting-desc">打卡时必须拍照（防代打卡）</span>
            </div>
            <el-switch v-model="config.require_photo" />
          </div>
          <div class="setting-divider"></div>
          <div class="setting-row">
            <div class="setting-info">
              <span class="setting-label">要求WiFi验证</span>
              <span class="setting-desc">需连接门店WiFi才能打卡（企微内生效）</span>
            </div>
            <el-switch v-model="config.require_wifi" />
          </div>
          <div class="setting-divider"></div>
          <div class="setting-row">
            <div class="setting-info">
              <span class="setting-label">迟到宽容</span>
              <span class="setting-desc">上班后多少分钟内不算迟到</span>
            </div>
            <div class="number-input-group">
              <button class="num-btn" @click="adjustGrace(-1)">-</button>
              <span class="num-value">{{ config.grace_minutes }}分</span>
              <button class="num-btn" @click="adjustGrace(1)">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 智能班次归位 -->
      <div class="section">
        <h2 class="section-title">智能班次归位</h2>
        <p class="section-desc">员工打卡时，系统自动判断属于哪个班次、是上班还是下班</p>

        <!-- 算法流程图 -->
        <div class="algo-flow">
          <div class="algo-step">
            <div class="algo-step-num">1</div>
            <div class="algo-step-body">
              <span class="algo-step-title">排班优先</span>
              <span class="algo-step-desc">有排班 → 直接用排班班次</span>
            </div>
          </div>
          <div class="algo-arrow">↓</div>
          <div class="algo-step">
            <div class="algo-step-num">2</div>
            <div class="algo-step-body">
              <span class="algo-step-title">时间窗口兜底</span>
              <span class="algo-step-desc">无排班 → 在班次前后{{ config.time_window_minutes }}分钟内找最近的</span>
            </div>
          </div>
          <div class="algo-arrow">↓</div>
          <div class="algo-step">
            <div class="algo-step-num">3</div>
            <div class="algo-step-body">
              <span class="algo-step-title">交替打卡</span>
              <span class="algo-step-desc">无匹配 → 有上班记录就下班，没有就上班</span>
            </div>
          </div>
        </div>

        <!-- 时间窗口配置 -->
        <div class="setting-card">
          <div class="setting-row">
            <div class="setting-info">
              <span class="setting-label">时间窗口</span>
              <span class="setting-desc">打卡时间在班次开始/结束前后多少分钟内可匹配</span>
            </div>
            <div class="number-input-group">
              <button class="num-btn" @click="adjustWindow(-30)">-</button>
              <span class="num-value">±{{ config.time_window_minutes }}分</span>
              <button class="num-btn" @click="adjustWindow(30)">+</button>
            </div>
          </div>
        </div>

        <!-- 示例 -->
        <div class="example-card">
          <div class="example-title">示例（早班14:00-20:00 / 晚班19:00-03:00）</div>
          <div class="example-row">
            <span class="example-time">14:05 打卡</span>
            <span class="example-arrow">→</span>
            <span class="example-result">早班·上班（排班优先）</span>
          </div>
          <div class="example-row">
            <span class="example-time">20:10 打卡</span>
            <span class="example-arrow">→</span>
            <span class="example-result">早班·下班（排班优先）</span>
          </div>
          <div class="example-row">
            <span class="example-time">19:30 打卡</span>
            <span class="example-arrow">→</span>
            <span class="example-result">晚班·上班（无排班时按窗口）</span>
          </div>
          <div class="example-row">
            <span class="example-time">03:00 打卡</span>
            <span class="example-arrow">→</span>
            <span class="example-result">晚班·下班（归昨天记录）</span>
          </div>
        </div>
      </div>

      <!-- 照片保留 -->
      <div class="section">
        <h2 class="section-title">照片保留期</h2>
        <div class="setting-card">
          <div class="setting-row">
            <div class="setting-info">
              <span class="setting-label">自动清理</span>
              <span class="setting-desc">超期照片自动删除，WiFi/时间记录保留</span>
            </div>
            <div class="number-input-group">
              <button class="num-btn" @click="adjustRetention(-30)">-</button>
              <span class="num-value">{{ config.photo_retention_days }}天</span>
              <button class="num-btn" @click="adjustRetention(30)">+</button>
            </div>
          </div>
        </div>
      </div>

      <!-- WiFi绑定 -->
      <div class="section">
        <div class="section-header">
          <h2 class="section-title">WiFi绑定</h2>
          <button class="btn-add" @click="showAddWifi = true">+ 添加</button>
        </div>
        <div class="setting-card">
          <div v-if="config.wifis.length === 0" class="empty-text">
            暂未绑定WiFi，员工打卡时不校验WiFi
          </div>
          <div v-else class="wifi-list">
            <div v-for="wifi in config.wifis" :key="wifi.id" class="wifi-item">
              <div class="wifi-info">
                <span class="wifi-ssid">{{ wifi.ssid }}</span>
                <span class="wifi-bssid">{{ wifi.bssid }}</span>
                <span v-if="wifi.label" class="wifi-label">{{ wifi.label }}</span>
              </div>
              <button class="btn-delete" @click="handleDeleteWifi(wifi.id)">删除</button>
            </div>
          </div>
        </div>
      </div>

      <!-- 保存按钮 -->
      <button class="save-btn" :disabled="saving" @click="saveConfig">
        {{ saving ? '保存中...' : '保存设置' }}
      </button>
    </template>

    <!-- 添加WiFi弹窗 -->
    <el-dialog v-model="showAddWifi" title="添加WiFi绑定" width="90%" class="wifi-dialog">
      <div class="form-item">
        <label class="form-label">WiFi名称 (SSID)</label>
        <el-input v-model="newWifi.ssid" placeholder="如：Crush-Bar-WiFi" />
      </div>
      <div class="form-item">
        <label class="form-label">MAC地址 (BSSID)</label>
        <el-input v-model="newWifi.bssid" placeholder="如：AA:BB:CC:DD:EE:FF" />
        <div class="form-hint">在路由器背面可查看，或手机连接WiFi后查看详情</div>
      </div>
      <div class="form-item">
        <label class="form-label">备注 (可选)</label>
        <el-input v-model="newWifi.label" placeholder="如：前台WiFi、包间WiFi" />
      </div>
      <el-button type="primary" class="submit-btn" :loading="addingWifi" @click="handleAddWifi">
        确认添加
      </el-button>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { attendanceAPI } from '@/api/attendance'
import type { CheckinConfig } from '@/api/attendance'

const loading = ref(true)
const saving = ref(false)
const config = ref<CheckinConfig>({
  require_wifi: true,
  require_photo: true,
  grace_minutes: 5,
  photo_retention_days: 90,
  time_window_minutes: 120,
  wifis: [],
})

const showAddWifi = ref(false)
const addingWifi = ref(false)
const newWifi = reactive({
  ssid: '',
  bssid: '',
  label: '',
})

async function loadConfig() {
  loading.value = true
  try {
    const res = await attendanceAPI.getCheckinConfig()
    if (res.data.code === 0) {
      config.value = res.data.data
    }
  } catch (e) {
    console.error('[CheckinSetting] loadConfig failed:', e)
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  if (saving.value) return
  saving.value = true
  try {
    await attendanceAPI.updateCheckinConfig({
      require_wifi: config.value.require_wifi,
      require_photo: config.value.require_photo,
      grace_minutes: config.value.grace_minutes,
      photo_retention_days: config.value.photo_retention_days,
      time_window_minutes: config.value.time_window_minutes,
    })
    ElMessage.success('设置已保存')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '保存失败')
    await loadConfig()
  } finally {
    saving.value = false
  }
}

function adjustGrace(delta: number) {
  const val = Math.max(0, Math.min(60, config.value.grace_minutes + delta))
  config.value.grace_minutes = val
}

function adjustWindow(delta: number) {
  const val = Math.max(30, Math.min(360, config.value.time_window_minutes + delta))
  config.value.time_window_minutes = val
}

function adjustRetention(delta: number) {
  const val = Math.max(30, Math.min(365, config.value.photo_retention_days + delta))
  config.value.photo_retention_days = val
}

async function handleAddWifi() {
  if (!newWifi.ssid.trim() || !newWifi.bssid.trim()) {
    ElMessage.warning('请填写WiFi名称和MAC地址')
    return
  }
  addingWifi.value = true
  try {
    const res = await attendanceAPI.addCheckinWifi({
      ssid: newWifi.ssid.trim(),
      bssid: newWifi.bssid.trim(),
      label: newWifi.label.trim() || undefined,
    })
    if (res.data.code === 0) {
      ElMessage.success('WiFi已添加')
      showAddWifi.value = false
      newWifi.ssid = ''
      newWifi.bssid = ''
      newWifi.label = ''
      await loadConfig()
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '添加失败')
  } finally {
    addingWifi.value = false
  }
}

async function handleDeleteWifi(wifiId: string) {
  try {
    await ElMessageBox.confirm('确认删除此WiFi绑定？', '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await attendanceAPI.deleteCheckinWifi(wifiId)
    ElMessage.success('已删除')
    await loadConfig()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '删除失败')
  }
}

onMounted(() => {
  loadConfig()
})
</script>

<style scoped>
.checkin-setting-page {
  padding: 16px;
  padding-bottom: 48px;
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
  margin-bottom: 20px;
}

.loading-text {
  color: #7A7C80;
  text-align: center;
  padding: 40px 0;
}

.section {
  margin-bottom: 24px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #C8C8C8;
  margin: 0 0 4px;
}

.section-desc {
  font-size: 11px;
  color: #7A7C80;
  margin: 0 0 12px;
}

.btn-add {
  padding: 4px 12px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.setting-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 4px 16px;
}

.setting-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 0;
}

.setting-divider {
  height: 1px;
  background: #222222;
}

.setting-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
  flex: 1;
}

.setting-label {
  font-size: 14px;
  color: #FFFFFF;
  font-weight: 500;
}

.setting-desc {
  font-size: 11px;
  color: #7A7C80;
}

.number-input-group {
  display: flex;
  align-items: center;
  gap: 12px;
}

.num-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #1a1a1a;
  color: #C8C8C8;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
}

.num-btn:active {
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
}

.num-value {
  font-size: 14px;
  font-weight: 600;
  color: #FB0079;
  min-width: 60px;
  text-align: center;
}

/* 智能算法流程图 */
.algo-flow {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.algo-step {
  display: flex;
  align-items: center;
  gap: 12px;
}

.algo-step-num {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: #FB0079;
  color: #FFFFFF;
  font-size: 12px;
  font-weight: 700;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.algo-step-body {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.algo-step-title {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}

.algo-step-desc {
  font-size: 11px;
  color: #7A7C80;
}

.algo-arrow {
  text-align: center;
  color: #333333;
  font-size: 14px;
  padding: 4px 0 4px 12px;
}

/* 示例卡片 */
.example-card {
  background: #0a0a0a;
  border: 1px solid #222222;
  border-radius: 10px;
  padding: 12px 14px;
  margin-top: 8px;
}

.example-title {
  font-size: 11px;
  color: #7A7C80;
  margin-bottom: 8px;
}

.example-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 4px 0;
  font-size: 12px;
}

.example-time {
  color: #C8C8C8;
  min-width: 80px;
}

.example-arrow {
  color: #333333;
}

.example-result {
  color: #FB0079;
}

/* WiFi 列表 */
.wifi-list {
  display: flex;
  flex-direction: column;
}

.wifi-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 0;
  border-bottom: 1px solid #222222;
}

.wifi-item:last-child {
  border-bottom: none;
}

.wifi-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.wifi-ssid {
  font-size: 14px;
  color: #FFFFFF;
  font-weight: 500;
}

.wifi-bssid {
  font-size: 11px;
  color: #7A7C80;
  font-family: 'Poppins', monospace;
}

.wifi-label {
  font-size: 10px;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
  padding: 1px 6px;
  border-radius: 3px;
  align-self: flex-start;
  margin-top: 2px;
}

.btn-delete {
  padding: 4px 10px;
  background: transparent;
  color: #FB0079;
  border: 1px solid #FB0079;
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
}

.empty-text {
  padding: 24px 0;
  text-align: center;
  color: #7A7C80;
  font-size: 13px;
}

/* 弹窗 */
.wifi-dialog :deep(.el-dialog) {
  background: #111111;
  border-radius: 12px;
}

.wifi-dialog :deep(.el-dialog__header) {
  background: #111111;
  border-bottom: 1px solid #333333;
  margin-right: 0;
  padding: 16px;
}

.wifi-dialog :deep(.el-dialog__title) {
  color: #FFFFFF;
  font-size: 16px;
  font-weight: 600;
}

.wifi-dialog :deep(.el-dialog__headerbtn .el-dialog__close) {
  color: #7A7C80;
}

.wifi-dialog :deep(.el-dialog__body) {
  background: #111111;
  color: #C8C8C8;
  padding: 16px;
}

.form-item {
  margin-bottom: 16px;
}

.form-label {
  display: block;
  font-size: 13px;
  color: #C8C8C8;
  margin-bottom: 6px;
}

.form-hint {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.submit-btn {
  width: 100%;
  background: #FB0079;
  border-color: #FB0079;
  color: #FFFFFF;
  border-radius: 8px;
  font-size: 14px;
  height: 40px;
  margin-top: 8px;
}

.submit-btn:hover {
  background: #FB0079;
  border-color: #FB0079;
}

/* Element Plus 覆盖 */
:deep(.el-input__wrapper) {
  background: #1a1a1a;
  box-shadow: 0 0 0 1px #333333;
  border-radius: 8px;
}

:deep(.el-input.is-focus .el-input__wrapper) {
  box-shadow: 0 0 0 1.5px #FB0079;
}

:deep(.el-input__inner) {
  color: #FFFFFF;
  font-size: 13px;
}

:deep(.el-input__inner::placeholder) {
  color: #7A7C80;
}

:deep(.el-switch.is-checked .el-switch__core) {
  background-color: #FB0079;
  border-color: #FB0079;
}

/* 保存按钮 */
.save-btn {
  width: 100%;
  height: 48px;
  background: #FB0079;
  color: #FFFFFF;
  border: none;
  border-radius: 12px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  margin-top: 16px;
  transition: opacity 0.2s;
}

.save-btn:active {
  opacity: 0.85;
}

.save-btn:disabled {
  background: #444444;
  color: #7A7C80;
  cursor: not-allowed;
}
</style>
