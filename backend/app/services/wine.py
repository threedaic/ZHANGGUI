"""
存酒管理业务逻辑层
- 瓶身码生成
- 存酒 + 云打印机出标签 + 短信通知
- 服务员取酒（分批）
- 客人自助取酒 + 云打印机出小票
"""
import asyncio
import secrets
import uuid
from datetime import date, timedelta, datetime
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger
from app.models.wine_storage import WineStorage
from app.repositories.wine import WineRepository
from app.utils.exceptions import NotFoundError, ConflictError, ValidationError
from app.utils.deps import get_extra_config
from app.services.printer_service import PrinterService
from app.services.sms import send_stored_sms as _sms_stored, send_retrieved_sms as _sms_retrieved

# 存酒打印分类 ID（需与 sys_print_routes 种子数据一致）
WINE_PRINT_CATEGORY_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")

# 后台异步任务引用集合，防止被 GC 回收（Python asyncio 已知行为）
_pending_tasks: set[asyncio.Task] = set()


def _spawn(coro) -> asyncio.Task:
    """创建后台任务并保留引用，完成后自动清理，防止任务被 GC 中途回收。"""
    task = asyncio.create_task(coro)
    _pending_tasks.add(task)
    task.add_done_callback(_pending_tasks.discard)
    return task


def generate_bottle_label(store_id) -> str:
    """生成瓶身码：取 store_id 前4位 + 随机8位十六进制（约 43 亿种组合，防暴力枚举）"""
    suffix = secrets.token_hex(4).upper()
    prefix = str(store_id).replace("-", "")[:4].upper()
    return f"{prefix}-{suffix}"


async def generate_unique_label(repo: WineRepository) -> str:
    for _ in range(100):
        label = generate_bottle_label(repo.store_id)
        existing = await repo.get_by_bottle_label(label)
        if not existing:
            return label
    ts = int(datetime.now().timestamp() * 1000) % 100000000
    prefix = str(repo.store_id).replace("-", "")[:4].upper()
    return f"{prefix}-{ts:08d}"


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

    # 读取店铺存酒配置：保质期天数
    wine_cfg = await get_extra_config(session, str(store_id), "wine")
    shelf_life_days = wine_cfg.get("shelf_life_days", 180)
    try:
        shelf_life_days = int(shelf_life_days)
    except (TypeError, ValueError):
        shelf_life_days = 180

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
            expiry_date=date.today() + timedelta(days=shelf_life_days),
            initial_ml=remaining_ml,
            remaining_ml=remaining_ml,
            cabinet_no=cabinet_no,
            status="stored",
            notes=notes,
        )
        await repo.create(wine)
        last_wine = wine

        # 每瓶异步出标签（满瓶不打印，下次直接从库房拿新的）
        if remaining_ml < 750:
            _spawn(_safe_print_label(bottle_label, customer_name, phone, wine_name, remaining_ml, date.today().isoformat(), cabinet_no, store_id))

    # 短信只发一次
    _spawn(_safe_send_sms(phone, customer_name, wine_name, last_wine.bottle_label, remaining_ml))

    qty = max(quantity, 1)
    logger.info(f"存酒成功: x{qty} {customer_name} {wine_name} {remaining_ml}ml")
    return last_wine


async def _safe_print_label(bottle_label: str, customer_name: str, phone: str, wine_name: str,
                            remaining_ml: int, date_stored: str, cabinet_no: str, store_id: uuid.UUID):
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text as sql_text
        async with AsyncSessionLocal() as session:
            # 异步任务需要设置RLS上下文，否则查询会被行级安全拦截
            # 注意：asyncpg 不支持 SET LOCAL 的参数绑定，必须用字符串内联
            await session.execute(sql_text(f"SET LOCAL app.current_store_id = '{store_id}'"))
            await session.execute(sql_text("SET LOCAL app.current_user_role = 'boss'"))

            service = PrinterService(session)
            # 构建标签内容
            capacity_map = {750: "满瓶", 562: "3/4瓶", 375: "1/2瓶", 187: "1/4瓶"}
            capacity = capacity_map.get(remaining_ml, "满瓶")

            store_uuid = uuid.UUID(str(store_id)) if not isinstance(store_id, uuid.UUID) else store_id

            # 优先使用模块打印配置（老板在设置页配置的"存酒标签"打印机）
            printer = await service.get_module_printer(store_uuid, "wine_storage", "store_label")

            if printer:
                content = _build_label_content(printer, customer_name, phone, wine_name, capacity, bottle_label, cabinet_no, date_stored)
                await service._send_print(store_uuid, printer, content)
                logger.info(f"存酒标签已发送到模块配置的打印机: {printer.name}")
            else:
                # 兜底：直接查找标签类型的打印机
                printer = await service._find_printer_by_type(store_uuid, "label")
                if printer:
                    content = _build_label_content(printer, customer_name, phone, wine_name, capacity, bottle_label, cabinet_no, date_stored)
                    await service._send_print(store_uuid, printer, content)
                    logger.info(f"存酒标签已发送到标签打印机: {printer.name}")
                else:
                    logger.warning(f"未找到标签打印机，跳过打印")
    except Exception as e:
        logger.error(f"打印标签失败（不影响存酒）: {e}")


