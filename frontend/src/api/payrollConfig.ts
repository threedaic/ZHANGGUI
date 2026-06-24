// 工资项配置 API（公式编辑器使用）
import client from './client'
import type { ApiResponse } from './types'

// ====== 公式 AST 类型定义（与后端 formula_engine.py 对齐）======

export type FormulaNode =
  | { type: 'const'; value: number; isPlaceholder?: boolean }
  | { type: 'field'; source: FormulaSource; field: string }
  | { type: 'op'; op: '+' | '-' | '*' | '/'; left: FormulaNode; right: FormulaNode }
  | { type: 'func'; name: 'max' | 'min' | 'round' | 'abs' | 'if'; args: FormulaNode[] }

export type FormulaSource =
  | 'contract'
  | 'attendance'
  | 'performance'
  | 'kpi'
  | 'rule'
  | 'manual'

export type DataSource =
  | 'contract'
  | 'attendance'
  | 'performance'
  | 'kpi'
  | 'rule'
  | 'manual'

export type ItemType = 'income' | 'deduction'

export interface PayrollItemConfig {
  id: string
  item_code: string
  item_name: string
  item_type: ItemType
  data_source: DataSource
  formula_ast: FormulaNode | null
  default_value: number
  is_active: boolean
  is_system: boolean
  sort_order: number
  note: string | null
}

export interface SalaryRule {
  id: string
  rule_code: string
  rule_name: string
  rule_value: number
  rule_unit: string | null
  is_active: boolean
  note: string | null
}

export interface ItemConfigRequest {
  item_code: string
  item_name: string
  item_type: ItemType
  data_source: DataSource
  formula_ast: FormulaNode | null
  default_value: number
  sort_order: number
  note?: string
}

// ====== 数据源字段映射（公式编辑器使用）======

export const SOURCE_FIELDS: Record<FormulaSource, { field: string; label: string }[]> = {
  contract: [
    { field: 'monthly_salary', label: '合同月薪' },
    { field: 'base_salary', label: '底薪' },
    { field: 'meal_allowance', label: '餐补' },
    { field: 'allowance', label: '津贴' },
  ],
  attendance: [
    { field: 'late_count', label: '迟到次数' },
    { field: 'total_late_minutes', label: '迟到总分钟' },
    { field: 'absent_count', label: '旷工天数' },
    { field: 'early_count', label: '早退次数' },
    { field: 'present_days', label: '出勤天数' },
    { field: 'total_days', label: '应出勤天数' },
  ],
  performance: [
    { field: 'total_amount', label: '业绩总额' },
    { field: 'booking', label: '订桌业绩' },
    { field: 'wework_payment', label: '企微收款业绩' },
    { field: 'bottle', label: '存酒业绩' },
    { field: 'card', label: '卡券业绩' },
  ],
  kpi: [
    { field: 'coefficient', label: 'KPI系数' },
    { field: 'total_score', label: 'KPI总分' },
  ],
  rule: [
    { field: 'late_deduction_per_minute', label: '迟到每分钟扣款' },
    { field: 'absent_factor', label: '旷工扣款倍数' },
    { field: 'early_deduction_per_time', label: '早退每次扣款' },
    { field: 'commission_rate', label: '提成比例' },
    { field: 'rest_days_per_month', label: '月休息天数' },
  ],
  manual: [],
}

export const SOURCE_LABELS: Record<FormulaSource, string> = {
  contract: '合同',
  attendance: '考勤',
  performance: '业绩',
  kpi: 'KPI',
  rule: '规则',
  manual: '手工',
}

export const FUNCTIONS = [
  { name: 'max', label: '最大值 max(a,b,...)', argCount: 2 },
  { name: 'min', label: '最小值 min(a,b,...)', argCount: 2 },
  { name: 'round', label: '四舍五入 round(x,位数)', argCount: 2 },
  { name: 'abs', label: '绝对值 abs(x)', argCount: 1 },
  { name: 'if', label: '条件 if(条件,真,假)', argCount: 3 },
] as const

// ====== API 方法 ======

export function listItems() {
  return client.get<ApiResponse<PayrollItemConfig[]>>('/payroll-config/items')
}

export function upsertItem(body: ItemConfigRequest) {
  return client.post<ApiResponse<null>>('/payroll-config/items', body)
}

export function deleteItem(item_code: string) {
  return client.delete<ApiResponse<null>>(`/payroll-config/items/${item_code}`)
}

export function listRules() {
  return client.get<ApiResponse<SalaryRule[]>>('/payroll-config/rules')
}

export function updateRule(rule_code: string, rule_value: number) {
  return client.put<ApiResponse<null>>(`/payroll-config/rules/${rule_code}`, {
    rule_value,
  })
}

export function toggleRule(rule_code: string, is_active: boolean) {
  return client.put<ApiResponse<null>>(`/payroll-config/rules/${rule_code}/toggle`, {
    is_active,
  })
}

export function initConfig() {
  return client.post<ApiResponse<null>>('/payroll-config/init')
}
