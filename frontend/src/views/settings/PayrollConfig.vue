<script setup lang="ts">
// 工资项配置列表
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  listItems,
  listRules,
  deleteItem,
  initConfig,
  type PayrollItemConfig,
  type SalaryRule,
  SOURCE_LABELS,
} from '@/api/payrollConfig'

const router = useRouter()

const items = ref<PayrollItemConfig[]>([])
const rules = ref<SalaryRule[]>([])
const loading = ref(false)
const activeTab = ref<'items' | 'rules'>('items')

async function loadItems() {
  loading.value = true
  try {
    const res = await listItems()
    items.value = res.data.data
  } finally {
    loading.value = false
  }
}

async function loadRules() {
  try {
    const res = await listRules()
    rules.value = res.data.data
  } catch (e) {
    /* ignore */
  }
}

async function onInit() {
  try {
    await ElMessageBox.confirm(
      '将初始化默认工资项配置（不影响已有配置）。是否继续？',
      '初始化默认配置',
      { type: 'warning' }
    )
    await initConfig()
    ElMessage.success('初始化成功')
    await loadItems()
    await loadRules()
  } catch (e) {
    /* 取消 */
  }
}

async function onDelete(item: PayrollItemConfig) {
  if (item.is_system) {
    ElMessage.warning('系统内置项不可删除')
    return
  }
  try {
    await ElMessageBox.confirm(
      `确认删除工资项「${item.item_name}」？`,
      '删除确认',
      { type: 'warning' }
    )
    await deleteItem(item.item_code)
    ElMessage.success('已删除')
    await loadItems()
  } catch (e) {
    /* 取消 */
  }
}

function goEdit(item?: PayrollItemConfig) {
  if (item) {
    router.push({
      name: 'FormulaEditor',
      params: { code: item.item_code },
    })
  } else {
    router.push({ name: 'FormulaEditor' })
  }
}

const dataSourceLabel = (s: string) =>
  SOURCE_LABELS[s as keyof typeof SOURCE_LABELS] ?? s

onMounted(() => {
  loadItems()
  loadRules()
})
</script>

<template>
  <div class="payroll-config">
    <div class="header">
      <div class="tabs">
        <button
          class="tab"
          :class="{ active: activeTab === 'items' }"
          @click="activeTab = 'items'"
        >
          工资项
        </button>
        <button
          class="tab"
          :class="{ active: activeTab === 'rules' }"
          @click="activeTab = 'rules'"
        >
          薪资规则
        </button>
      </div>
      <div class="actions">
        <button class="btn-ghost small" @click="onInit">初始化默认</button>
        <button v-if="activeTab === 'items'" class="btn-primary small" @click="goEdit()">
          + 新增工资项
        </button>
      </div>
    </div>

    <!-- 工资项列表 -->
    <div v-if="activeTab === 'items'" v-loading="loading">
      <div v-if="items.length === 0 && !loading" class="empty-state">
        暂无工资项配置，点击「初始化默认」生成系统推荐项
      </div>
      <div v-for="item in items" :key="item.item_code" class="item-card">
        <div class="item-header">
          <div>
            <span class="item-name">{{ item.item_name }}</span>
            <span
              class="badge"
              :class="item.item_type === 'income' ? 'income' : 'deduction'"
            >
              {{ item.item_type === 'income' ? '收入' : '扣款' }}
            </span>
            <span v-if="item.is_system" class="badge system">系统</span>
            <span v-if="!item.is_active" class="badge inactive">已停用</span>
          </div>
          <div class="item-actions">
            <button class="btn-ghost small" @click="goEdit(item)">编辑公式</button>
            <button
              v-if="!item.is_system"
              class="btn-ghost small danger"
              @click="onDelete(item)"
            >
              删除
            </button>
          </div>
        </div>
        <div class="item-meta">
          <span>代码：{{ item.item_code }}</span>
          <span>数据源：{{ dataSourceLabel(item.data_source) }}</span>
          <span>排序：{{ item.sort_order }}</span>
          <span>默认值：{{ item.default_value }}</span>
        </div>
        <div v-if="item.note" class="item-note">{{ item.note }}</div>
      </div>
    </div>

    <!-- 薪资规则列表 -->
    <div v-if="activeTab === 'rules'">
      <div v-if="rules.length === 0" class="empty-state">
        暂无薪资规则，点击「初始化默认」生成
      </div>
      <div v-for="rule in rules" :key="rule.rule_code" class="item-card">
        <div class="item-header">
          <span class="item-name">{{ rule.rule_name }}</span>
          <span v-if="!rule.is_active" class="badge inactive">已停用</span>
        </div>
        <div class="item-meta">
          <span>代码：{{ rule.rule_code }}</span>
          <span>值：{{ rule.rule_value }}{{ rule.rule_unit ? ' ' + rule.rule_unit : '' }}</span>
        </div>
        <div v-if="rule.note" class="item-note">{{ rule.note }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payroll-config {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.tabs {
  display: flex;
  gap: 4px;
}

.tab {
  background: transparent;
  border: 1px solid $color-divider;
  color: #888;
  padding: 6px 14px;
  border-radius: $radius-sm;
  font-size: 13px;
  cursor: pointer;

  &.active {
    background-color: $brand-primary;
    color: $brand-white;
    border-color: $brand-primary;
  }
}

.actions {
  display: flex;
  gap: 8px;
}

.btn-primary.small,
.btn-ghost.small {
  padding: 6px 12px;
  font-size: 12px;
}

.btn-ghost.danger {
  color: $brand-primary;
  border-color: $brand-primary;
}

.item-card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 14px;
  border: 1px solid $color-divider;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.item-name {
  font-size: 15px;
  font-weight: 600;
  color: $brand-white;
  margin-right: 8px;
}

.badge {
  display: inline-block;
  padding: 2px 8px;
  border-radius: 10px;
  font-size: 11px;
  margin-right: 4px;

  &.income {
    background-color: rgba(251, 0, 121, 0.15);
    color: $brand-primary;
  }
  &.deduction {
    background-color: $color-divider;
    color: $brand-white;
  }
  &.system {
    background-color: $color-black;
    color: #888;
    border: 1px solid $color-divider;
  }
  &.inactive {
    background-color: transparent;
    color: #888;
    border: 1px solid #555;
  }
}

.item-actions {
  display: flex;
  gap: 6px;
}

.item-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 12px;
  color: #888;
}

.item-note {
  margin-top: 6px;
  font-size: 12px;
  color: #888;
  padding-top: 6px;
  border-top: 1px dashed $color-divider;
}
</style>
