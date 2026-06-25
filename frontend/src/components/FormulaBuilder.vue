<script setup lang="ts">
// 拼积木式可视化公式构建器
// 点击下方积木块自动添加到公式区，公式像真正的数学公式一样用彩色方块横向排列
// 支持拖动排序、点击删除、高端 CSS 动画
import { ref, computed, watch, nextTick } from 'vue'
import {
  SOURCE_FIELDS,
  SOURCE_LABELS,
  type FormulaNode,
  type FormulaSource,
} from '@/api/payrollConfig'

const props = defineProps<{
  modelValue: FormulaNode | null
}>()
const emit = defineEmits<{
  (e: 'update:modelValue', value: FormulaNode | null): void
}>()

// ====== Token 数据结构（线性公式表示）======
interface Token {
  id: string
  kind: 'field' | 'op' | 'const'
  label: string
  color: string
  // field
  source?: FormulaSource
  field?: string
  // op
  op?: '+' | '-' | '*' | '/'
  // const
  value?: number
}

let idCounter = 0
function genId(): string {
  return `tk_${Date.now()}_${idCounter++}`
}

// ====== 颜色配置 ======
const SOURCE_COLORS: Record<FormulaSource, string> = {
  contract: '#4CAF50',
  attendance: '#FF9800',
  performance: '#E91E63',
  kpi: '#00BCD4',
  rule: '#9C27B0',
  manual: '#607D8B',
}

const SOURCE_GRADIENTS: Record<FormulaSource, string> = {
  contract: 'linear-gradient(135deg, #4CAF50, #2E7D32)',
  attendance: 'linear-gradient(135deg, #FF9800, #E65100)',
  performance: 'linear-gradient(135deg, #E91E63, #AD1457)',
  kpi: 'linear-gradient(135deg, #00BCD4, #006064)',
  rule: 'linear-gradient(135deg, #9C27B0, #4A148C)',
  manual: 'linear-gradient(135deg, #607D8B, #37474F)',
}

const OP_LABELS: Record<string, string> = {
  '+': '+',
  '-': '−',
  '*': '×',
  '/': '÷',
}

// ====== Token 数组（本地编辑状态）======
const tokens = ref<Token[]>([])
const constInput = ref('')
const expandedSource = ref<Set<string>>(new Set(['contract', 'attendance']))

// 拖动状态
const dragIndex = ref<number | null>(null)
const dragOverIndex = ref<number | null>(null)

// ====== AST <-> Token 转换 ======

// AST -> Tokens（中序遍历）
function astToTokens(node: FormulaNode | null): Token[] {
  if (!node) return []
  const result: Token[] = []
  function inorder(n: FormulaNode) {
    if (n.type === 'const') {
      result.push({
        id: genId(),
        kind: 'const',
        label: String(n.value),
        color: '#607D8B',
        value: n.value,
      })
    } else if (n.type === 'field') {
      const label =
        SOURCE_FIELDS[n.source]?.find((f) => f.field === n.field)?.label ?? n.field
      result.push({
        id: genId(),
        kind: 'field',
        label,
        color: SOURCE_COLORS[n.source] ?? '#607D8B',
        source: n.source,
        field: n.field,
      })
    } else if (n.type === 'op') {
      inorder(n.left)
      result.push({
        id: genId(),
        kind: 'op',
        label: OP_LABELS[n.op] ?? n.op,
        color: '#2196F3',
        op: n.op,
      })
      inorder(n.right)
    }
  }
  inorder(node)
  return result
}

