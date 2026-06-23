"""
智能管家模块业务逻辑层
- AI Provider 抽象（DummyProvider / VisionLLMProvider）
- 会话创建与管理
- 照片上传与 AI 判定
- 临时加项
- 人工复核
"""
import os
import base64
import json
import uuid
from datetime import datetime
from typing import Protocol
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.repositories.butler import ButlerRepository
from app.models.butler import ClosingSession
from app.utils.exceptions import NotFoundError, ValidationError
from app.utils.http_client import http_client
from app.config import get_settings


# ==================== AI Provider 抽象层 ====================

class AIProvider(Protocol):
    """AI 图像判定提供者接口"""

    async def analyze_photo(self, photo_path: str, item_name: str, ai_prompt: str | None = None) -> dict:
        """分析照片，返回 {'pass': bool, 'confidence': float, 'reason': str}"""
        ...


class DummyProvider:
    """占位 AI Provider：所有照片标记为人工复核"""

    async def analyze_photo(self, photo_path: str, item_name: str, ai_prompt: str | None = None) -> dict:
        return {
            "pass": None,
            "confidence": 0.0,
            "reason": "AI 服务未配置，需人工复核",
            "provider": "dummy",
        }


class VisionLLMProvider:
    """基于 OpenAI 兼容视觉 API 的图像判定 Provider

    使用门店级 AI 配置（ai_engine.get_ai_config），调用支持 vision 的聊天接口。
    支持 GPT-4o / Qwen-VL / GLM-4V 等兼容 OpenAI 格式的多模态模型。
    """

    def __init__(self, config: dict):
        self.config = config

    def _encode_image(self, photo_path: str) -> str:
        with open(photo_path, "rb") as f:
            return base64.b64encode(f.read()).decode("utf-8")

    def _build_prompt(self, item_name: str, ai_prompt: str | None) -> str:
        """构建判定提示词"""
        custom = ai_prompt.strip() if ai_prompt and ai_prompt.strip() else ""
        if custom:
            task = f"检查项：{item_name}\n判定标准：{custom}"
        else:
            task = f"检查项：{item_name}\n请判断该检查项是否合格完成。"

        return (
            f"你是酒吧开闭店检查助手。请根据照片判断以下检查项是否合格。\n\n"
            f"{task}\n\n"
            f"请严格按以下 JSON 格式回复（不要输出其他内容）：\n"
            f'{{"pass": true/false, "confidence": 0.0-1.0, "reason": "一句话说明判定依据"}}\n'
            f"pass=true 表示合格，false 表示不合格，confidence 为置信度（0-1）。"
        )

    async def analyze_photo(self, photo_path: str, item_name: str, ai_prompt: str | None = None) -> dict:
        url = self.config.get("ai_api_url")
        api_key = self.config.get("ai_api_key")
        model = self.config.get("ai_model") or "gpt-4o-mini"

        if not url or not api_key:
            return {
                "pass": None,
                "confidence": 0.0,
                "reason": "AI 未配置，需人工复核",
                "provider": "none",
            }

        try:
            image_b64 = self._encode_image(photo_path)
            prompt = self._build_prompt(item_name, ai_prompt)

            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
            body = {
                "model": model,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"},
                            },
                        ],
                    }
                ],
                "temperature": 0.2,
                "max_tokens": 300,
            }

            resp = await http_client.post(url, headers=headers, json_body=body)
            data = resp.json()
            choices = data.get("choices", [])
            if not choices:
                return {
                    "pass": None,
                    "confidence": 0.0,
                    "reason": "AI 返回为空",
                    "provider": "vision",
                }

            content = choices[0]["message"]["content"]
            # 尝试解析 JSON（兼容 markdown 代码块）
            content_clean = content.strip()
            if content_clean.startswith("```"):
                lines = content_clean.split("\n")
                content_clean = "\n".join(l for l in lines if not l.startswith("```"))
            try:
                parsed = json.loads(content_clean)
                return {
                    "pass": bool(parsed.get("pass")),
                    "confidence": float(parsed.get("confidence", 0.5)),
                    "reason": str(parsed.get("reason", "")),
                    "provider": "vision",
                }
            except (json.JSONDecodeError, ValueError):
                return {
                    "pass": None,
                    "confidence": 0.0,
                    "reason": f"AI 返回无法解析: {content[:100]}",
                    "provider": "vision",
                }
        except Exception as e:
            logger.opt(exception=True).warning(f"AI 图像判定失败: {e}")
            return {
                "pass": None,
                "confidence": 0.0,
                "reason": f"AI 调用失败: {str(e)[:100]}",
                "provider": "vision",
            }


