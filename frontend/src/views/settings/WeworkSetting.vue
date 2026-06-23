<template>
  <div class="wework-setting-page">
    <div class="page-header">
      <span class="page-title">企业微信配置</span>
    </div>

    <div class="section">
      <div class="section-header">
        <span>企业微信配置</span>
      </div>
      <div class="section-body">
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

        <button class="save-btn" :disabled="saving" @click="saveWework">
          {{ saving ? '保存中...' : '保存企微配置' }}
        </button>
        <button class="sync-btn" :disabled="syncing" @click="syncContacts">
          {{ syncing ? '同步中...' : '同步通讯录' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { storeAPI, type StoreInfo } from '@/api/store'
import apiClient from '@/api/client'

const wework = reactive({
  corp_id: '',
  agent_id: '',
  secret: '',
  token: '',
  aes_key: '',
  department_id: null as number | null,
})

const saving = ref(false)
const syncing = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getInfo()
    const info = res.data.data
    if (info.wework_corp_id) wework.corp_id = info.wework_corp_id
    if (info.wework_agent_id) wework.agent_id = info.wework_agent_id
    if (info.wework_department_id) wework.department_id = info.wework_department_id
  } catch { /* silent */ }
}

async function saveWework() {
  saving.value = true
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
  saving.value = false
}

async function syncContacts() {
  syncing.value = true
  try {
    await apiClient.post('/stores/wework/sync-contacts')
  } catch { /* silent */ }
  syncing.value = false
}

onMounted(loadData)
</script>

<style scoped>
.wework-setting-page {
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
.input-long { width: 140px; text-align: left; }
.input:focus { outline: none; border-color: #FB0079; }

.hint-row {
  border-bottom: none;
}
.hint-text {
  font-size: 12px;
  color: #7A7C80;
}

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

.sync-btn {
  width: 100%;
  margin-top: 8px;
  padding: 12px;
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
  cursor: pointer;
  transition: opacity 0.2s;
}
.sync-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.sync-btn:active { opacity: 0.7; }
</style>
