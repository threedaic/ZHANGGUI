// 共享类型定义（AGENTS.md 铁律：所有 API 类型从此文件导入）

export interface ApiResponse<T = unknown> {
  code: number
  message: string
  data: T
  request_id: string | null
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages: number
}

export interface EmployeeBrief {
  id: string
  name: string
  role: string
}

// 业务错误码（与后端 app/utils/exceptions.py 对齐）
export const ERROR_CODES = {
  SUCCESS: 0,
  VALIDATION: 40001,
  UNAUTHORIZED: 40100,
  FORBIDDEN: 40300,
  NOT_FOUND: 40400,
  CONFLICT: 40900,
  RATE_LIMIT: 42900,
  SERVER_ERROR: 50000,
  EXTERNAL_SERVICE: 50200,
} as const
