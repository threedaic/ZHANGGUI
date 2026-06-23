<template>
  <div class="shift-setting-panel">
    <div class="panel-header">
      <h3>班次设置</h3>
      <button class="close-btn" @click="$emit('saved')">完成</button>
    </div>

    <div class="shift-list">
      <div v-for="(item, index) in list" :key="index" class="shift-item">
        <div class="field-row">
          <label>名称</label>
          <input v-model="item.shift_name" type="text" placeholder="如：白班" />
        </div>
        <div class="field-row">
          <label>代码</label>
          <input v-model="item.shift_code" type="text" placeholder="如：day" />
        </div>
        <div class="field-row">
          <label>上班时间</label>
          <input v-model="item.start_time" type="text" placeholder="12:00" />
        </div>
        <div class="field-row">
          <label>下班时间</label>
          <input v-model="item.end_time" type="text" placeholder="20:00" />
        </div>
        <div class="field-row">
          <label>颜色</label>
          <input v-model="item.color" type="color" />
        </div>
        <div class="field-row inline">
          <label>
            <input v-model="item.is_overnight" type="checkbox" />
            跨天
          </label>
          <label>
            <input v-model="item.is_active" type="checkbox" />
            启用
          </label>
        </div>
        <button class="remove-btn" @click="removeShift(index)">删除</button>
      </div>
    </div>

    <button class="add-btn" @click="addShift">+ 添加班次</button>
    <button class="save-btn" :disabled="saving" @click="handleSave">保存</button>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { attendanceAPI, type ShiftConfig } from '@/api/attendance'

const emit = defineEmits(['saved'])

const list = ref<Partial<ShiftConfig>[]>([])
const saving = ref(false)

function addShift() {
  list.value.push({
    shift_code: '',
    shift_name: '',
    start_time: '',
    end_time: '',
    is_overnight: false,
    color: '#FB0079',
    sort_order: list.value.length,
    is_active: true,
  } as Partial<ShiftConfig>)
}

function removeShift(index: number) {
  list.value.splice(index, 1)
}

async function handleSave() {
  saving.value = true
  try {
    for (const item of list.value) {
      if (!item.shift_code || !item.shift_name) continue
      await attendanceAPI.saveShiftConfig(item as Partial<ShiftConfig> & { shift_code: string; shift_name: string; start_time: string; end_time: string })
    }
    emit('saved')
  } catch (e: any) {
    alert(e.response?.data?.message || '保存失败')
  } finally {
    saving.value = false
  }
}

async function loadData() {
  const res = await attendanceAPI.getShiftConfigs()
  list.value = res.data?.data || []
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.shift-setting-panel {
  padding: 16px;
  background: #111111;
  border-radius: 12px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.panel-header h3 {
  margin: 0;
  color: #FFFFFF;
  font-size: 16px;
}

.close-btn {
  background: transparent;
  border: none;
  color: #FB0079;
  cursor: pointer;
}

.shift-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
}

.shift-item {
  background: #1a1a1a;
  border: 1px solid #333333;
  border-radius: 8px;
  padding: 12px;
}

.field-row {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.field-row label {
  width: 80px;
  font-size: 12px;
  color: #C8C8C8;
}

.field-row input[type="text"] {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid #333333;
  border-radius: 6px;
  background: #111111;
  color: #FFFFFF;
  font-size: 13px;
}

.field-row input[type="color"] {
  width: 40px;
  height: 28px;
  border: none;
  background: transparent;
}

.field-row.inline {
  gap: 16px;
}

.field-row.inline label {
  width: auto;
  display: flex;
  align-items: center;
  gap: 4px;
}

.remove-btn {
  width: 100%;
  margin-top: 8px;
  padding: 6px;
  border: 1px solid #FB0079;
  border-radius: 6px;
  background: transparent;
  color: #FB0079;
  font-size: 12px;
  cursor: pointer;
}

.add-btn,
.save-btn {
  width: 100%;
  margin-top: 12px;
  padding: 10px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

.add-btn {
  background: #333333;
  color: #C8C8C8;
}

.save-btn {
  background: #FB0079;
  color: #FFFFFF;
}

.save-btn:disabled {
  opacity: 0.4;
}
</style>
