import apiClient from './client'
import type { ApiResponse } from './types'

/** 打印机信息 */
export interface PrinterInfo {
  printer_id: string
  name: string
  printer_type: 'label' | 'receipt' | 'order'
  brand?: string
  device_sn?: string
  api_url?: string
  api_user?: string
  paper_width: number
  online_status: boolean
  last_heartbeat?: string
  is_active: boolean
}

/** 打印机表单 */
export interface PrinterForm {
  name: string
  printer_type: 'label' | 'receipt' | 'order'
  brand?: string
  device_sn?: string
  api_url?: string
  api_key?: string
  api_user?: string
  api_secret?: string
  paper_width?: number
}

/** 路由规则 */
export interface PrintRoute {
  route_id: string
  name: string
  trigger_event: string
  document_type: string
  filter_type: string
  filter_value?: {
    category_ids?: string[]
    product_ids?: string[]
    order_type?: string[]
  }
  printer_id: string
  printer_name: string
  priority: number
  is_active: boolean
  created_at?: string
}

/** 路由规则表单 */
export interface PrintRouteForm {
  name: string
  trigger_event: string
  document_type: string
  filter_type: string
  filter_value?: {
    category_ids?: string[]
    product_ids?: string[]
    order_type?: string[]
  }
  printer_id: string
  priority?: number
}

/** 分类打印机绑定 */
export interface CategoryPrinter {
  category_id: string
  name: string
  sort_order: number
  printer_id?: string
  printer_name?: string
  backup_printer_id?: string
  backup_printer_name?: string
}

/** 打印结果 */
export interface PrintResult {
  status: 'sent' | 'queued' | 'no_printer' | 'failed'
  printer?: string
  printer_id?: string
  queue_id?: string
  message?: string
}

export const printersAPI = {
  // ==================== 打印机管理 ====================

  /** 获取打印机列表 */
  list() {
    return apiClient.get<ApiResponse<PrinterInfo[]>>('/printers')
  },

  /** 添加打印机 */
  create(data: PrinterForm) {
    return apiClient.post<ApiResponse<{ printer_id: string }>>('/printers', data)
  },

  /** 更新打印机 */
  update(printerId: string, data: Partial<PrinterForm>) {
    return apiClient.put<ApiResponse<void>>(`/printers/${printerId}`, data)
  },

  /** 删除打印机 */
  delete(printerId: string) {
    return apiClient.delete<ApiResponse<void>>(`/printers/${printerId}`)
  },

  /** 测试打印 */
  test(printerId: string) {
    return apiClient.post<ApiResponse<PrintResult>>(`/printers/${printerId}/test`)
  },

  // ==================== 统一打印接口 ====================

  /** 根据分类自动路由打印 */
  printByCategory(data: {
    category_id: string
    content: string
    trigger?: string
    document_type?: string
  }) {
    return apiClient.post<ApiResponse<PrintResult>>('/printers/print', data)
  },

  /** 直接打印到指定打印机 */
  printDirect(data: {
    printer_id: string
    content: string
  }) {
    return apiClient.post<ApiResponse<PrintResult>>('/printers/print/direct', data)
  },

  // ==================== 路由规则管理 ====================

  /** 获取路由规则列表 */
  listRoutes() {
    return apiClient.get<ApiResponse<PrintRoute[]>>('/printers/routes')
  },

  /** 添加路由规则 */
  createRoute(data: PrintRouteForm) {
    return apiClient.post<ApiResponse<{ route_id: string }>>('/printers/routes', data)
  },

  /** 更新路由规则 */
  updateRoute(routeId: string, data: Partial<PrintRouteForm>) {
    return apiClient.put<ApiResponse<void>>(`/printers/routes/${routeId}`, data)
  },

  /** 删除路由规则 */
  deleteRoute(routeId: string) {
    return apiClient.delete<ApiResponse<void>>(`/printers/routes/${routeId}`)
  },

  // ==================== 分类打印机绑定 ====================

  /** 获取分类列表（含打印机绑定） */
  listCategories() {
    return apiClient.get<ApiResponse<CategoryPrinter[]>>('/printers/categories')
  },

  /** 更新分类绑定的打印机 */
  updateCategoryPrinter(categoryId: string, data: {
    printer_id?: string | null
    backup_printer_id?: string | null
  }) {
    return apiClient.put<ApiResponse<void>>(`/printers/categories/${categoryId}/printer`, data)
  },
}
