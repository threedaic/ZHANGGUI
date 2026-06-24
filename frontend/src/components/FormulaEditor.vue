<script setup lang="ts">
// 拖拽式可视化公式编辑器：积木块拖拽构建 AST
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
  placeholderNode,
  isPlaceholder as isPlaceholderFn,
  validateAst,
} from '@/utils/formulaAst'
import VisualNode from './VisualNode.vue'

const props = defineProps<{
  modelValue: FormulaNode | null
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: FormulaNode | null): void
}>()

// 当前编辑中的 AST（本地副本）
const ast = ref<FormulaNode | null>(cloneAst(props.modelValue))
// 当前选中的槽位路径
const activeSlot = ref<number[]>([])
// 常量输入弹窗
const constValue = ref('0')
// 撤销栈
const undoStack = ref<(FormulaNode | null)[]>([])
// 展开/折叠面板
const expandedSources = ref<Set<string>>(new Set(['__templates', 'contract', 'attendance']))

watch(
  () => props.modelValue,
  (v) => {
    ast.value = cloneAst(v)
    activeSlot.value = []
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

// ====== 撤销功能 ======
function pushUndo() {
  undoStack.value.push(cloneAst(ast.value))
  if (undoStack.value.length > 30) undoStack.value.shift()
}

function undo() {
  if (undoStack.value.length === 0) return
  ast.value = undoStack.value.pop()!
  activeSlot.value = []
}

// ====== 路径操作 ======
function getNodeAtPath(node: FormulaNode, path: number[]): FormulaNode {
  let cur = node
  for (const idx of path) {
    if (cur.type === 'op') {
      cur = idx === 0 ? cur.left : cur.right
    } else if (cur.type === 'func') {
      cur = cur.args[idx]
    }
  }
  return cur
}

function replaceAtPath(
  node: FormulaNode | null,
  path: number[],
  newNode: FormulaNode
): FormulaNode | null {
  if (path.length === 0) return newNode
  if (!node) return newNode
  const root = cloneAst(node)!
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
  return root
}

// ====== 槽位操作 ======
function selectSlot(path: number[]) {
  activeSlot.value = path
}

// ====== 插入操作 ======
function insertAtSlot(newNode: FormulaNode) {
  pushUndo()
  if (!ast.value) {
    ast.value = newNode
  } else {
    ast.value = replaceAtPath(ast.value, activeSlot.value, newNode)
  }
  activeSlot.value = []
}

function onConstSubmit() {
  const v = parseFloat(constValue.value)
  if (Number.isNaN(v)) return
  insertAtSlot(constNode(v))
  constValue.value = '0'
}

function insertField(source: FormulaSource, field: string) {
  insertAtSlot(fieldNode(source, field))
}

function insertOp(op: '+' | '-' | '*' | '/') {
  pushUndo()
  if (!ast.value) {
    ast.value = opNode(op, placeholderNode(), placeholderNode())
    activeSlot.value = [0]
  } else if (activeSlot.value.length > 0) {
    const cur = getNodeAtPath(ast.value, activeSlot.value)
    const newNode = opNode(op, cur, placeholderNode())
    ast.value = replaceAtPath(ast.value, activeSlot.value, newNode)
    activeSlot.value = [...activeSlot.value, 1]
  } else {
    ast.value = opNode(op, ast.value, placeholderNode())
    activeSlot.value = [1]
  }
}

function insertFunc(name: 'max' | 'min' | 'round' | 'abs' | 'if') {
  pushUndo()
  const fn = FUNCTIONS.find((f) => f.name === name)
  const argCount = fn?.argCount ?? 2
  const args: FormulaNode[] = []
  for (let i = 0; i < argCount; i++) args.push(placeholderNode())

  if (!ast.value) {
    ast.value = funcNode(name, args)
    activeSlot.value = [0]
  } else if (activeSlot.value.length > 0) {
    const cur = getNodeAtPath(ast.value, activeSlot.value)
    args[0] = cur
    const newNode = funcNode(name, args)
    ast.value = replaceAtPath(ast.value, activeSlot.value, newNode)
    activeSlot.value = []
  } else {
    args[0] = ast.value
    ast.value = funcNode(name, args)
    activeSlot.value = []
  }
}

function clearFormula() {
  pushUndo()
  ast.value = null
  activeSlot.value = []
}

function applyTemplate(templateAst: FormulaNode) {
  pushUndo()
  ast.value = cloneAst(templateAst)
  activeSlot.value = []
}

// ====== 拖拽处理 ======
function onDragStart(e: DragEvent, blockId: string) {
  e.dataTransfer!.effectAllowed = 'copy'
  e.dataTransfer!.setData('text/plain', blockId)
}

function executeBlockAction(blockId: string, targetPath?: number[]) {
  if (targetPath) {
    activeSlot.value = targetPath
  }
  const [kind, value] = blockId.split(':')
  if (kind === 'field') {
    const [source, field] = value.split('.')
    insertField(source as FormulaSource, field)
  } else if (kind === 'op') {
    insertOp(value as '+' | '-' | '*' | '/')
  } else if (kind === 'func') {
    insertFunc(value as 'max' | 'min' | 'round' | 'abs' | 'if')
  } else if (kind === 'template') {
    const tpl = BUILTIN_TEMPLATES.find((t) => t.id === value)
    if (tpl) applyTemplate(tpl.ast)
  }
}

// 触摸拖拽支持
const touchDragBlock = ref<string | null>(null)

function onTouchStart(blockId: string) {
  touchDragBlock.value = blockId
}

function onTouchMove(e: TouchEvent) {
  if (!touchDragBlock.value) return
  // 模板已用 .prevent 修饰符阻止默认滚动
}

function onTouchEnd(e: TouchEvent) {
  if (!touchDragBlock.value) return
  const touch = e.changedTouches[0]
  const el = document.elementFromPoint(touch.clientX, touch.clientY)
  const slotEl = el?.closest('[data-slot-path]')
  if (slotEl) {
    const pathStr = slotEl.getAttribute('data-slot-path')!
    const path = pathStr.split(',').map(Number)
    executeBlockAction(touchDragBlock.value, path)
  }
  touchDragBlock.value = null
}

// ====== 模板 ======
interface Template {
  id: string
  name: string
  desc: string
  ast: FormulaNode
}

const BUILTIN_TEMPLATES: Template[] = [
  {
    id: 'base_salary',
    name: '底薪',
    desc: '直接取合同月薪',
    ast: { type: 'field', source: 'contract', field: 'monthly_salary' },
  },
  {
    id: 'meal_allowance',
    name: '餐补',
    desc: '直接取合同餐补',
    ast: { type: 'field', source: 'contract', field: 'meal_allowance' },
  },
  {
    id: 'commission',
    name: '提成',
    desc: '业绩总额 × 提成比例',
    ast: {
      type: 'op',
      op: '*',
      left: { type: 'field', source: 'performance', field: 'total_amount' },
      right: { type: 'field', source: 'rule', field: 'commission_rate' },
    },
  },
  {
    id: 'kpi_bonus',
    name: 'KPI奖金',
    desc: '月薪 × (KPI系数 - 1)',
    ast: {
      type: 'op',
      op: '*',
      left: { type: 'field', source: 'contract', field: 'monthly_salary' },
      right: {
        type: 'op',
        op: '-',
        left: { type: 'field', source: 'kpi', field: 'coefficient' },
        right: { type: 'const', value: 1 },
      },
    },
  },
  {
    id: 'deduction_late',
    name: '迟到扣款',
    desc: '迟到分钟 × 每分钟扣款',
    ast: {
      type: 'op',
      op: '*',
      left: { type: 'field', source: 'attendance', field: 'total_late_minutes' },
      right: { type: 'field', source: 'rule', field: 'late_deduction_per_minute' },
    },
  },
  {
    id: 'deduction_absent',
    name: '旷工扣款',
    desc: '旷工天数 × 日薪 × 倍数',
    ast: {
      type: 'op',
      op: '*',
      left: { type: 'field', source: 'attendance', field: 'absent_count' },
      right: {
        type: 'op',
        op: '*',
        left: {
          type: 'op',
          op: '/',
          left: { type: 'field', source: 'contract', field: 'monthly_salary' },
          right: {
            type: 'op',
            op: '-',
            left: { type: 'const', value: 30 },
            right: { type: 'field', source: 'rule', field: 'rest_days_per_month' },
          },
        },
        right: { type: 'field', source: 'rule', field: 'absent_factor' },
      },
    },
  },
  {
    id: 'deduction_early',
    name: '早退扣款',
    desc: '早退次数 × 每次扣款',
    ast: {
      type: 'op',
      op: '*',
      left: { type: 'field', source: 'attendance', field: 'early_count' },
      right: { type: 'field', source: 'rule', field: 'early_deduction_per_time' },
    },
  },
]

// ====== 积木块渲染 ======
interface BlockDef {
  id: string
  label: string
  color: string
  icon: string
}

const FIELD_BLOCKS = computed(() => {
  const result: Record<string, BlockDef[]> = {}
  for (const [source, fields] of Object.entries(SOURCE_FIELDS)) {
    if (source === 'manual') continue
    result[source] = fields.map((f) => ({
      id: `field:${source}.${f.field}`,
      label: f.label,
      color: SOURCE_COLORS[source as FormulaSource],
      icon: SOURCE_ICONS[source as FormulaSource],
    }))
  }
  return result
})

const OP_BLOCKS: BlockDef[] = [
  { id: 'op:+', label: '加', color: '#2196F3', icon: '+' },
  { id: 'op:-', label: '减', color: '#2196F3', icon: '-' },
  { id: 'op:*', label: '乘', color: '#2196F3', icon: '×' },
  { id: 'op:/', label: '除', color: '#2196F3', icon: '÷' },
]

const FUNC_BLOCKS: BlockDef[] = [
  { id: 'func:if', label: '条件判断', color: '#9C27B0', icon: '?' },
  { id: 'func:max', label: '取最大', color: '#9C27B0', icon: '↑' },
  { id: 'func:min', label: '取最小', color: '#9C27B0', icon: '↓' },
  { id: 'func:round', label: '四舍五入', color: '#9C27B0', icon: '≈' },
  { id: 'func:abs', label: '绝对值', color: '#9C27B0', icon: '|x|' },
]

const SOURCE_COLORS: Record<FormulaSource, string> = {
  contract: '#4CAF50',
  attendance: '#FF9800',
  performance: '#E91E63',
  kpi: '#00BCD4',
  rule: '#795548',
  manual: '#607D8B',
}

const SOURCE_ICONS: Record<FormulaSource, string> = {
  contract: '📄',
  attendance: '⏰',
  performance: '📈',
  kpi: '🎯',
  rule: '📐',
  manual: '✏️',
}

function toggleSource(source: string) {
  if (expandedSources.value.has(source)) {
    expandedSources.value.delete(source)
  } else {
    expandedSources.value.add(source)
  }
}

// ====== 可视化 AST 树 ======
interface VisualBlock {
  type: 'op' | 'func' | 'leaf'
  label: string
  color: string
  path: number[]
  children: (VisualBlock | VisualSlot)[]
  nodeType: string
}

interface VisualSlot {
  type: 'slot'
  path: number[]
  child: VisualBlock | null
}

function buildVisualTree(node: FormulaNode | null, path: number[] = []): VisualBlock | null {
  if (!node) return null

  if (node.type === 'const') {
    return {
      type: 'leaf',
      label: String(node.value),
      color: '#607D8B',
      path: [...path],
      children: [],
      nodeType: 'const',
    }
  }

  if (node.type === 'field') {
    const f = SOURCE_FIELDS[node.source]?.find((x) => x.field === node.field)
    return {
      type: 'leaf',
      label: f?.label ?? node.field,
      color: SOURCE_COLORS[node.source] ?? '#607D8B',
      path: [...path],
      children: [],
      nodeType: 'field',
    }
  }

  if (node.type === 'op') {
    return {
      type: 'op',
      label: node.op === '*' ? '×' : node.op === '/' ? '÷' : node.op,
      color: '#2196F3',
      path: [...path],
      nodeType: 'op',
      children: [
        buildSlotOrBlock(node.left, [...path, 0]),
        buildSlotOrBlock(node.right, [...path, 1]),
      ],
    }
  }

  if (node.type === 'func') {
    return {
      type: 'func',
      label: node.name,
      color: '#9C27B0',
      path: [...path],
      nodeType: 'func',
      children: node.args.map((arg, i) => buildSlotOrBlock(arg, [...path, i])),
    }
  }

  return null
}

function buildSlotOrBlock(node: FormulaNode, path: number[]): VisualBlock | VisualSlot {
  if (isPlaceholderFn(node)) {
    return { type: 'slot', path: [...path], child: null }
  }
  return buildVisualTree(node, path)!
}

const visualTree = computed(() => buildVisualTree(ast.value))
</script>

<template>
  <div class="formula-editor">
    <!-- 顶部：公式预览 -->
    <div class="formula-preview">
      <div class="preview-header">
        <span class="preview-label">公式</span>
        <div class="preview-actions">
          <button
            class="icon-btn"
            title="撤销"
            :disabled="undoStack.length === 0"
            @click="undo"
          >
            ↩
          </button>
          <button class="icon-btn danger" title="清空" @click="clearFormula">
            ✕
          </button>
        </div>
      </div>
      <div class="preview-text" :class="{ error: !!validationError, empty: !preview }">
        {{ preview || '点击下方积木块开始构建公式' }}
      </div>
      <div v-if="validationError" class="error-msg">{{ validationError }}</div>
    </div>

    <!-- 中部：可视化积木块公式画布 -->
    <div class="formula-canvas">
      <div class="canvas-label">公式结构</div>
      <div v-if="visualTree" class="visual-tree">
        <VisualNode
          :node="visualTree"
          :active-slot="activeSlot"
          @select-slot="selectSlot"
        />
      </div>
      <div v-else class="canvas-empty">
        <div class="empty-icon">+</div>
        <div class="empty-text">从下方选择积木块拖入</div>
      </div>
    </div>

    <!-- 底部：积木块面板 -->
    <div class="palette">
      <!-- 快捷模板 -->
      <div class="palette-section">
        <div class="palette-title" @click="toggleSource('__templates')">
          <span class="title-icon">⚡</span>
          <span>快捷模板</span>
          <span class="expand-icon">{{ expandedSources.has('__templates') ? '▾' : '▸' }}</span>
        </div>
        <div v-show="expandedSources.has('__templates')" class="palette-body">
          <div class="template-grid">
            <div
              v-for="tpl in BUILTIN_TEMPLATES"
              :key="tpl.id"
              class="template-card"
              draggable="true"
              @click="applyTemplate(tpl.ast)"
              @dragstart="onDragStart($event, `template:${tpl.id}`)"
            >
              <div class="tpl-name">{{ tpl.name }}</div>
              <div class="tpl-desc">{{ tpl.desc }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 数据字段 -->
      <div v-for="(blocks, source) in FIELD_BLOCKS" :key="source" class="palette-section">
        <div class="palette-title" @click="toggleSource(source)">
          <span class="title-icon">{{ SOURCE_ICONS[source as FormulaSource] }}</span>
          <span>{{ SOURCE_LABELS[source as FormulaSource] }}</span>
          <span class="field-count">{{ blocks.length }}</span>
          <span class="expand-icon">{{ expandedSources.has(source) ? '▾' : '▸' }}</span>
        </div>
        <div v-show="expandedSources.has(source)" class="palette-body">
          <div class="block-chips">
            <div
              v-for="block in blocks"
              :key="block.id"
              class="block-chip"
              :style="{ borderColor: block.color, color: block.color }"
              draggable="true"
              @click="executeBlockAction(block.id)"
              @dragstart="onDragStart($event, block.id)"
              @touchstart.passive="onTouchStart(block.id)"
              @touchmove.prevent="onTouchMove"
              @touchend="onTouchEnd"
            >
              {{ block.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- 运算符 -->
      <div class="palette-section">
        <div class="palette-title" @click="toggleSource('__ops')">
          <span class="title-icon">🔢</span>
          <span>运算符</span>
          <span class="expand-icon">{{ expandedSources.has('__ops') ? '▾' : '▸' }}</span>
        </div>
        <div v-show="expandedSources.has('__ops')" class="palette-body">
          <div class="block-chips">
            <div
              v-for="block in OP_BLOCKS"
              :key="block.id"
              class="block-chip op"
              draggable="true"
              @click="executeBlockAction(block.id)"
              @dragstart="onDragStart($event, block.id)"
              @touchstart.passive="onTouchStart(block.id)"
              @touchmove.prevent="onTouchMove"
              @touchend="onTouchEnd"
            >
              {{ block.icon }} {{ block.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- 函数 -->
      <div class="palette-section">
        <div class="palette-title" @click="toggleSource('__funcs')">
          <span class="title-icon">ƒ</span>
          <span>函数</span>
          <span class="expand-icon">{{ expandedSources.has('__funcs') ? '▾' : '▸' }}</span>
        </div>
        <div v-show="expandedSources.has('__funcs')" class="palette-body">
          <div class="block-chips">
            <div
              v-for="block in FUNC_BLOCKS"
              :key="block.id"
              class="block-chip func"
              draggable="true"
              @click="executeBlockAction(block.id)"
              @dragstart="onDragStart($event, block.id)"
              @touchstart.passive="onTouchStart(block.id)"
              @touchmove.prevent="onTouchMove"
              @touchend="onTouchEnd"
            >
              {{ block.icon }} {{ block.label }}
            </div>
          </div>
        </div>
      </div>

      <!-- 常量 -->
      <div class="palette-section">
        <div class="palette-title" @click="toggleSource('__const')">
          <span class="title-icon">#</span>
          <span>常量数值</span>
          <span class="expand-icon">{{ expandedSources.has('__const') ? '▾' : '▸' }}</span>
        </div>
        <div v-show="expandedSources.has('__const')" class="palette-body">
          <div class="const-input-row">
            <input
              v-model="constValue"
              type="number"
              class="const-input"
              placeholder="输入数值"
              @keyup.enter="onConstSubmit"
            />
            <button class="btn-add" @click="onConstSubmit">添加</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.formula-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

// ====== 公式预览区 ======
.formula-preview {
  background-color: $color-black;
  border: 1px solid $color-divider;
  border-radius: $radius-md;
  padding: 12px;
}

.preview-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.preview-label {
  font-size: 12px;
  color: #888;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.preview-actions {
  display: flex;
  gap: 4px;
}

.icon-btn {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid $color-divider;
  background: transparent;
  color: #888;
  font-size: 14px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;

  &:hover:not(:disabled) {
    border-color: $brand-primary;
    color: $brand-primary;
  }

  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  &.danger:hover {
    border-color: $brand-primary;
    color: $brand-primary;
  }
}

.preview-text {
  font-family: $font-family-number;
  font-size: 14px;
  color: $brand-white;
  word-break: break-all;
  min-height: 22px;
  line-height: 1.6;

  &.empty {
    color: #555;
    font-style: italic;
  }

  &.error {
    color: $brand-primary;
  }
}

.error-msg {
  color: $brand-primary;
  font-size: 12px;
  margin-top: 6px;
}

// ====== 公式画布 ======
.formula-canvas {
  background-color: $color-black;
  border: 2px dashed $color-divider;
  border-radius: $radius-md;
  padding: 16px;
  min-height: 80px;
  transition: border-color 0.2s;
}

.canvas-label {
  font-size: 11px;
  color: #555;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  color: #555;

  .empty-icon {
    width: 40px;
    height: 40px;
    border: 2px dashed #444;
    border-radius: 8px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 20px;
    color: #444;
    margin-bottom: 8px;
  }

  .empty-text {
    font-size: 13px;
  }
}

.visual-tree {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  line-height: 2;
}

// ====== 积木块面板 ======
.palette {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.palette-section {
  background-color: $color-bg;
  border: 1px solid $color-divider;
  border-radius: $radius-md;
  overflow: hidden;
}

.palette-title {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  color: $brand-white;
  user-select: none;
  transition: background-color 0.15s;

  &:hover {
    background-color: $color-divider;
  }

  .title-icon {
    font-size: 14px;
  }

  .field-count {
    font-size: 11px;
    color: #666;
    background-color: $color-black;
    padding: 1px 6px;
    border-radius: 10px;
  }

  .expand-icon {
    margin-left: auto;
    font-size: 12px;
    color: #666;
  }
}

.palette-body {
  padding: 8px 14px 12px;
  border-top: 1px solid $color-divider;
}

// ====== 积木块 Chips ======
.block-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.block-chip {
  display: inline-flex;
  align-items: center;
  padding: 6px 12px;
  border: 2px solid;
  border-radius: 20px;
  font-size: 12px;
  font-weight: 600;
  cursor: grab;
  transition: all 0.15s;
  background-color: transparent;
  user-select: none;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 3px 10px rgba(0, 0, 0, 0.3);
  }

  &:active {
    cursor: grabbing;
    transform: scale(0.95);
  }

  &.op {
    border-color: #2196F3;
    color: #2196F3;

    &:hover {
      background-color: rgba(33, 150, 243, 0.1);
    }
  }

  &.func {
    border-color: #9C27B0;
    color: #9C27B0;
    border-style: dashed;

    &:hover {
      background-color: rgba(156, 39, 176, 0.1);
    }
  }
}

// ====== 快捷模板 ======
.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
  gap: 8px;
}

.template-card {
  background-color: $color-black;
  border: 1px solid $color-divider;
  border-radius: $radius-sm;
  padding: 10px;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: $brand-primary;
    transform: translateY(-1px);
  }

  .tpl-name {
    font-size: 13px;
    font-weight: 600;
    color: $brand-white;
    margin-bottom: 4px;
  }

  .tpl-desc {
    font-size: 11px;
    color: #888;
    line-height: 1.4;
  }
}

// ====== 常量输入 ======
.const-input-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.const-input {
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

  &:focus {
    border-color: $brand-primary;
  }
}

.btn-add {
  height: 36px;
  padding: 0 16px;
  background-color: $brand-primary;
  color: $brand-white;
  border: none;
  border-radius: $radius-sm;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;

  &:hover {
    opacity: 0.9;
  }
}
</style>
