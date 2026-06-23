// 公式 AST 工具：构建、序列化、预览
import type {
  FormulaNode,
  FormulaSource,
} from '@/api/payrollConfig'
import { SOURCE_FIELDS, SOURCE_LABELS } from '@/api/payrollConfig'

// 构造常量节点
export function constNode(value: number): FormulaNode {
  return { type: 'const', value }
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
