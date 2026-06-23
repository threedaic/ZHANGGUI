"""
合同系统 API

端点（前缀 /api/v1/contracts）:
  GET    ""                          合同列表（分页 + 筛选）
  GET    "/salary-matrix"            查看薪资矩阵
  PUT    "/salary-matrix/{id}"       更新薪资矩阵条目
  POST   ""                          创建合同
  GET    "/{contract_id}"            合同详情（含模板数据）
  PUT    "/{contract_id}"            更新合同
  DELETE "/{contract_id}"            删除合同
  POST   "/{contract_id}/send-sign"   发起电子签
"""
import uuid
from datetime import date
from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.models.contract import Contract
from app.repositories.contract import ContractRepository
from app.services.contract import (
    compute_allowance,
    generate_contract_no,
    build_template_data,
    send_for_esign,
    seed_salary_matrix,
    BASE_SALARY,
    MEAL_ALLOWANCE,
)
from app.schemas.contract import (
    SalaryMatrixResponse,
    SalaryMatrixUpdate,
    ContractCreate,
    ContractUpdate,
    ContractResponse,
    ContractDetailResponse,
    SendSignRequest,
    VALID_POSITIONS,
    VALID_GRADES,
)
from app.utils.exceptions import NotFoundError, ValidationError, ConflictError, ForbiddenError
from app.utils.deps import get_store_id, make_response, require_contract_initiator
from app.utils.pagination import paginate, PageParams

router = APIRouter()


# ---- 依赖注入 ----

async def get_repo(request: Request, db: AsyncSession = Depends(get_db)):
    store_id = get_store_id(request)
    return ContractRepository(db, store_id)


async def get_user_id(request: Request) -> int:
    """获取当前用户 ID，必须已登录。
    实际使用中该依赖只在认证路由中被调用，user_id 始终存在。"""
    user_id = getattr(request.state, "user_id", None)
    if user_id is None:
        raise ForbiddenError("无法获取用户信息")
    return user_id


# ---- 辅助 ----

def _contract_to_dict(c: Contract, emp_map: dict[int, str]) -> dict:
    return {
        "id": c.id,
        "store_id": c.store_id,
        "employee_id": c.employee_id,
        "employee_name": emp_map.get(c.employee_id, ""),
        "contract_no": c.contract_no,
        "position": c.position,
        "grade": c.grade,
        "monthly_salary": c.monthly_salary,
        "base_salary": c.base_salary,
        "meal_allowance": c.meal_allowance,
        "allowance": c.allowance,
        "start_date": str(c.start_date),
        "end_date": str(c.end_date) if c.end_date else None,
        "status": c.status,
        "esign_flow_id": c.esign_flow_id,
        "signed_at": str(c.signed_at) if c.signed_at else None,
        "created_at": str(c.created_at) if c.created_at else None,
        "updated_at": str(c.updated_at) if c.updated_at else None,
    }


def _contract_to_detail(c: Contract, emp_map: dict[int, str]) -> dict:
    data = _contract_to_dict(c, emp_map)
    data["template_data"] = c.template_data
    return data


# ---- 薪资矩阵 ----

@router.get("/salary-matrix", response_model=dict)
async def get_salary_matrix(
    request: Request,
    repo: ContractRepository = Depends(get_repo),
):
    """返回薪资矩阵（5岗 x 4档），含启用/禁用标识。"""
    await seed_salary_matrix(repo)
    entries = await repo.list_salary_matrix()
    return make_response(data=[
        {
            "id": e.id,
            "position": e.position,
            "grade": e.grade,
            "monthly_salary": e.monthly_salary,
            "base_salary": e.base_salary,
            "meal_allowance": e.meal_allowance,
            "is_active": e.is_active,
        }
        for e in entries
    ], request=request)


