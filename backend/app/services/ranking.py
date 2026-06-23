"""
员工排名服务

四维排名激励:
  - performance  业绩排名（按个人业绩金额，来自 employee_monthly_performance）
  - kpi          KPI排名（按KPI总分，来自 kpi_results）
  - attendance   考勤排名（按全勤天数/迟到次数倒序，来自 attendance_records）
  - rating       评分排名（按客户评分均分，来自 guest_ratings）

设计要点:
  - 排名结果写入 employee_rankings 表（支持重算）
  - 排行榜全员可见名次（透明激励），但不显示工资金额
  - 按门店+月份+排名类型聚合
  - 考勤排名: 全勤天数优先，迟到次数倒序（次数少排前）
"""
import json
from datetime import datetime
from sqlalchemy import select, and_, delete, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.models.ranking import EmployeeRanking
from app.models.performance import EmployeeMonthlyPerformance
from app.models.kpi import KPIResult
from app.models.attendance import AttendanceRecord
from app.models.rating import GuestRating
from app.models.employee import Employee
from app.utils.exceptions import NotFoundError, ValidationError


# 排名类型枚举
RANK_TYPES = ("performance", "kpi", "attendance", "rating")


class RankingService:
    """员工排名 Service"""

    def __init__(self, session: AsyncSession, store_id: int):
        self.session = session
        self.store_id = store_id

    # ==================== 计算排名 ====================

    async def calculate_rankings(
        self,
        period: str,
        rank_type: str | None = None,
    ) -> list[EmployeeRanking]:
        """计算指定月份的员工排名

        Args:
            period: 账期 YYYY-MM
            rank_type: 排名类型，None=计算全部4维

        Returns:
            写入的排名记录列表
        """
        types_to_calc = [rank_type] if rank_type else list(RANK_TYPES)
        for t in types_to_calc:
            if t not in RANK_TYPES:
                raise ValidationError(f"不支持的排名类型: {t}，可选: {RANK_TYPES}")

        all_records: list[EmployeeRanking] = []
        for t in types_to_calc:
            records = await self._calc_one_type(period, t)
            all_records.extend(records)

        await self.session.commit()
        logger.info(
            f"[Ranking] 门店 {self.store_id} 账期 {period} "
            f"计算 {len(all_records)} 条排名记录"
        )
        return all_records

    async def _calc_one_type(
        self, period: str, rank_type: str
    ) -> list[EmployeeRanking]:
        """计算单个维度的排名"""
        # 1. 清理该月该类型的旧排名（支持重算）
        await self.session.execute(
            delete(EmployeeRanking).where(
                and_(
                    EmployeeRanking.store_id == self.store_id,
                    EmployeeRanking.period == period,
                    EmployeeRanking.rank_type == rank_type,
                )
            )
        )

        # 2. 取原始排名数据 [{employee_id, rank_value, detail}, ...]
        if rank_type == "performance":
            raw_data = await self._calc_performance_rank(period)
        elif rank_type == "kpi":
            raw_data = await self._calc_kpi_rank(period)
        elif rank_type == "attendance":
            raw_data = await self._calc_attendance_rank(period)
        else:  # rating
            raw_data = await self._calc_rating_rank(period)

        if not raw_data:
            return []

        # 3. 排序并分配名次
        # 考勤排名特殊: 迟到次数越少越好，已在 _calc_attendance_rank 中处理 rank_value
        # 这里统一按 rank_value 降序
        sorted_data = sorted(raw_data, key=lambda x: x["rank_value"], reverse=True)

        now = datetime.now()
        records: list[EmployeeRanking] = []
        for position, item in enumerate(sorted_data, start=1):
            record = EmployeeRanking(
                store_id=self.store_id,
                employee_id=item["employee_id"],
                period=period,
                rank_type=rank_type,
                rank_value=round(float(item["rank_value"]), 2),
                rank_position=position,
                detail=json.dumps(item.get("detail", {}), ensure_ascii=False),
                calculated_at=now,
            )
            self.session.add(record)
            records.append(record)

        await self.session.flush()
        return records

    async def _calc_performance_rank(self, period: str) -> list[dict]:
        """业绩排名: 按个人业绩总金额降序"""
        stmt = (
            select(
                EmployeeMonthlyPerformance.employee_id,
                func.sum(EmployeeMonthlyPerformance.total_amount).label("total_amount"),
            )
            .where(
                and_(
                    EmployeeMonthlyPerformance.store_id == self.store_id,
                    EmployeeMonthlyPerformance.period == period,
                )
            )
            .group_by(EmployeeMonthlyPerformance.employee_id)
        )
        result = await self.session.execute(stmt)
        rows = result.all()

        return [
            {
                "employee_id": row.employee_id,
                "rank_value": float(row.total_amount or 0),
                "detail": {"total_amount": float(row.total_amount or 0)},
            }
            for row in rows
        ]

    async def _calc_kpi_rank(self, period: str) -> list[dict]:
        """KPI排名: 按KPI总分降序"""
        stmt = select(KPIResult).where(
            and_(
                KPIResult.store_id == self.store_id,
                KPIResult.period == period,
                KPIResult.status == "confirmed",
            )
        )
        result = await self.session.execute(stmt)
        kpi_results = list(result.scalars().all())

        return [
            {
                "employee_id": r.employee_id,
                "rank_value": float(r.total_score or 0),
                "detail": {
                    "total_score": float(r.total_score or 0),
                    "coefficient": float(r.coefficient or 1.0),
                },
            }
            for r in kpi_results
        ]

    async def _calc_attendance_rank(self, period: str) -> list[dict]:
        """考勤排名: 全勤天数优先，迟到次数倒序

        rank_value 设计: 全勤天数 × 1000 - 迟到次数 × 10 - 早退次数 × 5
        （全勤天数越多越好，迟到/早退次数越少越好）
        """
        year, month = int(period[:4]), int(period[5:7])
        month_str = f"{year}-{month:02d}"

        result = await self.session.execute(
            text(
                "SELECT "
                "  employee_id, "
                "  COUNT(*) FILTER (WHERE status = 'present') AS present_days, "
                "  COUNT(*) FILTER (WHERE status = 'late') AS late_count, "
                "  COUNT(*) FILTER (WHERE status = 'early') AS early_count, "
                "  COUNT(*) FILTER (WHERE status = 'absent') AS absent_count "
                "FROM att_records "
                "WHERE store_id = :sid "
                "  AND date_trunc('month', date) = :month "
                "GROUP BY employee_id"
            ),
            {"sid": self.store_id, "month": f"{month_str}-01"},
        )
        rows = result.mappings().all()

        data: list[dict] = []
        for row in rows:
            present = int(row.get("present_days") or 0)
            late = int(row.get("late_count") or 0)
            early = int(row.get("early_count") or 0)
            absent = int(row.get("absent_count") or 0)
            # 全勤天数权重最高，迟到/早退/旷工扣分
            rank_value = present * 1000 - late * 10 - early * 5 - absent * 50
            data.append({
                "employee_id": row["employee_id"],
                "rank_value": rank_value,
                "detail": {
                    "present_days": present,
                    "late_count": late,
                    "early_count": early,
                    "absent_count": absent,
                },
            })
        return data

    async def _calc_rating_rank(self, period: str) -> list[dict]:
        """评分排名: 按客户评分均分降序"""
        year, month = int(period[:4]), int(period[5:7])
        month_str = f"{year}-{month:02d}"

        result = await self.session.execute(
            text(
                "SELECT "
                "  employee_id, "
                "  AVG(overall_score) AS avg_score, "
                "  COUNT(*) AS rating_count "
                "FROM guest_ratings "
                "WHERE store_id = :sid "
                "  AND employee_id IS NOT NULL "
                "  AND date_trunc('month', created_at) = :month "
                "GROUP BY employee_id"
            ),
            {"sid": self.store_id, "month": f"{month_str}-01"},
        )
        rows = result.mappings().all()

        return [
            {
                "employee_id": row["employee_id"],
                "rank_value": float(row.get("avg_score") or 0),
                "detail": {
                    "avg_score": round(float(row.get("avg_score") or 0), 2),
                    "rating_count": int(row.get("rating_count") or 0),
                },
            }
            for row in rows
        ]

    # ==================== 查询排行榜 ====================

    async def get_leaderboard(
        self,
        period: str,
        rank_type: str,
        limit: int = 50,
    ) -> dict:
        """获取排行榜（全员可见，仅名次和数值，不显示工资）

        Returns:
          {
            "period": "2026-06",
            "rank_type": "performance",
            "items": [
              {"rank_position": 1, "employee_id": 1, "employee_name": "张三",
               "rank_value": 12345.67, "detail": {...}},
              ...
            ]
          }
        """
        if rank_type not in RANK_TYPES:
            raise ValidationError(f"不支持的排名类型: {rank_type}")

        stmt = (
            select(EmployeeRanking)
            .where(
                and_(
                    EmployeeRanking.store_id == self.store_id,
                    EmployeeRanking.period == period,
                    EmployeeRanking.rank_type == rank_type,
                )
            )
            .order_by(EmployeeRanking.rank_position)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        rankings = list(result.scalars().all())

        if not rankings:
            return {
                "period": period,
                "rank_type": rank_type,
                "items": [],
            }

        # 批量取员工姓名（避免 N+1）
        emp_ids = [r.employee_id for r in rankings]
        emp_name_map = await self._get_employee_names(emp_ids)

        items = []
        for r in rankings:
            detail = {}
            if r.detail:
                try:
                    detail = json.loads(r.detail) if isinstance(r.detail, str) else r.detail
                except (json.JSONDecodeError, TypeError):
                    detail = {}

            items.append({
                "rank_position": r.rank_position,
                "employee_id": r.employee_id,
                "employee_name": emp_name_map.get(r.employee_id, f"员工{r.employee_id}"),
                "rank_value": float(r.rank_value or 0),
                "detail": detail,
            })

        return {
            "period": period,
            "rank_type": rank_type,
            "items": items,
        }

    async def get_my_rankings(
        self, employee_id: int, period: str
    ) -> list[dict]:
        """员工查看自己的四维排名"""
        stmt = select(EmployeeRanking).where(
            and_(
                EmployeeRanking.store_id == self.store_id,
                EmployeeRanking.employee_id == employee_id,
                EmployeeRanking.period == period,
            )
        )
        result = await self.session.execute(stmt)
        rankings = list(result.scalars().all())

        # 统计每个类型的总人数（用于显示"排名 3/15"）
        type_counts = await self._get_rank_type_counts(period)

        return [
            {
                "rank_type": r.rank_type,
                "rank_position": r.rank_position,
                "total_count": type_counts.get(r.rank_type, 0),
                "rank_value": float(r.rank_value or 0),
                "detail": (
                    json.loads(r.detail)
                    if r.detail and isinstance(r.detail, str)
                    else (r.detail or {})
                ),
            }
            for r in rankings
        ]

    async def _get_rank_type_counts(self, period: str) -> dict[str, int]:
        """获取各排名类型的总参与人数"""
        stmt = (
            select(
                EmployeeRanking.rank_type,
                func.count(EmployeeRanking.id).label("cnt"),
            )
            .where(
                and_(
                    EmployeeRanking.store_id == self.store_id,
                    EmployeeRanking.period == period,
                )
            )
            .group_by(EmployeeRanking.rank_type)
        )
        result = await self.session.execute(stmt)
        return {row.rank_type: int(row.cnt) for row in result.all()}

    async def _get_employee_names(self, employee_ids: list[int]) -> dict[int, str]:
        """批量获取员工姓名"""
        if not employee_ids:
            return {}
        stmt = select(Employee.id, Employee.name).where(
            and_(
                Employee.id.in_(employee_ids),
                Employee.store_id == self.store_id,
            )
        )
        result = await self.session.execute(stmt)
        return {row[0]: row[1] for row in result.all()}