# 单例
_ai_provider: AIProvider = DummyProvider()


def get_ai_provider() -> AIProvider:
    return _ai_provider


def set_ai_provider(provider: AIProvider) -> None:
    global _ai_provider
    _ai_provider = provider


async def get_vision_provider(db: AsyncSession, store_id: int) -> VisionLLMProvider | DummyProvider:
    """根据门店 AI 配置动态创建 Vision Provider"""
    try:
        from app.services.ai_engine import get_ai_config
        config = await get_ai_config(db, store_id)
        if config.get("ai_api_url") and config.get("ai_api_key"):
            return VisionLLMProvider(config)
    except Exception as e:
        logger.opt(exception=True).warning(f"加载 AI 配置失败: {e}")
    return DummyProvider()


# ==================== 照片上传 ====================

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "closing")

def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


async def save_uploaded_photo(file_content: bytes, filename: str) -> str:
    """保存上传的检查照片，返回访问路径"""
    _ensure_upload_dir()
    ext = filename.rsplit(".", 1)[-1] if "." in filename else "jpg"
    safe_name = f"{uuid.uuid4().hex}.{ext}"
    filepath = os.path.join(UPLOAD_DIR, safe_name)
    with open(filepath, "wb") as f:
        f.write(file_content)
    return f"/uploads/closing/{safe_name}"


# ==================== 会话管理 ====================

async def start_session(
    db: AsyncSession,
    store_id: int,
    user_id: int,
    session_type: str,
) -> dict:
    """创建开店/闭店会话，自动拉取所有相关模板并预创建检查项"""
    repo = ButlerRepository(db, store_id)

    # 检查是否已有进行中的同类型会话
    existing = await repo.get_active_session(session_type)
    if existing:
        raise ValidationError(f"已有进行中的{session_type}检查，请先完成或结束当前会话")

    # 拉取本店所有匹配类型的活跃模板
    templates_raw = await repo.list_templates(session_type=session_type)
    templates = [t for t in templates_raw if t.get("is_active")]

    if not templates:
        raise ValidationError(f"本店尚未配置{session_type}检查清单模板，请在管理页配置")

    # 创建会话
    total_items = sum(len(t.get("items", [])) for t in templates)
    session = await repo.create_session({
        "store_id": store_id,
        "session_type": session_type,
        "operator_user_id": user_id,
        "status": "in_progress",
        "started_at": datetime.utcnow(),
        "total_items": total_items,
        "completed_items": 0,
    })

    # 为每个模板的每个项预创建 result（pending 状态）
    results = []
    for tpl in templates:
        for item in tpl.get("items", []):
            results.append({
                "session_id": session.id,
                "template_id": tpl["id"],
                "item_id": item["id"],
                "item_name": item.get("item_name"),
                "item_type": item.get("item_type", "checkbox"),
                "review_status": "pending",
            })

    if results:
        result_objs = await repo.create_results_batch(results)

    logger.info(f"会话已创建: id={session.id} type={session_type} store={store_id} items={total_items}")
    return await _build_session_detail(repo, session.id)


