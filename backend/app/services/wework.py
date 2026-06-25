"""企业微信 API 服务层

- Token 管理（Redis 缓存，7200秒有效期）
- 通讯录同步：企微成员 → employees 表（by wework_userid）
- 打卡数据拉取：定时调用，写入 attendance_records
"""

import json
import uuid
from datetime import datetime, date, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from loguru import logger

from app.config import get_settings
from app.utils.http_client import http_client
from app.utils.redis_client import get_redis
from app.utils.security import decrypt_aes, encrypt_aes
from app.utils.exceptions import NotFoundError, ExternalServiceError
from app.models.store import Store
from app.models.employee import Employee

WECOM_API = get_settings().WECOM_API_BASE
TOKEN_KEY = "wework:access_token:{corp_id}"
TOKEN_TTL = 7000  # 7200 - 200 安全余量


async def _get_store_config(db: AsyncSession, store_id: uuid.UUID | None = None) -> dict | None:
    """读取企微配置：优先环境变量（全局），其次门店表（兼容旧数据）。"""
    settings = get_settings()

    # 优先使用环境变量中的全局企微配置
    if settings.WECOM_CORP_ID and settings.WECOM_SECRET:
        return {
            "corp_id": settings.WECOM_CORP_ID,
            "agent_id": settings.WECOM_AGENT_ID,
            "secret": settings.WECOM_SECRET,
        }

    # 回退到门店表（兼容旧数据）
    if store_id is None:
        return None
    stmt = select(Store).where(Store.id == store_id)
    result = await db.execute(stmt)
    store = result.scalar_one_or_none()
    if not store or not store.wework_corp_id or not store.wework_secret:
        return None
    return {
        "corp_id": store.wework_corp_id,
        "agent_id": store.wework_agent_id,
        "secret": decrypt_aes(store.wework_secret),
    }


async def get_access_token(db: AsyncSession, store_id: uuid.UUID | None = None) -> str:
    """获取/刷新企微 access_token，自动 Redis 缓存。"""
    cfg = await _get_store_config(db, store_id)
    if not cfg:
        raise NotFoundError("企微未配置，请在 .env 中设置 WECOM_CORP_ID / WECOM_AGENT_ID / WECOM_SECRET")

    redis = await get_redis()
    cache_key = TOKEN_KEY.format(corp_id=cfg["corp_id"])
    cached = await redis.get(cache_key)
    if cached:
        return cached

    # 请求新 token
    url = f"{WECOM_API}/gettoken?corpid={cfg['corp_id']}&corpsecret={cfg['secret']}"
    resp = await http_client.get(url)
    data = resp.json()
    if data.get("errcode") != 0:
        raise ExternalServiceError(f"企微 token 获取失败: {data}")

    token = data["access_token"]
    await redis.setex(cache_key, TOKEN_TTL, token)
    return token


# ==================== 通讯录同步（部门+角色映射） ====================

# 角色映射规则常量
BOSS_DEPT_KEYWORD = "管理"  # 名称含此关键字的部门成员 → boss
ROLE_BOSS = "boss"
ROLE_STORE_MANAGER = "store_manager"
ROLE_STAFF = "staff"


def _resolve_role(
    userid: str,
    dept_ids: list[int],
    is_leader: bool,
    admin_dept_ids: set[int],
    boss_userids: set[str],
) -> str:
    """规则引擎：根据企微用户属性决定角色。

    优先级（从高到低）：
    1. BOSS_WEWORK_USERIDS 白名单 → boss（永不降级）
    2. 属于「管理」部门 → boss
    3. 是部门负责人 (is_leader_in_dept=1) → store_manager
    4. 其他 → staff
    """
    # 1. 强制 boss 白名单
    if boss_userids and userid in boss_userids:
        logger.debug(f"角色映射: {userid} → boss (白名单)")
        return ROLE_BOSS

    # 2. 管理部门成员 → boss
    if admin_dept_ids:
        member_admin = bool(set(dept_ids) & admin_dept_ids)
        if member_admin:
            logger.debug(f"角色映射: {userid} → boss (管理部)")
            return ROLE_BOSS

    # 3. 部门负责人 → store_manager
    if is_leader:
        logger.debug(f"角色映射: {userid} → store_manager")
        return ROLE_STORE_MANAGER

    # 4. 普通成员
    return ROLE_STAFF


