<template>
  <div class="template-editor">
    <!-- 头部：模板名 + 展开/收起 -->
    <div class="editor-header" @click="expanded = !expanded">
      <div class="header-left">
        <span class="toggle-icon">{{ expanded ? '▼' : '▶' }}</span>
        <span class="tpl-name">{{ template.name }}</span>
        <span class="role-badge">{{ roleLabel }}</span>
      </div>
      <div class="header-right">
        <span class="item-count">{{ editItems.length }} 项</span>
      </div>
    </div>

    <!-- 展开内容 -->
    <div v-if="expanded" class="editor-body">
      <!-- 模板信息编辑 -->
      <div class="meta-row">
        <input
          v-model="localName"
          placeholder="检查单名称"
          class="meta-input"
          @blur="$emit('update', template.id, { name: localName })"
        />
        <select
          v-model="localRole"
          class="meta-select"
          @change="$emit('update', template.id, { role_tag: localRole })"
        >
          <option value="store_manager">店长</option>
          <option value="bartender">吧台长</option>
          <option value="server">服务员</option>
          <option value="all">所有人</option>
        </select>
      </div>

      <!-- 检查项列表 -->
      <div class="items-list">
        <div v-for="(item, idx) in editItems" :key="idx" class="item-row">
          <span class="item-index">{{ idx + 1 }}</span>
          <div class="item-main">
            <input
              v-model="item.item_name"
              placeholder="检查项名称"
              class="item-input"
            />
            <div class="type-toggle">
              <button
                :class="{ active: item.item_type === 'checkbox' }"
                @click="item.item_type = 'checkbox'"
              >打勾</button>
              <button
                :class="{ active: item.item_type === 'photo' }"
                @click="item.item_type = 'photo'"
              >拍照</button>
            </div>
            <input
              v-if="item.item_type === 'photo'"
              v-model="item.ai_prompt"
              placeholder="AI 判定标准（可选，如：酒水摆放整齐、标签朝外）"
              class="ai-prompt-input"
              maxlength="200"
            />
            <span v-if="item.item_type === 'photo'" class="ai-hint">
              留空则使用默认判定，填写后 AI 按此标准判断照片
            </span>
          </div>
          <button class="btn-del" @click="removeItem(idx)">×</button>
        </div>
      </div>

      <!-- 添加检查项 -->
      <button class="btn-add-item" @click="addItem">+ 添加检查项</button>

      <!-- 底部操作 -->
      <div class="footer-actions">
        <button class="btn-action btn-delete" @click="$emit('delete', template.id)">删除检查单</button>
        <button class="btn-action btn-save" @click="save">保存</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { ChecklistTemplate } from '@/api/butler'

const props = defineProps<{ template: ChecklistTemplate }>()
const emit = defineEmits<{
  (e: 'save', templateId: string, items: { item_name: string; item_type: string; sort_order?: number; ai_prompt?: string | null }[]): void
  (e: 'delete', id: string): void
  (e: 'update', id: string, data: Record<string, any>): void
}>()

const expanded = ref(false)
const localName = ref(props.template.name)
const localRole = ref(props.template.role_tag)

const editItems = ref(
  (props.template.items || []).map(i => ({
    item_name: i.item_name,
    item_type: i.item_type,
    ai_prompt: i.ai_prompt || '',
  }))
)

// 当模板切换时同步（按 id 判断，避免同一模板更新时重置用户输入）
watch(() => props.template.id, (newId, oldId) => {
  if (newId !== oldId) {
    localName.value = props.template.name
    localRole.value = props.template.role_tag
    editItems.value = (props.template.items || []).map(i => ({
      item_name: i.item_name,
      item_type: i.item_type,
      ai_prompt: i.ai_prompt || '',
    }))
  }
})

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    store_manager: '店长',
    bartender: '吧台长',
    server: '服务员',
    all: '所有人',
  }
  return map[props.template.role_tag] || props.template.role_tag
})

