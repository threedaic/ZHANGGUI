<script setup lang="ts">
// 可视化公式编辑器：通过点击数据项/运算符/函数构建 AST
import { ref, computed, watch } from 'vue'
import {
  SOURCE_FIELDS,
  SOURCE_LABELS,
  FUNCTIONS,
  type FormulaNode,
  type FormulaSource,
} from '@/api/payrollConfig'
import {
  astToString,
  cloneAst,
  constNode,
  fieldNode,
  funcNode,
  opNode,
  validateAst,
} from '@/utils/formulaAst'

const props = defineProps<{
  modelValue: FormulaNode | null
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: FormulaNode | null): void
}>()

// 当前编辑中的 AST（本地副本）
const ast = ref<FormulaNode | null>(cloneAst(props.modelValue))
// 当前选中节点路径（用于在指定位置插入）
const selectedPath = ref<number[]>([])
// 常量输入
const constInput = ref<string>('0')
// 函数参数数量
const funcArgCount = ref<number>(2)

watch(
  () => props.modelValue,
  (v) => {
    ast.value = cloneAst(v)
    selectedPath.value = []
  }
)

watch(
  ast,
  (v) => {
    emit('update:modelValue', v)
  },
  { deep: true }
)

const preview = computed(() => astToString(ast.value))
const validationError = computed(() => validateAst(ast.value))

// 当前选中节点
function getNodeAtPath(path: number[]): FormulaNode | null {
  if (!ast.value) return null
  let cur: FormulaNode = ast.value
  for (const idx of path) {
    if (cur.type === 'op') {
      cur = idx === 0 ? cur.left : cur.right
    } else if (cur.type === 'func') {
      cur = cur.args[idx]
    } else {
      return null
    }
  }
  return cur
}

function selectNode(path: number[]) {
  selectedPath.value = path
}

// 替换指定路径的节点
function replaceAtPath(path: number[], newNode: FormulaNode): FormulaNode | null {
  if (path.length === 0) {
    return newNode
  }
  if (!ast.value) {
    return newNode
  }
  const [head, ...rest] = path
  const root = cloneAst(ast.value)!
  let cur = root
  for (let i = 0; i < path.length - 1; i++) {
    const idx = path[i]
    if (cur.type === 'op') {
      cur = idx === 0 ? cur.left : cur.right
    } else if (cur.type === 'func') {
      cur = cur.args[idx]
    }
  }
  const lastIdx = path[path.length - 1]
  if (cur.type === 'op') {
    if (lastIdx === 0) cur.left = newNode
    else cur.right = newNode
  } else if (cur.type === 'func') {
    cur.args[lastIdx] = newNode
  }
  // head 用于消除未使用警告
  void head
  void rest
  return root
}

// ====== 插入操作 ======

function insertConst() {
  const v = parseFloat(constInput.value)
  if (Number.isNaN(v)) {
    return
  }
  ast.value = replaceAtPath(selectedPath.value, constNode(v))
  selectedPath.value = []
}

function insertField(source: FormulaSource, field: string) {
  ast.value = replaceAtPath(selectedPath.value, fieldNode(source, field))
  selectedPath.value = []
}

function insertOp(op: '+' | '-' | '*' | '/') {
  const cur = getNodeAtPath(selectedPath.value)
  // 以当前节点为左操作数，右操作数先放占位常量 0
  const left = cur ?? constNode(0)
  const newNode = opNode(op, left, constNode(0))
  ast.value = replaceAtPath(selectedPath.value, newNode)
  // 选中右操作数便于继续编辑
  selectedPath.value = [...selectedPath.value, 1]
}

function insertFunc(name: 'max' | 'min' | 'round' | 'abs' | 'if') {
  const cur = getNodeAtPath(selectedPath.value)
  const argCount = funcArgCount.value
  const args: FormulaNode[] = []
  if (cur) args.push(cur)
  while (args.length < argCount) args.push(constNode(0))
  const newNode = funcNode(name, args)
  ast.value = replaceAtPath(selectedPath.value, newNode)
  selectedPath.value = []
}

function clearFormula() {
  ast.value = null
  selectedPath.value = []
}

function resetToRoot() {
  selectedPath.value = []
}

// 渲染 AST 为可点击树
interface RenderNode {
  node: FormulaNode
  path: number[]
  label: string
  children: RenderNode[]
}

function renderTree(node: FormulaNode, path: number[] = []): RenderNode {
  let label = ''
  let children: RenderNode[] = []
  if (node.type === 'const') {
    label = `常量: ${node.value}`
  } else if (node.type === 'field') {
    const f = SOURCE_FIELDS[node.source]?.find((x) => x.field === node.field)
    label = `字段: ${SOURCE_LABELS[node.source]}.${f?.label ?? node.field}`
  } else if (node.type === 'op') {
    label = `运算: ${node.op}`
    children = [
      renderTree(node.left, [...path, 0]),
      renderTree(node.right, [...path, 1]),
    ]
  } else if (node.type === 'func') {
    label = `函数: ${node.name}`
    children = node.args.map((a, i) => renderTree(a, [...path, i]))
  }
  return { node, path, label, children }
}

const tree = computed<RenderNode | null>(() =>
  ast.value ? renderTree(ast.value) : null
)

function renderTreeFlat(node: RenderNode, depth = 0): RenderNode[] {
  const result: RenderNode[] = [{ ...node, children: [] }]
  for (const child of node.children) {
    result.push(...renderTreeFlat(child, depth + 1))
  }
  return result
}