// Tokens -> AST（递归下降解析，处理运算符优先级）
function tokensToAst(toks: Token[]): FormulaNode | null {
  if (toks.length === 0) return null
  let pos = 0

  function parseExpr(): FormulaNode | null {
    let left = parseTerm()
    if (!left) return null
    while (pos < toks.length && toks[pos].kind === 'op' &&
           (toks[pos].op === '+' || toks[pos].op === '-')) {
      const op = toks[pos].op as '+' | '-'
      pos++
      const right = parseTerm()
      if (!right) return left
      left = { type: 'op', op, left, right }
    }
    return left
  }

  function parseTerm(): FormulaNode | null {
    let left = parseFactor()
    if (!left) return null
    while (pos < toks.length && toks[pos].kind === 'op' &&
           (toks[pos].op === '*' || toks[pos].op === '/')) {
      const op = toks[pos].op as '*' | '/'
      pos++
      const right = parseFactor()
      if (!right) return left
      left = { type: 'op', op, left, right }
    }
    return left
  }

  function parseFactor(): FormulaNode | null {
    if (pos >= toks.length) return null
    const t = toks[pos]
    if (t.kind === 'const') {
      pos++
      return { type: 'const', value: t.value ?? 0, isPlaceholder: false }
    }
    if (t.kind === 'field') {
      pos++
      return { type: 'field', source: t.source!, field: t.field! }
    }
    // op 不能作为 factor，跳过
    if (t.kind === 'op') return null
    return null
  }

  return parseExpr()
}

// ====== 同步（用 syncing 标志避免双向 watch 循环）======
let syncing = false

watch(
  () => props.modelValue,
  (v) => {
    if (syncing) return
    tokens.value = astToTokens(v)
  },
  { immediate: true }
)

watch(
  tokens,
  (v) => {
    syncing = true
    const ast = tokensToAst(v)
    emit('update:modelValue', ast)
    nextTick(() => { syncing = false })
  },
  { deep: true }
)

// ====== 操作 ======
function addField(source: FormulaSource, field: string) {
  const label = SOURCE_FIELDS[source]?.find((f) => f.field === field)?.label ?? field
  // 如果上一个不是运算符且不是空，自动加 +
  const last = tokens.value[tokens.value.length - 1]
  if (last && last.kind !== 'op') {
    tokens.value.push({
      id: genId(),
      kind: 'op',
      label: '+',
      color: '#2196F3',
      op: '+',
    })
  }
  tokens.value.push({
    id: genId(),
    kind: 'field',
    label,
    color: SOURCE_COLORS[source],
    source,
    field,
  })
}

function addOp(op: '+' | '-' | '*' | '/') {
  // 运算符不能连续出现
  const last = tokens.value[tokens.value.length - 1]
  if (last && last.kind === 'op') {
    // 替换上一个运算符
    last.op = op
    last.label = OP_LABELS[op]
    return
  }
  if (!last) return // 不能以运算符开头
  tokens.value.push({
    id: genId(),
    kind: 'op',
    label: OP_LABELS[op],
    color: '#2196F3',
    op,
  })
}

function addConst() {
  const v = parseFloat(constInput.value)
  if (Number.isNaN(v)) return
  const last = tokens.value[tokens.value.length - 1]
  if (last && last.kind !== 'op') {
    tokens.value.push({
      id: genId(),
      kind: 'op',
      label: '+',
      color: '#2196F3',
      op: '+',
    })
  }
  tokens.value.push({
    id: genId(),
    kind: 'const',
    label: String(v),
    color: '#607D8B',
    value: v,
  })
  constInput.value = ''
}

function removeToken(index: number) {
  const removed = tokens.value[index]
  tokens.value.splice(index, 1)
  // 如果删除的是操作数，且两边都是运算符，删除多余的那个
  if (removed.kind !== 'op') {
    const prev = tokens.value[index - 1]
    const next = tokens.value[index]
    if (prev?.kind === 'op' && next?.kind === 'op') {
      tokens.value.splice(index, 1) // 删除多余的运算符
    }
    // 如果删完后第一个是运算符，删除它
    if (tokens.value.length > 0 && tokens.value[0].kind === 'op') {
      tokens.value.shift()
    }
    // 如果最后一个是运算符，删除它
    if (tokens.value.length > 0 && tokens.value[tokens.value.length - 1].kind === 'op') {
      tokens.value.pop()
    }
  } else {
    // 如果删除的是运算符，把两边的操作数用 + 连接
    const prev = tokens.value[index - 1]
    const next = tokens.value[index]
    if (prev && next && prev.kind !== 'op' && next.kind !== 'op') {
      tokens.value.splice(index, 0, {
        id: genId(),
        kind: 'op',
        label: '+',
        color: '#2196F3',
        op: '+',
      })
    }
  }
}

function clearAll() {
  tokens.value = []
}

// ====== 拖动排序 ======
function onDragStart(index: number) {
  dragIndex.value = index
}

