<template>
  <div class="ai-global-page">
    <h2 class="page-title">全局 AI 配置</h2>
    <p class="page-desc">配置全品牌共用的 AI 模型，所有门店默认继承。单店可在设置里单独覆盖。</p>

    <!-- 一键预设 -->
    <div class="preset-card">
      <div class="preset-title">智谱免费模型（推荐）</div>
      <p class="preset-desc">两个模型都免费，只需一个 API Key</p>
      <button class="btn-preset" @click="applyPreset" :disabled="saving">
        一键填入智谱免费模型
      </button>
      <a class="preset-link" href="https://open.bigmodel.cn" target="_blank">去智谱注册拿 Key ></a>
    </div>

    <!-- 聊天模型 -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-icon chat">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <path d="M2 4a2 2 0 012-2h8a2 2 0 012 2v6a2 2 0 01-2 2H6l-4 3v-3a2 2 0 01-0-2z"/>
          </svg>
        </span>
        <div>
          <div class="section-name">聊天模型</div>
          <div class="section-sub">老C问答、数据查询、排班建议</div>
        </div>
        <span class="section-tag free">免费</span>
      </div>

      <div class="form-row">
        <label>API 地址</label>
        <input v-model="form.chat_api_url" class="input" placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions" />
      </div>
      <div class="form-row">
        <label>模型名</label>
        <input v-model="form.chat_model" class="input" placeholder="glm-4-flash" />
      </div>
      <div class="form-row">
        <label>API Key</label>
        <input
          v-model="form.chat_api_key"
          class="input"
          type="password"
          :placeholder="chatKeyMasked ? `已保存 (${chatKeyMasked})` : '粘贴智谱 API Key'"
        />
      </div>
    </div>

    <!-- 视觉模型 -->
    <div class="section-card">
      <div class="section-header">
        <span class="section-icon vision">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="1.5" y="3" width="13" height="10" rx="1.5"/>
            <circle cx="8" cy="8" r="2.5"/>
          </svg>
        </span>
        <div>
          <div class="section-name">视觉模型</div>
          <div class="section-sub">开闭店拍照识别、AI 自动判定</div>
        </div>
        <span class="section-tag free">免费</span>
      </div>

      <div class="form-row">
        <label>API 地址</label>
        <input v-model="form.vision_api_url" class="input" placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions" />
      </div>
      <div class="form-row">
        <label>模型名</label>
        <input v-model="form.vision_model" class="input" placeholder="glm-4v-flash" />
      </div>
      <div class="form-row">
        <label>API Key</label>
        <input
          v-model="form.vision_api_key"
          class="input"
          type="password"
          :placeholder="visionKeyMasked ? `已保存 (${visionKeyMasked})` : '跟聊天模型用同一个 Key 即可'"
        />
      </div>
    </div>

    <!-- 保存 -->
    <button class="btn-save" :disabled="saving" @click="handleSave">
      {{ saving ? '保存中...' : '保存配置' }}
    </button>

    <transition name="fade">
      <div v-if="msg" class="msg" :class="msgType">{{ msg }}</div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { hqAPI } from '@/api/hq'

const saving = ref(false)
const msg = ref('')
const msgType = ref<'success' | 'error'>('success')
const chatKeyMasked = ref('')
const visionKeyMasked = ref('')

const form = reactive({
  chat_api_url: '',
  chat_api_key: '',
  chat_model: '',
  vision_api_url: '',
  vision_api_key: '',
  vision_model: '',
})

const ZHIPU_URL = 'https://open.bigmodel.cn/api/paas/v4/chat/completions'

function applyPreset() {
  if (!form.chat_api_url) form.chat_api_url = ZHIPU_URL
  if (!form.vision_api_url) form.vision_api_url = ZHIPU_URL
  if (!form.chat_model) form.chat_model = 'glm-4-flash'
  if (!form.vision_model) form.vision_model = 'glm-4v-flash'
  // 两个 key 用同一个值
  if (!form.chat_api_key && form.vision_api_key) {
    form.chat_api_key = form.vision_api_key
  }
  if (!form.vision_api_key && form.chat_api_key) {
    form.vision_api_key = form.chat_api_key
  }
  msg.value = '已填入智谱免费模型，请输入 API Key 后保存'
  msgType.value = 'success'
}