def _detect_label_size(printer) -> tuple[int, int]:
    """从打印机配置自动检测标签尺寸（宽mm, 高mm）

    优先级：extra_config.label_width/label_height > paper_width + 默认高 > 默认40x30
    常见标签规格：40x30, 50x30, 60x40, 80x50
    """
    extra = printer.extra_config or {}
    w = extra.get("label_width") or printer.paper_width or 40
    h = extra.get("label_height") or 30
    return int(w), int(h)


def _estimate_text_width(text: str, font_base: int, w_scale: int) -> int:
    """估算文本点阵宽度（dots）。中文字符等宽，ASCII约0.55倍宽。"""
    dots = 0
    for ch in text:
        if ord(ch) > 127:
            dots += font_base * w_scale  # 中文/全角
        else:
            dots += int(font_base * w_scale * 0.55)  # ASCII
    return dots


def _fit_font_scale(text: str, max_width_dots: int, base_font: int = 12,
                    max_scale: int = 4, min_scale: int = 1) -> int:
    """自动缩放字号使文本不超过最大宽度，返回最优 w/h 倍率"""
    for scale in range(max_scale, min_scale - 1, -1):
        if _estimate_text_width(text, base_font, scale) <= max_width_dots:
            return scale
    return min_scale


def _build_label_content(printer, customer_name: str, phone: str, wine_name: str, capacity: str,
                         bottle_label: str, cabinet_no: str, date_stored: str) -> str:
    """生成标签内容 —— 自适应布局引擎

    核心能力：
    1. 自动检测标签纸尺寸（宽×高 mm）
    2. 按比例划分区域，消除空白
    3. 根据可用宽度自动缩放字号
    4. 条码高度自适应填满底部

    区域分配（纵向比例）：
      客户姓名 35% | 手机号 17% | 酒名+容量 17% | 柜号 12% | 条码 19%
    """
    printer_type = (printer.printer_type or "").lower()
    brand = printer.brand or ""
    is_label = printer_type in ("label", "标签", "标签机")

    if not is_label or brand not in ("feie", "xpyun"):
        # 小票机格式（纯文本）
        return f"{customer_name}\n{phone}\n{wine_name} {capacity}\n{cabinet_no}柜\n{bottle_label}\n{date_stored}"

    # ---- 1. 检测标签尺寸，计算点阵网格 ----
    label_w_mm, label_h_mm = _detect_label_size(printer)
    DPI = 8  # 203DPI = 8 dots/mm
    max_x = label_w_mm * DPI
    max_y = label_h_mm * DPI

    # ---- 2. 按比例分配纵向区域 ----
    margin_x = max(3, max_x // 40)       # 左右边距（约2.5%）
    margin_y = max(2, max_y // 50)       # 上下边距
    usable_x = max_x - margin_x * 2      # 可用宽度
    usable_y = max_y - margin_y * 2      # 可用高度

    # 区域比例（姓名最大，条码填底）
    name_ratio, phone_ratio, wine_ratio, cabinet_ratio, barcode_ratio = 0.35, 0.17, 0.17, 0.12, 0.19

    y = margin_y
    name_zone_h = int(usable_y * name_ratio)
    phone_zone_h = int(usable_y * phone_ratio)
    wine_zone_h = int(usable_y * wine_ratio)
    cabinet_zone_h = int(usable_y * cabinet_ratio)
    barcode_zone_h = usable_y - name_zone_h - phone_zone_h - wine_zone_h - cabinet_zone_h

    name_y = y; y += name_zone_h
    phone_y = y; y += phone_zone_h
    wine_y = y; y += wine_zone_h
    cabinet_y = y; y += cabinet_zone_h
    barcode_y = y

    # ---- 3. 自动缩放字号 ----
    # 姓名最大：在不超过可用宽度的前提下尽量放大
    name_text = customer_name[:8]  # 限制长度防止溢出
    name_scale = _fit_font_scale(name_text, usable_x, max_scale=4, min_scale=1)

    # 普通信息行：根据标签物理宽度选择基础倍率
    if label_w_mm >= 50:     # 50mm+
        info_scale = 2
    elif label_w_mm >= 35:   # 40mm
        info_scale = 2
    else:                    # 30mm或更窄
        info_scale = 1

    # 各行文本如果太长就降级字号
    phone_text = phone
    wine_text = f"{wine_name} {capacity}"
    cabinet_text = f"{cabinet_no}柜"
    phone_scale = min(info_scale, _fit_font_scale(phone_text, usable_x, max_scale=info_scale))
    wine_scale = min(info_scale, _fit_font_scale(wine_text, usable_x, max_scale=info_scale))
    cabinet_scale = min(info_scale, _fit_font_scale(cabinet_text, usable_x, max_scale=info_scale))

    # ---- 4. 生成 TSPL 指令 ----
    parts = [
        f"<SIZE>{label_w_mm},{label_h_mm}</SIZE>",
        "<DIRECTION>1</DIRECTION>",
        # 客户姓名（最大字号，居顶）
        f"<TEXT x='{margin_x}' y='{name_y}' font='12' w='{name_scale}' h='{name_scale}'>{name_text}</TEXT>",
        # 手机号
        f"<TEXT x='{margin_x}' y='{phone_y}' font='12' w='{phone_scale}' h='{phone_scale}'>{phone_text}</TEXT>",
        # 酒名+容量
        f"<TEXT x='{margin_x}' y='{wine_y}' font='12' w='{wine_scale}' h='{wine_scale}'>{wine_text}</TEXT>",
        # 柜号
        f"<TEXT x='{margin_x}' y='{cabinet_y}' font='12' w='{cabinet_scale}' h='{cabinet_scale}'>{cabinet_text}</TEXT>",
    ]

    # 条形码：高度填满底部区域，宽度根据标签尺寸调整
    # BC128 参数: x y h(条码高度) s(是否显示文字1/0) n(1) w(窄条宽度1-4)
    bc_h = max(30, barcode_zone_h - 12)  # 留一点空间给条码下方的文字
    bc_w = 2 if usable_x >= 300 else 1   # 宽标签用粗条码更易扫
    parts.append(
        f"<BC128 x='{margin_x}' y='{barcode_y}' h='{bc_h}' s='1' n='1' w='{bc_w}'>{bottle_label}</BC128>"
    )

    return "".join(parts)


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

    _spawn(_sms_retrieved(wine.phone, wine.customer_name, wine.wine_name, retrieve_ml, bottle_label))
    # 服务员取酒也出取酒小票
    _spawn(_safe_print_receipt(bottle_label, wine.customer_name, wine.wine_name, retrieve_ml, table_no or "-", store_id))

    logger.info(f"服务员取酒: {bottle_label} {wine.customer_name} {retrieve_ml}ml 桌号={table_no}")
    return wine


async def _safe_print_receipt(bottle_label: str, customer_name: str, wine_name: str,
                              retrieve_ml: int, table_no: str, store_id: uuid.UUID):
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text as sql_text
        async with AsyncSessionLocal() as session:
            # 异步任务需要设置RLS上下文
            # 注意：asyncpg 不支持 SET LOCAL 的参数绑定，必须用字符串内联
            await session.execute(sql_text(f"SET LOCAL app.current_store_id = '{store_id}'"))
            await session.execute(sql_text("SET LOCAL app.current_user_role = 'boss'"))

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

            # 优先使用模块打印配置
            store_uuid = uuid.UUID(str(store_id)) if not isinstance(store_id, uuid.UUID) else store_id
            printer = await service.get_module_printer(store_uuid, "wine_storage", "take_receipt")

            if printer:
                await service._send_print(store_uuid, printer, content)
                logger.info(f"取酒小票已发送到模块配置的打印机: {printer.name}")
            else:
                # 兜底：查找小票打印机
                printer = await service._find_printer_by_type(store_uuid, "receipt")
                if printer:
                    await service._send_print(store_uuid, printer, content)
                    logger.info(f"取酒小票已发送到小票打印机: {printer.name}")
                else:
                    logger.warning(f"未找到小票打印机，跳过打印")
    except Exception as e:
        logger.error(f"打印取酒小票失败（不影响取酒）: {e}")


# ==================== 客人自助取酒 ====================

async def self_retrieve(
    session: AsyncSession,
    bottle_label: str,
    retrieve_ml: int,
    table_no: str | None = None,
) -> WineStorage:
    """客人自助取酒：查瓶身码（不限门店）→ 扣减 → 云打印机出小票

    bottle_label 作为能力令牌授权访问，查询时关闭 RLS 以跨店查找。
    """
    from sqlalchemy import select, text
    from app.models.wine_storage import WineStorage

    await session.execute(text("SET LOCAL row_security = off"))
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
    _spawn(_safe_print_receipt(
        bottle_label, wine.customer_name, wine.wine_name, retrieve_ml, table_no or "-", wine.store_id
    ))

    logger.info(f"客人自助取酒: {bottle_label} {wine.customer_name} {retrieve_ml}ml 桌号={table_no}")
    return wine
