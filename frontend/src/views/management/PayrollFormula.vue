<script setup lang="ts">
// 工资公式编辑器（统一页面）
// 顶部选工资项，下面直接是拼积木式公式编辑器
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  listItems,
  listRules,
  updateRule,
  upsertItem,
  type PayrollItemConfig,
  type SalaryRule,
  type FormulaNode,
} from '@/api/payrollConfig'
import FormulaBuilder from '@/components/FormulaBuilder.vue'

const items = ref<PayrollItemConfig[]>([])
const rules = ref<SalaryRule[]>([])
const loading = ref(false)
const saving = ref(false)

// 当前选中的工资项
const currentItemCode = ref<string>('')
const currentItem = computed(() =>
  items.value.find((i) => i.item_code === currentItemCode.value) ?? null
)
const editingAst = ref<FormulaNode | null>(null)

// 可调参数
const CALC_RULE_CODES = [
  'commission_rate',
  'late_deduction_per_minute',
  'absent_factor',
  'early_deduction_per_time',
  'rest_days_per_month',
]
const RULE_DISPLAY: Record<string, { label: string; unit: string; desc: string }> = {
  commission_rate: { label: '提成比例', unit: '%', desc: '业绩×比例=提成' },
  late_deduction_per_minute: { label: '迟到每分钟', unit: '元', desc: '迟到1分钟扣多少' },
  absent_factor: { label: '旷工倍数', unit: '倍', desc: '旷工1天扣几倍日薪' },
  early_deduction_per_time: { label: '早退每次', unit: '元', desc: '早退1次扣多少' },
  rest_days_per_month: { label: '月休息', unit: '天', desc: '算日薪用' },
}
const calcRules = computed(() =>
  rules.value.filter((r) => CALC_RULE_CODES.includes(r.rule_code))
)
const ruleEdits = ref<Record<string, number>>({})
const savingRuleCode = ref<string | null>(null)

function ruleDisplayValue(rule: SalaryRule): number {
  if (rule.rule_code === 'commission_rate') return Math.round(rule.rule_value * 100)
  return rule.rule_value
}
function ruleStoreValue(ruleCode: string, v: number): number {
  if (ruleCode === 'commission_rate') return v / 100
  return v
}

async function load() {
  loading.value = true
  try {
    const [itemsRes, rulesRes] = await Promise.all([listItems(), listRules()])
    items.value = itemsRes.data.data
    rules.value = rulesRes.data.data
    ruleEdits.value = {}
    for (const r of rules.value) ruleEdits.value[r.rule_code] = ruleDisplayValue(r)
    if (items.value.length > 0 && !currentItemCode.value) {
      currentItemCode.value = items.value[0].item_code
    }
    selectItem(currentItemCode.value)
  } finally {
    loading.value = false
  }
}

function selectItem(code: string) {
  currentItemCode.value = code
  const item = items.value.find((i) => i.item_code === code)
  if (item) {
    editingAst.value = item.formula_ast ? JSON.parse(JSON.stringify(item.formula_ast)) : null
  }
}

async function saveFormula() {
  if (!currentItem.value) return
  saving.value = true
  try {
    await upsertItem({
      item_code: currentItem.value.item_code,
      item_name: currentItem.value.item_name,
      item_type: currentItem.value.item_type,
      data_source: currentItem.value.data_source,
      formula_ast: editingAst.value,
      default_value: 0,
      sort_order: currentItem.value.sort_order,
      note: currentItem.value.note ?? undefined,
    })
    ElMessage.success(`${currentItem.value.item_name} 公式已保存`)
    // 更新本地
    const item = items.value.find((i) => i.item_code === currentItemCode.value)
    if (item) item.formula_ast = editingAst.value ? JSON.parse(JSON.stringify(editingAst.value)) : null
  } catch (e) {
    /* 错误已处理 */
  } finally {
    saving.value = false
  }
}