function addItem() {
  editItems.value.push({ item_name: '', item_type: 'checkbox', ai_prompt: '' })
}

function removeItem(idx: number) {
  editItems.value.splice(idx, 1)
}

function save() {
  // 过滤空名称
  const validItems = editItems.value
    .filter(i => i.item_name.trim())
    .map((i, idx) => ({
      item_name: i.item_name.trim(),
      item_type: i.item_type,
      sort_order: idx,
      ai_prompt: i.item_type === 'photo' ? (i.ai_prompt?.trim() || null) : null,
    }))
  emit('save', props.template.id, validItems)
}
</script>

<style scoped>
.template-editor {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  overflow: hidden;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  cursor: pointer;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.toggle-icon {
  font-size: 10px;
  color: #7A7C80;
}

.tpl-name {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
}

.role-badge {
  padding: 2px 6px;
  background: rgba(251, 0, 121, 0.1);
  color: #FB0079;
  border-radius: 4px;
  font-size: 11px;
}

.item-count {
  font-size: 12px;
  color: #7A7C80;
}

.editor-body {
  padding: 0 16px 16px;
  border-top: 1px solid #1F1F1F;
}

.meta-row {
  display: flex;
  gap: 8px;
  margin: 12px 0;
}

.meta-input, .meta-select {
  padding: 8px 10px;
  background: #1A1A1A;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #FFFFFF;
  font-size: 13px;
  font-family: inherit;
}

.meta-input { flex: 1; }
.meta-select { width: 100px; }

.items-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-bottom: 10px;
}

.item-row {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px 0;
  border-bottom: 1px solid #1a1a1a;
}

.item-row:last-child {
  border-bottom: none;
}

.item-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.item-index {
  width: 20px;
  text-align: center;
  font-size: 12px;
  color: #7A7C80;
  flex-shrink: 0;
  margin-top: 8px;
}

.item-input {
  flex: 1;
  padding: 6px 10px;
  background: #1A1A1A;
  border: 1px solid #333333;
  border-radius: 6px;
  color: #FFFFFF;
  font-size: 13px;
  font-family: inherit;
  min-width: 0;
}

.ai-prompt-input {
  width: 100%;
  padding: 6px 10px;
  background: rgba(251, 0, 121, 0.05);
  border: 1px dashed #5a2a3a;
  border-radius: 6px;
  color: #FFFFFF;
  font-size: 12px;
  font-family: inherit;
  box-sizing: border-box;
}

.ai-prompt-input::placeholder {
  color: #7A7C80;
}

.ai-prompt-input:focus {
  border-color: #FB0079;
  border-style: solid;
  outline: none;
}

.ai-hint {
  font-size: 11px;
  color: #7A7C80;
  padding-left: 4px;
}

.type-toggle {
  display: flex;
  background: #1A1A1A;
  border: 1px solid #333333;
  border-radius: 6px;
  overflow: hidden;
  flex-shrink: 0;
}

.type-toggle button {
  padding: 4px 10px;
  background: none;
  border: none;
  color: #7A7C80;
  font-size: 12px;
  cursor: pointer;
  font-family: inherit;
}

.type-toggle button.active {
  background: #FB0079;
  color: #FFFFFF;
}

.btn-del {
  width: 24px;
  height: 24px;
  background: none;
  border: 1px solid #444;
  border-radius: 50%;
  color: #FF5252;
  font-size: 16px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0;
  flex-shrink: 0;
  line-height: 1;
}

.btn-add-item {
  width: 100%;
  padding: 8px;
  background: rgba(251, 0, 121, 0.05);
  border: 1px dashed #444;
  color: #FB0079;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  font-family: inherit;
}

.footer-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  justify-content: flex-end;
}

.btn-action {
  padding: 8px 16px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  font-family: inherit;
}

.btn-delete {
  background: none;
  border: 1px solid #FF5252;
  color: #FF5252;
}

.btn-save {
  background: #FB0079;
  color: #FFFFFF;
}
</style>
