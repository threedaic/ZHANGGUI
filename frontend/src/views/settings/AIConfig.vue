<template>
  <div class="ai-config-page">
    <h2 class="page-title">AI 配置</h2>
    <p class="page-desc">配置大模型 API，用于小C 智能问答与开闭店图像识别判定。</p>

    <!-- 应用场景说明 -->
    <div class="usage-card">
      <div class="usage-title">本配置用于：</div>
      <div class="usage-item">
        <span class="usage-icon pink">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M2 12h10"/><path d="M3 12V7l4-4 4 4v5"/></svg>
        </span>
        <div>
          <div class="usage-name">小C 智能问答</div>
          <div class="usage-desc">文本对话，支持 DeepSeek / Qwen / GLM 等文本模型</div>
        </div>
      </div>
      <div class="usage-item">
        <span class="usage-icon pink">
          <svg width="14" height="14" viewBox="0 0 14 14" fill="none" stroke="currentColor" stroke-width="1.5"><rect x="2" y="3" width="10" height="8" rx="1"/><circle cx="7" cy="7" r="2"/></svg>
        </span>
        <div>
          <div class="usage-name">开闭店图像识别</div>
          <div class="usage-desc">员工拍照后 AI 自动判定是否合格（如吧台是否整洁、酒水摆放是否整齐）</div>
        </div>
      </div>
    </div>

    <!-- 视觉模型推荐 -->
    <div class="recommend-card">
      <div class="recommend-title">视觉模型推荐（用于开闭店拍照判定）</div>
      <div class="recommend-list">
        <button
          v-for="m in visionModels"
          :key="m.model"
          class="recommend-item"
          :class="{ active: form.ai_model === m.model }"
          @click="selectVisionModel(m)"
        >
          <div class="recommend-left">
            <span class="recommend-name">{{ m.name }}</span>
            <span class="recommend-model">{{ m.model }}</span>
          </div>
          <span class="recommend-price">{{ m.price }}</span>
        </button>
      </div>
      <div class="recommend-tip">
        以上模型均兼容 OpenAI Vision API 格式。国内推荐 智谱 GLM-4V（性价比高，中文场景友好）；海外推荐 GPT-4o-mini。
      </div>
    </div>

    <div class="form-card">
      <!-- API 地址 -->
      <div class="form-item">
        <label class="form-label">API 地址</label>
        <input
          v-model="form.ai_api_url"
          class="form-input"
          placeholder="https://open.bigmodel.cn/api/paas/v4/chat/completions"
        />
        <span class="form-hint">OpenAI 兼容格式的 Chat Completions 端点</span>
      </div>

      <!-- API Key -->
      <div class="form-item">
        <label class="form-label">API Key</label>
        <div class="key-input-wrap">
          <input
            v-model="form.ai_api_key"
            class="form-input"
            :type="showKey ? 'text' : 'password'"
            :placeholder="savedKeyMasked ? `已保存 (${savedKeyMasked})` : 'sk-...'"
          />
          <button
            v-if="savedKeyMasked || form.ai_api_key"
            class="key-toggle-btn"
            type="button"
            @click="showKey = !showKey"
          >
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
              <template v-if="showKey">
                <path d="M1 8s3-5 7-5 7 5 7 5-3 5-7 5-7-5-7-5z" stroke="#7A7C80" stroke-width="1.2"/>
                <circle cx="8" cy="8" r="2" stroke="#7A7C80" stroke-width="1.2"/>
              </template>
              <template v-else>
                <path d="M14 2L2 14" stroke="#7A7C80" stroke-width="1.2"/>
                <path d="M1 8s2.5-4 7-4 7 4 7 4-2.5 4-7 4-7-4-7-4z" stroke="#7A7C80" stroke-width="1.2"/>
              </template>
            </svg>
          </button>
        </div>
        <span class="form-hint">Key 将 AES 加密存储，不会明文保存</span>
      </div>

      <!-- 模型 -->
      <div class="form-item">
        <label class="form-label">模型</label>
        <input
          v-model="form.ai_model"
          class="form-input"
          list="model-options"
          placeholder="点击选择或输入模型名"
        />
        <datalist id="model-options">
          <option value="glm-4v" />
          <option value="glm-4v-flash" />
          <option value="glm-4" />
          <option value="qwen-vl-plus" />
          <option value="qwen-vl-max" />
          <option value="qwen-plus" />
          <option value="qwen-max" />
          <option value="gpt-4o-mini" />
          <option value="gpt-4o" />
          <option value="deepseek-chat" />
        </datalist>
        <span class="form-hint">视觉判定需选择带 V/VL/vision 的多模态模型；纯文本问答任意模型均可</span>
      </div>

      <!-- 温度 -->
      <div class="form-item">
        <label class="form-label">
          温度
          <span class="form-label-value">{{ form.ai_temperature.toFixed(1) }}</span>
        </label>
        <div class="slider-wrap">
          <input
            v-model.number="form.ai_temperature"
            type="range"
            min="0"
            max="2"
            step="0.1"
            class="form-slider"
          />
          <div class="slider-labels">
            <span>0 精确</span>
            <span>2 创意</span>
          </div>
        </div>
        <span class="form-hint">数值越低回答越精确，越高越有创意。推荐 0.7（图像判定固定使用 0.2）</span>
      </div>

      <!-- 操作按钮 -->
      <div class="form-actions">
        <button
          class="btn btn-test"
          :disabled="saving || testing"
          @click="handleTest"
        >
          {{ testing ? '测试中...' : '测试连接' }}
        </button>
        <button
          class="btn btn-save"
          :disabled="saving"
          @click="handleSave"
        >
          {{ saving ? '保存中...' : '保存配置' }}
        </button>
      </div>

      <!-- 消息提示 -->
      <div v-if="message" class="form-message" :class="messageType">
        {{ message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { aiAPI } from '@/api/ai'

interface FormData {
  ai_api_url: string
  ai_api_key: string
  ai_model: string
  ai_temperature: number
}

interface VisionModel {
  name: string
  model: string
  price: string
  apiUrl: string
}

// 视觉模型推荐列表
const visionModels: VisionModel[] = [
  {
    name: '智谱 GLM-4V（推荐）',
    model: 'glm-4v',
    price: '¥0.05/千token',
    apiUrl: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
  },
  {
    name: '智谱 GLM-4V-Flash（免费）',
    model: 'glm-4v-flash',
    price: '免费',
    apiUrl: 'https://open.bigmodel.cn/api/paas/v4/chat/completions',
  },
  {
    name: '通义千问 VL-Plus',
    model: 'qwen-vl-plus',
    price: '¥0.008/千token',
    apiUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
  },
  {
    name: '通义千问 VL-Max',
    model: 'qwen-vl-max',
    price: '¥0.02/千token',
    apiUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions',
  },
  {
    name: 'GPT-4o-mini（海外）',
    model: 'gpt-4o-mini',
    price: '$0.15/1M',
    apiUrl: 'https://api.openai.com/v1/chat/completions',
  },
]

function selectVisionModel(m: VisionModel) {
  form.ai_model = m.model
  // 如果当前 API 地址为空或是其他厂商的地址，自动填充
  if (!form.ai_api_url || !form.ai_api_url.includes('/chat/completions')) {
    form.ai_api_url = m.apiUrl
  }
}

const form = reactive<FormData>({
  ai_api_url: '',
  ai_api_key: '',
  ai_model: '',
  ai_temperature: 0.7,
})

const savedKeyMasked = ref('')
const showKey = ref(false)
const saving = ref(false)
const testing = ref(false)
const message = ref('')
const messageType = ref<'success' | 'error'>('success')

onMounted(async () => {
  try {
    const res = await aiAPI.getConfig()
    const data = res.data.data
    form.ai_api_url = data.ai_api_url || ''
    form.ai_model = data.ai_model || ''
    form.ai_temperature = data.ai_temperature ?? 0.7
    savedKeyMasked.value = data.ai_api_key_masked || ''
    // Don't prefill key — user needs to re-enter if they want to change
  } catch {
    message.value = '加载配置失败'
    messageType.value = 'error'
  }
})

async function handleSave() {
  saving.value = true
  message.value = ''
  try {
    const payload: Record<string, unknown> = {
      ai_api_url: form.ai_api_url || null,
      ai_model: form.ai_model || null,
      ai_temperature: form.ai_temperature,
    }
    // Only send key if user typed a new one
    if (form.ai_api_key) {
      payload.ai_api_key = form.ai_api_key
    }
    await aiAPI.updateConfig(payload)
    message.value = '配置已保存，实时生效'
    messageType.value = 'success'
    if (form.ai_api_key) {
      savedKeyMasked.value = '****' + form.ai_api_key.slice(-4)
      form.ai_api_key = ''
      showKey.value = false
    }
  } catch {
    message.value = '保存失败，请检查网络'
    messageType.value = 'error'
  } finally {
    saving.value = false
  }
}

async function handleTest() {
  testing.value = true
  message.value = ''
  try {
    // Send a simple test message via chat
    const keyToUse = form.ai_api_key || undefined
    if (!form.ai_api_url || (!keyToUse && !savedKeyMasked.value)) {
      message.value = '请先填写 API 地址和 Key'
      messageType.value = 'error'
      testing.value = false
      return
    }
    // Save first if there are unsaved changes
    await handleSaveForce()
    const res = await aiAPI.chat({ message: '你好，请回复"连接成功"' })
    if (res.data.code === 0) {
      message.value = '连接成功，小C 已就绪'
      messageType.value = 'success'
    } else {
      message.value = res.data.message || '连接失败'
      messageType.value = 'error'
    }
  } catch {
    message.value = '连接失败，请检查 API 地址和 Key'
    messageType.value = 'error'
  } finally {
    testing.value = false
  }
}

async function handleSaveForce() {
  try {
    const payload: Record<string, unknown> = {
      ai_api_url: form.ai_api_url || null,
      ai_model: form.ai_model || null,
      ai_temperature: form.ai_temperature,
    }
    if (form.ai_api_key) {
      payload.ai_api_key = form.ai_api_key
    }
    await aiAPI.updateConfig(payload)
    if (form.ai_api_key) {
      savedKeyMasked.value = '****' + form.ai_api_key.slice(-4)
      form.ai_api_key = ''
      showKey.value = false
    }
  } catch {
    // Ignore save error during test
  }
}
</script>

<style scoped>
.ai-config-page {
  padding: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0 0 4px;
}

.page-desc {
  font-size: 13px;
  color: #7A7C80;
  margin: 0 0 20px;
}

.form-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 20px 16px;
}

/* 应用场景卡片 */
.usage-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}