async function saveRule(rule: SalaryRule) {
  const v = ruleEdits.value[rule.rule_code]
  if (v == null || Number.isNaN(v)) {
    ElMessage.warning('请输入有效数值')
    return
  }
  savingRuleCode.value = rule.rule_code
  try {
    const storeVal = ruleStoreValue(rule.rule_code, v)
    await updateRule(rule.rule_code, storeVal)
    const r = rules.value.find((x) => x.rule_code === rule.rule_code)
    if (r) r.rule_value = storeVal
    ElMessage.success(`${RULE_DISPLAY[rule.rule_code]?.label ?? rule.rule_name} 已更新`)
  } catch (e) {
    /* 错误已处理 */
  } finally {
    savingRuleCode.value = null
  }
}

onMounted(load)
</script>

<template>
  <div class="payroll-formula" v-loading="loading">
    <!-- 顶部：选工资项 + 保存 -->
    <div class="top-bar">
      <select v-model="currentItemCode" class="item-select" @change="selectItem(currentItemCode)">
        <optgroup label="收入项">
          <option v-for="i in items.filter(x => x.item_type === 'income')" :key="i.item_code" :value="i.item_code">
            {{ i.item_name }}
          </option>
        </optgroup>
        <optgroup label="扣款项">
          <option v-for="i in items.filter(x => x.item_type === 'deduction')" :key="i.item_code" :value="i.item_code">
            {{ i.item_name }}
          </option>
        </optgroup>
      </select>
      <button class="save-btn" :disabled="saving || !currentItem" @click="saveFormula">
        {{ saving ? '保存中...' : '保存公式' }}
      </button>
    </div>

    <!-- 公式编辑器（直接嵌入，不是弹窗） -->
    <FormulaBuilder v-if="currentItem" v-model="editingAst" />

    <!-- 可调参数（紧凑横排） -->
    <div class="rules-bar">
      <span class="rules-title">可调参数</span>
      <div class="rules-row">
        <div v-for="rule in calcRules" :key="rule.rule_code" class="rule-item">
          <span class="rule-label">{{ RULE_DISPLAY[rule.rule_code]?.label ?? rule.rule_name }}</span>
          <input
            v-model.number="ruleEdits[rule.rule_code]"
            type="number"
            class="rule-input"
          />
          <span class="rule-unit">{{ RULE_DISPLAY[rule.rule_code]?.unit ?? '' }}</span>
          <button
            class="rule-save"
            :disabled="savingRuleCode === rule.rule_code"
            @click="saveRule(rule)"
          >
            {{ savingRuleCode === rule.rule_code ? '...' : '✓' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.payroll-formula {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.top-bar {
  display: flex;
  gap: 8px;
}

.item-select {
  flex: 1;
  height: 40px;
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 0 10px;
  color: $brand-white;
  font-size: 14px;
  font-weight: 600;
  outline: none;
  cursor: pointer;

  optgroup {
    background-color: #1a1a1a;
    color: #666;
    font-style: normal;
  }
  option {
    background-color: #1a1a1a;
    color: $brand-white;
    padding: 8px;
  }
}

.save-btn {
  height: 40px;
  padding: 0 20px;
  background: linear-gradient(135deg, #ff0079, #c10060);
  color: #fff;
  border: none;
  border-radius: $radius-sm;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;

  &:disabled {
    opacity: 0.4;
  }
}

// 可调参数
.rules-bar {
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 10px 12px;
}

.rules-title {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 1px;
  font-weight: 600;
}

.rules-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 8px;
}

.rule-item {
  display: flex;
  align-items: center;
  gap: 4px;
  background: #0d0d0d;
  border-radius: 6px;
  padding: 4px 8px;
}

.rule-label {
  font-size: 12px;
  color: #aaa;
  white-space: nowrap;
}

.rule-input {
  width: 50px;
  height: 28px;
  background: transparent;
  border: 1px solid #333;
  border-radius: 4px;
  padding: 0 4px;
  color: $brand-primary;
  font-size: 14px;
  font-weight: 700;
  font-family: $font-family-number;
  outline: none;
  text-align: center;

  &:focus {
    border-color: $brand-primary;
  }
}

.rule-unit {
  font-size: 11px;
  color: #666;
}

.rule-save {
  width: 24px;
  height: 24px;
  background: $brand-primary;
  color: #fff;
  border: none;
  border-radius: 4px;
  font-size: 12px;
  cursor: pointer;

  &:disabled {
    opacity: 0.4;
  }
}
</style>
