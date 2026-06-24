"""
存酒管理业务逻辑层
- 瓶身码生成
- 存酒 + 云打印机出标签 + 短信通知
- 服务员取酒（分批）
- 客人自助取酒 + 云打印机出小票
"""
import secrets
import uuid
from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.wine_storage import WineStorage
from app.repositories.wine import WineRepository
from app.utils.exceptions import NotFoundError, ConflictError, ValidationError
from app.services.printer_service import PrinterService
from app.services.sms import send_stored_sms as _sms_stored, send_retrieved_sms as _sms_retrieved


def generate_bottle_label(store_id) -> str:
    """生成瓶身码：取 store_id 前4位 + 随机4位"""
    suffix = secrets.randbelow(10000)
    prefix = str(store_id).replace("-", "")[:4].upper()
    return f"{prefix}-{suffix:04d}"


async def generate_unique_label(repo: WineRepository) -> str:
    for _ in range(100):
        label = generate_bottle_label(repo.store_id)
        existing = await repo.get_by_bottle_label(label)
        if not existing:
            return label
    ts = int(datetime.now().timestamp() * 1000) % 100000
    prefix = str(repo.store_id).replace("-", "")[:4].upper()
    return f"{prefix}-{ts:05d}"


# ==================== 存酒 ====================

async def store_wine(
    session: AsyncSession,
    store_id: uuid.UUID,
    customer_name: str,
    phone: str,
    wine_name: str,
    remaining_ml: int,
    quantity: int = 1,
    cabinet_no: str | None = None,
    notes: str | None = None,
) -> WineStorage:
    """存酒：生成瓶身码 → 自动分配柜号 → 入库（支持多瓶） → 云打印标签 → 短信通知"""
    repo = WineRepository(session, store_id)
    last_wine = None

    for _ in range(max(quantity, 1)):
        bottle_label = await generate_unique_label(repo)

        if not cabinet_no:
            cabinet_no = await repo.next_cabinet_no()

        wine = WineStorage(
            store_id=store_id,
            customer_name=customer_name,
            phone=phone,
            wine_name=wine_name,
            bottle_label=bottle_label,
            date_stored=date.today(),
            expiry_date=date.today() + timedelta(days=180),
            initial_ml=remaining_ml,
            remaining_ml=remaining_ml,
            cabinet_no=cabinet_no,
            status="stored",
            notes=notes,
        )
        await repo.create(wine)
        last_wine = wine

        # 每瓶异步出标签
        from asyncio import create_task
        create_task(_safe_print_label(bottle_label, customer_name, wine_name, remaining_ml, date.today().isoformat(), cabinet_no, store_id))

    # 短信只发一次
    from asyncio import create_task
    create_task(_safe_send_sms(phone, customer_name, wine_name, last_wine.bottle_label, remaining_ml))

    qty = max(quantity, 1)
    logger.info(f"存酒成功: x{qty} {customer_name} {wine_name} {remaining_ml}ml")
    return last_wine


async def _safe_print_label(bottle_label: str, customer_name: str, wine_name: str,
                            remaining_ml: int, date_stored: str, cabinet_no: str, store_id: uuid.UUID):
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            service = PrinterService(session)
            # 构建标签内容
            capacity_map = {750: "满瓶", 562: "3/4瓶", 375: "1/2瓶", 187: "1/4瓶"}
            capacity = capacity_map.get(remaining_ml, "满瓶")
            content = f"存酒标签\n客户: {customer_name}\n酒名: {wine_name}\n容量: {capacity}\n瓶码: {bottle_label}\n柜号: {cabinet_no}\n日期: {date_stored}"

            # 使用标签打印机
            store_uuid = uuid.UUID(str(store_id)) if not isinstance(store_id, uuid.UUID) else store_id
            await service.print_by_category(
                store_id=store_uuid,
                category_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # 存酒分类ID
                content=content,
                trigger="order_created",
                document_type="label",
            )
    except Exception as e:
        logger.error(f"打印标签失败（不影响存酒）: {e}")


async def _safe_send_sms(phone: str, customer_name: str, wine_name: str,
                          bottle_label: str, remaining_ml: int):
    try:
        await _sms_stored(phone, customer_name, wine_name, bottle_label, remaining_ml)
    except Exception as e:
        logger.error(f"短信发送失败（不影响存酒）: {e}")