onMounted(async () => {
  try {
    const res = await hqAPI.getGlobalAIConfig()
    const d = res.data.data
    form.chat_api_url = d.chat_api_url || ''
    form.chat_model = d.chat_model || ''
    form.vision_api_url = d.vision_api_url || ''
    form.vision_model = d.vision_model || ''
    chatKeyMasked.value = d.chat_api_key_masked || ''
    visionKeyMasked.value = d.vision_api_key_masked || ''
  } catch {
    msg.value = '加载配置失败'
    msgType.value = 'error'
  }
})

async function handleSave() {
  saving.value = true
  msg.value = ''
  try {
    const payload: Record<string, unknown> = {}
    if (form.chat_api_url) payload.chat_api_url = form.chat_api_url
    if (form.chat_model) payload.chat_model = form.chat_model
    if (form.chat_api_key) payload.chat_api_key = form.chat_api_key
    if (form.vision_api_url) payload.vision_api_url = form.vision_api_url
    if (form.vision_model) payload.vision_model = form.vision_model
    if (form.vision_api_key) payload.vision_api_key = form.vision_api_key

    await hqAPI.updateGlobalAIConfig(payload)
    msg.value = '全局配置已保存，全品牌门店立即生效'
    msgType.value = 'success'
    if (form.chat_api_key) {
      chatKeyMasked.value = '****' + form.chat_api_key.slice(-4)
      form.chat_api_key = ''
    }
    if (form.vision_api_key) {
      visionKeyMasked.value = '****' + form.vision_api_key.slice(-4)
      form.vision_api_key = ''
    }
  } catch {
    msg.value = '保存失败，请检查权限'
    msgType.value = 'error'
  } finally {
    saving.value = false
  }
}
</script>

<style scoped>
.ai-global-page {
  padding: 16px;
  max-width: 640px;
  margin: 0 auto;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 4px;
}

.page-desc {
  font-size: 13px;
  color: #7A7C80;
  margin: 0 0 16px;
  line-height: 1.5;
}

/* 预设卡片 */
.preset-card {
  background: rgba(251, 0, 121, 0.08);
  border: 1px solid rgba(251, 0, 121, 0.2);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  text-align: center;
}

.preset-title {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
  margin-bottom: 4px;
}

.preset-desc {
  font-size: 12px;
  color: #7A7C80;
  margin: 0 0 12px;
}

.btn-preset {
  padding: 10px 24px;
  background: #FB0079;
  color: #fff;
  border: none;
  border-radius: 20px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
}
.btn-preset:active { transform: scale(0.96); }
.btn-preset:disabled { opacity: 0.5; }

.preset-link {
  display: block;
  margin-top: 10px;
  font-size: 12px;
  color: #FB0079;
  text-decoration: none;
}

/* 模型区块 */
.section-card {
  background: #111;
  border: 1px solid #222;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 12px;
}

.section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
}

.section-icon {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.section-icon.chat {
  background: rgba(251, 0, 121, 0.12);
  color: #FB0079;
}

.section-icon.vision {
  background: rgba(0, 191, 255, 0.12);
  color: #00BFFF;
}

.section-name {
  font-size: 14px;
  font-weight: 600;
  color: #fff;
}

.section-sub {
  font-size: 11px;
  color: #7A7C80;
}

.section-tag {
  margin-left: auto;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 600;
}

.section-tag.free {
  background: rgba(0, 200, 100, 0.15);
  color: #00c864;
}

/* 表单 */
.form-row {
  margin-bottom: 12px;
}

.form-row label {
  display: block;
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 4px;
}

.input {
  width: 100%;
  height: 38px;
  padding: 0 12px;
  background: #000;
  border: 1px solid #333;
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  outline: none;
  box-sizing: border-box;
}

.input:focus {
  border-color: #FB0079;
}

.input::placeholder {
  color: #555;
  font-size: 12px;
}

/* 保存按钮 */
.btn-save {
  width: 100%;
  height: 44px;
  background: #FB0079;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  -webkit-tap-highlight-color: transparent;
  margin-top: 4px;
}

.btn-save:active { transform: scale(0.98); }
.btn-save:disabled { opacity: 0.5; }

/* 消息 */
.msg {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
  text-align: center;
}

.msg.success {
  background: rgba(0, 200, 100, 0.1);
  color: #00c864;
  border: 1px solid rgba(0, 200, 100, 0.2);
}

.msg.error {
  background: rgba(251, 0, 121, 0.1);
  color: #FB0079;
  border: 1px solid rgba(251, 0, 121, 0.2);
}

.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
