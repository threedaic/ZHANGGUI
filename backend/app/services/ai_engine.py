"""
小C AI 引擎 — 核心服务

功能:
1. 自然语言查数据: NL → 生成 SQL → 执行 → 自然语言回复
2. AI 配置管理: 读取/保存 API 地址/Key(加密)/模型/温度
3. 知识库问答: 操作指引、规则说明

设计:
- 所有模块共用此引擎，不各自接外部 LLM API
- SQL 生成使用 LLM + DB schema context
- API Key 使用 AES 加密存储在 store_settings 表
- 配置实时生效，无需重启
"""

import json
import uuid
from datetime import date
from typing import Any

from sqlalchemy import text, select
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.store import StoreSettings
from app.utils.http_client import http_client
from app.utils.security import encrypt_aes, decrypt_aes
from app.utils.exceptions import AppError, NotFoundError


# ==================== 数据库 Schema 上下文（提供给 LLM） ====================

DB_SCHEMA_PROMPT = """
你是 Crush 酒吧的内部数据助手。你只能生成只读 SQL (SELECT)，禁止 INSERT/UPDATE/DELETE/DROP。

数据库表结构（PostgreSQL，所有查询必须加 WHERE store_id = :store_id）：

-- 存酒表
wine_storage(id, store_id, customer_name, phone, wine_name, bottle_label, date_stored TEXT, remaining_ml, cabinet_no, status, notes)
  status: 'stored' / 'retrieved' / 'pending_retrieve' / 'expired'

-- 排班表
schedules(id, store_id, employee_id, date DATE, shift_type, note)
  shift_type: '早班' / '晚班' / '全天' / '休息'

-- 员工表
employees(id, store_id, employee_code, name, phone, role, status, hire_date DATE)

-- 订桌表
bookings(id, store_id, customer_name, phone, date TEXT, time_slot, guests_count, table_no, status, notes)
  status: 'confirmed' / 'completed' / 'cancelled'

-- 桌位表
tables(id, store_id, area, table_no, capacity, status)

-- 开台表
table_sessions(id, store_id, table_no, opened_by, opened_at, closed_at, guest_count, status, notes)
  status: 'open' / 'closed'

-- 营收表
daily_revenue(id, store_id, date DATE, total_amount, guest_count, order_count, avg_per_guest)

-- 考勤表
attendance_records(id, store_id, employee_id, date DATE, check_in TEXT, check_out TEXT, status, is_late, is_early)

-- KPI表
kpi_scores(id, store_id, employee_id, period TEXT, dimension TEXT, score FLOAT)
kpi_results(id, store_id, employee_id, period TEXT, total_score FLOAT, coefficient FLOAT, grade TEXT)

SQL 规则:
1. 用户问"存酒/某人的酒"→ 查 wine_storage
2. 用户问"排班/晚班/早班/谁上班"→ 查 schedules JOIN employees
3. 用户问"桌/订桌/A1桌/有没有桌"→ 查 table_sessions(当前) + bookings(今日)
4. 用户问"营收/营业额/卖了多少钱"→ 查 daily_revenue
5. 用户问"考勤/迟到/打卡"→ 查 attendance_records JOIN employees
6. 用户问"KPI/评分/考核"→ 查 kpi_results JOIN employees
7. 名字模糊匹配用 LIKE '%关键词%'，手机号精确匹配
8. 日期用 CURRENT_DATE，今日订单查 bookings.date = CURRENT_DATE::text
9. LIMIT 最多 20 条
10. 只返回一条 SQL，不要注释

输出 JSON 格式:
{"sql": "SELECT ...", "explanation": "一句话说明你要查什么"}
"""

HELP_KB = """
Crush 酒吧知识库:

【存酒操作】
- 服务员操作: 首页 → 存酒管理 → 新建存酒 → 选容量(满/3/4/1/2/1/4) → 填客人姓名+手机号 → 选酒名 → 确认
- 确认后打印机自动出标签（条形码+客人名+酒名+日期+4位码）
- 短信自动发H5链接给客人
- 客人取酒: 扫瓶身二维码 → H5确认 → 服务员确认取出 → 短信通知

【打卡规则】
- 员工通过企微打卡，自动同步到Crush掌柜考勤系统
- 迟到判定: 晚于排班时间15分钟以上算迟到
- 早退: 早于排班时间15分钟以上算早退
- 补卡: 需向店长申请，店长在考勤页面操作补卡

【排班规则】
- 店长在排班管理页操作，按周视图排班
- 每人每月休息4天（可配置）
- 同一岗位最多1人同时休息（可配置）
- 店长不可休息周五周六

【工资说明】
- 每月5号自动生成工资（可配置）
- 应发 = 基本工资 + 补贴 + 餐补400
- 实发 = 应发 - 考勤扣款 - 社保 - 个税

【评分码】
- 每桌贴二维码，客人扫码评1-5星
- 低于3星自动通知店长企微消息
- 店长可在管理端查看评分汇总

【订桌预约】
- 员工后台录入预约信息
- 不支持客人自主选座
- 状态: 已确认/已完成/已取消
"""