function onDragOver(e: DragEvent, index: number) {
  e.preventDefault()
  dragOverIndex.value = index
}

function onDrop(index: number) {
  if (dragIndex.value === null || dragIndex.value === index) {
    dragIndex.value = null
    dragOverIndex.value = null
    return
  }
  const item = tokens.value.splice(dragIndex.value, 1)[0]
  tokens.value.splice(index, 0, item)
  dragIndex.value = null
  dragOverIndex.value = null
}

function onDragEnd() {
  dragIndex.value = null
  dragOverIndex.value = null
}

// ====== 预览 ======
const preview = computed(() => {
  if (tokens.value.length === 0) return ''
  return tokens.value.map((t) => t.label).join(' ')
})

const isValid = computed(() => {
  if (tokens.value.length === 0) return false
  const last = tokens.value[tokens.value.length - 1]
  return last.kind !== 'op' // 最后一个不能是运算符
})

// ====== 积木块面板 ======
function toggleSource(source: string) {
  if (expandedSource.value.has(source)) {
    expandedSource.value.delete(source)
  } else {
    expandedSource.value.add(source)
  }
}

const fieldBlocks = computed(() => {
  const result: Record<string, { source: FormulaSource; field: string; label: string }[]> = {}
  for (const [source, fields] of Object.entries(SOURCE_FIELDS)) {
    if (source === 'manual') continue
    result[source] = fields.map((f) => ({
      source: source as FormulaSource,
      field: f.field,
      label: f.label,
    }))
  }
  return result
})
</script>

