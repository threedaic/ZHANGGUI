"""
云打印机服务
- 存酒出标签（自适应宽度: 58/60/80mm）
- 客人自助取酒出取酒小票
配置从 StoreSettings 表读取。
"""
from loguru import logger
from app.utils.http_client import http_client

CABINET_LABELS = {1: "一柜", 2: "二柜", 3: "三柜", 4: "四柜"}


async def _get_printer_config(store_id: int) -> dict:
    from app.database import AsyncSessionLocal
    from sqlalchemy import select
    from app.models.store import StoreSettings
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(StoreSettings).where(StoreSettings.store_id == store_id)
        )
        settings = result.scalar_one_or_none()
    if not settings:
        return {}
    return {
        "enabled": settings.printer_enabled,
        "label_printer_enabled": settings.label_printer_enabled if settings.label_printer_enabled is not None else False,
        "receipt_printer_enabled": settings.receipt_printer_enabled if settings.receipt_printer_enabled is not None else False,
        "brand": settings.printer_brand or "yilianyun",
        "api_url": settings.printer_api_url or "",
        "sn": settings.printer_sn or "",
        "user": settings.printer_user or "",
        "ukey": settings.printer_ukey or "",
        "label_width": settings.printer_label_width or 80,
        "label_height": settings.printer_label_height or 50,
    }


def _build_label(
    bottle_label: str, customer_name: str, wine_name: str,
    capacity: str, date_stored: str, cabinet_no: str, width_mm: int, height_mm: int,
) -> str:
    """构建标签内容，根据宽高自适应布局。"""
    w = max(width_mm, 40)
    h = height_mm
    total = int(w / 1.7)
    inner = total - 2

    # 根据标签高度决定空行数：40mm=紧凑(0空行)，50mm=标准(2空行)，60mm=宽松(4空行)
    spacers = 0
    if h >= 60:
        spacers = 4
    elif h >= 50:
        spacers = 2

    empty_line = "│" + " " * inner + "│"
    name_line = "│" + _center(customer_name, inner) + "│"
    wine_line = "│" + _pad(f"  {wine_name}", inner - len(capacity) - 3) + f"  {capacity}│"
    cabinet_line = "│" + _pad(f"  {cabinet_no}", inner - len(date_stored) - 3) + f"  {date_stored}│"
    barcode_placeholder = "│" + _center("[ CODE128 条码 ]", inner) + "│"
    code_line = "│" + _center(f"{bottle_label}", inner) + "│"
    box_top = "┌" + "─" * inner + "┐"
    box_bot = "└" + "─" * inner + "┘"

    lines = [box_top]
    lines.append(empty_line)
    lines.append(name_line)
    lines.append(empty_line)
    lines.append(wine_line)
    lines.append(cabinet_line)
    if spacers >= 1:
        lines.append(empty_line)
    lines.append(barcode_placeholder)
    lines.append(code_line)
    if spacers >= 2:
        lines.append(empty_line)
    lines.append(box_bot)
    return "\n".join(lines)


def _center(text: str, width: int) -> str:
    """居中文本。"""
    if len(text) >= width:
        return text[:width]
    pad = (width - len(text)) // 2
    return " " * pad + text + " " * (width - len(text) - pad)


def _pad(text: str, width: int) -> str:
    """左对齐填充到指定宽度。"""
    if len(text) >= width:
        return text[:width]
    return text + " " * (width - len(text))


async def print_label(
    bottle_label: str, customer_name: str, wine_name: str,
    remaining_ml: int, date_stored: str, cabinet_no: str, store_id: int,
) -> bool:
    config = await _get_printer_config(store_id)
    # 标签打印机独立开关：label_printer_enabled 优先；若未配置则回退到总开关 printer_enabled
    label_on = config.get("label_printer_enabled") or config.get("enabled") or False
    if not label_on:
        return True

    capacity_map = {750: "满瓶", 562: "3/4瓶", 375: "1/2瓶", 187: "1/4瓶"}
    capacity = capacity_map.get(remaining_ml, "满瓶")
    cabinet_display = CABINET_LABELS.get(int(cabinet_no), f"柜{cabinet_no}") if cabinet_no and cabinet_no.isdigit() else str(cabinet_no)

    width = config.get("label_width", 80)
    height = config.get("label_height", 50)
    content = _build_label(bottle_label, customer_name, wine_name, capacity, date_stored, cabinet_display, width, height)

    try:
        await _send_print(config, content)
        logger.info(f"存酒标签打印: {bottle_label} {width}mm")
        return True
    except Exception as e:
        logger.error(f"标签打印失败: {e}")
        return False


async def print_retrieve_receipt(
    bottle_label: str, customer_name: str, wine_name: str,
    retrieve_ml: int, table_no: str, store_id: int,
) -> bool:
    config = await _get_printer_config(store_id)
    # 取酒单打印机独立开关：receipt_printer_enabled 优先；若未配置则回退到总开关 printer_enabled
    receipt_on = config.get("receipt_printer_enabled") or config.get("enabled") or False
    if not receipt_on:
        return True

    content = (
        "┌──────────────────────────┐\n"
        "│      CRUSH 酒吧 取酒单     │\n"
        "├──────────────────────────┤\n"
        f"│  客人: {_pad(customer_name, 16)}│\n"
        f"│  酒名: {_pad(wine_name, 16)}│\n"
        f"│  取出: {_pad(str(retrieve_ml) + 'ml', 16)}│\n"
        f"│  桌号: {_pad(table_no, 16)}│\n"
        f"│  瓶码: {_pad(bottle_label, 16)}│\n"
        "├──────────────────────────┤\n"
        "│    >> 请送酒至对应桌台     │\n"
        "└──────────────────────────┘"
    )

    try:
        await _send_print(config, content)
        logger.info(f"取酒小票打印: {bottle_label}")
        return True
    except Exception as e:
        logger.error(f"取酒小票打印失败: {e}")
        return False


async def _send_print(config: dict, content: str):
    brand = config.get("brand", "yilianyun")
    sn = config.get("sn", "")
    if not sn:
        logger.warning("云打印 SN 未配置")
        return

    api_url = config.get("api_url", "")
    if not api_url:
        # 默认品牌 API 地址，应可通过环境变量覆盖
        brand_urls = {
            "feie": "http://api.feieyun.cn/Api/Open/printMsg",
            "yilianyun": "https://open-api.10ss.net/printer/print",
            "xpyun": "http://open.xpyun.net/api/openapi/xprinter/print",
            "gainscha": "https://api.poscom.cn/apisc/print",
            "jolimark": "https://cloud.jolimark.com/api/print",
        }
        api_url = brand_urls.get(brand, "")
    if not api_url:
        logger.warning("云打印 api_url 未配置")
        return

    user = config.get("user", "")
    ukey = config.get("ukey", "")
    payload = {"sn": sn, "content": content, "times": 1}

    if brand == "feie":
        payload["user"] = user; payload["ukey"] = ukey
    elif brand == "yilianyun":
        payload["client_id"] = user; payload["client_secret"] = ukey
    elif brand in ("xpyun", "gainscha"):
        payload["user"] = user; payload["user_key"] = ukey
    elif brand == "jolimark":
        payload["app_id"] = user; payload["app_secret"] = ukey

    await http_client.post(api_url, json_body=payload)