@router.put("/salary-matrix/{entry_id}", response_model=dict)
async def update_salary_matrix(
    entry_id: uuid.UUID,
    body: SalaryMatrixUpdate,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
):
    """更新薪资矩阵某条目（月薪/启用状态）。"""
    entries = await repo.list_salary_matrix()
    entry = next((e for e in entries if e.id == entry_id), None)
    if not entry:
        raise NotFoundError(f"薪资矩阵条目 #{entry_id} 不存在")

    updated = await repo.update_matrix_entry(entry, **body.model_dump(exclude_unset=True, exclude_none=True))
    return make_response(message="薪资矩阵已更新", data={
        "id": updated.id,
        "position": updated.position,
        "grade": updated.grade,
        "monthly_salary": updated.monthly_salary,
        "base_salary": updated.base_salary,
        "meal_allowance": updated.meal_allowance,
        "is_active": updated.is_active,
    }, request=request)


# ---- 合同 CRUD ----

@router.get("", response_model=dict)
async def list_contracts(
    request: Request,
    repo: ContractRepository = Depends(get_repo),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str = Query(None, description="筛选状态"),
    employee_id: uuid.UUID | None = Query(None, description="筛选员工"),
    position: str = Query(None, description="筛选岗位"),
):
    """合同列表，支持分页和筛选。"""
    items, total = await repo.list_contracts(
        page=page,
        page_size=page_size,
        status=status,
        employee_id=employee_id,
        position=position,
    )

    employee_ids = {c.employee_id for c in items}
    # Batch query employees (M-005 fix: eliminates N+1)
    emp_map = {}
    if employee_ids:
        employees = await repo.get_employees_by_ids(employee_ids)
        emp_map = {eid: emp.name for eid, emp in employees.items()}

    paged = paginate(
        items=[_contract_to_dict(c, emp_map) for c in items],
        total=total,
        params=PageParams(page=page, page_size=page_size),
    )

    return make_response(data=paged.model_dump(), request=request)


@router.get("/employees", response_model=dict)
async def list_contractable_employees(
    request: Request,
    repo: ContractRepository = Depends(get_repo),
):
    """获取当前门店在职员工列表（用于签约选择器）。"""
    employees = await repo.get_active_employees()
    return make_response(data=[
        {
            "id": e.id,
            "name": e.name,
            "role": e.role,
            "phone": e.phone,
        }
        for e in employees
    ], request=request)


@router.post("", response_model=dict, status_code=201)
async def create_contract(
    body: ContractCreate,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
    user_id: int = Depends(get_user_id),
    _perm=Depends(require_contract_initiator),
):
    """创建合同。

    签约流程：
    1. 选员工 + 岗位 + 职档
    2. 填月薪（>= 3000）
    3. 系统自动计算：补贴 = 月薪 - 3000，基本工资固定 3000，餐补固定 400
    4. 生成合同编号，模板数据自动填充
    """
    # 1. 验证员工存在
    employee = await repo.get_employee(body.employee_id)
    if not employee:
        raise NotFoundError(f"员工 #{body.employee_id} 不存在")

    # 2. 验证岗位/职档组合在薪资矩阵中是否有效
    matrix_entry = await repo.get_matrix_entry(body.position, body.grade)
    if not matrix_entry or not matrix_entry.is_active:
        raise ValidationError(
            f"岗位「{body.position}」+ 职档「{body.grade}」在薪资矩阵中不可用"
        )

    # 3. 检查是否已有活跃合同
    existing = await repo.get_active_by_employee(body.employee_id)
    if existing:
        raise ConflictError(
            f"员工「{employee.name}」已有活跃合同 #{existing.id} "
            f"({existing.status})，请先终止旧合同"
        )

    # 4. 计算补贴
    allowance = compute_allowance(body.monthly_salary)

    # 5. 生成合同编号（DB-based sequence, survives restarts）
    store_id = repo.store_id
    seq = await repo.get_next_contract_seq(store_id)
    contract_no = generate_contract_no(store_id, body.employee_id, seq)

    # 6. 创建合同
    contract = Contract(
        store_id=store_id,
        employee_id=body.employee_id,
        contract_no=contract_no,
        position=body.position,
        grade=body.grade,
        monthly_salary=body.monthly_salary,
        base_salary=BASE_SALARY,
        meal_allowance=MEAL_ALLOWANCE,
        allowance=allowance,
        start_date=body.start_date,
        end_date=body.end_date,
        status="draft",
        created_by=user_id,
    )

    created = await repo.create(contract)

    # 7. 填充模板数据
    template_data = build_template_data(
        created,
        employee_name=employee.name,
        employee_phone=employee.phone or "",
    )
    await repo.update(created, template_data=template_data)

    return make_response(message="合同创建成功", data=_contract_to_detail(created, {body.employee_id: employee.name}), request=request)


