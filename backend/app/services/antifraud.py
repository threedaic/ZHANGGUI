"""
防飞单业务逻辑层
- 5 规则异常检测引擎（每规则 0-20 分，总分 0-100）
- AI 引擎增强评分（可选）
- 企微群预警推送
"""
import json
import uuid
from datetime import date, datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.table_session import TableSession
from app.repositories.antifraud import AntiFraudRepository
from app.schemas.antifraud import RuleDetail, SessionRisk
from app.services.notification_service import NotificationService
from app.utils.deps import get_extra_config
from app.utils.exceptions import AppError, NotFoundError, ValidationError


class AntiFraudService:
    """防飞单 Service。每请求新实例。"""

    def __init__(self, session: AsyncSession, store_id: uuid.UUID):
        self.repo = AntiFraudRepository(session, store_id)
        self.session = session
        self.store_id = store_id
        # 默认阈值，scan_daily 时会从 extra_config 覆盖
        self.anomaly_threshold: float = 50.0
        self.critical_threshold: float = 80.0
        self.alert_push_enabled: bool = True
        self.enabled_rules: set[str] = set()

    async def _load_config(self) -> None:
        """从 store_settings.extra_config.antifraud 读取阈值与开关。"""
        cfg = await get_extra_config(self.session, str(self.store_id), "antifraud")
        try:
            self.anomaly_threshold = float(cfg.get("anomaly_threshold", 50))
        except (TypeError, ValueError):
            self.anomaly_threshold = 50.0
        try:
            self.critical_threshold = float(cfg.get("critical_threshold", 80))
        except (TypeError, ValueError):
            self.critical_threshold = 80.0
        self.alert_push_enabled = bool(cfg.get("alert_push_enabled", True))
        rules_cfg = cfg.get("rules") or {}
        # 未显式关闭的规则都启用
        self.enabled_rules = {
            code for code in ("cancellation", "account_diff", "amount_deviation", "time_gap", "employee_deviation")
            if rules_cfg.get(code, True)
        }

    # ==================== 5 规则引擎 ====================

    async def scan_daily(self, scan_date: str, push_alert: bool = True) -> dict:
        """
        扫描指定日期的所有开台会话，逐条打分。
        返回扫描汇总结果。
        """
        # 读取店铺防飞单配置（阈值/开关）
        await self._load_config()
        anomaly_threshold = self.anomaly_threshold
        critical_threshold = self.critical_threshold

        sessions = await self.repo.get_sessions_by_date(scan_date)
        if not sessions:
            return {
                "date": scan_date,
                "store_id": self.store_id,
                "total_sessions": 0,
                "anomaly_count": 0,
                "anomaly_rate": 0.0,
                "high_risk_count": 0,
                "critical_count": 0,
                "sessions": [],
            }

        # 获取门店均值（用于规则3）
        store_avg_per_guest = await self.repo.get_store_avg_per_guest(
            scan_date, days=7
        )

        # 获取所有涉及员工的历史异常数（用于规则5）
        employee_ids = list({s.opened_by for s in sessions})
        employee_names = await self.repo.get_employee_names(employee_ids)
        employee_anomaly_cache = await self.repo.get_employee_anomaly_history_batch(
            employee_ids, days=30
        )

        risk_results: list[SessionRisk] = []
        updates: list[dict] = []

        for session in sessions:
            rules = await self._score_session(
                session, store_avg_per_guest, employee_anomaly_cache
            )
            risk_score = sum(r.score for r in rules)
            risk_level = self._risk_level(risk_score)

            emp_info = employee_names.get(session.opened_by, {})
            emp_name = emp_info.get("name", "")

            session_risk = SessionRisk(
                session_id=session.id,
                store_id=session.store_id,
                table_no=session.table_no,
                employee_id=session.opened_by,
                employee_name=emp_name,
                opened_at=session.opened_at,
                closed_at=session.closed_at,
                guest_count=session.guest_count,
                crmeb_order_count=session.crmeb_order_count,
                crmeb_total_amount=session.crmeb_total_amount,
                wework_pay_count=session.wework_pay_count,
                wework_pay_amount=session.wework_pay_amount,
                risk_score=round(risk_score, 1),
                risk_level=risk_level,
                rules=rules,
                is_anomaly=risk_score > anomaly_threshold,
                anomaly_reason=json.dumps({
                    "risk_score": round(risk_score, 1),
                    "risk_level": risk_level,
                    "rules": [r.model_dump() for r in rules],
                }, ensure_ascii=False),
                status=session.status,
            )
            risk_results.append(session_risk)

            # 标记异常
            updates.append({
                "session_id": session.id,
                "is_anomaly": risk_score > anomaly_threshold,
                "anomaly_reason": session_risk.anomaly_reason,
            })

        # 批量更新数据库
        await self.repo.bulk_update_anomalies(updates)
        await self.session.commit()

        # 统计
        anomaly_sessions = [r for r in risk_results if r.is_anomaly]
        high_risk = [r for r in risk_results if r.risk_score > anomaly_threshold]
        critical = [r for r in risk_results if r.risk_score > critical_threshold]

        # 推送企微预警（超过异常阈值）
        if push_alert and self.alert_push_enabled and high_risk:
            await self._push_alerts(scan_date, high_risk)

        return {
            "date": scan_date,
            "store_id": self.store_id,
            "total_sessions": len(sessions),
            "anomaly_count": len(anomaly_sessions),
            "anomaly_rate": round(len(anomaly_sessions) / len(sessions) * 100, 1),
            "high_risk_count": len(high_risk),
            "critical_count": len(critical),
            "sessions": [r.model_dump() for r in risk_results],
        }

    async def _score_session(
        self,
        session: TableSession,
        store_avg_per_guest: float,
        employee_anomaly_cache: dict[int, int],
    ) -> list[RuleDetail]:
        """对单个会话逐规则打分，返回规则明细（跳过被关闭的规则）。"""

        rules: list[RuleDetail] = []
        enabled = self.enabled_rules

        # ---- 规则1: 作废异常 (0-20) ----
        if "cancellation" in enabled:
            rules.append(self._rule_cancellation(session))

        # ---- 规则2: 账差 (0-20) ----
        if "account_diff" in enabled:
            rules.append(self._rule_account_diff(session))

        # ---- 规则3: 金额偏离 (0-20) ----
        if "amount_deviation" in enabled:
            rules.append(self._rule_amount_deviation(session, store_avg_per_guest))

        # ---- 规则4: 时间裂隙 (0-20) ----
        if "time_gap" in enabled:
            rules.append(self._rule_time_gap(session))

        # ---- 规则5: 员工偏差 (0-20) ----
        if "employee_deviation" in enabled:
            rules.append(
                self._rule_employee_deviation(session, employee_anomaly_cache)
            )

        return rules

    # ---------- 规则1: 作废异常 ----------
    def _rule_cancellation(self, session: TableSession) -> RuleDetail:
        """
        检测异常关台：
        - 有开台时间但无 POS 订单（crmeb_order_count == 0）
        - 会话持续 > 30 分钟（不是误开）
        - 无企微收款记录
        """
        score = 0.0
        detail_parts = []

        # 无 POS 订单
        if session.crmeb_order_count == 0:
            # 计算会话时长
            try:
                opened = datetime.fromisoformat(session.opened_at)
                closed = (
                    datetime.fromisoformat(session.closed_at)
                    if session.closed_at
                    else datetime.now()
                )
                duration_min = (closed - opened).total_seconds() / 60

                if duration_min >= 30:
                    # 开了超过30分钟但没 POS 记录
                    base = min(duration_min / 120, 1.0)  # 2小时 = 满分
                    score = round(base * 15, 1)
                    detail_parts.append(f"开台 {duration_min:.0f} 分钟无 POS 订单")

                if session.wework_pay_count == 0:
                    score += 5  # 也无企微收款
                    detail_parts.append("无企微收款记录")
            except (ValueError, TypeError):
                pass

        return RuleDetail(
            rule_name="cancellation",
            rule_label="作废异常",
            score=min(score, 20),
            max_score=20,
            detail="; ".join(detail_parts) if detail_parts else "正常",
            raw_data={
                "order_count": session.crmeb_order_count,
                "pay_count": session.wework_pay_count,
            },
        )

    # ---------- 规则2: 账差 ----------
    def _rule_account_diff(self, session: TableSession) -> RuleDetail:
        """
        比对 POS 金额与企微收款金额。
        |crmeb - wework| / max(crmeb, 1) * 20
        """
        crmeb_amt = session.crmeb_total_amount or 0
        wework_amt = session.wework_pay_amount or 0

        if crmeb_amt <= 0:
            return RuleDetail(
                rule_name="account_diff",
                rule_label="账差",
                score=0,
                max_score=20,
                detail="无 POS 金额，跳过账差检测",
                raw_data={"crmeb": crmeb_amt, "wework": wework_amt},
            )

        diff = abs(crmeb_amt - wework_amt)
        ratio = diff / max(crmeb_amt, 1)
        score = round(min(ratio, 1.0) * 20, 1)

        if score > 10:
            detail = f"POS 金额 {crmeb_amt:.0f} vs 企微收款 {wework_amt:.0f}，差额 {diff:.0f} 元（{ratio:.1%}）"
        elif score > 5:
            detail = f"POS 与企微收款偏差 {ratio:.1%}"
        else:
            detail = "账差正常"

        return RuleDetail(
            rule_name="account_diff",
            rule_label="账差",
            score=score,
            max_score=20,
            detail=detail,
            raw_data={
                "crmeb_amount": crmeb_amt,
                "wework_amount": wework_amt,
                "diff": diff,
                "ratio": round(ratio, 4),
            },
        )

    # ---------- 规则3: 金额偏离 ----------
    def _rule_amount_deviation(
        self, session: TableSession, store_avg: float
    ) -> RuleDetail:
        """
        人均消费 vs 门店 7 日均值。
        显著低于均值 → 可能飞单（现金交易不经过系统）。
        """
        if session.guest_count <= 0 or session.crmeb_total_amount <= 0:
            return RuleDetail(
                rule_name="amount_deviation",
                rule_label="金额偏离",
                score=0,
                max_score=20,
                detail="无消费数据，跳过",
                raw_data={"per_guest": 0, "store_avg": store_avg},
            )

        per_guest = session.crmeb_total_amount / session.guest_count

        if store_avg <= 0:
            return RuleDetail(
                rule_name="amount_deviation",
                rule_label="金额偏离",
                score=0,
                max_score=20,
                detail="无门店均值数据，跳过",
                raw_data={"per_guest": round(per_guest, 1), "store_avg": store_avg},
            )

        # 低于均值 50% 以上开始扣分
        ratio = per_guest / store_avg if store_avg > 0 else 1
        if ratio >= 1.0:
            score = 0.0
            detail = f"人均 {per_guest:.0f} >= 门店平均 {store_avg:.0f}"
        elif ratio >= 0.5:
            score = round((1 - ratio) * 20, 1)
            detail = f"人均 {per_guest:.0f} 低于门店平均 {store_avg:.0f}（{ratio:.0%}）"
        else:
            # 低于 50% — 严重偏离
            score = 20.0
            detail = f"人均 {per_guest:.0f} 严重低于门店平均 {store_avg:.0f}（{ratio:.0%}）"

        return RuleDetail(
            rule_name="amount_deviation",
            rule_label="金额偏离",
            score=round(min(score, 20), 1),
            max_score=20,
            detail=detail,
            raw_data={
                "per_guest": round(per_guest, 1),
                "store_avg": round(store_avg, 1),
                "ratio": round(ratio, 4),
            },
        )

    # ---------- 规则4: 时间裂隙 ----------
    def _rule_time_gap(self, session: TableSession) -> RuleDetail:
        """
        检测异常时间模式：
        - 会话时长异常长但订单很少
        - 非营业时间（凌晨 4-6 点）开台
        """
        score = 0.0
        detail_parts = []

        try:
            opened = datetime.fromisoformat(session.opened_at)

            # 非营业时间（凌晨 4-6 点）
            if 4 <= opened.hour < 6:
                score += 8
                detail_parts.append(f"凌晨 {opened.hour}:{opened.minute:02d} 异常开台")

            # 会话时长 vs 订单密度
            if session.closed_at:
                closed = datetime.fromisoformat(session.closed_at)
                duration_h = (closed - opened).total_seconds() / 3600

                if duration_h >= 3 and session.crmeb_order_count <= 2:
                    sub = min((duration_h - 3) * 3, 12)
                    score += sub
                    detail_parts.append(
                        f"长时开台 {duration_h:.1f}h 仅 {session.crmeb_order_count} 笔订单"
                    )
                elif duration_h >= 1.5 and session.crmeb_order_count == 0:
                    score += 6
                    detail_parts.append(f"开台 {duration_h:.1f}h 无任何 POS 订单")
        except (ValueError, TypeError):
            pass

        return RuleDetail(
            rule_name="time_gap",
            rule_label="时间裂隙",
            score=round(min(score, 20), 1),
            max_score=20,
            detail="; ".join(detail_parts) if detail_parts else "时间模式正常",
            raw_data={
                "opened_at": session.opened_at,
                "closed_at": session.closed_at,
            },
        )

    # ---------- 规则5: 员工偏差 ----------
    def _rule_employee_deviation(
        self, session: TableSession, cache: dict[int, int]
    ) -> RuleDetail:
        """
        员工历史异常率。
        近 30 天异常会话数越多，当前会话风险分越高。
        """
        history_count = cache.get(session.opened_by, 0)

        if history_count <= 1:
            return RuleDetail(
                rule_name="employee_deviation",
                rule_label="员工偏差",
                score=0,
                max_score=20,
                detail="该员工历史异常少",
                raw_data={"history_anomalies_30d": history_count},
            )

        # 每多一次历史异常 +4 分
        score = min(history_count * 4, 20)
        detail = f"该员工近30天有 {history_count} 次异常会话"

        return RuleDetail(
            rule_name="employee_deviation",
            rule_label="员工偏差",
            score=round(score, 1),
            max_score=20,
            detail=detail,
            raw_data={"history_anomalies_30d": history_count},
        )

    # ==================== 风险等级 ====================

    @staticmethod
    def _risk_level(score: float) -> str:
        if score >= 80:
            return "critical"
        elif score >= 50:
            return "high"
        elif score >= 30:
            return "medium"
        return "low"

    # ==================== 企微推送 ====================

    async def _push_alerts(self, scan_date: str, high_risk: list[SessionRisk]):
        """推送高危预警到企微群"""
        if not high_risk:
            return

        lines = [
            f"## Crush掌柜 · 防飞单预警",
            f"> 日期: {scan_date}",
            f"> 高危会话: {len(high_risk)} 桌",
            "",
        ]

        for r in high_risk[:5]:  # 最多推送 5 条
            lines.append(f"### {r.table_no} · 风险分 {r.risk_score}/{r.risk_level}")
            lines.append(f"- 员工: {r.employee_name}")
            lines.append(f"- POS金额: ¥{r.crmeb_total_amount:.0f} | 企微收款: ¥{r.wework_pay_amount:.0f}")
            lines.append(f"- 客人数: {r.guest_count} | POS订单: {r.crmeb_order_count}")
            trigger_rules = [r2 for r2 in r.rules if r2.score > 5]
            if trigger_rules:
                lines.append(f"- 触发规则: {', '.join(f'{r2.rule_label}({r2.score}分)' for r2 in trigger_rules)}")
            lines.append("")

        if len(high_risk) > 5:
            lines.append(f"> 还有 {len(high_risk) - 5} 条预警，请登录 Crush掌柜 查看。")

        detail = "\n".join(lines)
        notif = NotificationService(self.session, self.store_id)
        await notif.send_alert("antifraud_alert", f"防飞单预警 · {scan_date}", detail)

    # ==================== 查询 ====================

    async def get_alerts(
        self,
        date_from: str | None = None,
        date_to: str | None = None,
        risk_level: str | None = None,
        employee_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> dict:
        """获取预警列表"""
        from app.utils.pagination import PageParams
        params = PageParams(page=page, page_size=page_size)
        sessions, total = await self.repo.get_anomaly_sessions(
            date_from=date_from,
            date_to=date_to,
            risk_level=risk_level,
            employee_id=employee_id,
            page=params,
        )

        employee_ids = list({s.opened_by for s in sessions})
        emp_names = await self.repo.get_employee_names(employee_ids)

        items = []
        for s in sessions:
            risk_score = 0.0
            risk_level_val = "low"
            anomaly_reason = s.anomaly_reason

            try:
                detail = json.loads(s.anomaly_reason or "{}")
                risk_score = detail.get("risk_score", 0)
                risk_level_val = detail.get("risk_level", "low")
            except (json.JSONDecodeError, TypeError):
                pass

            items.append({
                "session_id": s.id,
                "table_no": s.table_no,
                "employee_id": s.opened_by,
                "employee_name": emp_names.get(s.opened_by, {}).get("name", ""),
                "risk_score": risk_score,
                "risk_level": risk_level_val,
                "anomaly_reason": anomaly_reason,
                "opened_at": s.opened_at,
                "closed_at": s.closed_at,
                "status": s.status,
                "is_anomaly": s.is_anomaly,
            })

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size if total > 0 else 0,
        }

    async def get_alert_detail(self, session_id: uuid.UUID) -> dict:
        """获取单条预警详情（含完整规则明细）"""
        session = await self.repo.get_session_by_id(session_id)
        if not session:
            raise NotFoundError("会话不存在")

        # 解析 anomaly_reason 中的 JSON
        try:
            detail_data = json.loads(session.anomaly_reason or "{}")
        except (json.JSONDecodeError, TypeError):
            detail_data = {}

        emp_info = await self.repo.get_employee_names([session.opened_by])
        emp_name = emp_info.get(session.opened_by, {}).get("name", "")

        # 重新计算规则明细（用于展示）
        store_avg = await self.repo.get_store_avg_per_guest(
            date.today().isoformat(), 7
        )
        history = await self.repo.get_employee_anomaly_history(session.opened_by, 30)
        rules = await self._score_session(
            session, store_avg, {session.opened_by: history}
        )

        return {
            "session_id": session.id,
            "store_id": session.store_id,
            "table_no": session.table_no,
            "employee_id": session.opened_by,
            "employee_name": emp_name,
            "opened_at": session.opened_at,
            "closed_at": session.closed_at,
            "guest_count": session.guest_count,
            "crmeb_order_count": session.crmeb_order_count,
            "crmeb_total_amount": session.crmeb_total_amount,
            "wework_pay_count": session.wework_pay_count,
            "wework_pay_amount": session.wework_pay_amount,
            "risk_score": detail_data.get("risk_score", sum(r.score for r in rules)),
            "risk_level": detail_data.get("risk_level", "low"),
            "rules": [r.model_dump() for r in rules],
            "is_anomaly": session.is_anomaly,
            "anomaly_reason": session.anomaly_reason,
            "status": session.status,
        }

    async def get_stats(
        self, date_from: str, date_to: str
    ) -> dict:
        """获取统计数据"""
        sessions = await self.repo.get_sessions_in_range(date_from, date_to)
        revenue_list = await self.repo.get_revenue_range(date_from, date_to)

        anomaly_sessions = [s for s in sessions if s.is_anomaly]
        total = len(sessions)
        anomaly_count = len(anomaly_sessions)

        # 员工维度
        emp_stats: dict[int, dict] = {}
        for s in sessions:
            eid = s.opened_by
            if eid not in emp_stats:
                emp_stats[eid] = {"total": 0, "anomalies": 0, "risk_sum": 0.0}
            emp_stats[eid]["total"] += 1
            if s.is_anomaly:
                emp_stats[eid]["anomalies"] += 1
                try:
                    detail = json.loads(s.anomaly_reason or "{}")
                    emp_stats[eid]["risk_sum"] += detail.get("risk_score", 0)
                except (json.JSONDecodeError, TypeError):
                    pass

        employee_ids = list(emp_stats.keys())
        emp_names = await self.repo.get_employee_names(employee_ids)

        by_employee = []
        for eid, stats in emp_stats.items():
            by_employee.append({
                "employee_id": eid,
                "name": emp_names.get(eid, {}).get("name", ""),
                "anomaly_count": stats["anomalies"],
                "total_sessions": stats["total"],
                "anomaly_rate": round(stats["anomalies"] / stats["total"] * 100, 1) if stats["total"] else 0,
                "avg_risk": round(stats["risk_sum"] / stats["anomalies"], 1) if stats["anomalies"] else 0,
            })

        by_employee.sort(key=lambda x: x["anomaly_count"], reverse=True)

        # 每日趋势
        daily_map: dict[str, dict] = {}
        for s in sessions:
            try:
                d = datetime.fromisoformat(s.opened_at).strftime("%Y-%m-%d")
            except (ValueError, TypeError):
                d = "unknown"
            if d not in daily_map:
                daily_map[d] = {"date": d, "total": 0, "anomaly_count": 0}
            daily_map[d]["total"] += 1
            if s.is_anomaly:
                daily_map[d]["anomaly_count"] += 1

        daily_trend = []
        for d in sorted(daily_map.keys()):
            dm = daily_map[d]
            daily_trend.append({
                "date": dm["date"],
                "total": dm["total"],
                "anomaly_count": dm["anomaly_count"],
                "anomaly_rate": round(dm["anomaly_count"] / dm["total"] * 100, 1) if dm["total"] else 0,
            })

        # 规则维度简略统计
        avg_risk = 0.0
        if anomaly_sessions:
            total_risk = 0.0
            for s in anomaly_sessions:
                try:
                    d = json.loads(s.anomaly_reason or "{}")
                    total_risk += d.get("risk_score", 0)
                except (json.JSONDecodeError, TypeError):
                    pass
            avg_risk = round(total_risk / len(anomaly_sessions), 1)

        return {
            "store_id": self.store_id,
            "date_from": date_from,
            "date_to": date_to,
            "total_sessions": total,
            "anomaly_sessions": anomaly_count,
            "anomaly_rate": round(anomaly_count / total * 100, 1) if total else 0,
            "avg_risk_score": avg_risk,
            "by_employee": by_employee,
            "by_rule": [
                {"rule_name": "cancellation", "rule_label": "作废异常", "avg_score": 0, "trigger_count": 0},
                {"rule_name": "account_diff", "rule_label": "账差", "avg_score": 0, "trigger_count": 0},
                {"rule_name": "amount_deviation", "rule_label": "金额偏离", "avg_score": 0, "trigger_count": 0},
                {"rule_name": "time_gap", "rule_label": "时间裂隙", "avg_score": 0, "trigger_count": 0},
                {"rule_name": "employee_deviation", "rule_label": "员工偏差", "avg_score": 0, "trigger_count": 0},
            ],
            "daily_trend": daily_trend,
        }
