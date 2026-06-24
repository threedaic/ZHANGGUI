"""打印机路由引擎服务

统一的打印接口，支持：
1. 自定义路由规则匹配
2. 分类绑定打印机
3. 按打印机类型自动路由
4. 故障转移
5. 离线队列重试
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

from loguru import logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.sys import Printer, PrintRoute, PrintQueue
from app.models.shared import Category
from app.utils.http_client import http_client


class PrinterService:
    """打印机路由引擎"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def print_by_category(
        self,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
        content: str,
        trigger: str = "order_created",
        document_type: str = "order",
    ) -> Dict[str, Any]:
        """根据分类自动路由打印

        路由优先级：
        1. 自定义路由规则
        2. 分类绑定打印机
        3. 按打印机类型自动路由

        Args:
            store_id: 门店ID
            category_id: 分类ID
            content: 打印内容
            trigger: 触发时机
            document_type: 文档类型

        Returns:
            {"status": "queued"/"sent"/"no_printer", "printer": "打印机名", "queue_id": "..."}
        """
        # 1. 尝试匹配自定义路由规则
        printer = await self._match_route(store_id, category_id, trigger, document_type)

        # 2. 尝试分类绑定打印机
        if not printer:
            printer = await self._get_category_printer(store_id, category_id)

        # 3. 按打印机类型自动路由
        if not printer:
            type_map = {"order": "order", "receipt": "receipt", "label": "label"}
            printer_type = type_map.get(document_type, "order")
            printer = await self._find_printer_by_type(store_id, printer_type)

        if not printer:
            logger.warning(f"没有可用打印机: store={store_id}, category={category_id}")
            return {"status": "no_printer", "message": "没有可用的打印机"}

        # 4. 发送打印
        return await self._send_print(store_id, printer, content)

    async def print_by_route(
        self,
        store_id: uuid.UUID,
        route_id: uuid.UUID,
        content: str,
    ) -> Dict[str, Any]:
        """直接使用指定路由规则打印

        Args:
            store_id: 门店ID
            route_id: 路由规则ID
            content: 打印内容

        Returns:
            {"status": "queued"/"sent"/"failed", ...}
        """
        # 查询路由规则
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.route_id == route_id,
                PrintRoute.store_id == store_id,
                PrintRoute.is_active == True,
            )
        )
        route = result.scalar_one_or_none()

        if not route:
            return {"status": "failed", "message": "路由规则不存在或已禁用"}

        # 获取打印机
        result = await self.db.execute(
            select(Printer).where(
                Printer.printer_id == route.printer_id,
                Printer.store_id == store_id,
                Printer.is_active == True,
            )
        )
        printer = result.scalar_one_or_none()

        if not printer:
            return {"status": "failed", "message": "目标打印机不存在或已禁用"}

        return await self._send_print(store_id, printer, content)

    async def print_direct(
        self,
        store_id: uuid.UUID,
        printer_id: uuid.UUID,
        content: str,
    ) -> Dict[str, Any]:
        """直接打印到指定打印机

        Args:
            store_id: 门店ID
            printer_id: 打印机ID
            content: 打印内容

        Returns:
            {"status": "queued"/"sent"/"failed", ...}
        """
        result = await self.db.execute(
            select(Printer).where(
                Printer.printer_id == printer_id,
                Printer.store_id == store_id,
                Printer.is_active == True,
            )
        )
        printer = result.scalar_one_or_none()

        if not printer:
            return {"status": "failed", "message": "打印机不存在或已禁用"}

        return await self._send_print(store_id, printer, content)

    async def _match_route(
        self,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
        trigger: str,
        document_type: str,
    ) -> Optional[Printer]:
        """匹配自定义路由规则

        按优先级排序，返回第一个匹配的打印机
        """
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.store_id == store_id,
                PrintRoute.trigger_event == trigger,
                PrintRoute.document_type == document_type,
                PrintRoute.is_active == True,
            ).order_by(PrintRoute.priority)
        )
        routes = result.scalars().all()

        for route in routes:
            if self._match_filter(route, category_id):
                # 获取打印机
                printer_result = await self.db.execute(
                    select(Printer).where(
                        Printer.printer_id == route.printer_id,
                        Printer.store_id == store_id,
                        Printer.is_active == True,
                    )
                )
                printer = printer_result.scalar_one_or_none()
                if printer:
                    return printer

        return None

    def _match_filter(self, route: PrintRoute, category_id: uuid.UUID) -> bool:
        """检查路由规则是否匹配

        匹配类型：
        - category: 匹配分类ID列表
        - product: 匹配商品ID列表（这里简化为分类匹配）
        - order_type: 匹配订单类型
        - all: 匹配所有
        """
        if route.filter_type == "all":
            return True

        if route.filter_type == "category":
            filter_value = route.filter_value or {}
            category_ids = filter_value.get("category_ids", [])
            if not category_ids:
                return True
            return str(category_id) in category_ids

        if route.filter_type == "product":
            # 商品匹配暂时简化为分类匹配
            filter_value = route.filter_value or {}
            category_ids = filter_value.get("category_ids", [])
            if not category_ids:
                return True
            return str(category_id) in category_ids

        if route.filter_type == "order_type":
            # 订单类型匹配需要额外参数，这里返回True表示可以匹配
            return True

        return False

    async def _get_category_printer(
        self,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
    ) -> Optional[Printer]:
        """获取分类绑定的打印机"""
        result = await self.db.execute(
            select(Category).where(
                Category.category_id == category_id,
                Category.store_id == store_id,
            )
        )
        category = result.scalar_one_or_none()

        if not category:
            return None

        # 优先使用绑定的打印机
        if category.printer_id:
            printer = await self._get_printer(store_id, category.printer_id)
            if printer:
                return printer

        # 尝试备用打印机
        if category.backup_printer_id:
            printer = await self._get_printer(store_id, category.backup_printer_id)
            if printer:
                return printer

        return None

    async def _find_printer_by_type(
        self,
        store_id: uuid.UUID,
        printer_type: str,
    ) -> Optional[Printer]:
        """按打印机类型查找（优先在线的）"""
        # 优先查找在线的打印机
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.printer_type == printer_type,
                Printer.is_active == True,
                Printer.online_status == True,
            ).order_by(Printer.name)
        )
        printer = result.scalar_one_or_none()

        if printer:
            return printer

        # 没有在线的，查找任意可用的
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.printer_type == printer_type,
                Printer.is_active == True,
            ).order_by(Printer.name)
        )
        return result.scalar_one_or_none()

    async def _get_printer(
        self,
        store_id: uuid.UUID,
        printer_id: uuid.UUID,
    ) -> Optional[Printer]:
        """获取打印机"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.printer_id == printer_id,
                Printer.store_id == store_id,
                Printer.is_active == True,
            )
        )
        return result.scalar_one_or_none()

    async def _send_print(
        self,
        store_id: uuid.UUID,
        printer: Printer,
        content: str,
    ) -> Dict[str, Any]:
        """发送打印任务

        优先直接发送，失败则加入队列
        """
        try:
            # 尝试直接发送
            success = await self._call_cloud_printer(printer, content)

            if success:
                # 更新打印机状态
                printer.online_status = True
                printer.last_heartbeat = datetime.utcnow()
                await self.db.commit()

                return {
                    "status": "sent",
                    "printer": printer.name,
                    "printer_id": str(printer.printer_id),
                }
            else:
                # 发送失败，加入队列
                queue_id = await self._enqueue(store_id, printer.printer_id, content)
                return {
                    "status": "queued",
                    "printer": printer.name,
                    "printer_id": str(printer.printer_id),
                    "queue_id": str(queue_id),
                    "message": "打印任务已加入队列，将自动重试",
                }

        except Exception as e:
            logger.error(f"打印失败: {e}")
            # 异常时加入队列
            queue_id = await self._enqueue(store_id, printer.printer_id, content)
            return {
                "status": "queued",
                "printer": printer.name,
                "printer_id": str(printer.printer_id),
                "queue_id": str(queue_id),
                "message": f"打印异常: {str(e)}",
            }

    async def _call_cloud_printer(self, printer: Printer, content: str) -> bool:
        """调用云打印机API

        支持9种云打印机品牌，根据官方文档实现
        """
        brand = printer.brand or "yilianyun"
        sn = printer.device_sn

        if not sn:
            logger.warning(f"打印机SN未配置: {printer.name}")
            return False

        # 获取API地址
        api_url = printer.api_url
        if not api_url:
            api_url = self._get_default_api_url(brand)

        if not api_url:
            logger.warning(f"打印机API地址未配置: {printer.name}")
            return False

        # 根据品牌构建请求参数
        payload = self._build_payload(brand, printer, content)

        try:
            response = await http_client.post(api_url, json_body=payload)
            logger.info(f"打印成功: {printer.name}")
            return True
        except Exception as e:
            logger.error(f"云打印API调用失败: {e}")
            return False

    def _build_payload(self, brand: str, printer: Printer, content: str) -> dict:
        """根据不同品牌构建打印请求参数"""
        sn = printer.device_sn

        if brand == "yilianyun":
            # 易联云：OAuth2.0，需要先获取access_token
            return {
                "client_id": printer.api_user or "",
                "client_secret": printer.api_secret or "",
                "machine_code": sn,
                "content": content,
                "times": 1,
            }
        elif brand == "feie":
            # 飞鹅：user + ukey + stime，MD5签名
            import hashlib
            import time
            user = printer.api_user or ""
            ukey = printer.api_secret or ""
            stime = str(int(time.time()))
            sign = hashlib.md5(f"{user}{ukey}{stime}".encode()).hexdigest()
            return {
                "user": user,
                "stime": stime,
                "sig": sign,
                "apiname": "Open_printMsg",
                "sn": sn,
                "content": content,
                "times": 1,
            }
        elif brand == "xpyun":
            # 芯烨：user + userKey + timestamp，SHA1签名
            import hashlib
            import time
            user = printer.api_user or ""
            user_key = printer.api_secret or ""
            timestamp = str(int(time.time()))
            sign = hashlib.sha1(f"{user}{user_key}{timestamp}".encode()).hexdigest()
            return {
                "user": user,
                "timestamp": timestamp,
                "sign": sign,
                "sn": sn,
                "content": content,
                "copies": 1,
            }
        elif brand == "gainscha":
            # 佳博：memberCode + apiKey + msgId + timestamp，MD5签名
            import hashlib
            import time
            member_code = printer.api_user or ""
            api_key = printer.api_secret or ""
            msg_id = str(uuid.uuid4())
            timestamp = str(int(time.time()))
            sign = hashlib.md5(f"{member_code}{api_key}{msg_id}{timestamp}".encode()).hexdigest()
            return {
                "memberCode": member_code,
                "msgId": msg_id,
                "timestamp": timestamp,
                "sign": sign,
                "deviceID": sn,
                "content": content,
                "printTimes": 1,
            }
        elif brand == "jolimark":
            # 映美云：app_id + app_key
            return {
                "app_id": printer.api_user or "",
                "app_key": printer.api_secret or "",
                "device_no": sn,
                "content": content,
                "copies": 1,
            }
        elif brand == "zhongwu":
            # 中午云：appid + appsecret + deviceid + devicesecret，MD5签名
            import hashlib
            import time
            appid = printer.api_user or ""
            appsecret = printer.api_secret or ""
            deviceid = sn
            timestamp = str(int(time.time()))
            sign = hashlib.md5(f"{appid}{deviceid}{timestamp}{appsecret}".encode()).hexdigest()
            return {
                "appid": appid,
                "sign": sign,
                "timestamp": timestamp,
                "deviceid": deviceid,
                "content": content,
                "times": 1,
            }
        elif brand == "ushengyun":
            # 优声云：appId + appSecret + deviceid + devicesecret，MD5签名
            import hashlib
            import time
            app_id = printer.api_user or ""
            app_secret = printer.api_secret or ""
            device_id = sn
            timestamp = str(int(time.time()))
            sign = hashlib.md5(f"{app_id}{device_id}{timestamp}{app_secret}".encode()).hexdigest()
            return {
                "appId": app_id,
                "sign": sign,
                "timestamp": timestamp,
                "deviceId": device_id,
                "content": content,
                "times": 1,
            }
        elif brand == "kuaidi100":
            # 快递100：key + secret，MD5签名
            import hashlib
            import time
            key = printer.api_user or ""
            secret = printer.api_secret or ""
            timestamp = str(int(time.time()))
            sign = hashlib.md5(f"{key}{secret}{timestamp}".encode()).hexdigest()
            return {
                "key": key,
                "sign": sign,
                "timestamp": timestamp,
                "deviceNo": sn,
                "content": content,
                "times": 1,
            }
        elif brand == "printcenter":
            # 365智能云：deviceNo + key，无签名
            return {
                "deviceNo": sn,
                "key": printer.api_secret or "",
                "printContent": content,
                "times": 1,
            }
        else:
            # 默认使用通用参数
            return {
                "sn": sn,
                "content": content,
                "times": 1,
            }

    def _get_default_api_url(self, brand: str) -> str:
        """获取品牌默认API地址"""
        brand_urls = {
            "yilianyun": "https://open-api.10ss.net/printer/print",
            "feie": "http://api.feieyun.com/FeieServer/printOrderAction",
            "xpyun": "https://open.xpyun.net/api/openapi/xprinter/print",
            "gainscha": "https://api.poscom.cn/apisc/sendMsg",
            "jolimark": "https://cloud.jolimark.com/api/print",
            "zhongwu": "http://api.zhongwuyun.com/sendprint",
            "ushengyun": "https://api.ushengyun.com/print/send",
            "kuaidi100": "https://api.kuaidi100.com/printer/send",
            "printcenter": "http://open.printcenter.cn:8080/addOrder",
        }
        return brand_urls.get(brand, "")

    async def _enqueue(
        self,
        store_id: uuid.UUID,
        printer_id: uuid.UUID,
        content: str,
        route_id: Optional[uuid.UUID] = None,
    ) -> uuid.UUID:
        """加入打印队列"""
        queue = PrintQueue(
            store_id=store_id,
            printer_id=printer_id,
            content=content,
            route_id=route_id,
            status="pending",
        )
        self.db.add(queue)
        await self.db.commit()
        await self.db.refresh(queue)

        logger.info(f"打印任务已入队: {queue.queue_id}")
        return queue.queue_id

    async def process_queue(self, store_id: uuid.UUID) -> Dict[str, Any]:
        """处理打印队列（定时任务调用）

        Args:
            store_id: 门店ID

        Returns:
            {"processed": N, "success": N, "failed": N}
        """
        result = await self.db.execute(
            select(PrintQueue).where(
                PrintQueue.store_id == store_id,
                PrintQueue.status == "pending",
            ).order_by(PrintQueue.created_at).limit(50)
        )
        queue_items = result.scalars().all()

        processed = 0
        success = 0
        failed = 0

        for item in queue_items:
            processed += 1

            # 获取打印机
            printer = await self._get_printer(store_id, item.printer_id)
            if not printer:
                item.status = "failed"
                item.error_message = "打印机不存在"
                failed += 1
                continue

            # 尝试发送
            try:
                send_success = await self._call_cloud_printer(printer, item.content)
                if send_success:
                    item.status = "completed"
                    item.printed_at = datetime.utcnow()
                    success += 1
                else:
                    item.retry_count += 1
                    if item.retry_count >= item.max_retries:
                        item.status = "failed"
                        item.error_message = "重试次数超限"
                        failed += 1
                    else:
                        # 尝试备用打印机
                        backup_printer = await self._find_backup_printer(store_id, item.printer_id)
                        if backup_printer:
                            item.printer_id = backup_printer.printer_id
                            item.retry_count = 0  # 重置重试次数
            except Exception as e:
                item.retry_count += 1
                if item.retry_count >= item.max_retries:
                    item.status = "failed"
                    item.error_message = str(e)
                    failed += 1

        await self.db.commit()

        return {"processed": processed, "success": success, "failed": failed}

    async def _find_backup_printer(
        self,
        store_id: uuid.UUID,
        current_printer_id: uuid.UUID,
    ) -> Optional[Printer]:
        """查找备用打印机（同类型的其他打印机）"""
        # 获取当前打印机类型
        current = await self._get_printer(store_id, current_printer_id)
        if not current:
            return None

        # 查找同类型的其他打印机
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.printer_type == current.printer_type,
                Printer.printer_id != current_printer_id,
                Printer.is_active == True,
            ).order_by(Printer.online_status.desc())  # 优先在线的
        )
        return result.scalar_one_or_none()

    async def get_printer_status(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取所有打印机状态"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.is_active == True,
            ).order_by(Printer.name)
        )
        printers = result.scalars().all()

        return [
            {
                "printer_id": str(p.printer_id),
                "name": p.name,
                "printer_type": p.printer_type,
                "brand": p.brand,
                "device_sn": p.device_sn,
                "online_status": p.online_status,
                "last_heartbeat": p.last_heartbeat.isoformat() if p.last_heartbeat else None,
                "paper_width": p.paper_width,
            }
            for p in printers
        ]

    async def test_print(self, store_id: uuid.UUID, printer_id: uuid.UUID) -> Dict[str, Any]:
        """测试打印"""
        printer = await self._get_printer(store_id, printer_id)
        if not printer:
            return {"status": "failed", "message": "打印机不存在"}

        test_content = f"测试打印 - {printer.name}\n时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}\n打印机正常工作"
        return await self._send_print(store_id, printer, test_content)

    # ==================== CRUD 操作（供API层调用） ====================

    async def list_printers(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取打印机列表"""
        return await self.get_printer_status(store_id)

    async def create_printer(self, store_id: uuid.UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建打印机"""
        printer = Printer(
            store_id=store_id,
            name=data["name"],
            printer_type=data.get("printer_type", "order"),
            brand=data.get("brand"),
            device_sn=data.get("device_sn"),
            api_url=data.get("api_url"),
            api_key=data.get("api_key"),
            api_user=data.get("api_user"),
            api_secret=data.get("api_secret"),
            paper_width=data.get("paper_width", 80),
            extra_config=data.get("extra_config", {}),
            is_active=True,
        )
        self.db.add(printer)
        await self.db.commit()
        await self.db.refresh(printer)
        return {"printer_id": str(printer.printer_id)}

    async def update_printer(self, store_id: uuid.UUID, printer_id: uuid.UUID, data: Dict[str, Any]) -> bool:
        """更新打印机"""
        printer = await self._get_printer(store_id, printer_id)
        if not printer:
            return False

        for key, value in data.items():
            if value is not None and hasattr(printer, key):
                setattr(printer, key, value)

        await self.db.commit()
        return True

    async def delete_printer(self, store_id: uuid.UUID, printer_id: uuid.UUID) -> bool:
        """删除打印机（软删除）"""
        printer = await self._get_printer(store_id, printer_id)
        if not printer:
            return False

        printer.is_active = False
        await self.db.commit()
        return True

    async def get_printer_status_list(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取打印机状态列表"""
        result = await self.db.execute(
            select(Printer).where(
                Printer.store_id == store_id,
                Printer.is_active == True,
            ).order_by(Printer.name)
        )
        printers = result.scalars().all()

        data = []
        for p in printers:
            status = "offline"
            if p.online_status:
                status = "online"
            elif p.last_heartbeat and p.last_heartbeat > datetime.utcnow() - timedelta(minutes=5):
                status = "online"

            data.append({
                "printer_id": str(p.printer_id),
                "name": p.name,
                "printer_type": p.printer_type,
                "brand": p.brand,
                "device_sn": p.device_sn,
                "online_status": p.online_status,
                "last_heartbeat": p.last_heartbeat.isoformat() if p.last_heartbeat else None,
                "computed_status": status,
                "is_active": p.is_active,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            })

        return data

    # ==================== 路由规则 CRUD ====================

    async def list_routes(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取路由规则列表（批量查询，避免N+1）"""
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.store_id == store_id,
                PrintRoute.is_active == True,
            ).order_by(PrintRoute.trigger_event, PrintRoute.priority)
        )
        routes = result.scalars().all()

        if not routes:
            return []

        # 批量查询所有相关打印机
        printer_ids = {r.printer_id for r in routes}
        printers_result = await self.db.execute(
            select(Printer).where(
                Printer.printer_id.in_(printer_ids),
                Printer.store_id == store_id,
            )
        )
        printer_map = {p.printer_id: p.name for p in printers_result.scalars().all()}

        return [
            {
                "route_id": str(r.route_id),
                "name": r.name,
                "trigger_event": r.trigger_event,
                "document_type": r.document_type,
                "filter_type": r.filter_type,
                "filter_value": r.filter_value,
                "printer_id": str(r.printer_id),
                "printer_name": printer_map.get(r.printer_id, "未知打印机"),
                "priority": r.priority,
                "is_active": r.is_active,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in routes
        ]

    async def create_route(self, store_id: uuid.UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """创建路由规则"""
        route = PrintRoute(
            store_id=store_id,
            name=data["name"],
            trigger_event=data.get("trigger_event", "order_created"),
            document_type=data.get("document_type", "order"),
            filter_type=data.get("filter_type", "category"),
            filter_value=data.get("filter_value"),
            printer_id=uuid.UUID(data["printer_id"]),
            priority=data.get("priority", 1),
            is_active=True,
        )
        self.db.add(route)
        await self.db.commit()
        await self.db.refresh(route)
        return {"route_id": str(route.route_id)}

    async def update_route(self, store_id: uuid.UUID, route_id: uuid.UUID, data: Dict[str, Any]) -> bool:
        """更新路由规则"""
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.route_id == route_id,
                PrintRoute.store_id == store_id,
            )
        )
        route = result.scalar_one_or_none()
        if not route:
            return False

        for key, value in data.items():
            if value is not None and hasattr(route, key):
                if key == "printer_id":
                    setattr(route, key, uuid.UUID(value))
                else:
                    setattr(route, key, value)

        await self.db.commit()
        return True

    async def delete_route(self, store_id: uuid.UUID, route_id: uuid.UUID) -> bool:
        """删除路由规则"""
        result = await self.db.execute(
            select(PrintRoute).where(
                PrintRoute.route_id == route_id,
                PrintRoute.store_id == store_id,
            )
        )
        route = result.scalar_one_or_none()
        if not route:
            return False

        await self.db.delete(route)
        await self.db.commit()
        return True

    # ==================== 分类打印机绑定 CRUD ====================

    async def list_categories_with_printer(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取分类列表（含打印机绑定信息，批量查询避免N+1）"""
        result = await self.db.execute(
            select(Category).where(
                Category.store_id == store_id,
                Category.is_active == True,
            ).order_by(Category.sort_order)
        )
        categories = result.scalars().all()

        if not categories:
            return []

        # 收集所有打印机ID，批量查询
        printer_ids = set()
        for c in categories:
            if c.printer_id:
                printer_ids.add(c.printer_id)
            if c.backup_printer_id:
                printer_ids.add(c.backup_printer_id)

        printer_map = {}
        if printer_ids:
            printers_result = await self.db.execute(
                select(Printer).where(
                    Printer.printer_id.in_(printer_ids),
                    Printer.store_id == store_id,
                )
            )
            printer_map = {p.printer_id: p.name for p in printers_result.scalars().all()}

        return [
            {
                "category_id": str(c.category_id),
                "name": c.name,
                "sort_order": c.sort_order,
                "printer_id": str(c.printer_id) if c.printer_id else None,
                "printer_name": printer_map.get(c.printer_id) if c.printer_id else None,
                "backup_printer_id": str(c.backup_printer_id) if c.backup_printer_id else None,
                "backup_printer_name": printer_map.get(c.backup_printer_id) if c.backup_printer_id else None,
            }
            for c in categories
        ]

    async def update_category_printer(
        self,
        store_id: uuid.UUID,
        category_id: uuid.UUID,
        printer_id: Optional[str],
        backup_printer_id: Optional[str],
    ) -> bool:
        """更新分类绑定的打印机"""
        result = await self.db.execute(
            select(Category).where(
                Category.category_id == category_id,
                Category.store_id == store_id,
                Category.is_active == True,
            )
        )
        category = result.scalar_one_or_none()
        if not category:
            return False

        category.printer_id = uuid.UUID(printer_id) if printer_id else None
        category.backup_printer_id = uuid.UUID(backup_printer_id) if backup_printer_id else None
        await self.db.commit()
        return True

    # ==================== 模块打印配置 CRUD ====================

    # 系统内置的模块打印场景
    SYSTEM_PRINT_SCENES = [
        {
            "module_code": "wine_storage",
            "scene_code": "store_label",
            "scene_name": "存酒标签",
            "description": "客户存酒时打印的标签，贴在酒瓶上",
            "document_type": "label",
            "trigger_event": "order_created",
            "printer_type": "label",
        },
        {
            "module_code": "wine_storage",
            "scene_code": "take_receipt",
            "scene_name": "取酒凭证",
            "description": "客户取酒时打印的凭证小票",
            "document_type": "receipt",
            "trigger_event": "manual",
            "printer_type": "receipt",
        },
        {
            "module_code": "pos",
            "scene_code": "order_slip",
            "scene_name": "厨房/吧台出单",
            "description": "订单创建时，根据商品分类自动路由到厨房或吧台打印机",
            "document_type": "order",
            "trigger_event": "order_created",
            "printer_type": "order",
        },
        {
            "module_code": "pos",
            "scene_code": "receipt",
            "scene_name": "客户小票",
            "description": "支付完成时打印的客户收据",
            "document_type": "receipt",
            "trigger_event": "payment_completed",
            "printer_type": "receipt",
        },
        {
            "module_code": "pos",
            "scene_code": "refund_receipt",
            "scene_name": "退款凭证",
            "description": "退款时打印的退款凭证",
            "document_type": "receipt",
            "trigger_event": "manual",
            "printer_type": "receipt",
        },
        {
            "module_code": "inventory",
            "scene_code": "stocktake_list",
            "scene_name": "盘点单",
            "description": "库存盘点时打印的盘点清单",
            "document_type": "receipt",
            "trigger_event": "manual",
            "printer_type": "receipt",
        },
        {
            "module_code": "employee",
            "scene_code": "sign_form",
            "scene_name": "签收单",
            "description": "员工签收工资条或其他文件时打印",
            "document_type": "receipt",
            "trigger_event": "manual",
            "printer_type": "receipt",
        },
        {
            "module_code": "booking",
            "scene_code": "booking_confirm",
            "scene_name": "预订确认",
            "description": "客户预订桌位时打印的确认单",
            "document_type": "receipt",
            "trigger_event": "order_created",
            "printer_type": "receipt",
        },
    ]

    async def list_module_configs(self, store_id: uuid.UUID) -> List[Dict[str, Any]]:
        """获取模块打印配置列表

        如果门店还没有配置，自动创建默认配置
        """
        from app.models.sys import ModulePrintConfig

        # 查询现有配置
        result = await self.db.execute(
            select(ModulePrintConfig).where(
                ModulePrintConfig.store_id == store_id,
            ).order_by(ModulePrintConfig.module_code, ModulePrintConfig.scene_code)
        )
        configs = result.scalars().all()

        # 如果没有配置，自动创建默认配置
        if not configs:
            configs = []
            for scene in self.SYSTEM_PRINT_SCENES:
                config = ModulePrintConfig(
                    store_id=store_id,
                    module_code=scene["module_code"],
                    scene_code=scene["scene_code"],
                    scene_name=scene["scene_name"],
                    description=scene.get("description"),
                    document_type=scene["document_type"],
                    trigger_event=scene["trigger_event"],
                    printer_type=scene["printer_type"],
                    enabled=True,
                )
                self.db.add(config)
                configs.append(config)
            await self.db.commit()
            for c in configs:
                await self.db.refresh(c)

        # 查询打印机名称
        printer_ids = {c.printer_id for c in configs if c.printer_id}
        printer_map = {}
        if printer_ids:
            printers_result = await self.db.execute(
                select(Printer).where(
                    Printer.printer_id.in_(printer_ids),
                    Printer.store_id == store_id,
                )
            )
            printer_map = {p.printer_id: p.name for p in printers_result.scalars().all()}

        return [
            {
                "config_id": str(c.config_id),
                "module_code": c.module_code,
                "scene_code": c.scene_code,
                "scene_name": c.scene_name,
                "description": c.description,
                "document_type": c.document_type,
                "trigger_event": c.trigger_event,
                "printer_type": c.printer_type,
                "enabled": c.enabled,
                "printer_id": str(c.printer_id) if c.printer_id else None,
                "printer_name": printer_map.get(c.printer_id) if c.printer_id else None,
            }
            for c in configs
        ]

    async def update_module_config(
        self,
        store_id: uuid.UUID,
        config_id: uuid.UUID,
        data: Dict[str, Any],
    ) -> bool:
        """更新模块打印配置"""
        from app.models.sys import ModulePrintConfig

        result = await self.db.execute(
            select(ModulePrintConfig).where(
                ModulePrintConfig.config_id == config_id,
                ModulePrintConfig.store_id == store_id,
            )
        )
        config = result.scalar_one_or_none()
        if not config:
            return False

        if "enabled" in data:
            config.enabled = data["enabled"]
        if "printer_id" in data:
            config.printer_id = uuid.UUID(data["printer_id"]) if data["printer_id"] else None

        await self.db.commit()
        return True

    async def batch_update_module_configs(
        self,
        store_id: uuid.UUID,
        updates: List[Dict[str, Any]],
    ) -> int:
        """批量更新模块打印配置"""
        from app.models.sys import ModulePrintConfig

        updated_count = 0
        for update in updates:
            config_id = uuid.UUID(update["config_id"])
            result = await self.db.execute(
                select(ModulePrintConfig).where(
                    ModulePrintConfig.config_id == config_id,
                    ModulePrintConfig.store_id == store_id,
                )
            )
            config = result.scalar_one_or_none()
            if not config:
                continue

            if "enabled" in update:
                config.enabled = update["enabled"]
            if "printer_id" in update:
                config.printer_id = uuid.UUID(update["printer_id"]) if update["printer_id"] else None

            updated_count += 1

        await self.db.commit()
        return updated_count

    async def get_module_printer(
        self,
        store_id: uuid.UUID,
        module_code: str,
        scene_code: str,
    ) -> Optional[Printer]:
        """获取模块打印场景对应的打印机

        如果模块配置了指定打印机，使用指定的；
        否则使用默认的打印机类型匹配。
        """
        from app.models.sys import ModulePrintConfig

        # 查询模块配置
        result = await self.db.execute(
            select(ModulePrintConfig).where(
                ModulePrintConfig.store_id == store_id,
                ModulePrintConfig.module_code == module_code,
                ModulePrintConfig.scene_code == scene_code,
                ModulePrintConfig.enabled == True,
            )
        )
        config = result.scalar_one_or_none()

        if not config:
            return None

        # 如果配置了指定打印机
        if config.printer_id:
            printer_result = await self.db.execute(
                select(Printer).where(
                    Printer.printer_id == config.printer_id,
                    Printer.store_id == store_id,
                    Printer.is_active == True,
                )
            )
            return printer_result.scalar_one_or_none()

        # 否则按打印机类型匹配
        return await self._find_printer_by_type(store_id, config.printer_type)