<template>
  <div class="formula-builder">
    <!-- ====== 公式画布 ====== -->
    <div class="canvas-area">
      <div class="canvas-header">
        <span class="canvas-label">公式</span>
        <div class="canvas-actions">
          <button
            v-if="tokens.length > 0"
            class="action-btn clear"
            title="清空"
            @click="clearAll"
          >
            ✕ 清空
          </button>
        </div>
      </div>

      <!-- 公式方块区 -->
      <div
        class="formula-track"
        :class="{ empty: tokens.length === 0 }"
        @dragover.prevent
      >
        <transition-group name="block" tag="div" class="formula-row">
          <div
            v-for="(token, index) in tokens"
            :key="token.id"
            class="block"
            :class="[
              token.kind,
              { dragging: dragIndex === index, 'drag-over': dragOverIndex === index && dragIndex !== index }
            ]"
            :style="token.kind === 'field' ? { background: SOURCE_GRADIENTS[token.source!] } : {}"
            draggable="true"
            @dragstart="onDragStart(index)"
            @dragover="onDragOver($event, index)"
            @drop="onDrop(index)"
            @dragend="onDragEnd"
          >
            <span class="block-label">{{ token.label }}</span>
            <button class="block-remove" @click.stop="removeToken(index)">×</button>
          </div>
        </transition-group>

        <!-- 空状态 -->
        <div v-if="tokens.length === 0" class="empty-hint">
          <div class="empty-icon">🧩</div>
          <div class="empty-text">点击下方积木块，自动拼成公式</div>
        </div>
      </div>

      <!-- 预览 -->
      <div v-if="tokens.length > 0" class="preview-row">
        <span class="preview-label">=</span>
        <span class="preview-text" :class="{ invalid: !isValid }">{{ preview }}</span>
        <span v-if="!isValid" class="invalid-tip">公式不完整</span>
      </div>
    </div>

    <!-- ====== 积木块库 ====== -->
    <div class="palette">
      <!-- 数据字段 -->
      <div
        v-for="(blocks, source) in fieldBlocks"
        :key="source"
        class="palette-group"
      >
        <div class="palette-header" @click="toggleSource(source)">
          <span
            class="source-dot"
            :style="{ background: SOURCE_COLORS[source as FormulaSource] }"
          />
          <span class="source-name">{{ SOURCE_LABELS[source as FormulaSource] }}</span>
          <span class="source-count">{{ blocks.length }}</span>
          <span class="expand-icon">{{ expandedSource.has(source) ? '▾' : '▸' }}</span>
        </div>
        <transition name="expand">
          <div v-show="expandedSource.has(source)" class="palette-body">
            <button
              v-for="b in blocks"
              :key="b.field"
              class="field-chip"
              :style="{
                '--chip-color': SOURCE_COLORS[b.source],
                '--chip-grad': SOURCE_GRADIENTS[b.source],
              }"
              @click="addField(b.source, b.field)"
            >
              {{ b.label }}
            </button>
          </div>
        </transition>
      </div>

      <!-- 运算符 -->
      <div class="palette-group">
        <div class="palette-header" @click="toggleSource('__ops')">
          <span class="source-dot" style="background: #2196F3" />
          <span class="source-name">运算符</span>
          <span class="expand-icon">{{ expandedSource.has('__ops') ? '▾' : '▸' }}</span>
        </div>
        <transition name="expand">
          <div v-show="expandedSource.has('__ops')" class="palette-body">
            <button class="op-chip plus" @click="addOp('+')">＋ 加</button>
            <button class="op-chip minus" @click="addOp('-')">－ 减</button>
            <button class="op-chip mul" @click="addOp('*')">×</button>
            <button class="op-chip div" @click="addOp('/')">÷</button>
          </div>
        </transition>
      </div>

      <!-- 数字 -->
      <div class="palette-group">
        <div class="palette-header" @click="toggleSource('__const')">
          <span class="source-dot" style="background: #607D8B" />
          <span class="source-name">数字</span>
          <span class="expand-icon">{{ expandedSource.has('__const') ? '▾' : '▸' }}</span>
        </div>
        <transition name="expand">
          <div v-show="expandedSource.has('__const')" class="palette-body">
            <div class="const-row">
              <input
                v-model="constInput"
                type="number"
                class="const-input"
                placeholder="输入数字"
                @keyup.enter="addConst"
              />
              <button class="const-add-btn" @click="addConst">添加</button>
            </div>
          </div>
        </transition>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.formula-builder {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

// ====== 公式画布 ======
.canvas-area {
  background: linear-gradient(180deg, #1a1a1a, #0d0d0d);
  border: 1px solid rgba(251, 0, 121, 0.15);
  border-radius: 12px;
  padding: 14px;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.03);
}

.canvas-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.canvas-label {
  font-size: 11px;
  color: #666;
  text-transform: uppercase;
  letter-spacing: 2px;
  font-weight: 600;
}

.canvas-actions {
  display: flex;
  gap: 6px;
}

.action-btn {
  padding: 3px 10px;
  font-size: 11px;
  background: transparent;
  border: 1px solid #333;
  border-radius: 10px;
  color: #888;
  cursor: pointer;
  transition: all 0.15s;

  &:hover {
    border-color: #ff0079;
    color: #ff0079;
  }
}

// 公式轨道
.formula-track {
  min-height: 64px;
  border-radius: 8px;
  padding: 10px;
  background: rgba(0, 0, 0, 0.3);
  border: 1px dashed #222;
  transition: border-color 0.2s;

  &.empty {
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.formula-row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
}

// ====== 公式方块 ======
.block {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 8px 14px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: grab;
  user-select: none;
  transition: transform 0.15s, box-shadow 0.15s;
  animation: blockIn 0.25s ease-out;

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);

    .block-remove {
      opacity: 1;
    }
  }

  &:active {
    cursor: grabbing;
    transform: scale(0.95);
  }

  &.dragging {
    opacity: 0.4;
    transform: scale(0.9);
  }

  &.drag-over {
    transform: translateX(4px);
    box-shadow: 0 0 0 2px #ff0079;
  }

  // 字段方块：渐变背景
  &.field {
    color: #fff;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);
  }

  // 运算符方块：圆形
  &.op {
    width: 36px;
    height: 36px;
    padding: 0;
    justify-content: center;
    border-radius: 50%;
    background: linear-gradient(135deg, #2196F3, #1565C0);
    color: #fff;
    font-size: 18px;
    box-shadow: 0 2px 8px rgba(33, 150, 243, 0.3);
  }

  // 常量方块
  &.const {
    background: linear-gradient(135deg, #607D8B, #37474F);
    color: #fff;
    font-family: 'SF Mono', 'Fira Code', monospace;
    box-shadow: 0 2px 8px rgba(96, 125, 139, 0.3);
  }
}

.block-label {
  pointer-events: none;
}

.block-remove {
  position: absolute;
  top: -6px;
  right: -6px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: #ff0079;
  color: #fff;
  border: 2px solid #1a1a1a;
  font-size: 12px;
  font-weight: 700;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.15s;
  display: flex;
  align-items: center;
  justify-content: center;
  line-height: 1;
  padding: 0;

  &:hover {
    transform: scale(1.2);
  }
}

// 空状态
.empty-hint {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;

  .empty-icon {
    font-size: 28px;
    opacity: 0.4;
  }

  .empty-text {
    font-size: 13px;
    color: #555;
  }
}

// 预览
.preview-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 10px;
  padding: 8px 10px;
  background: rgba(0, 0, 0, 0.4);
  border-radius: 6px;
}

.preview-label {
  font-size: 14px;
  color: #ff0079;
  font-weight: 700;
}

.preview-text {
  font-family: 'SF Mono', 'Fira Code', monospace;
  font-size: 13px;
  color: #ccc;

  &.invalid {
    color: #666;
  }
}

.invalid-tip {
  font-size: 11px;
  color: #ff0079;
  margin-left: auto;
}

// ====== 积木块库 ======
.palette {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.palette-group {
  background: #161616;
  border: 1px solid #222;
  border-radius: 8px;
  overflow: hidden;
}

.palette-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;

  &:hover {
    background: #1e1e1e;
  }

  .source-dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .source-name {
    font-size: 13px;
    font-weight: 600;
    color: #ddd;
  }

  .source-count {
    font-size: 10px;
    color: #555;
    background: #0d0d0d;
    padding: 1px 6px;
    border-radius: 8px;
  }

  .expand-icon {
    margin-left: auto;
    font-size: 12px;
    color: #555;
  }
}

.palette-body {
  padding: 8px 14px 12px;
  border-top: 1px solid #1a1a1a;
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

// 字段积木块
.field-chip {
  padding: 7px 14px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  border: none;
  color: #fff;
  background: var(--chip-grad);
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.3);
  transition: transform 0.15s, box-shadow 0.15s;
  text-shadow: 0 1px 2px rgba(0, 0, 0, 0.3);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }

  &:active {
    transform: scale(0.92);
  }
}

