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


# 飞鹅/芯烨 font=12 = 简体中文 24×24 dots，放大w/h倍后实际占 24×h dots 高
FONT_BASE_W = 24   # 中文字符宽度(dots)，font=12
FONT_BASE_H = 24   # 中文字符高度(dots)，font=12
ASCII_RATIO = 0.5  # ASCII字符宽度约为中文的50%
DPI = 8            # 203DPI = 8 dots/mm


def _text_height(scale: int) -> int:
    """单行文字高度（dots）"""
    return FONT_BASE_H * scale


def _text_width(text: str, scale: int) -> int:
    """估算文本点阵宽度（dots）"""
    dots = 0
    for ch in text:
        if ord(ch) > 127:
            dots += FONT_BASE_W * scale
        else:
            dots += int(FONT_BASE_W * scale * ASCII_RATIO)
    return dots


def _best_scale(text: str, max_width: int, max_s: int = 4, min_s: int = 1) -> int:
    """找不超过max_width的最大字号倍率"""
    for s in range(max_s, min_s - 1, -1):
        if _text_width(text, s) <= max_width:
            return s
    return min_s


def _build_label_content(printer, customer_name: str, phone: str, wine_name: str, capacity: str,
                         bottle_label: str, cabinet_no: str, date_stored: str) -> str:
    """生成标签内容 —— 自适应布局引擎

    基于飞鹅官方文档：font=12 的中文字体为 24×24 dots，w/h 为放大倍率。
    所有坐标基于实际渲染高度计算，确保不重叠。

    布局策略：
      从上到下依次排列，每个元素的 Y = 上一个元素的 Y + 上一个元素的实际高度 + 间距
      姓名（最大）→ 手机号 → 酒名+容量 → 柜号 → 条码
    """
    printer_type = (printer.printer_type or "").lower()
    brand = printer.brand or ""
    is_label = printer_type in ("label", "标签", "标签机")

    if not is_label or brand not in ("feie", "xpyun"):
        # 不支持TSPL坐标的标签机/小票机：用排版标签格式（居中+放大姓名）
        return (
            f"<C><B>{customer_name}</B></C>\n"
            f"<C>{phone}</C>\n"
            f"----------------------------\n"
            f"{wine_name} {capacity}\n"
            f"{cabinet_no}柜\n"
            f"瓶码:{bottle_label}\n"
            f"{date_stored}\n\n\n"
        )

    # ---- 1. 检测标签尺寸 ----
    label_w_mm, label_h_mm = _detect_label_size(printer)
    max_x = label_w_mm * DPI
    max_y = label_h_mm * DPI

    # ---- 2. 计算布局参数 ----
    margin = max(4, max_x // 30)      # 边距
    gap = max(2, max_y // 60)         # 行间距
    usable_w = max_x - margin * 2     # 可用宽度
    usable_h = max_y - margin * 2     # 可用高度

    # ---- 3. 确定各元素字号（宽度和高度双重约束）----
    name_text = customer_name[:6]
    phone_text = phone
    wine_text = f"{wine_name} {capacity}"
    cabinet_text = f"{cabinet_no}柜"

    # 条码至少需要的高度（条码本身40 + 下方文字24）
    bc_min_h = 64

    # 从大到小尝试字号组合，找到能放下的最大字号
    # 姓名倍率从4降到1，信息行倍率从2降到1
    chosen = None
    for name_s in range(4, 0, -1):
        # 宽度约束：姓名不能超宽
        if _text_width(name_text, name_s) > usable_w:
            continue
        for info_s in range(2, 0, -1):
            # 宽度约束：信息行不能超宽
            if (_text_width(phone_text, info_s) > usable_w or
                _text_width(wine_text, info_s) > usable_w):
                continue
            # 高度约束：所有元素 + 条码必须放得下
            total_h = (_text_height(name_s) + _text_height(info_s) * 3 +
                       gap * 4 + bc_min_h)
            if total_h <= usable_h:
                chosen = (name_s, info_s)
                break
        if chosen:
            break

    if chosen:
        name_scale, info_scale = chosen
    else:
        # 极端情况：全部用最小字号
        name_scale = _best_scale(name_text, usable_w, max_s=4, min_s=1)
        info_scale = 1

    phone_scale = min(info_scale, _best_scale(phone_text, usable_w, max_s=info_scale))
    wine_scale = min(info_scale, _best_scale(wine_text, usable_w, max_s=info_scale))
    cabinet_scale = min(info_scale, _best_scale(cabinet_text, usable_w, max_s=info_scale))

    # ---- 4. 从上到下计算每个元素的实际Y坐标 ----
    y = margin

    # 姓名
    name_y = y
    name_h = _text_height(name_scale)
    y += name_h + gap

    # 手机号
    phone_y = y
    phone_h = _text_height(phone_scale)
    y += phone_h + gap

    # 酒名+容量
    wine_y = y
    wine_h = _text_height(wine_scale)
    y += wine_h + gap

    # 柜号
    cabinet_y = y
    cabinet_h = _text_height(cabinet_scale)
    y += cabinet_h + gap

    # 条码：用剩余空间，至少留40 dots给条码本身 + 24 dots给条码下方文字
    barcode_y = y
    barcode_bottom = max_y - margin          # 标签底部
    bc_text_h = 24                            # 条码下方文字高度
    bc_h = max(40, barcode_bottom - barcode_y - bc_text_h)
    # 条码窄条宽度：宽标签用2，窄标签用1
    bc_narrow = 2 if usable_w >= 300 else 1

    # ---- 5. 生成 TSPL 指令 ----
    parts = [
        f"<SIZE>{label_w_mm},{label_h_mm}</SIZE>",
        "<DIRECTION>1</DIRECTION>",
        f"<TEXT x='{margin}' y='{name_y}' font='12' w='{name_scale}' h='{name_scale}'>{name_text}</TEXT>",
        f"<TEXT x='{margin}' y='{phone_y}' font='12' w='{phone_scale}' h='{phone_scale}'>{phone_text}</TEXT>",
        f"<TEXT x='{margin}' y='{wine_y}' font='12' w='{wine_scale}' h='{wine_scale}'>{wine_text}</TEXT>",
        f"<TEXT x='{margin}' y='{cabinet_y}' font='12' w='{cabinet_scale}' h='{cabinet_scale}'>{cabinet_text}</TEXT>",
        f"<BC128 x='{margin}' y='{barcode_y}' h='{bc_h}' s='1' n='{bc_narrow}' w='1'>{bottle_label}</BC128>",
    ]

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
