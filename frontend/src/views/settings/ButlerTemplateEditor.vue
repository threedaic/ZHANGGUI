<template>
  <div class="template-editor">
    <!-- 头部 -->
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
      <!-- 模板信息 -->
      <div class="meta-row">
        <input v-model="localName" placeholder="检查单名称" class="meta-input" @blur="$emit('update', template.id, { name: localName })" />
        <select v-model="localRole" class="meta-select" @change="$emit('update', template.id, { role_tag: localRole })">
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
            <input v-model="item.item_name" placeholder="检查项名称" class="item-input" />
            <div class="type-toggle">
              <button :class="{ active: item.item_type === 'checkbox' }" @click="item.item_type = 'checkbox'">打勾</button>
              <button :class="{ active: item.item_type === 'photo' }" @click="item.item_type = 'photo'">拍照</button>
            </div>

            <!-- 拍照项：维度选择器 -->
            <div v-if="item.item_type === 'photo'" class="dimension-section">
              <div class="dim-label">AI 检查维度（可多选）</div>
              <div class="dim-chips">
                <button
                  v-for="dim in DIMENSIONS"
                  :key="dim.id"
                  class="dim-chip"
                  :class="{ active: item.selected_dims?.includes(dim.id) }"
                  @click="toggleDim(item, dim.id)"
                >{{ dim.label }}</button>
              </div>
              <!-- 自定义补充 -->
              <input
                v-model="item.custom_prompt"
                placeholder="补充其他要求（可选）"
                class="custom-prompt-input"
                maxlength="200"
              />
              <!-- 预览生成的提示词 -->
              <div v-if="getPromptPreview(item)" class="prompt-preview">
                <span class="preview-label">AI 判定标准：</span>
                <span class="preview-text">{{ getPromptPreview(item) }}</span>
              </div>
            </div>
          </div>
          <button class="btn-del" @click="removeItem(idx)">×</button>
        </div>
      </div>

      <!-- 快速添加预设检查项 -->
      <div class="quick-add">
        <div class="quick-label">快速添加：</div>
        <div class="quick-chips">
          <button
            v-for="preset in QUICK_PRESETS[template.session_type] || []"
            :key="preset.name"
            class="quick-chip"
            @click="addPresetItem(preset)"
          >+ {{ preset.name }}</button>
        </div>
      </div>

      <button class="btn-add-item" @click="addItem">+ 自定义检查项</button>

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

// ========== 酒吧检查维度库（预设 AI 提示词）==========
const DIMENSIONS = [
  { id: 'clean', label: '干净', prompt: '表面干净无灰尘、无污渍' },
  { id: 'tidy', label: '整齐', prompt: '物品摆放整齐有序' },
  { id: 'label', label: '标签朝外', prompt: '酒水标签统一朝外展示' },
  { id: 'no_water', label: '无水渍', prompt: '台面无水渍、无液体残留' },
  { id: 'no_trash', label: '无垃圾', prompt: '无垃圾、无杂物残留' },
  { id: 'no odor', label: '无异味', prompt: '无明显异味（通过环境判断）' },
  { id: 'dry', label: '已晾干', prompt: '物品已晾干，无积水' },
  { id: 'closed', label: '已关闭', prompt: '设备/门窗已完全关闭或锁好' },
  { id: 'empty', label: '已清空', prompt: '容器/垃圾桶已清空并更换' },
  { id: 'full_view', label: '全景照', prompt: '拍摄角度应覆盖整个区域，能看清整体状况' },
  { id: 'date_marked', label: '日期标注', prompt: '新开封物品已标注日期' },
  { id: 'positioned', label: '归位', prompt: '椅子/物品已归位摆放' },
]

