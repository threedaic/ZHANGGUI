<template>
  <div class="config-page">
    <!-- 标题 -->
    <div class="page-head">
      <h1>检查单配置</h1>
      <p>设置检查项，员工拍照后 AI 按标准自动判定</p>
    </div>

    <!-- 闭店/开店 切换 -->
    <div class="seg-bar">
      <button :class="{ on: tab === 'closing' }" @click="tab = 'closing'">
        闭店检查<span class="seg-num">{{ closingTemplates.length }}</span>
      </button>
      <button :class="{ on: tab === 'opening' }" @click="tab = 'opening'">
        开店检查<span class="seg-num">{{ openingTemplates.length }}</span>
      </button>
    </div>

    <!-- 新建 -->
    <button v-if="!showNew" class="add-btn" @click="showNew = true">
      <svg width="16" height="16" viewBox="0 0 16 16" fill="none" stroke="currentColor" stroke-width="1.5"><path d="M8 3v10M3 8h10"/></svg>
      新建检查单
    </button>
    <div v-else class="add-panel">
      <input v-model="newTpl.name" placeholder="名称，如：吧台闭店检查单" class="add-input" />
      <div class="add-meta">
        <select v-model="newTpl.role_tag" class="add-sel">
          <option value="store_manager">店长</option>
          <option value="bartender">吧台长</option>
          <option value="server">服务员</option>
          <option value="all">所有人</option>
        </select>
        <button class="btn-ok" :disabled="!newTpl.name.trim()" @click="createTpl">创建</button>
        <button class="btn-no" @click="showNew = false">取消</button>
      </div>
    </div>

    <!-- 状态 -->
    <div v-if="loading" class="center-hint">加载中...</div>
    <div v-else-if="curList.length === 0" class="empty-box">
      <svg width="36" height="36" viewBox="0 0 36 36" fill="none" stroke="#2a2a2a" stroke-width="1.5"><rect x="7" y="9" width="22" height="20" rx="3"/><path d="M12 9V5M24 9V5M7 16h22"/></svg>
      <span>{{ tab === 'closing' ? '闭店' : '开店' }}检查单为空</span>
      <small>点击上方按钮创建</small>
    </div>

    <!-- 模板列表 -->
    <div v-else class="tpl-stack">
      <TemplateEditor v-for="tpl in curList" :key="tpl.id" :template="tpl" @save="saveItems" @delete="delTpl" @update="updTpl" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listTemplates, createTemplateAPI, batchUpdateItems, deleteTemplateAPI, updateTemplateAPI } from '@/api/butler'
import TemplateEditor from './ButlerTemplateEditor.vue'
import type { ChecklistTemplate } from '@/api/butler'

const loading = ref(false)
const showNew = ref(false)
const tab = ref<'closing' | 'opening'>('closing')
const templates = ref<ChecklistTemplate[]>([])
const newTpl = ref({ name: '', role_tag: 'store_manager' })

const closingTemplates = computed(() => templates.value.filter(t => t.session_type === 'closing'))
const openingTemplates = computed(() => templates.value.filter(t => t.session_type === 'opening'))
const curList = computed(() => tab.value === 'closing' ? closingTemplates.value : openingTemplates.value)

onMounted(() => load())

async function load() {
  loading.value = true
  try {
    const res: any = await listTemplates()
    templates.value = res.data?.data || res.data || []
  } catch {} finally { loading.value = false }
}

async function createTpl() {
  if (!newTpl.value.name.trim()) return
  try {
    await createTemplateAPI({ name: newTpl.value.name.trim(), session_type: tab.value, role_tag: newTpl.value.role_tag })
    newTpl.value = { name: '', role_tag: 'store_manager' }
    showNew.value = false
    await load()
  } catch (e: any) { alert(e?.response?.data?.message || '创建失败') }
}