# ==================== 服务员取酒 ====================

async def staff_retrieve(
    session: AsyncSession,
    store_id: uuid.UUID,
    bottle_label: str,
    retrieve_ml: int,
    table_no: str | None = None,
    user_id: uuid.UUID | None = None,
) -> WineStorage:
    """服务员取酒：查瓶身码 → 扣减 → 短信通知"""
    repo = WineRepository(session, store_id)
    wine = await repo.get_by_bottle_label(bottle_label)

    if not wine:
        raise NotFoundError(f"未找到瓶身码 {bottle_label}")

    if wine.status == "retrieved":
        raise ConflictError("该瓶酒已全部取完")

    current = wine.remaining_ml or 0
    if retrieve_ml > current:
        raise ValidationError(f"剩余 {current}ml，无法取出 {retrieve_ml}ml")

    wine = await repo.partial_retrieve(wine, retrieve_ml, table_no, user_id)

    from asyncio import create_task
    create_task(_sms_retrieved(wine.phone, wine.customer_name, wine.wine_name, retrieve_ml, bottle_label))
    # 服务员取酒也出取酒小票
    create_task(_safe_print_receipt(bottle_label, wine.customer_name, wine.wine_name, retrieve_ml, table_no or "-", store_id))

    logger.info(f"服务员取酒: {bottle_label} {wine.customer_name} {retrieve_ml}ml 桌号={table_no}")
    return wine


async def _safe_print_receipt(bottle_label: str, customer_name: str, wine_name: str,
                              retrieve_ml: int, table_no: str, store_id: uuid.UUID):
    try:
        from app.database import AsyncSessionLocal
        async with AsyncSessionLocal() as session:
            service = PrinterService(session)
            # 构建取酒小票内容
            content = (
                f"┌──────────────────────────┐\n"
                f"│      CRUSH 酒吧 取酒单     │\n"
                f"├──────────────────────────┤\n"
                f"│  客人: {customer_name:<16}│\n"
                f"│  酒名: {wine_name:<16}│\n"
                f"│  取出: {retrieve_ml}ml{' ' * (14 - len(str(retrieve_ml)))}│\n"
                f"│  桌号: {table_no:<16}│\n"
                f"│  瓶码: {bottle_label:<16}│\n"
                f"├──────────────────────────┤\n"
                f"│    >> 请送酒至对应桌台     │\n"
                f"└──────────────────────────┘"
            )

            # 使用小票打印机
            store_uuid = uuid.UUID(str(store_id)) if not isinstance(store_id, uuid.UUID) else store_id
            await service.print_by_category(
                store_id=store_uuid,
                category_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),  # 存酒分类ID
                content=content,
                trigger="manual",
                document_type="receipt",
            )
    except Exception as e:
        logger.error(f"打印取酒小票失败（不影响取酒）: {e}")


# ==================== 客人自助取酒 ====================

async def self_retrieve(
    session: AsyncSession,
    bottle_label: str,
    retrieve_ml: int,
    table_no: str | None = None,
) -> WineStorage:
    """客人自助取酒：查瓶身码（不限门店）→ 扣减 → 云打印机出小票"""
    from sqlalchemy import select
    from app.models.wine_storage import WineStorage

    stmt = select(WineStorage).where(WineStorage.bottle_label == bottle_label)
    result = await session.execute(stmt)
    wine = result.scalar_one_or_none()

    if not wine:
        raise NotFoundError(f"未找到瓶身码 {bottle_label}")

    if wine.status == "retrieved":
        raise ConflictError("该瓶酒已全部取完")

    current = wine.remaining_ml or 0
    if retrieve_ml > current:
        raise ValidationError(f"剩余 {current}ml，无法取出 {retrieve_ml}ml")

    wine.remaining_ml = current - retrieve_ml

    if table_no:
        wine.table_no = table_no

    if wine.remaining_ml == 0:
        wine.status = "retrieved"
        wine.retrieved_at = datetime.now()

    await session.flush()

    # 云打印机出取酒小票
    from asyncio import create_task
    create_task(_safe_print_receipt(
        bottle_label, wine.customer_name, wine.wine_name, retrieve_ml, table_no or "-", wine.store_id
    ))

    logger.info(f"客人自助取酒: {bottle_label} {wine.customer_name} {retrieve_ml}ml 桌号={table_no}")
    return wine