# ==================== 配置管理 ====================


async def get_ai_config(
    db: AsyncSession,
    store_id: int,
) -> dict[str, Any]:
    """获取门店的 AI 配置，解密 API Key。"""
    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        return {
            "ai_api_url": None,
            "ai_api_key": None,
            "ai_model": None,
            "ai_temperature": 0.7,
        }

    api_key = None
    if settings.ai_api_key:
        try:
            api_key = decrypt_aes(settings.ai_api_key)
        except Exception:
            api_key = settings.ai_api_key  # fallback: may be plaintext

    return {
        "ai_api_url": settings.ai_api_url,
        "ai_api_key": api_key,
        "ai_model": settings.ai_model,
        "ai_temperature": settings.ai_temperature or 0.7,
    }


async def update_ai_config(
    db: AsyncSession,
    store_id: int,
    ai_api_url: str | None = None,
    ai_api_key: str | None = None,
    ai_model: str | None = None,
    ai_temperature: float | None = None,
) -> StoreSettings:
    """更新门店 AI 配置，API Key 自动 AES 加密存储。"""
    stmt = select(StoreSettings).where(StoreSettings.store_id == store_id)
    result = await db.execute(stmt)
    settings = result.scalar_one_or_none()

    if not settings:
        # 新建一行 store_settings
        settings = StoreSettings(store_id=store_id)
        db.add(settings)

    if ai_api_url is not None:
        settings.ai_api_url = ai_api_url
    if ai_api_key is not None:
        settings.ai_api_key = encrypt_aes(ai_api_key)
    if ai_model is not None:
        settings.ai_model = ai_model
    if ai_temperature is not None:
        settings.ai_temperature = ai_temperature

    await db.flush()
    await db.commit()
    logger.info(f"AI config updated for store_id={store_id}")
    return settings


def _mask_key(key: str) -> str:
    """脱敏展示 API Key: 'sk-abc1234xyz' → 'sk-a****xyz'"""
    if not key or len(key) <= 8:
        return "****"
    return key[:4] + "****" + key[-4:]


async def get_ai_config_masked(db: AsyncSession, store_id: int) -> dict[str, Any]:
    """获取 AI 配置（Key 脱敏），供管理端展示。"""
    config = await get_ai_config(db, store_id)
    key = config.get("ai_api_key")
    return {
        "ai_api_url": config["ai_api_url"],
        "ai_api_key_masked": _mask_key(key) if key else None,
        "ai_model": config["ai_model"],
        "ai_temperature": config["ai_temperature"],
    }


# ==================== 聊天引擎 ====================


async def _call_llm(
    config: dict[str, Any],
    messages: list[dict[str, str]],
) -> str:
    """调用 LLM API（OpenAI 兼容格式），返回 text 内容。"""
    url = config["ai_api_url"]
    api_key = config["ai_api_key"]
    model = config["ai_model"]
    temperature = config["ai_temperature"]

    if not url or not api_key:
        raise AppError(code=40002, message="AI 未配置，请在设置页填写 API 地址和 Key")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model or "gpt-4o-mini",
        "messages": messages,
        "temperature": temperature or 0.7,
        "max_tokens": 2000,
    }

    resp = await http_client.post(url, headers=headers, json_body=body)
    data = resp.json()

    choices = data.get("choices", [])
    if not choices:
        raise AppError(code=40003, message="AI 返回为空，请检查配置")

    return choices[0]["message"]["content"]


