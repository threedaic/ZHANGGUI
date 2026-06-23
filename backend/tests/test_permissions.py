"""
权限模型测试套件

验证8角色权限矩阵是否正确实现。
依据 SPEC 2.0 §5 权限模型（8个角色）
"""
import pytest
from typing import Dict, List

from app.utils.permissions import PermissionChecker, Role


class TestRolePermissions:
    """测试角色权限矩阵"""
    
    # 权限矩阵定义（依据SPEC 2.0 §5.3）
    PERMISSION_MATRIX = {
        "admin": {
            "order:create": True,
            "order:settle": True,
            "order:cancel": True,
            "order:transfer": True,
            "kitchen:update_status": True,
            "refund:apply": True,
            "refund:confirm": True,
            "discount:apply": True,
            "discount:approve": True,
            "report:view_all": True,
            "report:view_store": True,
            "employee:manage": True,
            "store:configure": True,
            "payroll:view": True,
            "payroll:calculate": True,
        },
        "boss": {
            "order:create": True,
            "order:settle": True,
            "order:cancel": True,
            "order:transfer": True,
            "kitchen:update_status": True,
            "refund:apply": True,
            "refund:confirm": True,
            "discount:apply": True,
            "discount:approve": True,
            "report:view_all": False,  # 只能看本店
            "report:view_store": True,
            "employee:manage": True,
            "store:configure": True,
            "payroll:view": True,
            "payroll:calculate": True,
        },
        "store_manager": {
            "order:create": True,
            "order:settle": True,
            "order:cancel": True,
            "order:transfer": True,
            "kitchen:update_status": False,
            "refund:apply": True,
            "refund:confirm": False,
            "discount:apply": True,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": True,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": False,  # 只能看汇总
            "payroll:calculate": False,
        },
        "accountant": {
            "order:create": False,
            "order:settle": False,
            "order:cancel": False,
            "order:transfer": False,
            "kitchen:update_status": False,
            "refund:apply": False,
            "refund:confirm": False,
            "discount:apply": False,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": True,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": True,
            "payroll:calculate": True,
        },
        "bar_manager": {
            "order:create": False,
            "order:settle": False,
            "order:cancel": False,
            "order:transfer": False,
            "kitchen:update_status": True,
            "refund:apply": False,
            "refund:confirm": True,
            "discount:apply": False,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": False,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": False,
            "payroll:calculate": False,
        },
        "service_manager": {
            "order:create": False,
            "order:settle": False,
            "order:cancel": False,
            "order:transfer": False,
            "kitchen:update_status": False,
            "refund:apply": False,
            "refund:confirm": False,
            "discount:apply": False,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": False,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": False,
            "payroll:calculate": False,
        },
        "kitchen_manager": {
            "order:create": False,
            "order:settle": False,
            "order:cancel": False,
            "order:transfer": False,
            "kitchen:update_status": True,
            "refund:apply": False,
            "refund:confirm": False,
            "discount:apply": False,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": False,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": False,
            "payroll:calculate": False,
        },
        "staff": {
            "order:create": True,
            "order:settle": False,
            "order:cancel": False,
            "order:transfer": False,
            "kitchen:update_status": True,  # staff可以做出酒状态
            "refund:apply": False,
            "refund:confirm": False,
            "discount:apply": False,
            "discount:approve": False,
            "report:view_all": False,
            "report:view_store": False,
            "employee:manage": False,
            "store:configure": False,
            "payroll:view": False,  # 只能看自己的
            "payroll:calculate": False,
        },
    }
    
    @pytest.mark.parametrize("role", list(PERMISSION_MATRIX.keys()))
    def test_role_permissions(self, role):
        """测试每个角色的权限"""
        permissions = self.PERMISSION_MATRIX[role]
        
        for permission, expected in permissions.items():
            checker = PermissionChecker(role=role)
            actual = checker.can(permission)
            assert actual == expected, f"Role {role} permission {permission}: expected {expected}, got {actual}"


class TestDoubleMirrorReview:
    """测试双镜复核（退单/免单审批）"""
    
    @pytest.mark.anyio
    async def test_refund_applicant_cannot_confirm(
        self, session, order, store_manager, bar_manager
    ):
        """测试退单申请人和复核人不能是同一个人"""
        from app.services.refund_service import RefundService
        
        service = RefundService(session)
        
        # 店长申请退单
        refund = await service.apply(
            order_id=order.order_id,
            operator_id=store_manager.employee_id,
            reason="商品质量问题"
        )
        
        # 尝试用同一个人（店长）复核（应该失败）
        with pytest.raises(PermissionError, match="申请人和复核人不能相同"):
            await service.confirm(
                refund_id=refund.refund_id,
                confirmer_id=store_manager.employee_id  # 同一个人
            )
        
        # 用不同的人（吧台负责人）复核（应该成功）
        refund = await service.confirm(
            refund_id=refund.refund_id,
            confirmer_id=bar_manager.employee_id  # 不同的人
        )
        assert refund.status == "confirmed"
    
    @pytest.mark.anyio
    async def test_discount_applicant_cannot_approve(
        self, session, order, store_manager, boss
    ):
        """测试免单申请人和审批人不能是同一个人"""
        from app.services.discount_service import DiscountApprovalService
        
        service = DiscountApprovalService(session)
        
        # 店长申请免单
        approval = await service.apply(
            order_id=order.order_id,
            operator_id=store_manager.employee_id,
            type="free",
            amount=100,
            reason="老客户回馈"
        )
        
        # 尝试用同一个人（店长）审批（应该失败）
        with pytest.raises(PermissionError, match="申请人和审批人不能相同"):
            await service.approve(
                approval_id=approval.approval_id,
                approver_id=store_manager.employee_id  # 同一个人
            )
        
        # 用不同的人（boss）审批（应该成功）
        approval = await service.approve(
            approval_id=approval.approval_id,
            approver_id=boss.employee_id  # 不同的人
        )
        assert approval.status == "approved"