// 运算符积木块
.op-chip {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  border: none;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  color: #fff;
  transition: transform 0.15s, box-shadow 0.15s;

  &.plus {
    background: linear-gradient(135deg, #4CAF50, #2E7D32);
  }
  &.minus {
    background: linear-gradient(135deg, #FF9800, #E65100);
  }
  &.mul {
    background: linear-gradient(135deg, #9C27B0, #6A1B9A);
  }
  &.div {
    background: linear-gradient(135deg, #00BCD4, #006064);
  }

  &:hover {
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.5);
  }

  &:active {
    transform: scale(0.9);
  }
}

// 数字输入
.const-row {
  display: flex;
  gap: 6px;
  align-items: center;
}

.const-input {
  width: 100px;
  height: 36px;
  background: #0d0d0d;
  border: 1px solid #333;
  border-radius: 6px;
  padding: 0 10px;
  color: #fff;
  font-size: 14px;
  outline: none;
  font-family: 'SF Mono', monospace;

  &:focus {
    border-color: #ff0079;
  }
}

.const-add-btn {
  height: 36px;
  padding: 0 16px;
  background: linear-gradient(135deg, #607D8B, #37474F);
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;

  &:hover {
    opacity: 0.9;
  }
}

// ====== 动画 ======
@keyframes blockIn {
  from {
    opacity: 0;
    transform: scale(0.5) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

// transition-group 动画
.block-enter-active {
  transition: all 0.25s ease-out;
}
.block-leave-active {
  transition: all 0.2s ease-in;
  position: absolute;
}
.block-enter-from {
  opacity: 0;
  transform: scale(0.5) translateY(10px);
}
.block-leave-to {
  opacity: 0;
  transform: scale(0.5);
}
.block-move {
  transition: transform 0.25s ease;
}

// expand 动画
.expand-enter-active,
.expand-leave-active {
  transition: all 0.2s ease;
  overflow: hidden;
}
.expand-enter-from,
.expand-leave-to {
  opacity: 0;
  max-height: 0;
}
.expand-enter-to,
.expand-leave-from {
  opacity: 1;
  max-height: 300px;
}
</style>