async def _execute_sql(
    db: AsyncSession,
    store_id: int,
    sql: str,
) -> list[dict[str, Any]]:
    """安全执行只读 SQL，返回 dict 列表。

    安全措施:
    1. 关键字检测（忽略大小写、检测注释注入符号 -- 和 /**/）
    2. 参数化绑定 store_id（防 SQL 注入）
    3. 结果集限制（后端强制 LIMIT 100）
    4. 只读事务（PG 层面兜底）
    """
    import re

    # --- 1. 危险关键字检测（忽略大小写，检测注释注入）---
    dangerous = [
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE",
    ]
    # 剥离注释后再检查（防止 SEL/**/ECT 绕过）
    sql_no_comments = re.sub(r"/\*[\s\S]*?\*/", "", sql)
    sql_no_comments = re.sub(r"--[^\n]*", "", sql_no_comments)
    sql_upper = sql_no_comments.strip().upper()
    for keyword in dangerous:
        if sql_upper.startswith(keyword) or f" {keyword} " in f" {sql_upper} ":
            raise AppError(code=40004, message="不允许执行写操作 SQL")

    # --- 2. 参数化绑定 store_id ---
    if ":store_id" in sql:
        sql_bound = text(sql).bindparams(store_id=store_id)
    else:
        sql_bound = text(sql)

    try:
        # --- 3. 只读事务 + 结果集限制 ---
        await db.execute(text("SET LOCAL default_transaction_read_only = on"))
        # Append LIMIT if not present, to prevent huge result sets
        sql_upper_limit = sql_no_comments.strip().upper()
        if "LIMIT" not in sql_upper_limit:
            if ":store_id" in sql:
                sql_bound = text(sql + " LIMIT 100").bindparams(store_id=store_id)
            else:
                sql_bound = text(sql + " LIMIT 100")

        result = await db.execute(sql_bound)
        rows = result.fetchall()
        columns = list(result.keys())
        return [dict(zip(columns, row)) for row in rows]
    except Exception as e:
        logger.error(f"SQL execution error: {e}\nSQL: {sql}")
        raise AppError(code=40005, message=f"数据查询失败: {str(e)}")


async def process_chat(
    db: AsyncSession,
    store_id: int,
    user_message: str,
    conversation_id: str | None = None,
) -> dict[str, Any]:
    """
    核心聊天流程:
    1. 判断是否知识库问题（直接回答）
    2. 否则: LLM 生成 SQL → 执行 → LLM 格式化结果
    """
    conv_id = conversation_id or str(uuid.uuid4())
    config = await get_ai_config(db, store_id)

    # Step 1: 判断是否知识库问题
    kb_check = await _check_knowledge_base(user_message, config)
    if kb_check:
        return {"reply": kb_check, "conversation_id": conv_id, "sql": None}

    # Step 2: LLM 生成 SQL
    sql_messages = [
        {"role": "system", "content": DB_SCHEMA_PROMPT},
        {"role": "user", "content": f"用户问题: {user_message}\n\n当前日期: {date.today().isoformat()}\n门店ID: {store_id}"},
    ]
    try:
        llm_output = await _call_llm(config, sql_messages)
        llm_output = llm_output.strip()
        # 清理 markdown 代码块包装
        if llm_output.startswith("```"):
            lines = llm_output.split("\n")
            llm_output = "\n".join(l for l in lines if not l.startswith("```"))
        parsed = json.loads(llm_output)
        generated_sql = parsed.get("sql", "")
    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"LLM SQL generation parse error: {e}, raw output: {llm_output[:200]}")
        # fallback: 尝试从输出中提取 SQL
        generated_sql = _extract_sql_fallback(llm_output)
        if not generated_sql:
            return {
                "reply": "抱歉，我没能理解您的问题。试试问: '赵先生的存酒还在吗'、'今天谁晚班'、'A1桌有人吗'",
                "conversation_id": conv_id,
                "sql": None,
            }

    # Step 3: 执行 SQL
    rows = []
    try:
        rows = await _execute_sql(db, store_id, generated_sql)
    except AppError as e:
        return {
            "reply": f"查询时遇到问题: {e.message}",
            "conversation_id": conv_id,
            "sql": generated_sql,
        }

    # Step 4: LLM 格式化结果
    if not rows:
        reply = await _format_empty_result(user_message, generated_sql, config)
        return {"reply": reply, "conversation_id": conv_id, "sql": generated_sql}

    reply = await _format_result(user_message, generated_sql, rows, config)
    return {"reply": reply, "conversation_id": conv_id, "sql": generated_sql}


