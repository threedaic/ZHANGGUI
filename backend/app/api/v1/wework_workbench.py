"""企微工作台自定义展示 API

- POST /workbench/setup: 设置工作台模板为关键数据型（只需调一次）
- POST /workbench/push: 立即推送今日业绩/打卡状态到所有员工
"""
from fastapi import APIRouter, Request, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.database import get_db
from app.utils.deps import make_response, require_role, get_store_id
from app.services.wework_workbench import push_workbench_to_all, set_workbench_template

router = APIRouter()


@router.post("/workbench/setup")
async def setup_workbench(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """设置工作台模板为关键数据型（只需调一次）。

    设置后，企微工作台会显示"今日业绩"和"打卡状态"两个数据块。
    员工点击可跳转到掌柜应用。
    """
    require_role(request, ["boss"])
    store_id = get_store_id(request)
    ok = await set_workbench_template(db, store_id)
    if ok:
        return make_response(message="工作台模板设置成功", data={"success": True}, request=request)
    return make_response(message="工作台模板设置失败", data={"success": False}, request=request)


@router.post("/workbench/push")
async def push_workbench(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """立即推送今日业绩/打卡状态到所有员工的工作台。

    老板点击"立即推送"按钮调用此接口。
    每小时也会自动调用一次（通过定时任务）。
    """
    require_role(request, ["boss", "store_manager"])
    store_id = get_store_id(request)
    result = await push_workbench_to_all(db, store_id)
    return make_response(
        message=f"推送完成: 总数{result['total']} 成功{result['pushed']} 失败{result['failed']}",
        data=result,
        request=request,
    )
