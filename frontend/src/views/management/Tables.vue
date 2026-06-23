<template>
  <div class="tables-page">
    <!-- 头部统计 -->
    <div class="stats-row">
      <div class="stat-card">
        <span class="stat-value">{{ tables.length }}</span>
        <span class="stat-label">总桌数</span>
      </div>
      <div class="stat-card stat-card--active">
        <span class="stat-value stat-value--pink">{{ activeCount }}</span>
        <span class="stat-label">启用</span>
      </div>
      <div class="stat-card stat-card--inactive">
        <span class="stat-value stat-value--grey">{{ inactiveCount }}</span>
        <span class="stat-label">停用</span>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="section-header">
      <h3 class="section-title">桌位列表</h3>
      <button class="btn-add" @click="openCreate">
        <svg width="16" height="16" viewBox="0 0 16 16" fill="none">
          <path d="M8 2v12M2 8h12" stroke="#FB0079" stroke-width="2" stroke-linecap="round"/>
        </svg>
        新增桌位
      </button>
    </div>

    <!-- 桌位列表 -->
    <div v-if="tables.length === 0" class="empty-state">
      <p class="empty-text">暂无桌位数据，请先添加</p>
    </div>

    <!-- 按区域分组展示 -->
    <div v-for="[area, items] in groupedTables" :key="area" class="area-group">
      <div class="area-header">
        <span class="area-name">{{ area }}</span>
        <span class="area-count">{{ items.length }}桌</span>
      </div>
      <div class="table-grid">
        <div
          v-for="t in items"
          :key="t.id"
          class="table-tile"
          :class="{ 'table-tile--inactive': t.status === 'inactive' }"
          @click="openEdit(t)"
        >
          <span class="tile-no">{{ t.table_no }}</span>
          <span class="tile-cap">{{ t.capacity }}人</span>
          <span class="tile-status-dot" :class="t.status === 'active' ? 'dot-active' : 'dot-inactive'"></span>
        </div>
      </div>
    </div>

    <!-- 新增/编辑弹窗 -->
    <div v-if="showForm" class="modal-overlay" @click.self="closeForm">
      <div class="modal">
        <div class="modal-header">
          <span class="modal-title">{{ editing ? '编辑桌位' : '新增桌位' }}</span>
          <button class="modal-close" @click="closeForm">
            <svg width="18" height="18" viewBox="0 0 18 18" fill="none">
              <path d="M4 4l10 10M14 4l-10 10" stroke="#7A7C80" stroke-width="1.5" stroke-linecap="round"/>
            </svg>
          </button>
        </div>
        <div class="modal-body">
          <div class="form-group">
            <label class="form-label">区域分类 *</label>
            <select v-model="form.area" class="form-input">
              <option value="大桌">大桌</option>
              <option value="卡座">卡座</option>
              <option value="包间">包间</option>
              <option value="吧台">吧台</option>
              <option value="四人桌">四人桌</option>
              <option value="六人桌">六人桌</option>
              <option value="八人桌">八人桌</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">桌号 *</label>
            <input v-model="form.table_no" class="form-input" placeholder="如 1, A2, V1" />
          </div>
          <div class="form-group">
            <label class="form-label">容量</label>
            <input v-model.number="form.capacity" type="number" class="form-input" min="1" max="20" />
          </div>
          <div class="form-group" v-if="editing">
            <label class="form-label">状态</label>
            <select v-model="form.status" class="form-input">
              <option value="active">启用</option>
              <option value="inactive">停用</option>
            </select>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="editing" class="btn-delete" @click="handleDelete(editing.id); closeForm()">删除</button>
          <button class="btn-cancel" @click="closeForm">取消</button>
          <button class="btn-submit" @click="submitForm" :disabled="submitting">
            {{ editing ? '保存' : '添加' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { tableAPI } from '@/api/booking'
import type { TableItem } from '@/api/booking'

const tables = ref<TableItem[]>([])
const submitting = ref(false)
const showForm = ref(false)
const editing = ref<TableItem | null>(null)

const form = ref({
  area: '大桌',
  table_no: '',
  capacity: 8,
  status: 'active',
})

const activeCount = computed(() => tables.value.filter(t => t.status === 'active').length)
const inactiveCount = computed(() => tables.value.filter(t => t.status === 'inactive').length)

// 按区域分组
const areaOrder = ['大桌', '卡座', '包间', '吧台', '四人桌', '六人桌', '八人桌']
const groupedTables = computed(() => {
  const map = new Map<string, TableItem[]>()
  for (const t of tables.value) {
    if (!map.has(t.area)) map.set(t.area, [])
    map.get(t.area)!.push(t)
  }
  // 按预设顺序排列，未知区域排最后
  return Array.from(map.entries()).sort((a, b) => {
    const ia = areaOrder.indexOf(a[0])
    const ib = areaOrder.indexOf(b[0])
    return (ia === -1 ? 99 : ia) - (ib === -1 ? 99 : ib)
  })
})

async function loadTables() {
  try {
    const res = await tableAPI.list({ page_size: 200 })
    tables.value = res.data.data.items
  } catch {
    // ignore
  }
}

function openCreate() {
  editing.value = null
  form.value = { area: '大桌', table_no: '', capacity: 8, status: 'active' }
  showForm.value = true
}

function openEdit(table: TableItem) {
  editing.value = table
  form.value = {
    area: table.area,
    table_no: table.table_no,
    capacity: table.capacity,
    status: table.status,
  }
  showForm.value = true
}

function closeForm() {
  showForm.value = false
  editing.value = null
}

async function submitForm() {
  if (!form.value.table_no.trim()) {
    alert('请输入桌号')
    return
  }
  submitting.value = true
  try {
    if (editing.value) {
      await tableAPI.update(editing.value.id, {
        area: form.value.area,
        table_no: form.value.table_no,
        capacity: form.value.capacity,
        status: form.value.status,
      })
    } else {
      await tableAPI.create({
        area: form.value.area,
        table_no: form.value.table_no,
        capacity: form.value.capacity,
      })
    }
    closeForm()
    loadTables()
  } catch (e: any) {
    alert(e?.response?.data?.message || '操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(id: string) {
  if (!confirm('确认删除该桌位？')) return
  try {
    await tableAPI.delete(id)
    loadTables()
  } catch {
    alert('删除失败')
  }
}

onMounted(() => {
  loadTables()
})
</script>

<style scoped>
.tables-page {
  padding: 16px;
  min-height: 100vh;
  background: #000000;
}

/* Stats */
.stats-row {
  display: flex;
  gap: 8px;
  margin-bottom: 20px;
}
.stat-card {
  flex: 1;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 14px;
  text-align: center;
}
.stat-card--active {
  border-color: rgba(251, 0, 121, 0.5);
}
.stat-card--inactive {
  border-color: rgba(122, 124, 128, 0.5);
}
.stat-value {
  display: block;
  font-family: 'Poppins', sans-serif;
  font-size: 28px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}
.stat-value--pink {
  color: #FB0079;
}
.stat-value--grey {
  color: #7A7C80;
}
.stat-label {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 12px;
  color: #7A7C80;
}

/* Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.section-title {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  margin: 0;
}
.btn-add {
  display: flex;
  align-items: center;
  gap: 4px;
  background: transparent;
  border: none;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 13px;
  color: #FB0079;
  cursor: pointer;
  padding: 4px 8px;
}

/* Empty */
.empty-state {
  padding: 40px 0;
  text-align: center;
}
.empty-text {
  font-size: 13px;
  color: #7A7C80;
}

/* Table Grid */
.area-group {
  margin-bottom: 20px;
}
.area-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
  padding-left: 2px;
}
.area-name {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 13px;
  font-weight: 600;
  color: #FFFFFF;
}
.area-count {
  font-family: 'Poppins', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}
.table-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 8px;
}
.table-tile {
  position: relative;
  background: #111111;
  border: 1px solid #333333;
  border-radius: 10px;
  padding: 14px 8px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  transition: border-color 0.15s, transform 0.1s;
}
.table-tile:active {
  transform: scale(0.96);
}
.table-tile--inactive {
  opacity: 0.45;
}
.tile-no {
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FB0079;
}
.tile-cap {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 11px;
  color: #7A7C80;
}
.tile-status-dot {
  position: absolute;
  top: 8px;
  right: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
}
.dot-active {
  background: #FB0079;
}
.dot-inactive {
  background: #7A7C80;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0; left: 0; right: 0; bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 1000;
}
.modal {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 14px 14px 0 0;
  width: 100%;
  max-width: 450px;
  max-height: 85vh;
  overflow-y: auto;
}
.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px;
  border-bottom: 1px solid #222222;
}
.modal-title {
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 16px;
  font-weight: 600;
  color: #FFFFFF;
}
.modal-close {
  background: transparent;
  border: none;
  cursor: pointer;
  padding: 4px;
}
.modal-body {
  padding: 16px;
}
.modal-footer {
  display: flex;
  gap: 8px;
  padding: 16px;
  border-top: 1px solid #222222;
}

/* Form */
.form-group {
  margin-bottom: 14px;
}
.form-label {
  display: block;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 12px;
  color: #C8C8C8;
  margin-bottom: 6px;
}
.form-input {
  width: 100%;
  padding: 10px 12px;
  background: #000000;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: 'Poppins', 'Source Han Sans SC', sans-serif;
  font-size: 13px;
  color: #FFFFFF;
  outline: none;
  box-sizing: border-box;
}
.form-input:focus {
  border-color: #FB0079;
}
select.form-input {
  appearance: none;
}

/* Buttons */
.btn-cancel {
  flex: 1;
  padding: 12px;
  background: transparent;
  border: 1px solid #333333;
  border-radius: 8px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  color: #C8C8C8;
  cursor: pointer;
}
.btn-delete {
  flex: 0 0 auto;
  padding: 12px 16px;
  background: transparent;
  border: 1px solid rgba(251, 0, 121, 0.3);
  border-radius: 8px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  color: #FB0079;
  cursor: pointer;
}
.btn-submit {
  flex: 1;
  padding: 12px;
  background: #FB0079;
  border: none;
  border-radius: 8px;
  font-family: 'Source Han Sans SC', '思源黑体', sans-serif;
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  cursor: pointer;
}
.btn-submit:disabled {
  background: #333333;
  color: #7A7C80;
  cursor: not-allowed;
}
</style>
