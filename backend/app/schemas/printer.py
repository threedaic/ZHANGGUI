"""打印机模块 Pydantic Schema

用于 API 请求体验证
"""
from __future__ import annotations

import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from pydantic import BaseModel, Field


# ==================== 打印机 Schema ====================

class PrinterCreate(BaseModel):
    """创建打印机请求体"""
    name: str = Field(..., min_length=1, max_length=50, description="打印机名称")
    printer_type: str = Field(default="order", pattern="^(label|receipt|order)$", description="打印机类型")
    brand: Optional[str] = Field(None, max_length=50, description="品牌")
    device_sn: Optional[str] = Field(None, max_length=100, description="设备SN")
    api_url: Optional[str] = Field(None, description="API地址")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_user: Optional[str] = Field(None, max_length=100, description="API账号")
    api_secret: Optional[str] = Field(None, description="API密钥")
    paper_width: int = Field(default=80, ge=30, le=110, description="纸宽mm")
    extra_config: Optional[Dict[str, Any]] = Field(default_factory=dict, description="扩展配置(标签机可设label_width/label_height)")


class PrinterUpdate(BaseModel):
    """更新打印机请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="打印机名称")
    printer_type: Optional[str] = Field(None, pattern="^(label|receipt|order)$", description="打印机类型")
    brand: Optional[str] = Field(None, max_length=50, description="品牌")
    device_sn: Optional[str] = Field(None, max_length=100, description="设备SN")
    api_url: Optional[str] = Field(None, description="API地址")
    api_key: Optional[str] = Field(None, description="API密钥")
    api_user: Optional[str] = Field(None, max_length=100, description="API账号")
    api_secret: Optional[str] = Field(None, description="API密钥")
    paper_width: Optional[int] = Field(None, ge=30, le=110, description="纸宽mm")
    extra_config: Optional[Dict[str, Any]] = Field(None, description="扩展配置")
    is_active: Optional[bool] = Field(None, description="是否启用")


class PrinterResponse(BaseModel):
    """打印机响应体"""
    printer_id: str
    name: str
    printer_type: str
    brand: Optional[str]
    device_sn: Optional[str]
    api_user: Optional[str]
    paper_width: int
    online_status: bool
    last_heartbeat: Optional[str]
    is_active: bool
    extra_config: Optional[Dict[str, Any]] = None
    created_at: Optional[str]


# ==================== 路由规则 Schema ====================

class PrintRouteCreate(BaseModel):
    """创建路由规则请求体"""
    name: str = Field(..., min_length=1, max_length=100, description="规则名称")
    trigger_event: str = Field(
        default="order_created",
        pattern="^(order_created|payment_completed|manual)$",
        description="触发时机"
    )
    document_type: str = Field(
        default="order",
        pattern="^(order|receipt|label)$",
        description="文档类型"
    )
    filter_type: str = Field(
        default="category",
        pattern="^(category|product|order_type|all)$",
        description="匹配条件"
    )
    filter_value: Optional[Dict[str, Any]] = Field(None, description="匹配值")
    printer_id: str = Field(..., description="目标打印机ID")
    priority: int = Field(default=1, ge=1, le=99, description="优先级")


class PrintRouteUpdate(BaseModel):
    """更新路由规则请求体"""
    name: Optional[str] = Field(None, min_length=1, max_length=100, description="规则名称")
    trigger_event: Optional[str] = Field(
        None,
        pattern="^(order_created|payment_completed|manual)$",
        description="触发时机"
    )
    document_type: Optional[str] = Field(
        None,
        pattern="^(order|receipt|label)$",
        description="文档类型"
    )
    filter_type: Optional[str] = Field(
        None,
        pattern="^(category|product|order_type|all)$",
        description="匹配条件"
    )
    filter_value: Optional[Dict[str, Any]] = Field(None, description="匹配值")
    printer_id: Optional[str] = Field(None, description="目标打印机ID")
    priority: Optional[int] = Field(None, ge=1, le=99, description="优先级")
    is_active: Optional[bool] = Field(None, description="是否启用")


class PrintRouteResponse(BaseModel):
    """路由规则响应体"""
    route_id: str
    name: str
    trigger_event: str
    document_type: str
    filter_type: str
    filter_value: Optional[Dict[str, Any]]
    printer_id: str
    printer_name: str
    priority: int
    is_active: bool
    created_at: Optional[str]


# ==================== 打印请求 Schema ====================

class PrintByCategoryRequest(BaseModel):
    """按分类打印请求体"""
    category_id: str = Field(..., description="分类ID")
    content: str = Field(..., min_length=1, description="打印内容")
    trigger: str = Field(
        default="order_created",
        pattern="^(order_created|payment_completed|manual)$",
        description="触发时机"
    )
    document_type: str = Field(
        default="order",
        pattern="^(order|receipt|label)$",
        description="文档类型"
    )


class PrintDirectRequest(BaseModel):
    """直接打印请求体"""
    printer_id: str = Field(..., description="打印机ID")
    content: str = Field(..., min_length=1, description="打印内容")


# ==================== 分类打印机绑定 Schema ====================

class CategoryPrinterUpdate(BaseModel):
    """分类打印机绑定更新请求体"""
    printer_id: Optional[str] = Field(None, description="主打印机ID")
    backup_printer_id: Optional[str] = Field(None, description="备用打印机ID")


class CategoryPrinterResponse(BaseModel):
    """分类打印机绑定响应体"""
    category_id: str
    name: str
    sort_order: int
    printer_id: Optional[str]
    printer_name: Optional[str]
    backup_printer_id: Optional[str]
    backup_printer_name: Optional[str]


# ==================== 模块打印配置 Schema ====================

class ModulePrintConfigUpdate(BaseModel):
    """模块打印配置更新请求体"""
    enabled: Optional[bool] = Field(None, description="是否启用")
    printer_id: Optional[str] = Field(None, description="指定打印机ID")


class ModulePrintConfigBatchUpdate(BaseModel):
    """模块打印配置批量更新请求体"""
    updates: list[ModulePrintConfigUpdate] = Field(..., description="更新列表")


class ModulePrintConfigResponse(BaseModel):
    """模块打印配置响应体"""
    config_id: str
    module_code: str
    scene_code: str
    scene_name: str
    description: Optional[str]
    document_type: str
    trigger_event: str
    printer_type: str
    enabled: bool
    printer_id: Optional[str]
    printer_name: Optional[str]
