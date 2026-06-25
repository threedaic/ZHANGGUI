<template>
  <Teleport to="body">
    <Transition name="sheet">
      <div v-if="visible" class="chat-overlay" @click.self="close">
        <div class="chat-sheet">
          <!-- Header -->
          <div class="chat-header">
            <div class="chat-header-left">
              <img src="/laoc-avatar.png" class="chat-avatar" alt="老C" />
              <div class="chat-header-text">
                <span class="chat-title">老C</span>
                <span class="chat-subtitle">问排班、查存酒、看数据</span>
              </div>
            </div>
            <button class="chat-close" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M5 5l10 10M15 5L5 15" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <!-- Messages -->
          <div ref="msgListRef" class="chat-messages">
            <div v-if="messages.length === 0" class="chat-empty">
              <p class="chat-empty-title">有什么可以帮你？</p>
              <div class="chat-suggestions">
                <button
                  v-for="q in suggestions"
                  :key="q"
                  class="chat-suggestion-btn"
                  @click="sendMessage(q)"
                >{{ q }}</button>
              </div>
            </div>

            <div
              v-for="(msg, idx) in messages"
              :key="idx"
              class="chat-bubble-wrap"
              :class="msg.role"
            >
              <img v-if="msg.role === 'assistant'" src="/laoc-avatar.png" class="chat-bubble-avatar" alt="老C" />
              <div class="chat-bubble" :class="msg.role">
                <div class="chat-bubble-text">{{ msg.content }}</div>
              </div>
            </div>

            <!-- Loading -->
            <div v-if="loading" class="chat-bubble-wrap assistant">
              <img src="/laoc-avatar.png" class="chat-bubble-avatar" alt="老C" />
              <div class="chat-bubble assistant loading">
                <span class="dot"></span><span class="dot"></span><span class="dot"></span>
              </div>
            </div>
          </div>

          <!-- Input -->
          <div class="chat-input-area">
            <input
              v-model="inputText"
              class="chat-input"
              placeholder="输入问题..."
              :disabled="loading"
              @keydown.enter="handleSend"
            />
            <button
              class="chat-send-btn"
              :disabled="!inputText.trim() || loading"
              @click="handleSend"
            >
              <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
                <path d="M2 9l14-7-7 14-2-5-5-2z" :stroke="inputText.trim() && !loading ? '#FFFFFF' : '#7A7C80'" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
              </svg>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, nextTick, watch } from 'vue'
import { aiAPI } from '@/api/ai'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

const props = defineProps<{
  visible: boolean
}>()

const emit = defineEmits<{
  (e: 'close'): void
}>()

const messages = ref<ChatMessage[]>([])
const inputText = ref('')
const loading = ref(false)
const conversationId = ref<string | null>(null)
const msgListRef = ref<HTMLElement | null>(null)

const suggestions = [
  '今天谁晚班',
  '赵先生的存酒还在吗',
  'A1桌有人吗',
  '今天订桌情况',
  '存酒怎么操作',
]

function close() {
  emit('close')
}

async function handleSend() {
  const text = inputText.value.trim()
  if (!text || loading.value) return
  sendMessage(text)
}

async function sendMessage(text: string) {
  inputText.value = ''
  messages.value.push({ role: 'user', content: text })
  loading.value = true
  await scrollToBottom()

  try {
    const res = await aiAPI.chat({
      message: text,
      conversation_id: conversationId.value,
    })
    const data = res.data.data
    conversationId.value = data.conversation_id
    messages.value.push({ role: 'assistant', content: data.reply })
  } catch {
    messages.value.push({
      role: 'assistant',
      content: '抱歉，出了点问题，请稍后再试。',
    })
  } finally {
    loading.value = false
    await scrollToBottom()
  }
}

async function scrollToBottom() {
  await nextTick()
  if (msgListRef.value) {
    msgListRef.value.scrollTop = msgListRef.value.scrollHeight
  }
}

// Reset when dialog opens
watch(() => props.visible, (val) => {
  if (val) {
    messages.value = []
    conversationId.value = null
    inputText.value = ''
  }
})
</script>

<style scoped>
.chat-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(10px);
  -webkit-backdrop-filter: blur(10px);
  display: flex;
  align-items: center;
}

.chat-sheet {
  width: 100%;
  max-width: 480px;
  height: 85vh;
  margin: 0 auto;
  background: rgba(17, 17, 17, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 16px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
}

/* Header */
.chat-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.2);
  flex-shrink: 0;
}

