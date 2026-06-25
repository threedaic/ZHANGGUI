import apiClient from './client'
import type { ApiResponse } from './types'

// 模块信息
export interface ModuleInfo {
  name: string
  always_on: boolean
  color: string
}

// 各模块数据
export interface ContractModule {
  monthly_salary: number
  base_salary: number
  allowance: number
  total: number
}

export interface PerformanceModule {
  total_amount: number
  commission_rate: number
  commission: number
  total: number
}

export interface AttendanceModule {
  late_count: number
  total_late_minutes: number
  late_deduction: number
  absent_count: number
  absent_deduction: number
  early_count: number
  early_deduction: number
  total: number
}

export interface KpiModule {
  coefficient: number
  total_score: number
  bonus: number
  total: number
}

export interface RewardPenaltyModule {
  reward: number
  penalty: number
  total: number
}

export interface OvertimeModule {
  days: number
  daily_wage: number
  multiplier: number
  total: number
}

// 员工工资行
export interface PayrollRow {
  employee_id: string
  employee_name: string
  position: string
  modules: {
    contract: ContractModule
    performance: PerformanceModule
    attendance: AttendanceModule
    kpi: KpiModule
    reward_penalty: RewardPenaltyModule
    overtime: OvertimeModule
  }
  net_pay: number
}

// 汇总
export interface PayrollSummary {
  modules: Record<string, number>
  net_pay: number
  employee_count: number
}

// 大表格响应
export interface PayrollTable {
  period: string
  modules: Record<string, boolean>
  module_info: Record<string, ModuleInfo>
  rules: Record<string, number>
  employees: PayrollRow[]
  summary: PayrollSummary
}

export const autoPayrollAPI = {
  getTable(period: string) {
    return apiClient.get<ApiResponse<PayrollTable>>('/auto-payroll', {
      params: { period },
    })
  },

  calculate(period: string) {
    return apiClient.post<ApiResponse<PayrollTable>>('/auto-payroll/calculate', null, {
      params: { period },
    })
  },

  // 一键发薪：算完存档+推送签收
  finalize(period: string) {
    return apiClient.post<ApiResponse<{
      period: string
      count: number
      tasks_created: number
      total_net_pay: number
    }>>('/auto-payroll/finalize', null, {
      params: { period },
    })
  },

  getModules() {
    return apiClient.get<ApiResponse<{ modules: Record<string, boolean>; module_info: Record<string, ModuleInfo> }>>('/auto-payroll/modules')
  },

  setModules(modules: Partial<Record<string, boolean>>) {
    return apiClient.put<ApiResponse<Record<string, boolean>>>('/auto-payroll/modules', modules)
  },

  getRules() {
    return apiClient.get<ApiResponse<Record<string, number>>>('/auto-payroll/rules')
  },

  setRules(rules: Partial<Record<string, number>>) {
    return apiClient.put<ApiResponse<Record<string, number>>>('/auto-payroll/rules', rules)
  },

  updateCell(employee_id: string, period: string, module: string, amount: number) {
    return apiClient.put<ApiResponse<unknown>>('/auto-payroll/cell', {
      employee_id,
      period,
      module,
      amount,
    })
  },

  // 加班费日历：获取某月的三薪日期
  getOvertimeDays(period: string) {
    return apiClient.get<ApiResponse<Record<string, number>>>('/auto-payroll/overtime-days', {
      params: { period },
    })
  },

  // 加班费日历：保存某月的三薪日期
  setOvertimeDays(period: string, days: Record<string, number>) {
    return apiClient.put<ApiResponse<null>>('/auto-payroll/overtime-days', {
      period,
      days,
    })
  },
}
