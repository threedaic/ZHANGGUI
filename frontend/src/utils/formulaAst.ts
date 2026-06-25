// 公式 AST 工具：构建、序列化、预览
import type {
  FormulaNode,
  FormulaSource,
} from '@/api/payrollConfig'
import { SOURCE_FIELDS, SOURCE_LABELS } from '@/api/payrollConfig'

// 构造常量节点（isPlaceholder=false 表示真实常量，区别于占位槽位的 const(0)）
export function constNode(value: number): FormulaNode {
  return { type: 'const', value, isPlaceholder: false }
}

// 构造占位槽位节点（渲染为"拖入"槽位，不会传给后端）
export function placeholderNode(): FormulaNode {
  return { type: 'const', value: 0, isPlaceholder: true }
}

// 判断是否为占位槽位
export function isPlaceholder(node: FormulaNode): boolean {
  return node.type === 'const' && node.isPlaceholder === true
}

// 构造字段引用节点
export function fieldNode(source: FormulaSource, field: string): FormulaNode {
  return { type: 'field', source, field }
}

// 构造运算节点
export function opNode(
  op: '+' | '-' | '*' | '/',
  left: FormulaNode,
  right: FormulaNode
): FormulaNode {
  return { type: 'op', op, left, right }
}

// 构造函数节点
export function funcNode(
  name: 'max' | 'min' | 'round' | 'abs' | 'if',
  args: FormulaNode[]
): FormulaNode {
  return { type: 'func', name, args }
}

// 将 AST 转为可读字符串（用于预览）
export function astToString(node: FormulaNode | null): string {
  if (!node) return ''
  switch (node.type) {
    case 'const':
      if (isPlaceholder(node)) return '?'
      return String(node.value)
    case 'field': {
      const label =
        SOURCE_FIELDS[node.source]?.find((f) => f.field === node.field)?.label ??
        node.field
      return `[${SOURCE_LABELS[node.source]}.${label}]`
    }
    case 'op':
      return `(${astToString(node.left)} ${node.op} ${astToString(node.right)})`
    case 'func':
      return `${node.name}(${node.args.map(astToString).join(', ')})`
  }
}

// 将 AST 转为大白话描述（给老板看的人话）
// 例如: op(*, field(performance.total_amount), field(rule.commission_rate))
//    => "业绩总额 × 提成比例"
const OP_SYMBOLS: Record<string, string> = {
  '+': ' + ',
  '-': ' - ',
  '*': ' × ',
  '/': ' ÷ ',
}

const FUNC_LABELS: Record<string, string> = {
  max: '取最大',
  min: '取最小',
  round: '四舍五入',
  abs: '绝对值',
  if: '条件判断',
}

export function astToHumanReadable(node: FormulaNode | null): string {
  if (!node) return '未配置'
  switch (node.type) {
    case 'const':
      if (isPlaceholder(node)) return '？'
      return String(node.value)
    case 'field': {
      const label =
        SOURCE_FIELDS[node.source]?.find((f) => f.field === node.field)?.label ??
        node.field
      return label
    }
    case 'op': {
      const left = astToHumanReadable(node.left)
      const right = astToHumanReadable(node.right)
      return `${left}${OP_SYMBOLS[node.op] ?? ' ' + node.op + ' '}${right}`
    }
    case 'func': {
      const label = FUNC_LABELS[node.name] ?? node.name
      const args = node.args.map(astToHumanReadable).join('，')
      return `${label}(${args})`
    }
  }
}

// 深拷贝 AST
export function cloneAst(node: FormulaNode | null): FormulaNode | null {
  if (!node) return null
  switch (node.type) {
    case 'const':
      return { ...node }
    case 'field':
      return { ...node }
    case 'op':
      return {
        ...node,
        left: cloneAst(node.left)!,
        right: cloneAst(node.right)!,
      }
    case 'func':
      return { ...node, args: node.args.map((a) => cloneAst(a)!) }
  }
}

// 校验 AST 完整性（无空字段）
export function validateAst(node: FormulaNode | null): string | null {
  if (!node) return '公式不能为空'
  switch (node.type) {
    case 'const':
      if (isPlaceholder(node)) return '存在未填入的槽位'
      if (typeof node.value !== 'number' || Number.isNaN(node.value)) {
        return '常量值无效'
      }
      return null
    case 'field':
      if (!node.source || !node.field) return '字段引用不完整'
      return null
    case 'op':
      return validateAst(node.left) || validateAst(node.right)
    case 'func': {
      if (node.args.length === 0) return `函数 ${node.name} 缺少参数`
      for (const arg of node.args) {
        const err = validateAst(arg)
        if (err) return err
      }
      return null
    }
  }
}
