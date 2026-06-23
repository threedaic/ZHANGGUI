<template>
  <div class="butler-setting-page">
    <div class="page-header">
      <h1 class="page-title">检查单配置</h1>
    </div>

    <!-- 新建模板按钮 -->
    <button class="btn-new-template" @click="showNewTemplateForm = !showNewTemplateForm">
      + 新建检查单
    </button>

    <!-- 新建模板表单 -->
    <div v-if="showNewTemplateForm" class="new-template-form">
      <input
        v-model="newTemplate.name"
        placeholder="检查单名称（如：店长闭店检查单）"
        class="form-input"
      />
      <div class="form-row">
        <label class="form-label">类型</label>
        <div class="radio-group">
          <label><input type="radio" v-model="newTemplate.session_type" value="opening" /> 开店</label>
          <label><input type="radio" v-model="newTemplate.session_type" value="closing" /> 闭店</label>
        </div>
      </div>
      <div class="form-row">
        <label class="form-label">角色</label>
        <select v-model="newTemplate.role_tag" class="form-select">
          <option value="store_manager">店长</option>
          <option value="bartender">吧台长</option>
          <option value="server">服务员</option>
          <option value="all">所有人</option>
        </select>
      </div>
      <button class="btn-save" @click="createTemplate" :disabled="!newTemplate.name.trim()">创建</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <!-- 闭店模板组 -->
    <div v-else class="template-section">
      <h3 class="section-title">闭店检查单</h3>
      <div v-if="closingTemplates.length === 0" class="empty">暂无闭店检查单，点击上方"新建检查单"创建</div>
      <div v-for="tpl in closingTemplates" :key="tpl.id" class="template-card">
        <TemplateEditor
          :template="tpl"
          @save="saveItems"
          @delete="deleteTemplate"
          @update="updateTemplate"
        />
      </div>

      <h3 class="section-title" style="margin-top: 24px;">开店检查单</h3>
      <div v-if="openingTemplates.length === 0" class="empty">暂无开店检查单，点击上方"新建检查单"创建</div>
      <div v-for="tpl in openingTemplates" :key="tpl.id" class="template-card">
        <TemplateEditor
          :template="tpl"
          @save="saveItems"
          @delete="deleteTemplate"
          @update="updateTemplate"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listTemplates, createTemplateAPI, batchUpdateItems, deleteTemplateAPI, updateTemplateAPI } from '@/api/butler'
import TemplateEditor from './ButlerTemplateEditor.vue'
import type { ChecklistTemplate } from '@/api/butler'

const loading = ref(false)
const showNewTemplateForm = ref(false)
const templates = ref<ChecklistTemplate[]>([])

const newTemplate = ref({
  name: '',
  session_type: 'closing' as 'opening' | 'closing',
  role_tag: 'store_manager',
})

const closingTemplates = computed(() => templates.value.filter(t => t.session_type === 'closing'))
const openingTemplates = computed(() => templates.value.filter(t => t.session_type === 'opening'))

onMounted(() => {
  loadTemplates()
})

async function loadTemplates() {
  loading.value = true
  try {
    const res: any = await listTemplates()
    templates.value = res.data?.data || res.data || []
  } catch (e) {
    console.error(e)
  } finally {
    loading.value = false
  }
}

async function createTemplate() {
  if (!newTemplate.value.name.trim()) return
  try {
    await createTemplateAPI({
      name: newTemplate.value.name.trim(),
      session_type: newTemplate.value.session_type,
      role_tag: newTemplate.value.role_tag,
    })
    newTemplate.value = { name: '', session_type: 'closing', role_tag: 'store_manager' }
    showNewTemplateForm.value = false
    await loadTemplates()
  } catch (e: any) {
    alert(e?.response?.data?.message || '创建失败')
  }
}

async function saveItems(templateId: string, items: { item_name: string; item_type: string; sort_order?: number; ai_prompt?: string | null }[]) {
  try {
    await batchUpdateItems(templateId, items)
    // 本地更新对应模板的 items，避免全量重载导致展开状态丢失
    const tpl = templates.value.find(t => t.id === templateId)
    if (tpl) {
      tpl.items = items.map((i, idx) => ({
        id: String(idx),
        template_id: templateId,
        item_name: i.item_name,
        item_type: i.item_type as 'checkbox' | 'photo',
        required_photo: i.item_type === 'photo',
        sort_order: i.sort_order ?? idx,
        ai_prompt: i.ai_prompt ?? null,
      }))
    }
    alert('保存成功')
  } catch (e: any) {
    alert(e?.response?.data?.message || '保存失败')
  }
}

async function deleteTemplate(id: string) {
  if (!confirm('确定删除该检查单？')) return
  try {
    await deleteTemplateAPI(id)
    templates.value = templates.value.filter(t => t.id !== id)
  } catch (e: any) {
    alert(e?.response?.data?.message || '删除失败')
  }
}

async function updateTemplate(id: string, data: Record<string, any>) {
  try {
    await updateTemplateAPI(id, data)
    // 本地更新对应模板，不触发全量重载（避免展开状态丢失和输入丢失）
    const tpl = templates.value.find(t => t.id === id)
    if (tpl) {
      Object.assign(tpl, data)
    }
  } catch (e: any) {
    alert(e?.response?.data?.message || '更新失败')
  }
}
</script>

<style scoped>
.butler-setting-page {
  padding: 16px;
  padding-bottom: calc(64px + 24px);
  max-width: 640px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 4px;
}

.page-title {
  font-family: "Source Han Sans SC", sans-serif;
  font-size: 20px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.page-tip {
  font-size: 12px;
  color: #7A7C80;
  margin: 0 0 20px;
}

/* 配置说明卡片 */
.guide-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 16px;
}

.guide-title {
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 12px;
}

.guide-item {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 6px 0;
}

.guide-item + .guide-item {
  border-top: 1px solid #1a1a1a;
  margin-top: 4px;
  padding-top: 10px;
}

.guide-num {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 20px;
  height: 20px;
  background: rgba(251, 0, 121, 0.1);
  color: #FB0079;
  border-radius: 50%;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  margin-top: 2px;
}

.guide-name {
  font-size: 13px;
  font-weight: 600;
  color: #C8C8C8;
  margin-bottom: 2px;
}

.guide-desc {
  font-size: 11px;
  color: #7A7C80;
  line-height: 1.5;
}

.btn-new-template {
  width: 100%;
  padding: 12px;
  background: rgba(251, 0, 121, 0.08);
  border: 1px dashed #FB0079;
  color: #FB0079;
  border-radius: 10px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  margin-bottom: 12px;
}

.new-template-form {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.form-input, .form-select {
  width: 100%;
  padding: 10px 12px;
  background: #1A1A1A;
  border: 1px solid #333333;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  font-family: inherit;
  box-sizing: border-box;
}

.form-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.form-label {
  font-size: 13px;
  color: #7A7C80;
  width: 40px;
  flex-shrink: 0;
}

.radio-group {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: #C8C8C8;
}

.radio-group input, .form-row input[type="radio"] {
  margin-right: 4px;
}

.btn-save {
  padding: 10px 16px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #FFFFFF;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.btn-save:disabled {
  background: #553344;
  cursor: not-allowed;
}

.section-title {
  font-size: 15px;
  color: #C8C8C8;
  margin: 16px 0 10px;
  font-weight: 600;
}

.template-card {
  margin-bottom: 12px;
}

.loading, .empty {
  text-align: center;
  padding: 24px;
  color: #7A7C80;
  font-size: 13px;
}
</style>
