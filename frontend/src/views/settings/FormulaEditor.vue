<script setup lang="ts">
// 工资项公式编辑器页面
import { ref, reactive, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import FormulaEditor from '@/components/FormulaEditor.vue'
import {
  listItems,
  upsertItem,
  type FormulaNode,
  type ItemType,
  type DataSource,
  type PayrollItemConfig,
  SOURCE_LABELS,
} from '@/api/payrollConfig'
import { astToString, validateAst } from '@/utils/formulaAst'

const route = useRoute()
const router = useRouter()

const code = computed(() => (route.params.code as string) || '')
const isEdit = computed(() => !!code.value)

const form = reactive({
  item_code: '',
  item_name: '',
  item_type: 'income' as ItemType,
  data_source: 'contract' as DataSource,
  default_value: 0,
  sort_order: 100,
  note: '',
})

const formulaAst = ref<FormulaNode | null>(null)
const loading = ref(false)
const saving = ref(false)

const preview = computed(() => astToString(formulaAst.value))
const validationError = computed(() => validateAst(formulaAst.value))

async function loadDetail() {
  if (!code.value) return
  loading.value = true
  try {
    const res = await listItems()
    const item = res.data.data.find(
      (x: PayrollItemConfig) => x.item_code === code.value
    )
    if (item) {
      form.item_code = item.item_code
      form.item_name = item.item_name
      form.item_type = item.item_type
      form.data_source = item.data_source
      form.default_value = item.default_value
      form.sort_order = item.sort_order
      form.note = item.note ?? ''
      formulaAst.value = item.formula_ast
    } else {
      ElMessage.error('工资项不存在')
      router.back()
    }
  } finally {
    loading.value = false
  }
}

async function onSave() {
  if (!form.item_code || !form.item_name) {
    ElMessage.warning('请填写代码和名称')
    return
  }
  if (validationError.value) {
    ElMessage.warning(`公式无效：${validationError.value}`)
    return
  }
  saving.value = true
  try {
    await upsertItem({
      item_code: form.item_code,
      item_name: form.item_name,
      item_type: form.item_type,
      data_source: form.data_source,
      formula_ast: formulaAst.value,
      default_value: form.default_value,
      sort_order: form.sort_order,
      note: form.note || undefined,
    })
    ElMessage.success('保存成功')
    router.push({ name: 'PayrollConfig' })
  } catch (e) {
    /* 错误已处理 */
  } finally {
    saving.value = false
  }
}

onMounted(loadDetail)
</script>

<template>
  <div class="formula-page" v-loading="loading">
    <div class="page-header">
      <span class="page-title">{{ isEdit ? '编辑工资项' : '新增工资项' }}</span>
    </div>

    <!-- 基础信息 -->
    <div class="card">
      <div class="section-title">基础信息</div>
      <div class="form-row">
        <label>代码</label>
        <input
          v-model="form.item_code"
          type="text"
          class="input"
          placeholder="如 base_salary"
          :disabled="isEdit"
        />
      </div>
      <div class="form-row">
        <label>名称</label>
        <input v-model="form.item_name" type="text" class="input" placeholder="如 底薪" />
      </div>
      <div class="form-row">
        <label>类型</label>
        <div class="radio-group">
          <label class="radio">
            <input v-model="form.item_type" type="radio" value="income" /> 收入
          </label>
          <label class="radio">
            <input v-model="form.item_type" type="radio" value="deduction" /> 扣款
          </label>
        </div>
      </div>
      <div class="form-row">
        <label>数据源</label>
        <select v-model="form.data_source" class="input">
          <option v-for="(label, key) in SOURCE_LABELS" :key="key" :value="key">
            {{ label }}
          </option>
        </select>
      </div>
      <div class="form-row">
        <label>默认值</label>
        <input v-model.number="form.default_value" type="number" class="input" />
      </div>
      <div class="form-row">
        <label>排序</label>
        <input v-model.number="form.sort_order" type="number" class="input" />
      </div>
      <div class="form-row">
        <label>备注</label>
        <textarea v-model="form.note" class="input" rows="2" />
      </div>
    </div>

    <!-- 公式编辑器 -->
    <div class="card">
      <div class="section-title">计算公式</div>
      <FormulaEditor v-model="formulaAst" />
      <div class="preview-box">
        <div class="preview-label">最终公式</div>
        <div class="preview-value">{{ preview || '（未配置）' }}</div>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <button class="btn-ghost" @click="router.back()">取消</button>
      <button class="btn-primary" :disabled="saving" @click="onSave">
        {{ saving ? '保存中...' : '保存' }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.formula-page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding-bottom: 8px;

  .page-title {
    font-size: 18px;
    font-weight: 600;
    color: $brand-white;
  }
}

.section-title {
  font-size: 14px;
  color: $brand-primary;
  margin-bottom: 12px;
  font-weight: 600;
}

.form-row {
  display: flex;
  align-items: center;
  margin-bottom: 12px;

  label {
    width: 80px;
    font-size: 13px;
    color: #888;
    flex-shrink: 0;
  }

  .input {
    flex: 1;
    height: 38px;
    background-color: $color-black;
    border: 1px solid $color-divider;
    border-radius: $radius-sm;
    padding: 0 10px;
    color: $brand-white;
    font-size: 14px;
    outline: none;
    font-family: inherit;

    &:focus {
      border-color: $brand-primary;
    }

    &.textarea,
    &.is-textarea {
      height: auto;
      padding: 8px 10px;
      resize: vertical;
    }
  }
}

.radio-group {
  display: flex;
  gap: 16px;
}

.radio {
  display: flex;
  align-items: center;
  gap: 4px;
  color: $brand-white;
  font-size: 14px;
  cursor: pointer;
}

.preview-box {
  margin-top: 12px;
  padding: 10px;
  background-color: $color-black;
  border: 1px dashed $brand-primary;
  border-radius: $radius-sm;
}

.preview-label {
  font-size: 12px;
  color: #888;
  margin-bottom: 4px;
}

.preview-value {
  font-family: $font-family-number;
  color: $brand-white;
  font-size: 13px;
  word-break: break-all;
}

.actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;

  button {
    flex: 1;
    height: 44px;
  }
}
</style>
