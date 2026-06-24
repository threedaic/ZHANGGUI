"""
全量操作日志 — SQLAlchemy ORM 事件监听

基于 after_flush + after_commit 双事件机制：
- after_flush: 收集 session.new / dirty / deleted
- after_commit: 将变更写入 audit_logs 表

用户上下文通过 contextvars 传递，在 RLS 中间件中设置。
"""
import contextvars
import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy import event
from sqlalchemy.orm import Session, object_mapper
from loguru import logger

# 用户上下文（由 RLS 中间件设置）
_audit_user_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "audit_user_id", default=None
)
_audit_store_id: contextvars.ContextVar[uuid.UUID | None] = contextvars.ContextVar(
    "audit_store_id", default=None
)
_audit_request_id: contextvars.ContextVar[str] = contextvars.ContextVar(
    "audit_request_id", default=""
)
_audit_ip: contextvars.ContextVar[str] = contextvars.ContextVar(
    "audit_ip", default=""
)
_audit_ua: contextvars.ContextVar[str] = contextvars.ContextVar(
    "audit_ua", default=""
)

# 排除的表（内部/系统表，不记录日志）
SKIP_TABLES = {"audit_logs", "alembic_version"}

# 排除的列（不记录敏感或冗余字段）
SKIP_COLUMNS = {"password_hash", "token", "secret"}


def set_audit_context(
    user_id: uuid.UUID | None = None,
    store_id: uuid.UUID | None = None,
    request_id: str = "",
    ip_address: str = "",
    user_agent: str = "",
) -> None:
    _audit_user_id.set(user_id)
    _audit_store_id.set(store_id)
    _audit_request_id.set(request_id)
    _audit_ip.set(ip_address)
    _audit_ua.set(user_agent)


def _obj_to_dict(obj) -> dict:
    """提取 ORM 对象的公共列，排除 SKIP_COLUMNS。"""
    try:
        mapper = object_mapper(obj)
    except Exception:
        return {}
    result = {}
    for col in mapper.columns:
        if col.key in SKIP_COLUMNS:
            continue
        val = getattr(obj, col.key, None)
        # 序列化为 JSON 兼容格式
        if isinstance(val, (datetime,)):
            val = val.isoformat()
        result[col.key] = val
    return result


@event.listens_for(Session, "after_flush")
def _collect_changes(session: Session, flush_context):
    """收集本次 flush 中的变更对象，并预先序列化数据（避免 after_commit 时惰性加载失败）。"""
    changes = session.info.setdefault("_audit_changes", [])

    def _append(action, obj):
        if obj.__tablename__ not in SKIP_TABLES:
            # 预先序列化对象数据，避免 after_commit 时 session 已关闭导致惰性加载失败
            try:
                if action == "delete":
                    snapshot = _obj_to_dict(obj)
                else:
                    snapshot = _obj_to_dict(obj)
                old_snapshot = _get_old_values(obj) if action == "update" else None
                changes.append((action, obj, snapshot, old_snapshot))
            except Exception:
                # 序列化失败时记录对象id作为兜底
                changes.append((action, obj, {"_id": getattr(obj, "id", None)}, None))

    for obj in session.new:
        _append("create", obj)
    for obj in session.dirty:
        if obj.__tablename__ not in SKIP_TABLES:
            # 检查是否有实际列值变化（排除仅 updated_at 变更）
            if _has_real_change(obj):
                _append("update", obj)
    for obj in session.deleted:
        _append("delete", obj)

    # 去重（同一对象可能被多次标记）
    seen = set()
    deduped = []
    for item in changes:
        action, obj = item[0], item[1]
        key = (action, id(obj))
        if key not in seen:
            seen.add(key)
            deduped.append(item)
    session.info["_audit_changes"] = deduped


def _has_real_change(obj) -> bool:
    """检查对象是否有真实的数据变化（排除仅 updated_at 变更）。"""
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(obj)
    changed = set()
    for attr in insp.attrs:
        hist = insp.attrs[attr.key].history
        if hist.has_changes():
            changed.add(attr.key)
    # 如果变化只有 updated_at、created_at 等时间戳列，不算真变化
    time_cols = {"updated_at", "created_at"}
    real_changed = changed - time_cols
    return len(real_changed) > 0


@event.listens_for(Session, "after_commit")
def _write_audit(session: Session):
    """将收集的变更写入 audit_logs 表。"""
    changes = session.info.pop("_audit_changes", None)
    if not changes:
        return

    user_id = _audit_user_id.get()
    store_id = _audit_store_id.get()
    request_id = _audit_request_id.get() or ""
    ip_address = _audit_ip.get() or ""
    user_agent = _audit_ua.get() or ""
    now = datetime.now(timezone.utc).isoformat()

    rows = []
    for item in changes:
        # 兼容新旧格式：新格式 (action, obj, snapshot, old_snapshot)
        # 旧格式 (action, obj) - 兜底处理
        if len(item) == 4:
            action, obj, new_value, old_value = item
        else:
            action, obj = item
            new_value = None
            old_value = None

        tablename = getattr(obj, "__tablename__", "unknown")
        entity_id = getattr(obj, "id", None)

        rows.append({
            "user_id": user_id,
            "store_id": store_id,
            "action": action,
            "entity_type": tablename,
            "entity_id": entity_id,
            "old_value": _safe_json(old_value),
            "new_value": _safe_json(new_value),
            "request_id": request_id,
            "ip_address": ip_address,
            "user_agent": user_agent,
            "created_at": now,
        })

    if rows:
        _write_sync(rows)
        logger.debug(f"审计日志: 写入 {len(rows)} 条")


def _get_old_values(obj) -> dict | None:
    """获取对象变更前的值（来自 SQLAlchemy history）。"""
    from sqlalchemy import inspect as sa_inspect

    insp = sa_inspect(obj)
    old = {}
    for attr in insp.attrs:
        if attr.key in SKIP_COLUMNS:
            continue
        hist = insp.attrs[attr.key].history
        if hist.has_changes():
            val = hist.deleted[0] if hist.deleted else None
            if isinstance(val, (datetime,)):
                val = val.isoformat()
            old[attr.key] = val
    if not old:
        return None
    return old


def _safe_json(obj) -> str | None:
    import json as _json
    if obj is None:
        return None
    try:
        return _json.dumps(obj, ensure_ascii=False, default=str)
    except Exception:
        return str(obj)


# ---------- 同步写库 ----------
def _write_sync(rows: list[dict]) -> None:
    """使用同步连接写入 audit_logs（事件监听器是同步的）。"""
    from app.config import get_settings
    settings = get_settings()

    # 从异步 URL 推导同步 URL
    sync_url = settings.DATABASE_URL.replace("+asyncpg", "").replace(
        "postgresql+asyncpg", "postgresql"
    )
    try:
        engine = sa.create_engine(sync_url, echo=False)
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    """INSERT INTO sys_audit_logs
                    (user_id, store_id, action, entity_type, entity_id,
                     old_value, new_value, request_id, ip_address, user_agent, created_at)
                    VALUES
                    (:user_id, :store_id, :action, :entity_type, :entity_id,
                     :old_value, :new_value, :request_id, :ip_address, :user_agent, :created_at)"""
                ),
                rows,
            )
        engine.dispose()
    except Exception as e:
        logger.error(f"审计日志写入失败: {e}")


def init_audit_logger() -> None:
    """在应用启动时调用，确保事件监听器已注册。"""
    logger.info("审计日志监听器已启动")