async def _fetch_departments(token: str) -> list[dict]:
    """获取企微部门列表。"""
    url = f"{WECOM_API}/department/list?access_token={token}"
    resp = await http_client.get(url)
    data = resp.json()
    if data.get("errcode") != 0:
        raise ExternalServiceError(f"部门列表获取失败: {data}")
    return data.get("department", [])


def _collect_sub_depts(
    root_id: int,
    children_map: dict[int, list[int]],
    result: set[int],
) -> None:
    """递归收集 root_id 的全部子孙部门 ID。"""
    for child_id in children_map.get(root_id, []):
        if child_id not in result:
            result.add(child_id)
            _collect_sub_depts(child_id, children_map, result)


def _auto_detect_store_dept(
    store_name: str,
    store_code: str,
    departments: list[dict],
    admin_dept_ids: set[int],
    dept_id_by_name: dict[str, int],
) -> int | None:
    """根据门店名称自动识别对应的企微部门 ID。

    匹配策略（按优先级）：
    1. 精确匹配：部门名 == 门店名
    2. 包含匹配：门店名包含部门名，或部门名包含门店名
       （例如 门店"北京三里屯店" ↔ 部门"北京店"）
    3. store_code 精确匹配部门名
    """
    # 1. 精确匹配
    if store_name in dept_id_by_name:
        logger.info(f"自动匹配部门(精确): {store_name} → {dept_id_by_name[store_name]}")
        return dept_id_by_name[store_name]

    # 2. 包含匹配（排除根部门和管理部门）
    for dept_name, did in dept_id_by_name.items():
        if did in admin_dept_ids:
            continue
        if not dept_name:
            continue
        if dept_name in store_name or store_name in dept_name:
            logger.info(f"自动匹配部门(包含): 门店={store_name} ↔ 部门={dept_name} → {did}")
            return did

    # 3. store_code 匹配
    if store_code and store_code in dept_id_by_name:
        logger.info(f"自动匹配部门(store_code): {store_code} → {dept_id_by_name[store_code]}")
        return dept_id_by_name[store_code]

    logger.warning(
        f"门店自动匹配部门失败: store_name={store_name} store_code={store_code} "
        f"可用部门={list(dept_id_by_name.keys())}"
    )
    return None


async def _fetch_department_users(token: str, dept_id: int, fetch_child: bool = True) -> list[dict]:
    """获取指定部门及子部门的成员列表。"""
    url = f"{WECOM_API}/user/list?access_token={token}&department_id={dept_id}&fetch_child={1 if fetch_child else 0}"
    resp = await http_client.get(url)
    data = resp.json()
    if data.get("errcode") != 0:
        raise ExternalServiceError(f"部门成员获取失败(dept={dept_id}): {data}")
    return data.get("userlist", [])


