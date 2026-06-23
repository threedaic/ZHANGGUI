"""
工资项配置 API 路由
/api/v1/payroll-config/

GET    /items          工资项列表
POST   /items          新增/更新工资项
DELETE /items/{code}   删除工资项（非系统项）
GET    /rules          薪资规则列表
PUT    /rules/{code}   更新薪资规则
POST   /init           初始化默认配置
"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.payroll_config import PayrollConfigService
from app.utils.deps import get_store_id, require_role, make_response

router = APIRouter()


class ItemConfigRequest(BaseModel):
    item_code: str
    item_name: str
    item_type: str  # income / deduction
    data_source: str  # contract / attendance / performance / kpi / rule / manual
    formula_ast: dict | None = None
    default_value: float = 0
    sort_order: int = 0
    note: str | None = None


class RuleUpdateRequest(BaseModel):
    rule_value: float


@router.get("/items", summary="工资项列表")
async def list_items(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = PayrollConfigService(db, store_id)
    await service.init_default_config_if_empty()
    items = await service.get_items_config()
    return make_response(
        data=[
            {
                "id": i.id,
                "item_code": i.item_code,
                "item_name": i.item_name,
                "item_type": i.item_type,
                "data_source": i.data_source,
                "formula_ast": i.formula_ast,
                "default_value": float(i.default_value or 0),
                "is_active": i.is_active,
                "is_system": i.is_system,
                "sort_order": i.sort_order,
                "note": i.note,
            }
            for i in items
        ],
        request=request,
    )


@router.post("/items", summary="新增/更新工资项(老板)")
async def upsert_item(
    request: Request,
    body: ItemConfigRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    service = PayrollConfigService(db, store_id)
    item = await service.upsert_item_config(
        item_code=body.item_code,
        item_name=body.item_name,
        item_type=body.item_type,
        data_source=body.data_source,
        formula_ast=body.formula_ast,
        sort_order=body.sort_order,
        default_value=body.default_value,
        note=body.note,
    )
    await db.commit()
    return make_response(message=f"工资项 {body.item_code} 已保存", request=request)


@router.delete("/items/{item_code}", summary="删除工资项(老板)")
async def delete_item(
    request: Request,
    item_code: str,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    from sqlalchemy import select, and_, delete as del_stmt
    from app.models.payroll_config import PayrollItemConfig
    stmt = select(PayrollItemConfig).where(
        and_(
            PayrollItemConfig.store_id == store_id,
            PayrollItemConfig.item_code == item_code,
        )
    )
    result = await db.execute(stmt)
    item = result.scalar_one_or_none()
    if not item:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("工资项不存在")
    if item.is_system:
        from app.utils.exceptions import ValidationError
        raise ValidationError("系统内置工资项不可删除")
    await db.execute(
        del_stmt(PayrollItemConfig).where(
            and_(
                PayrollItemConfig.store_id == store_id,
                PayrollItemConfig.item_code == item_code,
            )
        )
    )
    await db.commit()
    return make_response(message=f"工资项 {item_code} 已删除", request=request)


@router.get("/rules", summary="薪资规则列表")
async def list_rules(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = PayrollConfigService(db, store_id)
    await service.init_default_config_if_empty()
    rules = await service.get_salary_rules()
    # 取完整规则对象
    from sqlalchemy import select
    from app.models.payroll_config import SalaryRule
    stmt = select(SalaryRule).where(SalaryRule.store_id == store_id)
    result = await db.execute(stmt)
    rule_objs = result.scalars().all()
    return make_response(
        data=[
            {
                "id": r.id,
                "rule_code": r.rule_code,
                "rule_name": r.rule_name,
                "rule_value": float(r.rule_value),
                "rule_unit": r.rule_unit,
                "is_active": r.is_active,
                "note": r.note,
            }
            for r in rule_objs
        ],
        request=request,
    )


@router.put("/rules/{rule_code}", summary="更新薪资规则(老板)")
async def update_rule(
    request: Request,
    rule_code: str,
    body: RuleUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    service = PayrollConfigService(db, store_id)
    rule = await service.update_salary_rule(rule_code, body.rule_value)
    if not rule:
        from app.utils.exceptions import NotFoundError
        raise NotFoundError("薪资规则不存在")
    await db.commit()
    return make_response(message=f"规则 {rule_code} 已更新", request=request)


@router.post("/init", summary="初始化默认配置(老板)")
async def init_config(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    service = PayrollConfigService(db, store_id)
    await service.init_default_config_if_empty()
    await db.commit()
    return make_response(message="默认配置已初始化", request=request)
