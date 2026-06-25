"""企微对外收款同步服务

从企微「对外收款」API 拉取收款记录 → 写入 wage_wework_payments 表
→ PerformanceService 汇总到 hr_performance → 自动算薪时算提成

API 文档: https://developer.work.weixin.qq.com/document/path/93667
"""

import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.config import get_settings
from app.utils.http_client import http_client
from app.utils.redis_client import get_redis
from app.utils.security import decrypt_aes
from app.utils.exceptions import NotFoundError, ExternalServiceError
from app.models.store import Store
from app.models.employee import Employee
from app.models.wework_payment import WeworkPaymentSync

WECOM_API = get_settings().WECOM_API_BASE
EXTERNALPAY_TOKEN_KEY = "wework:externalpay_token:{corp_id}"
EXTERNALPAY_TOKEN_TTL = 7000


class WeworkPaymentService:
    """企微对外收款同步服务"""

    def __init__(self, db: AsyncSession, store_id: uuid.UUID):
        self.db = db
        self.store_id = store_id

    async def _get_store(self) -> Store:
        result = await self.db.execute(
            select(Store).where(Store.id == self.store_id)
        )
        store = result.scalar_one_or_none()
        if not store:
            raise NotFoundError("门店不存在")
        return store

    async def get_externalpay_token(self) -> str:
        """用对外收款 Secret 获取 access_token（独立于主应用 token）"""
        store = await self._get_store()
        if not store.wework_corp_id or not store.wework_externalpay_secret:
            raise NotFoundError("企微对外收款未配置，请在设置页填写 Secret")

        secret = decrypt_aes(store.wework_externalpay_secret)
        corp_id = store.wework_corp_id

        # Redis 缓存
        redis = await get_redis()
        cache_key = EXTERNALPAY_TOKEN_KEY.format(corp_id=corp_id)
        cached = await redis.get(cache_key)
        if cached:
            return cached

        # 调企微 API 获取 token
        url = f"{WECOM_API}/gettoken?corpid={corp_id}&corpsecret={secret}"
        resp = await http_client.get(url)
        data = resp.json()
        if data.get("errcode") != 0:
            raise ExternalServiceError(f"企微 token 获取失败: {data.get('errmsg')}")

        token = data["access_token"]
        await redis.setex(cache_key, EXTERNALPAY_TOKEN_TTL, token)
        logger.info(f"[企微收款] 获取 externalpay token 成功")
        return token

    async def fetch_bill_list(
        self,
        begin_time: int,
        end_time: int,
        payee_userid: str | None = None,
    ) -> list[dict]:
        """调用 get_bill_list API 拉取收款记录

        Args:
            begin_time: 开始时间戳（秒）
            end_time: 结束时间戳（秒）
            payee_userid: 指定收款人（可选，不填=全部）

        Returns:
            收款记录列表
        """
        token = await self.get_externalpay_token()
        all_bills: list[dict] = []
        cursor = ""

        while True:
            url = f"{WECOM_API}/cgi-bin/externalpay/get_bill_list?access_token={token}"
            body: dict = {
                "begin_time": begin_time,
                "end_time": end_time,
                "limit": 1000,
            }
            if cursor:
                body["cursor"] = cursor
            if payee_userid:
                body["payee_userid"] = payee_userid

            resp = await http_client.post(url, json_body=body)
            data = resp.json()
            if data.get("errcode") != 0:
                raise ExternalServiceError(
                    f"企微收款记录拉取失败: {data.get('errmsg')}"
                )

            bills = data.get("bill_list", [])
            all_bills.extend(bills)
            logger.info(f"[企微收款] 本批拉取 {len(bills)} 条，累计 {len(all_bills)} 条")

            cursor = data.get("next_cursor", "")
            if not cursor or not bills:
                break

        return all_bills

    async def _map_userid_to_employee(self, payee_userid: str) -> uuid.UUID | None:
        """企微 userid → employee_id"""
        result = await self.db.execute(
            select(Employee.employee_id).where(
                and_(
                    Employee.store_id == self.store_id,
                    Employee.wework_userid == payee_userid,
                )
            )
        )
        row = result.scalar_one_or_none()
        return row

    async def sync_payments(
        self,
        begin_date: date,
        end_date: date,
    ) -> dict:
        """同步指定日期范围的企微收款记录到数据库

        Args:
            begin_date: 开始日期
            end_date: 结束日期

        Returns:
            {"total": 拉取数, "inserted": 新增数, "skipped": 重复跳过数}
        """
        begin_ts = int(datetime.combine(begin_date, datetime.min.time()).timestamp())
        end_ts = int(
            datetime.combine(end_date, datetime.min.time()).timestamp()
        ) + 86399  # 23:59:59

        bills = await self.fetch_bill_list(begin_ts, end_ts)

        total = len(bills)
        inserted = 0
        skipped = 0

        for bill in bills:
            txn_id = bill.get("transaction_id", "")
            if not txn_id:
                skipped += 1
                continue

            # 检查是否已存在（去重）
            exists = await self.db.execute(
                select(WeworkPaymentSync.id).where(
                    and_(
                        WeworkPaymentSync.store_id == self.store_id,
                        WeworkPaymentSync.transaction_id == txn_id,
                    )
                )
            )
            if exists.scalar_one_or_none():
                skipped += 1
                continue

            # 企微 userid → employee_id
            payee_userid = bill.get("payee_userid", "")
            employee_id = None
            if payee_userid:
                employee_id = await self._map_userid_to_employee(payee_userid)

            # 金额：分 → 元
            amount = float(bill.get("total_fee", 0)) / 100.0

            # 付款时间
            pay_time = datetime.fromtimestamp(
                bill.get("pay_time", 0), tz=datetime.now().astimezone().tzinfo
            )

            record = WeworkPaymentSync(
                store_id=self.store_id,
                transaction_id=txn_id,
                employee_id=employee_id,
                amount=amount,
                pay_time=pay_time,
                payer_name=bill.get("payer_info", {}).get("name"),
                payer_account=bill.get("external_userid"),
                remark=bill.get("remark"),
                raw_data=bill,
                sync_status="synced",
            )
            self.db.add(record)
            inserted += 1

        await self.db.commit()
        logger.info(
            f"[企微收款] 同步完成: {begin_date}~{end_date} "
            f"拉取{total}条 新增{inserted}条 跳过{skipped}条"
        )
        return {"total": total, "inserted": inserted, "skipped": skipped}