.usage-title {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 10px;
}

.usage-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
}

.usage-item + .usage-item {
  margin-top: 4px;
}

.usage-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  background: rgba(251, 0, 121, 0.1);
  border-radius: 6px;
  color: #FB0079;
  flex-shrink: 0;
  margin-top: 2px;
}

.usage-name {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 2px;
}

.usage-desc {
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
}

/* 视觉模型推荐卡片 */
.recommend-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}

.recommend-title {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 10px;
}

.recommend-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.recommend-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  cursor: pointer;
  transition: border-color 0.2s;
  text-align: left;
  width: 100%;
}

.recommend-item:hover {
  border-color: #555;
}

.recommend-item.active {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.05);
}

.recommend-left {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.recommend-name {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}

.recommend-model {
  font-size: 11px;
  color: #7A7C80;
  font-family: 'Poppins', monospace;
}

.recommend-price {
  font-size: 11px;
  color: #FB0079;
  font-weight: 500;
}

.recommend-tip {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 10px;
  line-height: 1.5;
}

.form-item {
  margin-bottom: 20px;
}

.form-label {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 14px;
  color: #C8C8C8;
  margin-bottom: 6px;
}

.form-label-value {
  font-family: 'Poppins', sans-serif;
  font-size: 13px;
  color: #FB0079;
}

.form-input,
.form-select {
  width: 100%;
  height: 40px;
  padding: 0 12px;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.form-input:focus,
.form-select:focus {
  border-color: #FB0079;
}

.form-input::placeholder {
  color: #7A7C80;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg width='12' height='8' viewBox='0 0 12 8' fill='none'%3E%3Cpath d='M1 1l5 5 5-5' stroke='%237A7C80' stroke-width='1.5'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
}

.form-select option {
  background: #111111;
  color: #C8C8C8;
}

.form-hint {
  display: block;
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.key-input-wrap {
  display: flex;
  gap: 8px;
}

.key-input-wrap .form-input {
  flex: 1;
}

.key-toggle-btn {
  width: 40px;
  height: 40px;
  border: 1px solid #333333;
  border-radius: 8px;
  background: #000000;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
}

.key-toggle-btn:hover {
  border-color: #FB0079;
}

.slider-wrap {
  padding: 4px 0;
}

.form-slider {
  width: 100%;
  height: 4px;
  -webkit-appearance: none;
  appearance: none;
  background: #333333;
  border-radius: 2px;
  outline: none;
}

.form-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #FB0079;
  cursor: pointer;
  border: 2px solid #000000;
}

.slider-labels {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: #7A7C80;
  margin-top: 4px;
}

.form-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.btn {
  flex: 1;
  height: 44px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.btn-test {
  background: #333333;
  color: #C8C8C8;
  border: 1px solid #333333;
}

.btn-save {
  background: #FB0079;
  color: #FFFFFF;
}

.btn-save:not(:disabled):hover {
  opacity: 0.9;
}

.form-message {
  margin-top: 12px;
  padding: 10px 14px;
  border-radius: 8px;
  font-size: 13px;
}

.form-message.success {
  background: rgba(0, 200, 100, 0.1);
  color: #00c864;
  border: 1px solid rgba(0, 200, 100, 0.2);
}

.form-message.error {
  background: rgba(251, 0, 121, 0.1);
  color: #FB0079;
  border: 1px solid rgba(251, 0, 121, 0.2);
}
</style>