const flatTree = computed<RenderNode[]>(() => {
  if (!tree.value) return []
  return renderTreeFlat(tree.value)
})
</script>

<template>
  <div class="formula-editor">
    <!-- 预览区 -->
    <div class="preview-block">
      <div class="preview-label">公式预览</div>
      <div class="preview-text" :class="{ error: !!validationError }">
        {{ preview || '（空）' }}
      </div>
      <div v-if="validationError" class="error-text">{{ validationError }}</div>
    </div>

    <!-- AST 树形展示 -->
    <div v-if="ast" class="ast-tree">
      <div class="block-title">公式结构（点击节点选中后可替换）</div>
      <div
        v-for="(item, idx) in flatTree"
        :key="idx"
        class="tree-node"
        :class="{ selected: selectedPath.join(',') === item.path.join(',') }"
        :style="{ paddingLeft: 12 + item.path.length * 16 + 'px' }"
        @click="selectNode(item.path)"
      >
        <span class="node-label">{{ item.label }}</span>
      </div>
      <div class="tree-actions">
        <button class="btn-ghost small" @click="resetToRoot">回到根节点</button>
        <button class="btn-ghost small danger" @click="clearFormula">清空公式</button>
      </div>
    </div>

    <!-- 当前选中提示 -->
    <div v-if="selectedPath.length > 0" class="selected-hint">
      已选中路径：{{ selectedPath.join(' → ') }}
    </div>

    <!-- 常量输入 -->
    <div class="block">
      <div class="block-title">常量</div>
      <div class="row">
        <input v-model="constInput" type="number" class="num-input" />
        <button class="btn-primary small" @click="insertConst">插入</button>
      </div>
    </div>

    <!-- 字段选择 -->
    <div class="block">
      <div class="block-title">数据字段</div>
      <div v-for="(fields, source) in SOURCE_FIELDS" :key="source" class="source-group">
        <div class="source-title">{{ SOURCE_LABELS[source as FormulaSource] }}</div>
        <div class="field-chips">
          <button
            v-for="f in fields"
            :key="f.field"
            class="chip"
            @click="insertField(source as FormulaSource, f.field)"
          >
            {{ f.label }}
          </button>
        </div>
      </div>
    </div>

    <!-- 运算符 -->
    <div class="block">
      <div class="block-title">运算符（以当前选中节点为左操作数）</div>
      <div class="field-chips">
        <button class="chip op" @click="insertOp('+')">+ 加</button>
        <button class="chip op" @click="insertOp('-')">- 减</button>
        <button class="chip op" @click="insertOp('*')">×</button>
        <button class="chip op" @click="insertOp('/')">÷</button>
      </div>
    </div>

    <!-- 函数 -->
    <div class="block">
      <div class="block-title">函数</div>
      <div class="row" style="margin-bottom: 8px;">
        <span class="hint">参数数量：</span>
        <input v-model.number="funcArgCount" type="number" min="1" max="5" class="num-input small" />
      </div>
      <div class="field-chips">
        <button
          v-for="fn in FUNCTIONS"
          :key="fn.name"
          class="chip func"
          @click="insertFunc(fn.name)"
        >
          {{ fn.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.formula-editor {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
}

.preview-block {
  background-color: $color-black;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 12px;
  margin-bottom: 16px;
}

.preview-label {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}

.preview-text {
  font-family: $font-family-number;
  font-size: 14px;
  color: $brand-white;
  word-break: break-all;
  min-height: 20px;

  &.error {
    color: $brand-primary;
  }
}

.error-text {
  color: $brand-primary;
  font-size: 12px;
  margin-top: 6px;
}

.ast-tree {
  background-color: $color-black;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 12px;
  margin-bottom: 16px;
}

.block-title {
  font-size: 12px;
  color: #888;
  margin-bottom: 8px;
}

.tree-node {
  padding: 6px 8px;
  margin: 2px 0;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  color: $brand-white;
  border: 1px solid transparent;

  &:hover {
    background-color: $color-divider;
  }

  &.selected {
    background-color: rgba(251, 0, 121, 0.15);
    border-color: $brand-primary;
  }
}

.tree-actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.selected-hint {
  font-size: 12px;
  color: $brand-primary;
  margin-bottom: 12px;
  padding: 6px 8px;
  background-color: rgba(251, 0, 121, 0.1);
  border-radius: 4px;
}

.block {
  margin-bottom: 16px;
}

.row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.num-input {
  flex: 1;
  height: 36px;
  background-color: $color-black;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 0 10px;
  color: $brand-white;
  font-family: $font-family-number;
  font-size: 14px;
  outline: none;

  &.small {
    width: 80px;
    flex: none;
  }
}

.source-group {
  margin-bottom: 12px;
}

.source-title {
  font-size: 12px;
  color: $brand-primary;
  margin-bottom: 6px;
}

.field-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.chip {
  background-color: $color-black;
  border: 1px solid $color-divider;
  color: $brand-white;
  border-radius: 14px;
  padding: 5px 12px;
  font-size: 12px;
  cursor: pointer;

  &:hover {
    border-color: $brand-primary;
    color: $brand-primary;
  }

  &.op {
    border-color: $brand-primary;
    color: $brand-primary;
  }

  &.func {
    border-style: dashed;
  }
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

.hint {
  font-size: 12px;
  color: #888;
}
</style>