// ========== 快速添加预设 ==========
const QUICK_PRESETS: Record<string, { name: string; type: string; dims: string[] }[]> = {
  closing: [
    { name: '锁门设防', type: 'photo', dims: ['closed', 'full_view'] },
    { name: '收银交接', type: 'checkbox', dims: [] },
    { name: '清洁吧台', type: 'photo', dims: ['clean', 'no_water', 'tidy'] },
    { name: '杯具清洗', type: 'photo', dims: ['clean', 'dry'] },
    { name: '清倒垃圾', type: 'photo', dims: ['empty', 'no_trash'] },
    { name: '地面清洁', type: 'photo', dims: ['clean', 'no_water', 'no_trash'] },
    { name: '酒水归位', type: 'photo', dims: ['tidy', 'label'] },
    { name: '桌椅归位', type: 'photo', dims: ['positioned', 'tidy'] },
    { name: '设备断电', type: 'photo', dims: ['closed'] },
    { name: '大厅全景', type: 'photo', dims: ['full_view'] },
  ],
  opening: [
    { name: '门面检查', type: 'photo', dims: ['full_view', 'clean'] },
    { name: '开启灯光', type: 'photo', dims: ['closed'] },
    { name: '开启音响', type: 'checkbox', dims: [] },
    { name: 'POS机检查', type: 'photo', dims: ['closed'] },
    { name: '吧台准备', type: 'photo', dims: ['clean', 'tidy', 'no_water'] },
    { name: '冰机检查', type: 'photo', dims: ['clean'] },
    { name: '酒水盘点', type: 'photo', dims: ['tidy', 'label'] },
    { name: '卫生间检查', type: 'photo', dims: ['clean', 'no_trash', 'no_water'] },
  ],
}

function dimsToPrompt(dims: string[], custom: string): string {
  const parts = DIMENSIONS.filter(d => dims.includes(d.id)).map(d => d.prompt)
  if (custom?.trim()) parts.push(custom.trim())
  return parts.join('；') || ''
}

function getPromptPreview(item: any): string {
  return dimsToPrompt(item.selected_dims || [], item.custom_prompt || '')
}

function toggleDim(item: any, dimId: string) {
  if (!item.selected_dims) item.selected_dims = []
  const idx = item.selected_dims.indexOf(dimId)
  if (idx >= 0) item.selected_dims.splice(idx, 1)
  else item.selected_dims.push(dimId)
}

function addPresetItem(preset: { name: string; type: string; dims: string[] }) {
  editItems.value.push({
    item_name: preset.name,
    item_type: preset.type,
    selected_dims: [...preset.dims],
    custom_prompt: '',
    ai_prompt: '',
  })
}

// ========== 组件逻辑 ==========
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
    selected_dims: [] as string[],
    custom_prompt: '',
    ai_prompt: i.ai_prompt || '',
  }))
)

watch(() => props.template.id, (newId, oldId) => {
  if (newId !== oldId) {
    localName.value = props.template.name
    localRole.value = props.template.role_tag
    editItems.value = (props.template.items || []).map(i => ({
      item_name: i.item_name,
      item_type: i.item_type,
      selected_dims: [] as string[],
      custom_prompt: '',
      ai_prompt: i.ai_prompt || '',
    }))
  }
})

const roleLabel = computed(() => {
  const map: Record<string, string> = {
    store_manager: '店长', bartender: '吧台长', server: '服务员', all: '所有人',
  }
  return map[props.template.role_tag] || props.template.role_tag
})

function addItem() {
  editItems.value.push({ item_name: '', item_type: 'checkbox', selected_dims: [], custom_prompt: '', ai_prompt: '' })
}

function removeItem(idx: number) {
  editItems.value.splice(idx, 1)
}

function save() {
  const validItems = editItems.value
    .filter(i => i.item_name.trim())
    .map((i, idx) => ({
      item_name: i.item_name.trim(),
      item_type: i.item_type,
      sort_order: idx,
      ai_prompt: i.item_type === 'photo' ? dimsToPrompt(i.selected_dims || [], i.custom_prompt || '') || null : null,
    }))
  emit('save', props.template.id, validItems)
}
</script>