async def sync_contacts(db: AsyncSession, store_id: uuid.UUID) -> dict:
    """同步企微通讯录到本地 employees 表，自动映射角色。

    角色映射规则（优先级从高到低）：
    1. BOSS_WEWORK_USERIDS 白名单 → boss
    2. 名称含「管理」的部门成员 → boss
    3. 部门负责人 (is_leader_in_dept=1) → store_manager
    4. 其余 → staff

    如果 store 配置了 wework_department_id，仅同步该部门及其子部门的成员。
    """
    from app.config import get_settings

    token = await get_access_token(db, store_id)

    # 获取门店配置的企微根部门
    stmt = select(Store).where(Store.id == store_id)
    store_result = await db.execute(stmt)
    store = store_result.scalar_one_or_none()
    root_dept_id = store.wework_department_id if store else None

    # Step 1: 获取部门列表，识别管理部门
    departments = await _fetch_departments(token)
    admin_dept_ids: set[int] = set()
    dept_children: dict[int, list[int]] = {}  # parentid → [child_ids]
    dept_id_by_name: dict[str, int] = {}  # name → id

    for dept in departments:
        did = dept["id"]
        parentid = dept.get("parentid", 0)
        name = dept.get("name", "")
        dept_children.setdefault(parentid, []).append(did)
        dept_id_by_name[name] = did

        if BOSS_DEPT_KEYWORD in name and parentid == 1:
            admin_dept_ids.add(did)
            logger.info(f"识别管理部门: id={did} name={name}")

    # 自动识别门店部门（如果未手动配置 wework_department_id）
    if not root_dept_id and store:
        root_dept_id = _auto_detect_store_dept(
            store_name=store.name,
            store_code=store.store_code,
            departments=departments,
            admin_dept_ids=admin_dept_ids,
            dept_id_by_name=dept_id_by_name,
        )

    # 确定需要同步的部门 ID 集合
    if root_dept_id:
        sync_dept_ids: set[int] = {root_dept_id}
        _collect_sub_depts(root_dept_id, dept_children, sync_dept_ids)
        logger.info(
            f"门店 {store_id} 部门过滤: 根部门={root_dept_id}, "
            f"含子部门共 {len(sync_dept_ids)} 个"
        )
    else:
        # 安全策略：匹配失败时拒绝同步，避免误拉管理群等全公司成员
        raise ExternalServiceError(
            f"门店未匹配到企微部门，已中止同步以防误拉全公司成员。"
            f"请在门店配置中手动设置 wework_department_id，"
            f"或将门店名改为与企微部门名一致。"
            f"门店={store.name if store else store_id}, "
            f"store_code={store.store_code if store else 'N/A'}, "
            f"可用部门={list(dept_id_by_name.keys())}"
        )

    # Step 2: 获取 BOSS 白名单
    settings = get_settings()
    boss_userids: set[str] = set()
    if settings.BOSS_WEWORK_USERIDS:
        boss_userids = {uid.strip() for uid in settings.BOSS_WEWORK_USERIDS.split(",") if uid.strip()}
        logger.info(f"BOSS 白名单: {boss_userids}")

    # Step 3: 拉取指定部门成员
    wecom_users: list[dict] = []
    for did in sync_dept_ids:
        try:
            users = await _fetch_department_users(token, did, fetch_child=False)
            wecom_users.extend(users)
        except Exception as e:
            logger.warning(f"获取部门 {did} 成员失败: {e}")

    # 去重（userid 可能跨部门）
    seen: set[str] = set()
    unique_users: list[dict] = []
    for u in wecom_users:
        uid = u.get("userid")
        if uid and uid not in seen:
            seen.add(uid)
            unique_users.append(u)

    logger.info(f"企微通讯录: {len(departments)} 部门, {len(unique_users)} 成员")

    # Step 4: 收集全部 userid → 统一查本地现有员工，避免循环内逐条查
    all_userids = [u["userid"] for u in unique_users if u.get("userid")]
    existing_map: dict[str, Employee] = {}
    if all_userids:
        stmt = select(Employee).where(
            and_(Employee.store_id == store_id, Employee.wework_userid.in_(all_userids))
        )
        emp_result = await db.execute(stmt)
        for emp in emp_result.scalars().all():
            existing_map[emp.wework_userid] = emp

    # Step 5: 应用规则 + 批量创建/更新
    # 反向映射：部门ID → 部门名（用于存到员工 department 字段）
    dept_name_by_id: dict[int, str] = {did: name for name, did in dept_id_by_name.items()}

    result = {
        "synced": 0,
        "created": 0,
        "updated": 0,
        "role_changed": 0,
        "boss_from_env": 0,
        "boss_from_dept": 0,
        "manager_from_leader": 0,
        "staff_count": 0,
        "errors": [],
        "details": [],
    }

    for wu in unique_users:
        userid = wu.get("userid", "")
        name = wu.get("name", "")
        if not userid or not name:
            continue

        try:
            dept_ids = wu.get("department", [])
            # is_leader_in_dept 是数组，取该成员所在部门中的 leader 状态
            is_leader = bool(wu.get("is_leader_in_dept", [0])[0]) if wu.get("is_leader_in_dept") else False

            role = _resolve_role(userid, dept_ids, is_leader, admin_dept_ids, boss_userids)

            # 部门名称：取第一个同步范围内的部门名（员工可能属于多个部门）
            dept_name = ""
            for did in dept_ids:
                if did in sync_dept_ids and did in dept_name_by_id:
                    dept_name = dept_name_by_id[did]
                    break
            if not dept_name and dept_ids:
                # fallback：取第一个任意部门名
                dept_name = dept_name_by_id.get(dept_ids[0], "")

            # 统计
            if boss_userids and userid in boss_userids:
                result["boss_from_env"] += 1
            elif admin_dept_ids and (set(dept_ids) & admin_dept_ids):
                result["boss_from_dept"] += 1
            elif is_leader:
                result["manager_from_leader"] += 1
            else:
                result["staff_count"] += 1

            # 查本地记录
            emp = existing_map.get(userid)
            if emp:
                changed = False
                if emp.name != name:
                    emp.name = name
                    changed = True
                if emp.role != role:
                    old_role = emp.role
                    emp.role = role
                    changed = True
                    result["role_changed"] += 1
                    logger.info(f"角色变更: {userid} {old_role} → {role}")
                if emp.department != dept_name:
                    emp.department = dept_name
                    changed = True
                if changed:
                    result["updated"] += 1
                else:
                    result["synced"] += 1
            else:
                new_emp = Employee(
                    store_id=store_id,
                    employee_code=f"WX-{userid[:10]}",
                    name=name,
                    role=role,
                    base_salary=0,
                    hire_date=date.today(),
                    wework_userid=userid,
                    department=dept_name,
                    status="active",
                )
                db.add(new_emp)
                result["created"] += 1

            result["details"].append({
                "userid": userid,
                "name": name,
                "role": role,
                "department": dept_name,
                "dept_ids": dept_ids,
                "is_leader": is_leader,
            })
        except Exception as e:
            result["errors"].append(f"{userid}: {e}")
            logger.error(f"同步员工失败 {userid}: {e}")

    await db.commit()
    logger.info(
        f"通讯录同步完成: created={result['created']} updated={result['updated']} "
        f"synced={result['synced']} role_changed={result['role_changed']} "
        f"boss=({result['boss_from_env']}+{result['boss_from_dept']}) "
        f"manager={result['manager_from_leader']} staff={result['staff_count']}"
    )
    return result