.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chat-avatar {
  width: 36px;
  height: 36px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 0 12px rgba(251, 0, 121, 0.3);
}

.chat-header-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.chat-title {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
}

.chat-subtitle {
  font-size: 11px;
  color: #7A7C80;
}

.chat-close {
  width: 32px;
  height: 32px;
  border: none;
  background: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  transition: all 0.2s ease;
}

.chat-close:hover {
  background: rgba(255, 255, 255, 0.1);
}

/* Messages */
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  scroll-behavior: smooth;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
  margin-top: 40px;
}

.chat-empty-title {
  font-size: 15px;
  color: #C8C8C8;
}

.chat-suggestions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

.chat-suggestion-btn {
  padding: 8px 14px;
  background: rgba(17, 17, 17, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: #C8C8C8;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.chat-suggestion-btn:hover {
  border-color: #FB0079;
  background: rgba(251, 0, 121, 0.1);
  box-shadow: 0 4px 12px rgba(251, 0, 121, 0.15);
}

/* Bubbles */
.chat-bubble-wrap {
  display: flex;
  gap: 8px;
  max-width: 85%;
}

.chat-bubble-wrap.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.chat-bubble-wrap.assistant {
  align-self: flex-start;
}

.chat-bubble-avatar {
  width: 28px;
  height: 28px;
  border-radius: 999px;
  object-fit: cover;
  flex-shrink: 0;
  box-shadow: 0 0 8px rgba(251, 0, 121, 0.2);
}

.chat-bubble {
  padding: 10px 14px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.5;
  word-break: break-word;
}

.chat-bubble.user {
  background: linear-gradient(135deg, #FB0079 0%, #ff3d9a 100%);
  color: #FFFFFF;
  border-bottom-right-radius: 4px;
  box-shadow: 0 4px 12px rgba(251, 0, 121, 0.3);
}

.chat-bubble.assistant {
  background: rgba(34, 34, 34, 0.6);
  backdrop-filter: blur(10px);
  color: #C8C8C8;
  border-bottom-left-radius: 4px;
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.chat-bubble.loading {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 14px 18px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #FB0079;
  animation: dotPulse 1.4s infinite ease-in-out both;
  box-shadow: 0 0 6px rgba(251, 0, 121, 0.4);
}

.dot:nth-child(1) { animation-delay: -0.32s; }
.dot:nth-child(2) { animation-delay: -0.16s; }
.dot:nth-child(3) { animation-delay: 0s; }

@keyframes dotPulse {
  0%, 80%, 100% { opacity: 0.3; transform: scale(0.8); }
  40% { opacity: 1; transform: scale(1); }
}

/* Input */
.chat-input-area {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  background: rgba(0, 0, 0, 0.3);
  backdrop-filter: blur(10px);
  flex-shrink: 0;
}

.chat-input {
  flex: 1;
  height: 40px;
  padding: 0 14px;
  background: rgba(17, 17, 17, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  outline: none;
  transition: all 0.3s ease;
  backdrop-filter: blur(10px);
}

.chat-input:focus {
  border-color: #FB0079;
  box-shadow: 0 0 12px rgba(251, 0, 121, 0.2);
}

.chat-input::placeholder {
  color: #7A7C80;
}

.chat-send-btn {
  width: 40px;
  height: 40px;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #FB0079 0%, #ff3d9a 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  transition: all 0.3s ease;
  box-shadow: 0 4px 12px rgba(251, 0, 121, 0.3);
}

.chat-send-btn:disabled {
  background: rgba(51, 51, 51, 0.6);
  box-shadow: none;
  cursor: not-allowed;
}

.chat-send-btn:not(:disabled):hover {
  transform: scale(1.05);
  box-shadow: 0 6px 16px rgba(251, 0, 121, 0.4);
}

.chat-send-btn:not(:disabled):active {
  transform: scale(0.95);
}

/* Transition */
.sheet-enter-active,
.sheet-leave-active {
  transition: opacity 0.25s ease;
}

.sheet-enter-active .chat-sheet {
  transition: transform 0.25s ease, opacity 0.25s ease;
}

.sheet-leave-active .chat-sheet {
  transition: transform 0.2s ease, opacity 0.2s ease;
}

.sheet-enter-from {
  opacity: 0;
}

.sheet-enter-from .chat-sheet {
  transform: scale(0.95);
  opacity: 0;
}

.sheet-leave-to {
  opacity: 0;
}

.sheet-leave-to .chat-sheet {
  transform: scale(0.95);
  opacity: 0;
}
</style>
