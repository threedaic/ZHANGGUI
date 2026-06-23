"""Crush 2.0 角色与权限常量

依据 SPEC 2.0 第五章：
- 8角色体系：admin/boss/store_manager/accountant/bar_manager/service_manager/kitchen_manager/staff
- RLS session 变量方式（current_setting('app.current_role')）
- 权限矩阵集中定义
"""
from enum import Enum


class Role(str, Enum):
    """8角色体系（SPEC 2.0 §5.1）"""
    ADMIN = "admin"                          # 管理员：全国所有门店
    BOSS = "boss"                            # 老板：本店全部数据
    STORE_MANAGER = "store_manager"          # 店长：本店运营数据（不含工资明细）
    ACCOUNTANT = "accountant"                # 会计：本店财务/工资
    BAR_MANAGER = "bar_manager"             # 吧台负责人：出酒状态+退单复核
    SERVICE_MANAGER = "service_manager"      # 服务负责人：服务相关
    KITCHEN_MANAGER = "kitchen_manager"      # 厨房负责人：厨房订单管理
    STAFF = "staff"                          # 店员：日常操作


# 全部角色代码
ALL_ROLES = [r.value for r in Role]

# 管理层角色（可看本店全部或部分管理数据）
MANAGER_ROLES = {
    Role.ADMIN.value,
    Role.BOSS.value,
    Role.STORE_MANAGER.value,
    Role.ACCOUNTANT.value,
    Role.BAR_MANAGER.value,
    Role.SERVICE_MANAGER.value,
    Role.KITCHEN_MANAGER.value,
}

# 可看全国数据的角色
NATIONAL_ROLES = {Role.ADMIN.value}

# 退单复核角色（双镜复核人）
REFUND_CONFIRMER_ROLES = {Role.ADMIN.value, Role.BOSS.value, Role.BAR_MANAGER.value}

# 免单/折扣审批角色
DISCOUNT_APPROVER_ROLES = {Role.ADMIN.value, Role.BOSS.value}

# 工资相关角色
PAYROLL_ROLES = {Role.ADMIN.value, Role.BOSS.value, Role.ACCOUNTANT.value}

# RLS 豁免角色（可看所有门店）
RLS_EXEMPT_ROLES = {Role.ADMIN.value}


# ---------------------------------------------------------------------------
# 权限矩阵（SPEC 2.0 §5.3）
# 值：True=允许 / "national"=全国 / "own_shift"=自己班次 / False=禁止
# ---------------------------------------------------------------------------
PERMISSION_MATRIX = {
    "table.open": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.STAFF.value},
    "table.order": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.STAFF.value},
    "table.settle": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.STAFF.value},
    "bar.status_switch": {Role.ADMIN.value, Role.BOSS.value, Role.BAR_MANAGER.value, Role.STAFF.value},
    "refund.apply": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value},
    "refund.confirm": {Role.ADMIN.value, Role.BOSS.value, Role.BAR_MANAGER.value},
    "discount.apply": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value},
    "discount.approve": {Role.ADMIN.value, Role.BOSS.value},
    "order.view_history": {
        Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.STAFF.value,
    },
    "report.view": {
        Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.ACCOUNTANT.value,
    },
    "store.config": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value},
    "menu.manage": {Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value},
    "employee.manage": {Role.ADMIN.value, Role.BOSS.value},
    "system.config": {Role.ADMIN.value, Role.BOSS.value},
    "payroll.manage": {Role.ADMIN.value, Role.BOSS.value, Role.ACCOUNTANT.value},
    "dashboard.view": {Role.ADMIN.value, Role.BOSS.value},
    "game.initiate": {
        Role.ADMIN.value, Role.BOSS.value, Role.STORE_MANAGER.value, Role.STAFF.value,
    },
    "sign.task": ALL_ROLES,
}


def has_permission(role: str, permission: str) -> bool:
    """检查角色是否拥有指定权限。"""
    allowed = PERMISSION_MATRIX.get(permission, set())
    return role in allowed


def is_rls_exempt(role: str) -> bool:
    """是否豁免 RLS 门店隔离（admin 可看全国）。"""
    return role in RLS_EXEMPT_ROLES
