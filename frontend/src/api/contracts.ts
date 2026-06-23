import apiClient from './client'
import type { ApiResponse, EmployeeBrief, PageResult } from './types'

// 重新导出共享类型，便于视图层从 contracts.ts 统一导入
export type { EmployeeBrief }

// ---- 类型定义 ----

export interface SalaryMatrixItem {
  id: string
  position: string
  grade: string
  monthly_salary: number
  base_salary: number
  meal_allowance: number
  is_active: boolean
}

export interface ContractItem {
  id: string
  store_id: string
  employee_id: string
  employee_name: string
  contract_no: string
  position: string
  grade: string
  monthly_salary: number
  base_salary: number
  meal_allowance: number
  allowance: number
  start_date: string
  end_date: string | null
  status: string
  esign_flow_id: string | null
  signed_at: string | null
  created_at: string | null
  updated_at: string | null
}

export interface ContractDetail extends ContractItem {
  template_data: Record<string, unknown> | null
}

export interface ContractCreateParams {
  employee_id: string
  position: string
  grade: string
  monthly_salary: number
  start_date: string
  end_date?: string | null
}

export interface ContractUpdateParams {
  position?: string
  grade?: string
  monthly_salary?: number
  start_date?: string
  end_date?: string | null
  status?: string
}

export interface ContractListParams {
  page?: number
  page_size?: number
  status?: string
  employee_id?: string
  position?: string
}

// ---- API ----

export const contractsAPI = {
  // 薪资矩阵
  getSalaryMatrix() {
    return apiClient.get<ApiResponse<SalaryMatrixItem[]>>('/contracts/salary-matrix')
  },

  updateSalaryMatrix(id: string, data: { monthly_salary?: number; is_active?: boolean }) {
    return apiClient.put<ApiResponse<SalaryMatrixItem>>(`/contracts/salary-matrix/${id}`, data)
  },

  // 合同列表
  listContracts(params: ContractListParams = {}) {
    return apiClient.get<ApiResponse<PageResult<ContractItem>>>('/contracts', { params })
  },

  // 可签约员工列表
  listEmployees() {
    return apiClient.get<ApiResponse<EmployeeBrief[]>>('/contracts/employees')
  },

  // 创建合同
  createContract(data: ContractCreateParams) {
    return apiClient.post<ApiResponse<ContractDetail>>('/contracts', data)
  },

  // 合同详情
  getContract(id: string) {
    return apiClient.get<ApiResponse<ContractDetail>>(`/contracts/${id}`)
  },

  // 更新合同
  updateContract(id: string, data: ContractUpdateParams) {
    return apiClient.put<ApiResponse<ContractDetail>>(`/contracts/${id}`, data)
  },

  // 删除合同
  deleteContract(id: string) {
    return apiClient.delete<ApiResponse<null>>(`/contracts/${id}`)
  },

  // 发起电子签
  sendForSign(id: string) {
    return apiClient.post<ApiResponse<{ flow_id: string; status: string; message: string }>>(`/contracts/${id}/send-sign`)
  },
}