async def _build_session_detail(repo: ButlerRepository, session_id: int) -> dict:
    """组装会话详情（含模板和检查结果分组）"""
    session = await repo.get_session(session_id)
    if not session:
        raise NotFoundError("会话不存在")

    results = await repo.get_results_by_session(session_id)

    # 按模板分组结果
    template_groups: dict[int, list] = {}
    for r in results:
        tid = r.template_id or 0  # 0 = 临时加项
        if tid not in template_groups:
            template_groups[tid] = []
        template_groups[tid].append(r)

    # 构建模板列表
    templates_output = []
    templates_raw = await repo.list_templates(session_type=session.session_type)

    for tpl in templates_raw:
        tid = tpl["id"]
        tpl_results = template_groups.pop(tid, [])
        tpl["results"] = [
            {
                "id": r.id,
                "session_id": r.session_id,
                "template_id": r.template_id,
                "item_id": r.item_id,
                "item_name": r.item_name,
                "item_type": r.item_type,
                "completed_by": r.completed_by,
                "photo_url": r.photo_url,
                "ai_result": r.ai_result,
                "review_status": r.review_status,
                "review_comment": r.review_comment,
                "completed_at": r.completed_at.isoformat() if r.completed_at else None,
            }
            for r in tpl_results
        ]
        templates_output.append(tpl)

    # 临时加项（template_id=0 或 NULL）
    if 0 in template_groups:
        adhoc_results = template_groups[0]
        templates_output.append({
            "id": 0,
            "store_id": session.store_id,
            "name": "临时加项",
            "session_type": session.session_type,
            "role_tag": "all",
            "sort_order": 999,
            "is_active": True,
            "items": [],
            "results": [
                {
                    "id": r.id,
                    "session_id": r.session_id,
                    "template_id": None,
                    "item_id": None,
                    "item_name": r.item_name,
                    "item_type": r.item_type,
                    "completed_by": r.completed_by,
                    "photo_url": r.photo_url,
                    "ai_result": r.ai_result,
                    "review_status": r.review_status,
                    "review_comment": r.review_comment,
                    "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                }
                for r in adhoc_results
            ],
        })

    return {
        "id": session.id,
        "store_id": session.store_id,
        "session_type": session.session_type,
        "operator_user_id": session.operator_user_id,
        "status": session.status,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "completed_at": session.completed_at.isoformat() if session.completed_at else None,
        "total_items": session.total_items,
        "completed_items": session.completed_items,
        "templates": templates_output,
    }


async def _check_session_complete(repo: ButlerRepository, session_id: int) -> None:
    """检查会话是否所有项都已完成，如果是则自动标记 completed"""
    session = await repo.get_session(session_id)
    if not session or session.status != "in_progress":
        return

    results = await repo.get_results_by_session(session_id)
    all_done = all(r.review_status != "pending" for r in results)

    if all_done:
        await repo.update_session(session, status="completed", completed_at=datetime.utcnow())
        logger.info(f"会话已完成: id={session_id}")


# ==================== 检查项操作 ====================

async def confirm_item(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    result_id: int,
    user_id: int,
    comment: str | None = None,
) -> dict:
    """打勾确认一个检查项（checkbox 类型）"""
    repo = ButlerRepository(db, store_id)
    result = await repo.get_result(result_id, session_id)
    if not result:
        raise NotFoundError("检查项不存在")

    if result.review_status != "pending":
        raise ValidationError("该检查项已完成，不能重复提交")

    await repo.update_result(
        result,
        review_status="passed",
        completed_by=user_id,
        review_comment=comment,
        completed_at=datetime.utcnow(),
    )

    # 更新会话进度
    session = await repo.get_session(session_id)
    if session:
        await repo.update_session(session, completed_items=session.completed_items + 1)

    await _check_session_complete(repo, session_id)
    return {
        "id": result.id,
        "review_status": "passed",
        "completed_at": datetime.utcnow().isoformat(),
    }


async def upload_photo(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    result_id: int,
    user_id: int,
    file_content: bytes,
    filename: str,
) -> dict:
    """拍照上传一个检查项（photo 类型）—— AI 判定 + 保存"""
    repo = ButlerRepository(db, store_id)
    result = await repo.get_result(result_id, session_id)
    if not result:
        raise NotFoundError("检查项不存在")

    if result.review_status != "pending":
        raise ValidationError("该检查项已完成，不能重复提交")

    # 保存照片
    photo_url = await save_uploaded_photo(file_content, filename)

    # 获取检查项的 ai_prompt（从模板项中查询）
    ai_prompt: str | None = None
    if result.item_id:
        items = await repo.get_items_by_ids([result.item_id])
        if items:
            ai_prompt = getattr(items[0], "ai_prompt", None)

    # AI 判定（动态获取门店级 Vision Provider）
    item_name = result.item_name or "未知检查项"
    photo_path = os.path.join(UPLOAD_DIR, os.path.basename(photo_url))
    ai = await get_vision_provider(db, store_id)
    ai_result = await ai.analyze_photo(photo_path, item_name, ai_prompt)

    # 根据 AI 置信度决定状态
    # DummyProvider 始终返回 confidence=0，走人工复核
    if ai_result.get("pass") is True and ai_result.get("confidence", 0) >= 0.85:
        review_status = "auto_passed"
    elif ai_result.get("pass") is False:
        review_status = "manual_reviewing"
    else:
        review_status = "manual_reviewing"

    await repo.update_result(
        result,
        photo_url=photo_url,
        ai_result=ai_result,
        review_status=review_status,
        completed_by=user_id,
        completed_at=datetime.utcnow(),
    )

    # 更新会话进度
    session = await repo.get_session(session_id)
    if session:
        await repo.update_session(session, completed_items=session.completed_items + 1)

    await _check_session_complete(repo, session_id)

    # 需要人工审核时，发送企微群通知+图片
    if review_status == "manual_reviewing":
        try:
            await _notify_manual_review(
                db, store_id, session_id, result.id, item_name,
                photo_url, file_content, user_id,
            )
        except Exception as e:
            logger.error(f"人工审核通知发送失败: {e}")

    return {
        "id": result.id,
        "photo_url": photo_url,
        "ai_result": ai_result,
        "review_status": review_status,
        "completed_at": datetime.utcnow().isoformat(),
    }


async def _notify_manual_review(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    result_id: int,
    item_name: str,
    photo_url: str,
    image_bytes: bytes,
    submitted_by: int,
) -> None:
    """发送人工审核通知（统一推送：站内信 + 企微群机器人图片+文本）

    推送行为由 notification_settings 表中 butler_manual_review 配置控制：
    - enabled: 总开关
    - channel: 站内信/企微应用消息
    - push_to_group: 是否推送到企微群机器人（图片+文本）
    """
    from app.services.notification_service import NotificationService
    from sqlalchemy import select
    from app.models.user import User
    from app.models.employee import Employee
    from app.models.notification import NotificationSetting

    # 查提交人姓名
    stmt = select(User).join(Employee, User.employee_id == Employee.id).where(User.id == submitted_by)
    user_result = await db.execute(stmt)
    user = user_result.scalar_one_or_none()
    submitter_name = user.real_name if user and user.real_name else (user.username if user else "员工")

    notif = NotificationService(db, store_id)

    # 读取 butler_manual_review 推送配置
    setting = await notif.repo.get_setting_by_key("butler_manual_review")
    if setting and not setting.enabled:
        return  # 总开关关闭，不推送

    push_to_group = bool(setting.push_to_group) if setting else False

    review_url = f"https://zhanggui.crushserver.cloud/daily/butler/{session_id}?review={result_id}"
    text = (
        f"【开闭店检查待审核】\n"
        f"检查项：{item_name}\n"
        f"提交人：{submitter_name}\n"
        f"会话ID：{session_id}\n"
        f"请店长/老板及时审核：{review_url}"
    )

    # 1. 如果开启群推送，先发送图片到企微群
    if push_to_group:
        await notif.send_group_image(image_bytes)

    # 2. 统一推送文本通知（站内信 + 企微应用消息 + 群文本，由配置控制）
    await notif.send(
        notification_type="butler_manual_review",
        title=f"检查项待审核：{item_name}",
        content=f"{submitter_name} 提交的「{item_name}」需要人工审核\n{text}",
        target_user_ids=None,  # 按 target_roles 发送
        channel="all",
        push_to_group=push_to_group,  # 由配置控制是否群推文本
        extra={"session_id": session_id, "result_id": result_id, "photo_url": photo_url},
    )


async def add_adhoc_item(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    item_name: str,
    item_type: str,
) -> dict:
    """在会话中临时添加一个检查项"""
    repo = ButlerRepository(db, store_id)
    session = await repo.get_session(session_id)
    if not session:
        raise NotFoundError("会话不存在")
    if session.status != "in_progress":
        raise ValidationError("会话已结束，不能再添加检查项")

    result = await repo.create_result({
        "session_id": session_id,
        "template_id": None,
        "item_id": None,
        "item_name": item_name,
        "item_type": item_type,
        "review_status": "pending",
    })

    # 更新会话总数
    await repo.update_session(session, total_items=session.total_items + 1)

    return {
        "id": result.id,
        "session_id": result.session_id,
        "item_name": result.item_name,
        "item_type": result.item_type,
        "review_status": result.review_status,
    }


# ==================== 人工复核 ====================

async def manual_review(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    result_id: int,
    reviewer_id: int,
    action: str,
    comment: str | None = None,
) -> dict:
    """店长/老板人工复核一个检查项

    action: pass / reject
    - pass: 标记为 manual_passed
    - reject: 标记为 manual_rejected，员工需重新拍照
    """
    if action not in ("pass", "reject"):
        raise ValidationError("action 必须为 pass 或 reject")

    repo = ButlerRepository(db, store_id)
    result = await repo.get_result(result_id, session_id)
    if not result:
        raise NotFoundError("检查项不存在")

    # 只能复核待人工复核的项（manual_reviewing）
    if result.review_status != "manual_reviewing":
        raise ValidationError(f"当前状态({result.review_status})不可人工复核")

    new_status = "manual_passed" if action == "pass" else "manual_rejected"
    await repo.update_result(
        result,
        review_status=new_status,
        review_user_id=reviewer_id,
        review_comment=comment,
    )

    # 如果驳回，需要把会话进度回退（让员工重新提交）
    if action == "reject":
        session = await repo.get_session(session_id)
        if session and session.completed_items > 0:
            await repo.update_session(session, completed_items=session.completed_items - 1)

    return {
        "id": result.id,
        "review_status": new_status,
        "review_user_id": reviewer_id,
        "review_comment": comment,
    }


async def resubmit_photo(
    db: AsyncSession,
    store_id: int,
    session_id: int,
    result_id: int,
    user_id: int,
    file_content: bytes,
    filename: str,
) -> dict:
    """员工被驳回后重新拍照提交"""
    repo = ButlerRepository(db, store_id)
    result = await repo.get_result(result_id, session_id)
    if not result:
        raise NotFoundError("检查项不存在")

    if result.review_status != "manual_rejected":
        raise ValidationError("只有被驳回的检查项才能重新提交")

    # 保存新照片
    photo_url = await save_uploaded_photo(file_content, filename)

    # 获取 ai_prompt
    ai_prompt: str | None = None
    if result.item_id:
        items = await repo.get_items_by_ids([result.item_id])
        if items:
            ai_prompt = getattr(items[0], "ai_prompt", None)

    # 重新 AI 判定
    item_name = result.item_name or "未知检查项"
    photo_path = os.path.join(UPLOAD_DIR, os.path.basename(photo_url))
    ai = await get_vision_provider(db, store_id)
    ai_result = await ai.analyze_photo(photo_path, item_name, ai_prompt)

    if ai_result.get("pass") is True and ai_result.get("confidence", 0) >= 0.85:
        review_status = "auto_passed"
    elif ai_result.get("pass") is False:
        review_status = "manual_reviewing"
    else:
        review_status = "manual_reviewing"

    await repo.update_result(
        result,
        photo_url=photo_url,
        ai_result=ai_result,
        review_status=review_status,
        completed_by=user_id,
        review_comment=None,
        review_user_id=None,
        completed_at=datetime.utcnow(),
    )

    # 重新提交通过时，进度+1
    if review_status in ("auto_passed", "manual_reviewing"):
        session = await repo.get_session(session_id)
        if session:
            await repo.update_session(session, completed_items=session.completed_items + 1)

    await _check_session_complete(repo, session_id)
    return {
        "id": result.id,
        "photo_url": photo_url,
        "ai_result": ai_result,
        "review_status": review_status,
        "completed_at": datetime.utcnow().isoformat(),
    }