@router.get("/{contract_id}", response_model=dict)
async def get_contract(
    contract_id: uuid.UUID,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
):
    """合同详情（含模板填充数据）。"""
    contract = await repo.get_by_id(contract_id)
    if not contract:
        raise NotFoundError(f"合同 #{contract_id} 不存在")

    employee = await repo.get_employee(contract.employee_id)
    emp_map = {contract.employee_id: employee.name if employee else ""}

    return make_response(data=_contract_to_detail(contract, emp_map), request=request)


@router.put("/{contract_id}", response_model=dict)
async def update_contract(
    contract_id: uuid.UUID,
    body: ContractUpdate,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
    _perm=Depends(require_contract_initiator),
):
    """更新合同信息。

    若修改月薪，自动重算补贴。
    若修改岗位/职档，重新验证薪资矩阵有效性。
    """
    contract = await repo.get_by_id(contract_id)
    if not contract:
        raise NotFoundError(f"合同 #{contract_id} 不存在")

    if contract.status == "signed":
        raise ValidationError("已签署的合同不可修改，请终止后重新创建")

    update_data = body.model_dump(exclude_unset=True, exclude_none=True)

    # 若修改月薪，重算补贴
    if "monthly_salary" in update_data:
        update_data["allowance"] = compute_allowance(update_data["monthly_salary"])

    # 若修改岗位或职档，验证薪资矩阵
    new_position = update_data.get("position", contract.position)
    new_grade = update_data.get("grade", contract.grade)
    if "position" in update_data or "grade" in update_data:
        matrix_entry = await repo.get_matrix_entry(new_position, new_grade)
        if not matrix_entry or not matrix_entry.is_active:
            raise ValidationError(
                f"岗位「{new_position}」+ 职档「{new_grade}」在薪资矩阵中不可用"
            )

    if not update_data:
        return make_response(data=_contract_to_dict(contract, {}), request=request)

    updated = await repo.update(contract, **update_data)

    # 若关键字段变更，重建模板数据
    employee = await repo.get_employee(updated.employee_id)
    if employee and any(k in update_data for k in ["position", "grade", "monthly_salary", "start_date", "end_date"]):
        template_data = build_template_data(
            updated,
            employee_name=employee.name,
            employee_phone=employee.phone or "",
        )
        await repo.update(updated, template_data=template_data)

    emp_map = {updated.employee_id: employee.name if employee else ""}
    return make_response(message="合同更新成功", data=_contract_to_detail(updated, emp_map), request=request)


@router.delete("/{contract_id}", response_model=dict)
async def delete_contract(
    contract_id: uuid.UUID,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
    _perm=Depends(require_contract_initiator),
):
    """删除合同（仅 draft 状态可删除）。"""
    contract = await repo.get_by_id(contract_id)
    if not contract:
        raise NotFoundError(f"合同 #{contract_id} 不存在")

    if contract.status not in ("draft",):
        raise ValidationError(f"只有「草稿」状态的合同可删除，当前状态: {contract.status}")

    await repo.delete(contract)
    return make_response(message="合同已删除", data=None, request=request)


# ---- 电子签 ----

@router.post("/{contract_id}/send-sign", response_model=dict)
async def send_contract_for_sign(
    contract_id: uuid.UUID,
    request: Request,
    repo: ContractRepository = Depends(get_repo),
):
    """发起腾讯电子签签署流程。

    合同状态变更为 pending_sign，员工将在企微中收到签署链接。
    当前为占位实现。
    """
    contract = await repo.get_by_id(contract_id)
    if not contract:
        raise NotFoundError(f"合同 #{contract_id} 不存在")

    if contract.status == "signed":
        raise ValidationError("合同已签署，无需重复发起")

    result = await send_for_esign(contract, repo)
    return make_response(message="电子签流程已发起", data=result, request=request)
