"""企微通讯录变更回调

- GET  /callback/contact: 企微 URL 验证（echostr 校验）
- POST /callback/contact: 接收通讯录变更事件（员工新增/删除/变更）

企微后台配置:
  URL:           https://zhanggui.crushserver.cloud/api/v1/wework/callback/contact
  Token:         WECOM_CALLBACK_TOKEN (见 .env)
  EncodingAESKey: WECOM_CALLBACK_AES_KEY (见 .env)

事件类型:
  - create_user: 新员工加入 → 拉取信息并写入 employees 表
  - delete_user: 员工离职 → 标记为 inactive
  - update_user: 员工信息变更 → 更新本地记录
"""
import xml.etree.ElementTree as ET
from fastapi import APIRouter, Request, Query
from fastapi.responses import PlainTextResponse
from loguru import logger

from app.utils.wework_crypto import verify_url, verify_signature, decrypt, parse_event_xml
from app.database import AsyncSessionLocal
from app.services.wework import sync_contacts
from app.models.store import Store
from app.models.employee import Employee
from sqlalchemy import select, update

router = APIRouter()


@router.get("/callback/contact", response_class=PlainTextResponse)
async def verify_callback_url(
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
    echostr: str = Query(...),
):
    """企微 URL 验证: GET 请求，校验签名并返回解密后的 echostr 明文。"""
    try:
        plain = verify_url(msg_signature, timestamp, nonce, echostr)
        logger.info("企微通讯录回调URL验证成功")
        return PlainTextResponse(plain)
    except Exception as e:
        logger.error(f"企微通讯录回调URL验证失败: {e}")
        return PlainTextResponse("verify failed", status_code=403)


@router.post("/callback/contact", response_class=PlainTextResponse)
async def receive_contact_event(
    request: Request,
    msg_signature: str = Query(...),
    timestamp: str = Query(...),
    nonce: str = Query(...),
):
    """接收企微通讯录变更事件推送。

    企微回调返回 "success" 即可，处理失败也返回 success 避免重试风暴，
    通过日志监控错误。
    """
    try:
        body = await request.body()
        # 解析外层 XML 获取 Encrypt 字段
        root = ET.fromstring(body)
        encrypt = root.findtext("Encrypt", "")
        if not encrypt:
            logger.warning("企微回调缺少 Encrypt 字段")
            return PlainTextResponse("success")

        # 校验签名
        if not verify_signature(msg_signature, timestamp, nonce, encrypt):
            logger.error(f"企微回调签名校验失败: sig={msg_signature}")
            return PlainTextResponse("success")

        # 解密事件 XML
        xml_content, from_corp_id = decrypt(encrypt)
        event = parse_event_xml(xml_content)
        change_type = event.get("ChangeType", "")
        user_id = event.get("UserID", "")

        logger.info(f"企微通讯录变更: type={change_type} user={user_id} event={event}")

        # 异步处理（不阻塞响应）
        if change_type == "create_user":
            await _handle_create_user(user_id, event)
        elif change_type == "delete_user":
            await _handle_delete_user(user_id, event)
        elif change_type == "update_user":
            await _handle_update_user(user_id, event)
        else:
            logger.info(f"未处理的变更类型: {change_type}")

        return PlainTextResponse("success")
    except Exception as e:
        logger.error(f"企微回调处理异常: {e}", exc_info=True)
        # 即使异常也返回 success，避免企微重试风暴
        return PlainTextResponse("success")


async def _handle_create_user(user_id: str, event: dict) -> None:
    """新员工加入: 触发对应门店的通讯录同步。"""
    async with AsyncSessionLocal() as session:
        # 根据员工部门找出对应门店
        dept_ids = event.get("Department", "")
        if not dept_ids:
            logger.info(f"新员工 {user_id} 无部门信息，跳过自动同步")
            return

        # 查找部门 ID 匹配的门店（store.wework_department_id 是逗号分隔的部门ID列表）
        dept_id_list = [d.strip() for d in dept_ids.split(",") if d.strip()]
        result = await session.execute(select(Store).where(Store.status == "active"))
        stores = result.scalars().all()

        matched_store = None
        for store in stores:
            if not store.wework_department_id:
                continue
            store_depts = [d.strip() for d in str(store.wework_department_id).split(",") if d.strip()]
            if any(d in store_depts for d in dept_id_list):
                matched_store = store
                break

        if not matched_store:
            logger.info(f"新员工 {user_id} 部门 {dept_ids} 不匹配任何门店，跳过自动同步")
            return

        # 触发该门店的同步
        result = await sync_contacts(session, matched_store.id)
        await session.commit()
        logger.info(
            f"新员工 {user_id} 加入门店 {matched_store.name} 同步完成: "
            f"新增={result.get('created', 0)} 更新={result.get('updated', 0)}"
        )


async def _handle_delete_user(user_id: str, event: dict) -> None:
    """员工离职: 标记为 inactive。"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Employee).where(Employee.wework_userid == user_id)
        )
        employee = result.scalar_one_or_none()
        if not employee:
            logger.info(f"离职员工 {user_id} 不在系统中，无需处理")
            return

        await session.execute(
            update(Employee)
            .where(Employee.id == employee.id)
            .values(status="inactive")
        )
        await session.commit()
        logger.info(f"员工 {user_id} ({employee.name}) 已标记为 inactive")


async def _handle_update_user(user_id: str, event: dict) -> None:
    """员工信息变更: 触发对应门店同步（保险起见，覆盖所有可能变更）。"""
    async with AsyncSessionLocal() as session:
        # 查找该员工当前所属门店
        result = await session.execute(
            select(Employee).where(Employee.wework_userid == user_id)
        )
        employee = result.scalar_one_or_none()
        if not employee or not employee.store_id:
            # 不在系统中 → 可能是从未同步过的新人变更，走 create_user 流程兜底
            logger.info(f"变更员工 {user_id} 不在系统，转 create_user 处理")
            await _handle_create_user(user_id, event)
            return

        # 触发该门店的同步
        result = await sync_contacts(session, employee.store_id)
        await session.commit()
        logger.info(f"员工 {user_id} 变更同步完成: 更新={result.get('updated', 0)}")
