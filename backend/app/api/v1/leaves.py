import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.leave_balance import LeaveBalanceRepository
from app.utils.deps import get_store_id, get_employee_id, make_response

router = APIRouter(prefix="/leaves", tags=["leaves"])


@router.get("/balance")
async def get_leave_balance(
    request: Request,
    year: int | None = Query(None),
    employee_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    store_id = get_store_id(request)
    # 老板可以查任意员工，员工只能查自己
    if employee_id:
        from app.utils.deps import require_role
        require_role(request, ["system_admin", "boss", "store_manager"])
    else:
        employee_id = get_employee_id(request)
    if year is None:
        year = datetime.now().year

    repo = LeaveBalanceRepository(db, store_id)
    balances = await repo.get_balance(employee_id, year)

    items = []
    for b in balances:
        items.append({
            "leave_type": b.leave_type,
            "total_days": b.total_days,
            "used_days": b.used_days,
            "remaining": b.total_days - b.used_days,
            "year": b.year,
        })

    DEFAULT_BALANCES = {"annual": 5, "sick": 12, "personal": 3}
    if not items:
        for lt, total in DEFAULT_BALANCES.items():
            items.append({
                "leave_type": lt,
                "total_days": total,
                "used_days": 0,
                "remaining": total,
                "year": year,
            })

    return make_response(request=request, data={"balances": items})