async function saveItems(id: string, items: { item_name: string; item_type: string; sort_order?: number; ai_prompt?: string | null }[]) {
  try {
    await batchUpdateItems(id, items)
    const tpl = templates.value.find(t => t.id === id)
    if (tpl) tpl.items = items.map((i, idx) => ({ id: String(idx), template_id: id, item_name: i.item_name, item_type: i.item_type as any, required_photo: i.item_type === 'photo', sort_order: i.sort_order ?? idx, ai_prompt: i.ai_prompt ?? null }))
  } catch (e: any) { alert(e?.response?.data?.message || '保存失败') }
}

async function delTpl(id: string) {
  if (!confirm('删除该检查单？')) return
  try { await deleteTemplateAPI(id); templates.value = templates.value.filter(t => t.id !== id) }
  catch (e: any) { alert(e?.response?.data?.message || '删除失败') }
}

async function updTpl(id: string, data: Record<string, any>) {
  try { await updateTemplateAPI(id, data); const tpl = templates.value.find(t => t.id === id); if (tpl) Object.assign(tpl, data) }
  catch (e: any) { alert(e?.response?.data?.message || '更新失败') }
}
</script>

<style scoped>
.config-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 20px 16px calc(64px + 20px);
}

/* 标题 */
.page-head {
  margin-bottom: 20px;
}
.page-head h1 {
  font-size: 22px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 4px;
}
.page-head p {
  font-size: 13px;
  color: #555;
  margin: 0;
}

/* 分段切换 */
.seg-bar {
  display: flex;
  background: #0f0f0f;
  border-radius: 10px;
  padding: 3px;
  margin-bottom: 16px;
}
.seg-bar button {
  flex: 1;
  padding: 9px 0;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: #666;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.25s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.seg-bar button.on {
  background: #FB0079;
  color: #fff;
  box-shadow: 0 2px 8px rgba(251, 0, 121, 0.25);
}
.seg-num {
  font-size: 11px;
  min-width: 18px;
  height: 18px;
  line-height: 18px;
  text-align: center;
  border-radius: 9px;
  background: rgba(255, 255, 255, 0.08);
}
.seg-bar button.on .seg-num {
  background: rgba(255, 255, 255, 0.2);
}

/* 新建按钮 */
.add-btn {
  width: 100%;
  height: 44px;
  border: 1px dashed #333;
  border-radius: 10px;
  background: transparent;
  color: #666;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  cursor: pointer;
  transition: all 0.2s;
  margin-bottom: 16px;
}
.add-btn:active {
  border-color: #FB0079;
  color: #FB0079;
}

/* 新建面板 */
.add-panel {
  background: #0f0f0f;
  border: 1px solid #222;
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.add-input {
  width: 100%;
  height: 40px;
  padding: 0 14px;
  background: #000;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #fff;
  font-size: 14px;
  box-sizing: border-box;
  outline: none;
  transition: border-color 0.2s;
}
.add-input:focus { border-color: #FB0079; }
.add-input::placeholder { color: #444; }

.add-meta {
  display: flex;
  gap: 8px;
  align-items: center;
}
.add-sel {
  flex: 1;
  height: 36px;
  padding: 0 10px;
  background: #000;
  border: 1px solid #2a2a2a;
  border-radius: 8px;
  color: #ccc;
  font-size: 13px;
  outline: none;
}
.btn-ok {
  height: 36px;
  padding: 0 18px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  color: #fff;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
}
.btn-ok:disabled { opacity: 0.35; }
.btn-no {
  height: 36px;
  padding: 0 14px;
  background: transparent;
  border: 1px solid #333;
  border-radius: 8px;
  color: #666;
  font-size: 13px;
  cursor: pointer;
}

/* 状态 */
.center-hint {
  text-align: center;
  padding: 60px 0;
  color: #444;
  font-size: 14px;
}

.empty-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 56px 20px;
  text-align: center;
}
.empty-box span {
  font-size: 15px;
  color: #888;
  margin-top: 8px;
}
.empty-box small {
  font-size: 12px;
  color: #444;
}

/* 列表 */
.tpl-stack {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
</style>
