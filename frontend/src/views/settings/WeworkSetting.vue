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
          <span>回调Token</span>
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

    <!-- 对外收款配置（用于提成计算） -->
    <div class="section">
      <div class="section-header">
        <span>对外收款配置</span>
        <span class="section-tag">提成数据源</span>
      </div>
      <div class="section-body">
        <div class="form-row hint-row">
          <span class="hint-text">开通企微「对外收款」后，在这里填 Secret。系统会自动拉取员工个人收款记录，用于计算提成。</span>
        </div>
        <div class="form-row">
          <span>对外收款 Secret</span>
          <input v-model="wework.externalpay_secret" type="password" class="input input-long" placeholder="对外收款专用 Secret" />
        </div>
        <div class="form-row" v-if="externalpayConfigured">
          <span class="status-tag configured">已配置</span>
        </div>
        <button class="save-btn" :disabled="saving" @click="saveExternalpay">
          {{ saving ? '保存中...' : '保存收款配置' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { storeAPI, type StoreInfo } from '@/api/store'
import apiClient from '@/api/client'

const wework = reactive({
  corp_id: '',
  agent_id: '',
  secret: '',
  token: '',
  aes_key: '',
  department_id: null as number | null,
  externalpay_secret: '',
})

// 后端返回"已配置"表示已存过 Secret（不返回明文）
const externalpayConfigured = ref(false)

const saving = ref(false)
const syncing = ref(false)

async function loadData() {
  try {
    const res = await storeAPI.getInfo()
    const info = res.data.data
    if (info.wework_corp_id) wework.corp_id = info.wework_corp_id
    if (info.wework_agent_id) wework.agent_id = info.wework_agent_id
    if (info.wework_department_id) wework.department_id = info.wework_department_id
    // 后端返回"已配置"字符串表示已存过
    if (info.wework_externalpay_secret === '已配置') {
      externalpayConfigured.value = true
    }
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
    ElMessage.success('企微配置已保存')
  } catch {
    ElMessage.error('保存失败')
  }
  saving.value = false
}

async function saveExternalpay() {
  if (!wework.externalpay_secret) {
    ElMessage.warning('请先填写对外收款 Secret')
    return
  }
  saving.value = true
  try {
    await storeAPI.updateWework({
      wework_externalpay_secret: wework.externalpay_secret,
    })
    ElMessage.success('收款配置已保存')
    externalpayConfigured.value = true
    wework.externalpay_secret = ''  // 清空输入框，避免重复保存
  } catch {
    ElMessage.error('保存失败')
  }
  saving.value = false
}

async function syncContacts() {
  syncing.value = true
  try {
    await apiClient.post('/stores/wework/sync-contacts')
    ElMessage.success('通讯录同步完成')
  } catch {
    ElMessage.error('同步失败')
  }
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

/* 对外收款标签 */
.section-tag {
  font-size: 10px;
  color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
  padding: 2px 8px;
  border-radius: 4px;
}

.status-tag {
  font-size: 11px;
  padding: 4px 10px;
  border-radius: 6px;
}
.status-tag.configured {
  color: #4CAF50;
  background: rgba(76, 175, 80, 0.15);
}
</style>