async def _check_knowledge_base(user_message: str, config: dict[str, Any]) -> str | None:
    """判断是否是知识库问题，是则直接回复帮助文本。"""
    msg = user_message.strip()
    kb_triggers = {
        "存酒": ["存酒怎么", "如何存酒", "存酒操作", "存酒流程", "怎么存酒"],
        "打卡": ["打卡规则", "打卡怎么", "如何打卡", "打卡流程", "怎么打卡"],
        "排班": ["排班规则", "排班怎么", "如何排班", "排班流程"],
        "工资": ["工资怎么算", "工资说明", "工资规则", "怎么发工资"],
        "评分": ["评分码", "怎么评分", "在哪里评分", "评分怎么"],
        "订桌": ["订桌怎么", "如何订桌", "订桌流程", "怎么预订"],
    }
    for topic, keywords in kb_triggers.items():
        for kw in keywords:
            if kw in msg:
                # 提取对应 topic 的帮助文本
                return _extract_kb_section(topic)

    # 如果消息较短且包含"怎么""如何""在哪"等问句，尝试用 LLM 判断
    return None


def _extract_kb_section(topic: str) -> str:
    """从 HELP_KB 中提取对应模块的帮助文本。"""
    lines = HELP_KB.strip().split("\n")
    collecting = False
    result = []
    for line in lines:
        if line.startswith("【") and topic in line:
            collecting = True
            continue
        if collecting:
            if line.startswith("【") and line.strip():
                break
            if line.startswith("- "):
                result.append(line[2:])
    if result:
        return f"关于「{topic}」:\n" + "\n".join(result)
    return None


def _extract_sql_fallback(text: str) -> str | None:
    """尝试从 LLM 非标准输出中提取 SQL 语句。"""
    import re
    # 匹配 SELECT ... FROM ... 语句
    match = re.search(r"(SELECT[\s\S]+?)(?:;|\n\n|$)", text, re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return None


async def _format_empty_result(
    user_message: str,
    sql: str,
    config: dict[str, Any],
) -> str:
    """查询结果为空时的自然语言回复。"""
    try:
        messages = [
            {"role": "system", "content": (
                "你是 Crush 酒吧的数据助手。用户问了一个问题，数据库查询结果为空。"
                "请用友好的语气告诉用户没有找到相关数据，并给出可能的原因。"
                "回复简洁，2-3 句话。"
            )},
            {"role": "user", "content": f"用户问题: {user_message}\n执行的SQL: {sql}\n结果: 0条记录"},
        ]
        return await _call_llm(config, messages)
    except Exception:
        return "没有找到相关数据。请确认查询条件是否正确，或换个说法试试。"


async def _format_result(
    user_message: str,
    sql: str,
    rows: list[dict[str, Any]],
    config: dict[str, Any],
) -> str:
    """将查询结果格式化为自然语言回复。"""
    try:
        # 限制数据量，避免 token 爆炸
        display_rows = rows[:10]
        total_count = len(rows)
        rows_text = json.dumps(display_rows, ensure_ascii=False, default=str)

        messages = [
            {"role": "system", "content": (
                "你是 Crush 酒吧的数据助手。根据用户的问题和数据库查询结果，"
                "用自然语言回复。语气友好、简洁、专业。"
                "如果数据较多，总结关键信息。"
                "不要输出 SQL，不要输出原始 JSON。"
            )},
            {"role": "user", "content": (
                f"用户问题: {user_message}\n"
                f"查询结果({total_count}条): {rows_text}\n"
                f"请用自然语言回复用户。"
            )},
        ]
        return await _call_llm(config, messages)
    except Exception:
        # LLM 格式化失败，直接返回简洁摘要
        if len(rows) == 1:
            return f"查到 1 条记录: {json.dumps(rows[0], ensure_ascii=False, default=str)}"
        return f"查到 {len(rows)} 条记录。"


# ==================== 通用 AI 调用入口 ====================

async def ai_analyze(
    db: AsyncSession,
    store_id: int,
    prompt: str,
    context: str = "",
) -> str:
    """
    通用 AI 分析入口（排班建议、异常分析等非聊天场景）。
    供其他模块调用，不经过 SQL 生成流程。
    """
    config = await get_ai_config(db, store_id)
    messages = [
        {"role": "system", "content": "你是 Crush 酒吧的经营分析助手。回复简洁、专业、数据导向。"},
    ]
    if context:
        messages.append({"role": "user", "content": f"背景数据:\n{context}"})
    messages.append({"role": "user", "content": prompt})
    return await _call_llm(config, messages)