# ==================== 打卡数据 ====================

def _parse_checkin_time(ts: int | None) -> str | None:
    """Unix 时间戳 → HH:MM 字符串"""
    if not ts:
        return None
    return datetime.fromtimestamp(ts).strftime("%H:%M")


def _calc_late_minutes(clock_in: str, scheduled_start: str = "18:00") -> int:
    """计算迟到分钟数，负数=早到"""
    fmt = "%H:%M"
    try:
        diff = datetime.strptime(clock_in, fmt) - datetime.strptime(scheduled_start, fmt)
        return max(0, int(diff.total_seconds() / 60))
    except ValueError:
        return 0


async def fetch_checkin_data(
    db: AsyncSession, store_id: uuid.UUID, target_date: str
) -> dict:
    """拉取当日打卡数据，写入 attendance_records。

    target_date: "2026-06-15"
    返回 {synced: N, records: [...], errors: [...]}

    核心逻辑：
    1. 用 checkin_type 区分上班打卡/下班打卡（自由上下班规则）
    2. 旧规则"仅记录"类型 fallback 到时间排序
    3. 关联排班或 shift_group，写入 shift_start_time/shift_end_time
    4. 调用 _evaluate_status 计算迟到/早退
    """
    token = await get_access_token(db, store_id)

    # 获取有 wework_userid 的员工
    stmt = select(Employee).where(
        and_(
            Employee.store_id == store_id,
            Employee.status == "active",
            Employee.wework_userid.isnot(None),
        )
    )
    emp_result = await db.execute(stmt)
    employees = {e.wework_userid: e for e in emp_result.scalars().all()}
    if not employees:
        return {"synced": 0, "records": [], "errors": []}

    # 加载班次配置，用于推断员工班次
    from app.models.attendance import ShiftConfig
    shift_stmt = select(ShiftConfig).where(
        and_(ShiftConfig.store_id == store_id, ShiftConfig.is_active.is_(True))
    )
    shift_result = await db.execute(shift_stmt)
    shift_configs = {sc.shift_code: sc for sc in shift_result.scalars().all()}
    # shift_group → shift_code 映射：白班组→day, 夜班组/空→night
    group_to_code = {"day": "day", "白班": "day", "night": "night", "夜班": "night"}

    # 构造请求时间范围：从当天 10:00 到次日 10:00
    # 自由上下班规则：打卡开始时间10:00，覆盖跨夜班次
    dt = date.fromisoformat(target_date)
    next_dt = dt + timedelta(days=1)
    start_ts = int(datetime(dt.year, dt.month, dt.day, 10, 0, 0).timestamp())
    end_ts = int(datetime(next_dt.year, next_dt.month, next_dt.day, 10, 0, 0).timestamp())

    userid_list = list(employees.keys())
    url = f"{WECOM_API}/checkin/getcheckindata?access_token={token}"
    body = {
        "opencheckindatatype": 3,  # 所有类型
        "starttime": start_ts,
        "endtime": end_ts,
        "useridlist": userid_list,
    }

    try:
        resp = await http_client.post(url, json_body=body)
        data = resp.json()
    except Exception as e:
        logger.error(f"打卡数据请求失败: {e}")
        return {"synced": 0, "records": [], "errors": [str(e)]}

    if data.get("errcode") != 0:
        logger.error(f"打卡数据接口错误: {data}")
        return {"synced": 0, "records": [], "errors": [data.get("errmsg", "")]}

    from app.models.attendance import AttendanceRecord
    from app.repositories.attendance import AttendanceRepository
    from app.services.attendance import AttendanceService

    repo = AttendanceRepository(db, store_id)
    service = AttendanceService(db, store_id)

    # 按 (userid, shift_date) 分组原始打卡数据
    existing_records = await repo.get_records_by_date_range(dt, dt)
    existing_map: dict[int, AttendanceRecord] = {
        r.employee_id: r for r in existing_records
    }

    # 按 (userid, shift_date) 分组原始打卡数据
    user_day_data: dict[tuple[str, str], dict] = {}

    for item in data.get("checkindata", []):
        userid = item.get("userid")
        checkin_ts = item.get("checkin_time")
        if not userid or not checkin_ts:
            continue

        checkin_dt = datetime.fromtimestamp(checkin_ts)
        # API 时间范围已精确覆盖一天班次（10:00当天 ~ 10:00次日）
        # 所有打卡直接归入 target_date，不再需要 12:00 分界逻辑
        shift_date = target_date

        key = (userid, shift_date)
        if key not in user_day_data:
            user_day_data[key] = {"clock_in_items": [], "clock_out_items": [], "all_items": [], "exceptions": set()}

        checkin_type = item.get("checkin_type", "")
        time_entry = {
            "timestamp": checkin_ts,
            "time_str": checkin_dt.strftime("%Y-%m-%d %H:%M:%S"),
            "hour_str": checkin_dt.strftime("%H:%M"),
            "type": checkin_type,
        }

        # 根据 checkin_type 分类
        if "上班" in checkin_type:
            user_day_data[key]["clock_in_items"].append(time_entry)
        elif "下班" in checkin_type:
            user_day_data[key]["clock_out_items"].append(time_entry)
        else:
            # "仅记录打卡时间和地点"等旧规则 → 放入all_items，后面用时间排序
            user_day_data[key]["all_items"].append(time_entry)

        exc = item.get("exception_type", "")
        if exc:
            user_day_data[key]["exceptions"].add(exc)

    # 聚合写入
    synced = 0
    records_list = []
    errors = []

    for (userid, shift_date), day_data in user_day_data.items():
        emp = employees.get(userid)
        if not emp:
            continue

        # ---- 确定上班/下班打卡时间 ----
        clock_in_items = day_data["clock_in_items"]
        clock_out_items = day_data["clock_out_items"]
        all_items = day_data["all_items"]

        if clock_in_items or clock_out_items:
            # 新规则：有明确的上班打卡/下班打卡字段
            # 取最早的上班打卡
            clock_in_items.sort(key=lambda t: t["timestamp"])
            clock_out_items.sort(key=lambda t: t["timestamp"])
            clock_in = clock_in_items[0]["hour_str"] if clock_in_items else None
            clock_out = clock_out_items[-1]["hour_str"] if clock_out_items else None
        elif all_items:
            # 旧规则"仅记录"：按时间排序，最早=上班，最晚=下班
            all_items.sort(key=lambda t: t["timestamp"])
            clock_in = all_items[0]["hour_str"]
            clock_out = all_items[-1]["hour_str"] if len(all_items) > 1 else None
        else:
            continue

        # ---- 确定班次（scheduled_shift + shift_start/end_time）----
        existing = existing_map.get(emp.id)
        if existing and existing.scheduled_shift and existing.scheduled_shift not in ("休息", "请假", "unknown"):
            # 有排班记录 → 使用排班的班次和时间
            scheduled_shift = existing.scheduled_shift
            shift_start_time = existing.shift_start_time
            shift_end_time = existing.shift_end_time
            is_overnight = existing.is_overnight or False
        else:
            # 无排班 → 从员工的 shift_group 推断
            shift_code = group_to_code.get(emp.shift_group or "", "night")
            shift_config = shift_configs.get(shift_code)
            if shift_config:
                scheduled_shift = shift_config.shift_name
                shift_start_time = shift_config.start_time
                shift_end_time = shift_config.end_time
                is_overnight = shift_config.is_overnight
            else:
                scheduled_shift = None
                shift_start_time = None
                shift_end_time = None
                is_overnight = False

        # ---- 异常类型 ----
        exceptions = day_data["exceptions"]
        note_parts = []
        if "迟到" in exceptions:
            note_parts.append("迟到")
        if "早退" in exceptions:
            note_parts.append("早退")
        if "缺卡" in exceptions:
            note_parts.append("缺卡")
        if "地点异常" in exceptions:
            note_parts.append("地点异常")
        note = "企微异常: " + ", ".join(note_parts) if note_parts else ""

        # ---- 写入记录 ----
        record = AttendanceRecord(
            store_id=store_id,
            employee_id=emp.id,
            date=shift_date,
            scheduled_shift=scheduled_shift,
            shift_start_time=shift_start_time,
            shift_end_time=shift_end_time,
            is_overnight=is_overnight,
            clock_in=clock_in,
            clock_out=clock_out,
            status="unknown",  # 先写unknown，下面用evaluate计算
            late_minutes=0,
            early_minutes=0,
            source="wecom",
            note=note,
        )

        try:
            target = await repo.upsert_record(record)
            # 用 AttendanceService._evaluate_status 计算迟到/早退
            if target.shift_start_time and target.shift_end_time and target.clock_in:
                service._evaluate_status(target)
            synced += 1
            records_list.append({
                "employee_id": emp.id, "name": emp.name, "date": shift_date,
                "scheduled_shift": scheduled_shift,
                "clock_in": clock_in, "clock_out": clock_out,
                "shift_start_time": shift_start_time, "shift_end_time": shift_end_time,
            })
        except Exception as e:
            logger.error(f"打卡写入失败 {emp.name}: {e}")
            errors.append(f"{emp.name}: {e}")

    await db.commit()
    logger.info(f"打卡同步完成: {synced} 条记录, 日期={target_date}")
    return {"synced": synced, "records": records_list, "errors": errors}


# ==================== OAuth 登录辅助 ====================

async def get_userid_by_code(db: AsyncSession, store_id: uuid.UUID | None, code: str) -> str | None:
    """用 OAuth code 换取企微成员 userid。

    调用企微 user/getuserinfo 接口，返回企业成员的 UserId；
    非企业成员返回 None。接口报错时抛出 ExternalServiceError。
    """
    token = await get_access_token(db, store_id)
    url = f"{WECOM_API}/user/getuserinfo?access_token={token}&code={code}"
    resp = await http_client.get(url)
    data = resp.json()
    if data.get("errcode") != 0:
        raise ExternalServiceError(f"企微 getuserinfo 失败: {data}")
    return data.get("UserId") or data.get("userid")