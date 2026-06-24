import apiClient from './client'
import type { ApiResponse, PageResult } from './types'

export interface WineCreateParams {
  customer_name: string
  phone: string
  wine_name: string
  remaining_ml: number
  quantity?: number
  cabinet_no?: string
  notes?: string
}

export interface WineStaffRetrieveParams {
  bottle_label: string
  retrieve_ml: number
  table_no?: string
}

export interface WineInfo {
  id: string
  store_id: string
  customer_name: string
  phone: string
  wine_name: string
  bottle_label: string | null
  date_stored: string
  initial_ml: number | null
  remaining_ml: number | null
  cabinet_no: string | null
  table_no: string | null
  status: string
  retrieved_at: string | null
  retrieved_by: string | null
  retriever_name: string | null
  retriever_employee_code: string | null
  notes: string | null
  created_at: string | null
  updated_at: string | null
}

export interface InventorySummary {
  total: number
  stored: number
  retrieved: number
}

export interface InventoryItem {
  bottle_label: string | null
  customer_name: string
  wine_name: string
  remaining_ml: number | null
  status: string
}

export const wineAPI = {
  /** 存酒 */
  create(params: WineCreateParams) {
    return apiClient.post<ApiResponse<WineInfo>>('/wine-storage', params)
  },

  /** 存酒列表 */
  list(params?: { status?: string; keyword?: string; search_type?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<WineInfo>>>('/wine-storage', { params })
  },

  /** 存酒详情 */
  getById(id: string) {
    return apiClient.get<ApiResponse<WineInfo>>(`/wine-storage/${id}`)
  },

  /** 服务员取酒 */
  retrieve(params: WineStaffRetrieveParams) {
    return apiClient.post<ApiResponse<{ id: string; bottle_label: string; status: string; remaining_ml: number }>>(
      '/wine-storage/retrieve',
      params
    )
  },

  /** 盘点汇总 */
  inventorySummary() {
    return apiClient.get<ApiResponse<InventorySummary>>('/wine-storage/inventory/summary')
  },

  /** 盘点明细 */
  inventoryItems(params?: { page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<InventoryItem>>>('/wine-storage/inventory/items', { params })
  },

  /** 批量存酒 */
  batchStore(data: {
    customer_name: string
    phone: string
    wines: Array<{ wine_name: string; remaining_ml: number; quantity: number }>
    notes?: string
  }) {
    return apiClient.post<ApiResponse<null>>('/wine-storage/batch', data)
  },
}

// ==================== 盘点单 ====================

export interface StocktakeItem {
  id: string
  stocktake_id: string
  wine_id: string | null
  bottle_label: string
  customer_name: string
  phone: string
  wine_name: string
  expected_ml: number | null
  actual_ml: number | null
  check_status: string  // pending/matched/missing/mismatch
  checked_at: string | null
  checked_by: string | null
  notes: string | null
}

export interface Stocktake {
  id: string
  store_id: string
  period: string
  status: string  // pending/in_progress/completed
  assigned_to: string | null
  total_count: number
  checked_count: number
  matched_count: number
  missing_count: number
  extra_count: number
  started_at: string | null
  completed_at: string | null
  notes: string | null
  created_at: string | null
}

export interface StocktakeScanResult {
  bottle_label: string
  check_status: string  // matched/missing/mismatch/extra
  wine_name: string | null
  customer_name: string | null
  expected_ml: number | null
  actual_ml: number | null
  message: string
}

export const stocktakeAPI = {
  /** 盘点单列表 */
  list(params?: { status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<Stocktake>>>('/wine-storage/stocktake', { params })
  },

  /** 盘点单详情 */
  getById(id: string) {
    return apiClient.get<ApiResponse<Stocktake>>(`/wine-storage/stocktake/${id}`)
  },

  /** 盘点单明细列表 */
  listItems(id: string, params?: { check_status?: string; page?: number; page_size?: number }) {
    return apiClient.get<ApiResponse<PageResult<StocktakeItem>>>(`/wine-storage/stocktake/${id}/items`, { params })
  },

  /** 手动创建盘点单 */
  create(params?: { period?: string }) {
    return apiClient.post<ApiResponse<{ id: string }>>('/wine-storage/stocktake', params || {})
  },

  /** 扫码核对 */
  scan(stocktakeId: string, params: { bottle_label: string; actual_ml?: number }) {
    return apiClient.post<ApiResponse<StocktakeScanResult>>(`/wine-storage/stocktake/${stocktakeId}/scan`, params)
  },

  /** 完成盘点 */
  complete(stocktakeId: string, params?: { notes?: string }) {
    return apiClient.post<ApiResponse<unknown>>(`/wine-storage/stocktake/${stocktakeId}/complete`, params || {})
  },
}