<style scoped>
.template-editor {
  background: #111;
  border: 1px solid #333;
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

.header-left { display: flex; align-items: center; gap: 8px; }
.toggle-icon { font-size: 10px; color: #7A7C80; }
.tpl-name { font-size: 15px; font-weight: 600; color: #fff; }
.role-badge { padding: 2px 6px; background: rgba(251,0,121,0.1); color: #FB0079; border-radius: 4px; font-size: 11px; }
.item-count { font-size: 12px; color: #7A7C80; }

.editor-body { padding: 0 16px 16px; border-top: 1px solid #1f1f1f; }

.meta-row { display: flex; gap: 8px; margin: 12px 0; }
.meta-input, .meta-select {
  padding: 8px 10px; background: #1a1a1a; border: 1px solid #333;
  border-radius: 6px; color: #fff; font-size: 13px;
}
.meta-input { flex: 1; }
.meta-select { width: 100px; }

.items-list { display: flex; flex-direction: column; gap: 8px; margin-bottom: 10px; }

.item-row {
  display: flex; align-items: flex-start; gap: 6px;
  padding: 10px 0; border-bottom: 1px solid #1a1a1a;
}
.item-row:last-child { border-bottom: none; }

.item-index { width: 20px; text-align: center; font-size: 12px; color: #7A7C80; flex-shrink: 0; margin-top: 8px; }

.item-main { flex: 1; display: flex; flex-direction: column; gap: 6px; min-width: 0; }

.item-input {
  width: 100%; padding: 8px 10px; background: #000;
  border: 1px solid #333; border-radius: 6px; color: #fff;
  font-size: 13px; box-sizing: border-box;
}
.item-input:focus { border-color: #FB0079; }

.type-toggle { display: flex; gap: 4px; }
.type-toggle button {
  padding: 4px 12px; border: 1px solid #333; border-radius: 4px;
  background: #1a1a1a; color: #7A7C80; font-size: 11px; cursor: pointer;
}
.type-toggle button.active { background: #FB0079; color: #fff; border-color: #FB0079; }

/* 维度选择 */
.dimension-section {
  background: #0d0d0d; border: 1px solid #222; border-radius: 8px; padding: 10px;
}

.dim-label { font-size: 11px; color: #7A7C80; margin-bottom: 6px; }

.dim-chips { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }

.dim-chip {
  padding: 4px 10px; border: 1px solid #333; border-radius: 12px;
  background: #1a1a1a; color: #7A7C80; font-size: 11px; cursor: pointer;
  transition: all 0.15s;
}
.dim-chip.active { background: rgba(251,0,121,0.15); color: #FB0079; border-color: #FB0079; }

.custom-prompt-input {
  width: 100%; padding: 6px 10px; background: #000;
  border: 1px solid #333; border-radius: 6px; color: #fff;
  font-size: 12px; box-sizing: border-box; margin-bottom: 6px;
}
.custom-prompt-input::placeholder { color: #555; }

.prompt-preview {
  font-size: 11px; color: #555; line-height: 1.5;
  padding: 6px 8px; background: rgba(251,0,121,0.04); border-radius: 4px;
}
.preview-label { color: #FB0079; font-weight: 600; }

/* 快速添加 */
.quick-add { margin: 12px 0 8px; }
.quick-label { font-size: 11px; color: #7A7C80; margin-bottom: 6px; }
.quick-chips { display: flex; flex-wrap: wrap; gap: 4px; }
.quick-chip {
  padding: 5px 10px; border: 1px dashed #444; border-radius: 12px;
  background: transparent; color: #999; font-size: 11px; cursor: pointer;
}
.quick-chip:active { border-color: #FB0079; color: #FB0079; }

.btn-add-item {
  width: 100%; padding: 8px; border: 1px dashed #444; border-radius: 8px;
  background: transparent; color: #7A7C80; font-size: 13px; cursor: pointer;
  margin-bottom: 12px;
}

.btn-del {
  width: 28px; height: 28px; border: none; border-radius: 50%;
  background: rgba(255,59,48,0.1); color: #FF3B30; font-size: 16px;
  cursor: pointer; flex-shrink: 0; margin-top: 4px;
}

.footer-actions { display: flex; gap: 8px; }
.btn-action {
  flex: 1; height: 38px; border: none; border-radius: 8px;
  font-size: 13px; font-weight: 600; cursor: pointer;
}
.btn-delete { background: rgba(255,59,48,0.1); color: #FF3B30; border: 1px solid rgba(255,59,48,0.2); }
.btn-save { background: #FB0079; color: #fff; }
</style>