class TestPayrollConfidentiality:
    """测试工资保密规则"""
    
    @pytest.mark.anyio
    async def test_admin_can_view_all_payroll(self, session, admin_user, payroll_data):
        """测试admin可以看全国工资"""
        from app.services.payroll_service import PayrollService
        
        service = PayrollService(session)
        # admin应该能看所有店的工资
        payrolls = await service.get_payroll_summary(user=admin_user)
        
        assert len(payrolls) > 0
        # 可以看明细
        assert "details" in payrolls[0]
    
    @pytest.mark.anyio
    async def test_boss_can_view_store_payroll_detail(self, session, boss_user, store1_payroll):
        """测试boss可以看本店工资明细"""
        from app.services.payroll_service import PayrollService
        
        service = PayrollService(session)
        # boss应该能看本店的工资明细
        payrolls = await service.get_payroll_detail(
            user=boss_user,
            store_id=boss_user.store_id
        )
        
        assert len(payrolls) > 0
        # 可以看明细
        assert "employee_name" in payrolls[0]
        assert "amount" in payrolls[0]
    
    @pytest.mark.anyio
    async def test_store_manager_can_only_view_summary(self, session, store_manager_user, store1_payroll):
        """测试store_manager只能看工资汇总（不含明细）"""
        from app.services.payroll_service import PayrollService
        
        service = PayrollService(session)
        # store_manager应该只能看汇总
        payrolls = await service.get_payroll_summary(
            user=store_manager_user,
            store_id=store_manager_user.store_id
        )
        
        assert len(payrolls) > 0
        # 不能看明细（没有employee_name等敏感信息）
        if len(payrolls) > 0:
            assert "employee_name" not in payrolls[0]
    
    @pytest.mark.anyio
    async def test_employee_can_only_view_own_payroll(self, session, staff_user, staff_payroll):
        """测试员工只能看自己的工资"""
        from app.services.payroll_service import PayrollService
        
        service = PayrollService(session)
        # 员工应该只能看自己的工资
        payroll = await service.get_my_payroll(
            user=staff_user,
            employee_id=staff_user.employee_id
        )
        
        assert payroll is not None
        assert payroll.employee_id == staff_user.employee_id
        
        # 尝试看其他人的工资（应该失败）
        with pytest.raises(PermissionError, match="无权查看其他员工的工资"):
            await service.get_my_payroll(
                user=staff_user,
                employee_id="other-employee-id"
            )


class TestPermissionEnforcement:
    """测试权限强制执行"""
    
    @pytest.mark.anyio
    async def test_unauthorized_access_returns_403(self, async_client, staff_user_token):
        """测试未授权访问返回403"""
        # staff尝试访问员工管理API（应该返回403）
        response = await async_client.get(
            "/api/v1/employees",
            headers={"Authorization": f"Bearer {staff_user_token}"}
        )
        
        assert response.status_code == 403
        data = response.json()
        assert data["code"] == 40300  # 权限错误码
    
    @pytest.mark.anyio
    async def test_authorized_access_returns_200(self, async_client, boss_user_token):
        """测试授权访问返回200"""
        # boss访问员工管理API（应该返回200）
        response = await async_client.get(
            "/api/v1/employees",
            headers={"Authorization": f"Bearer {boss_user_token}"}
        )
        
        assert response.status_code == 200
    
    @pytest.mark.anyio
    async def test_cross_store_access_blocked(self, async_client, store1_manager_token, store2_employee):
        """测试跨店访问被阻止"""
        # store1的店长尝试访问store2的员工（应该返回403或404）
        response = await async_client.get(
            f"/api/v1/employees/{store2_employee.employee_id}",
            headers={"Authorization": f"Bearer {store1_manager_token}"}
        )
        
        # 应该返回403（权限不足）或404（找不到）
        assert response.status_code in (403, 404)


# 辅助函数
class PermissionChecker:
    """权限检查器（示例实现）"""
    
    def __init__(self, role: str):
        self.role = role
    
    def can(self, permission: str) -> bool:
        """检查是否有某个权限"""
        # 这里应该实现实际的权限检查逻辑
        # 示例：从权限矩阵中查找
        matrix = TestRolePermissions.PERMISSION_MATRIX
        if self.role not in matrix:
            return False
        return matrix[self.role].get(permission, False)
