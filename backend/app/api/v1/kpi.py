"""
KPI 考核 API 路由
/api/v1/kpi/
"""
import uuid
from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.schemas.kpi import (
    KPITemplateResponse,
    KPIScoreCreate,
    KPIScoreResponse,
    KPIScoreBatchCreate,
    KPIResultResponse,
    KPIResultDetail,
    KPICalculateRequest,
    KPIConfirmRequest,
    KPIAppealCreate,
    KPIAppealReview,
    KPIAppealResponse,
)
from app.services.kpi import KPIService
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.deps import get_store_id, require_role, get_employee_id, require_employee_id, get_user_id, make_response

router = APIRouter()


# ==================== 模板 ====================

@router.get("/templates", summary="获取 KPI 模板")
async def list_templates(
    request: Request,
    role: str | None = Query(None, description="岗位筛选"),
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    templates = await service.get_templates(role=role)
    return make_response(data=[KPITemplateResponse.model_validate(t).model_dump() for t in templates], request=request)


# ==================== 评分 ====================

@router.get("/scores", summary="查询评分明细")
async def list_scores(
    request: Request,
    employee_id: uuid.UUID | None = Query(None),
    period: str | None = Query(None),
    dimension: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    repo = service.repo
    scores = await repo.get_scores(
        employee_id=employee_id, period=period, dimension=dimension
    )
    return make_response(data=[KPIScoreResponse.model_validate(s).model_dump() for s in scores], request=request)


@router.post("/scores/batch", summary="批量录入评分(手动维度)")
async def batch_create_scores(
    request: Request,
    body: KPIScoreBatchCreate,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    service = KPIService(db, store_id)

    from app.models.kpi import KPIScore
    saved = []
    for sc in body.scores:
        templates = await service.get_templates()
        weight = 0.0
        for t in templates:
            if t.dimension == sc.dimension:
                weight = t.weight
                break

        score = KPIScore(
            employee_id=sc.employee_id,
            store_id=store_id,
            period=body.period,
            dimension=sc.dimension,
            raw_value=sc.raw_value,
            raw_description=sc.raw_description,
            normalized_score=sc.raw_value or 0.0,
            weight=weight,
            weighted_score=(sc.raw_value or 0.0) * weight,
            data_source=sc.data_source or "manual",
        )
        saved.append(score)

    await service.repo.upsert_scores(saved)
    await db.commit()
    return make_response(message=f"已保存 {len(saved)} 条评分", request=request)


# ==================== 计算 ====================

@router.post("/scores/calculate", summary="触发 KPI 自动计算(5维度加权)")
async def calculate_kpi(
    request: Request,
    body: KPICalculateRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    service = KPIService(db, store_id)

    # 如果未指定员工，取门店所有在职员工
    if not body.employee_ids:
        from app.models.employee import Employee
        from sqlalchemy import select, and_
        stmt = select(Employee.id).where(
            and_(Employee.store_id == store_id, Employee.status == "active")
        )
        result = await db.execute(stmt)
        body.employee_ids = [row[0] for row in result.all()]

    if not body.employee_ids:
        raise ValidationError("门店没有在职员工")

    results = await service.calculate_scores(body.employee_ids, body.period)
    return make_response(
        message=f"计算完成，共 {len(results)} 人",
        data=[KPIResultResponse.model_validate(r).model_dump() for r in results],
        request=request,
    )


# ==================== 结果查询 ====================

@router.get("/results", summary="门店 KPI 结果汇总")
async def list_results(
    request: Request,
    period: str = Query(..., description="月份 2026-06"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    data = await service.get_store_results(period=period, page_size=page_size, page=page)
    return make_response(data=data, request=request)


@router.get("/results/my", summary="员工查看自己的 KPI 结果")
async def my_results(
    request: Request,
    period: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    results = await service.get_employee_results(employee_id=employee_id, period=period)

    items = []
    for r in results:
        scores = await service.repo.get_scores(employee_id=employee_id, period=r.period)
        items.append({
            **KPIResultResponse.model_validate(r).model_dump(),
            "dimensions": [KPIScoreResponse.model_validate(s).model_dump() for s in scores],
        })

    return make_response(data=items, request=request)


@router.get("/results/{result_id}", summary="KPI 结果详情")
async def get_result(
    request: Request,
    result_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    result = await service.repo.get_result_by_id(result_id)
    if not result:
        raise NotFoundError("KPI 结果不存在")

    scores = await service.repo.get_scores(
        employee_id=result.employee_id, period=result.period
    )
    emp_info = await service.repo.get_employee_info([result.employee_id])
    emp = emp_info.get(result.employee_id, {"name": "", "role": ""})

    return make_response(data={
        **KPIResultResponse.model_validate(result).model_dump(),
        "employee_name": emp["name"],
        "employee_role": emp["role"],
        "dimensions": [KPIScoreResponse.model_validate(s).model_dump() for s in scores],
    }, request=request)


# ==================== 确认 ====================

@router.post("/results/{result_id}/confirm", summary="确认 KPI 结果(店长)")
async def confirm_result(
    request: Request,
    result_id: uuid.UUID,
    body: KPIConfirmRequest,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["system_admin", "boss", "store_manager"])
    user_id = get_user_id(request)
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    result = await service.confirm_result(
        result_id=result_id,
        user_id=user_id,
        coefficient=body.coefficient,
        reason=body.coefficient_reason,
    )
    return make_response(
        message="确认成功",
        data=KPIResultResponse.model_validate(result).model_dump(),
        request=request,
    )


# ==================== 申诉 ====================

@router.post("/appeals", summary="员工发起 KPI 申诉")
async def create_appeal(
    request: Request,
    body: KPIAppealCreate,
    db: AsyncSession = Depends(get_db),
):
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    appeal = await service.create_appeal(
        employee_id=employee_id,
        result_id=body.result_id,
        dimension=body.dimension,
        reason=body.reason,
        evidence=body.evidence,
    )
    return make_response(
        message="申诉已提交，等待店长审批",
        data=KPIAppealResponse.model_validate(appeal).model_dump(),
        request=request,
    )


@router.get("/appeals", summary="申诉列表(店长查看待处理)")
async def list_appeals(
    request: Request,
    status: str | None = Query(None, description="pending/approved/rejected"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["system_admin", "boss", "store_manager"])
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    data = await service.get_appeals_for_review(status=status, page=page, page_size=page_size)
    return make_response(data=data, request=request)


@router.get("/appeals/my", summary="我的申诉记录")
async def my_appeals(
    request: Request,
    status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """员工查看自己的申诉记录（M-008 fix: 只返回当前员工的申诉）。"""
    employee_id = require_employee_id(request)
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    data = await service.get_employee_appeals(
        employee_id=employee_id, status=status, page=page, page_size=page_size
    )
    return make_response(data=data, request=request)


@router.put("/appeals/{appeal_id}/review", summary="店长审批申诉")
async def review_appeal(
    request: Request,
    appeal_id: uuid.UUID,
    body: KPIAppealReview,
    db: AsyncSession = Depends(get_db),
):
    require_role(request, ["system_admin", "boss", "store_manager"])
    user_id = get_user_id(request)
    store_id = get_store_id(request)
    service = KPIService(db, store_id)
    appeal = await service.review_appeal(
        appeal_id=appeal_id,
        reviewer_id=user_id,
        action=body.action,
        resolution=body.resolution,
    )
    return make_response(
        message="审批完成",
        data=KPIAppealResponse.model_validate(appeal).model_dump(),
        request=request,
    )
