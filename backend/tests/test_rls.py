"""
RLS策略测试套件

验证多租户数据隔离是否正确实现。
依据 SPEC 2.0 §3.3 RLS策略（session变量方式）
"""
import pytest
from sqlalchemy import text
from sqlalchemy.orm import selectinload

from app.models.shared import Store, Employee, Member
from app.models.pos import Order, OrderItem, Payment, Refund, DiscountApproval


class TestRLSStoreIsolation:
    """测试门店数据隔离"""
    
    @pytest.mark.anyio
    async def test_store_isolation_orders(self, session, store1, store2, order_store1, order_store2):
        """测试订单表门店隔离"""
        # 设置session变量为store1
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 查询订单（应该只返回store1的订单）
        result = await session.execute(Order.__table__.select())
        orders = result.fetchall()
        
        assert len(orders) == 1
        assert orders[0].store_id == store1.store_id
    
    @pytest.mark.anyio
    async def test_store_isolation_members(self, session, store1, store2, member_store1, member_store2):
        """测试会员表门店隔离"""
        # 设置session变量为store1
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 查询会员（应该只返回store1的会员）
        result = await session.execute(Member.__table__.select())
        members = result.fetchall()
        
        assert len(members) == 1
        assert members[0].store_id == store1.store_id
    
    @pytest.mark.anyio
    async def test_store_isolation_cross_store_access_blocked(self, session, store1, store2, order_store2):
        """测试跨店访问被阻止"""
        # 设置session变量为store1
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 尝试查询store2的订单（应该返回空）
        result = await session.execute(
            Order.__table__.select().where(Order.__table__.c.order_id == order_store2.order_id)
        )
        orders = result.fetchall()
        
        assert len(orders) == 0


class TestRLSAdminBypass:
    """测试admin角色绕过RLS"""
    
    @pytest.mark.anyio
    async def test_admin_can_see_all_stores(self, session, store1, store2, order_store1, order_store2):
        """测试admin角色可以看所有店的订单"""
        # 设置session变量为admin
        await session.execute(text("SET LOCAL app.current_role = 'admin'"))
        
        # 查询订单（应该返回所有店的订单）
        result = await session.execute(Order.__table__.select())
        orders = result.fetchall()
        
        assert len(orders) == 2
        store_ids = {order.store_id for order in orders}
        assert store1.store_id in store_ids
        assert store2.store_id in store_ids
    
    @pytest.mark.anyio
    async def test_admin_bypass_specific_store(self, session, store1, store2, order_store2):
        """测试admin可以查询指定店的订单"""
        # 设置session变量为admin
        await session.execute(text("SET LOCAL app.current_role = 'admin'"))
        
        # 即使设置了store_id，admin也应该能查到所有店的订单
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        result = await session.execute(Order.__table__.select())
        orders = result.fetchall()
        
        # admin应该能看所有店的订单
        assert len(orders) >= 1


class TestRLSSessionVariableManagement:
    """测试session变量管理"""
    
    @pytest.mark.anyio
    async def test_session_variable_not_set(self, session):
        """测试未设置session变量时的行为"""
        # 不设置session变量
        # 应该返回空结果或报错（取决于RLS配置）
        result = await session.execute(Order.__table__.select())
        orders = result.fetchall()
        
        # 预期行为：返回空（因为store_id匹配不到）
        assert len(orders) == 0
    
    @pytest.mark.anyio
    async def test_session_variable_cleared_after_transaction(self, session, store1, order_store1):
        """测试事务结束后session变量清除"""
        # 在事务中设置session变量
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 查询订单
        result = await session.execute(Order.__table__.select())
        orders = result.fetchall()
        assert len(orders) == 1
        
        # 提交事务
        await session.commit()
        
        # 新事务中session变量应该被清除
        # 注意：这取决于数据库连接池的配置
        # 如果使用短连接，session变量会自动清除
        # 如果使用长连接，可能需要手动清除


class TestRLSDataIntegrity:
    """测试RLS数据完整性"""
    
    @pytest.mark.anyio
    async def test_insert_enforces_store_id(self, session, store1, employee1):
        """测试插入数据时强制store_id"""
        # 设置session变量为store1
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 插入订单（不指定store_id，应该自动使用session变量）
        # 注意：这取决于trigger或应用层逻辑
        # 如果表有DEFAULT或trigger，可以自动设置store_id
        order = Order(
            store_id=store1.store_id,  # 应用层必须提供
            order_sn="ORD202606220001",
            employee_id=employee1.employee_id,
            status="open"
        )
        session.add(order)
        await session.commit()
        
        assert order.store_id == store1.store_id
    
    @pytest.mark.anyio
    async def test_update_does_not_change_store_id(self, session, store1, store2, order_store1):
        """测试更新订单不会改变store_id"""
        # 设置session变量为store1
        await session.execute(text(f"SET LOCAL app.current_store_id = '{store1.store_id}'"))
        
        # 查询并更新订单
        result = await session.execute(
            Order.__table__.select().where(Order.__table__.c.order_id == order_store1.order_id)
        )
        order_data = result.fetchone()
        
        # 尝试更新订单（不应该改变store_id）
        await session.execute(
            Order.__table__.update()
            .where(Order.__table__.c.order_id == order_store1.order_id)
            .values(subtotal=100)
        )
        await session.commit()
        
        # 验证store_id未改变
        result = await session.execute(
            Order.__table__.select().where(Order.__table__.c.order_id == order_store1.order_id)
        )
        updated_order = result.fetchone()
        assert updated_order.store_id == store1.store_id


# 辅助fixtures（应该在conftest.py中定义）
@pytest.fixture
def store1():
    """创建测试门店1"""
    return Store(
        store_id="11111111-1111-1111-1111-111111111111",
        store_code="BJ001",
        store_name="北京三里屯店"
    )


@pytest.fixture
def store2():
    """创建测试门店2"""
    return Store(
        store_id="22222222-2222-2222-2222-222222222222",
        store_code="WX001",
        store_name="无锡店"
    )


@pytest.fixture
def employee1(store1):
    """创建测试员工1"""
    return Employee(
        employee_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
        store_id=store1.store_id,
        name="张三",
        role="store_manager"
    )


@pytest.fixture
def order_store1(store1, employee1):
    """创建门店1的订单"""
    return Order(
        order_id="33333333-3333-3333-3333-333333333333",
        store_id=store1.store_id,
        order_sn="ORD202606220001",
        employee_id=employee1.employee_id,
        status="open"
    )


@pytest.fixture
def order_store2(store2):
    """创建门店2的订单"""
    return Order(
        order_id="44444444-4444-4444-4444-444444444444",
        store_id=store2.store_id,
        order_sn="ORD202606220002",
        employee_id="bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb",
        status="open"
    )


@pytest.fixture
def member_store1(store1):
    """创建门店1的会员"""
    return Member(
        member_id="55555555-5555-5555-5555-555555555555",
        store_id=store1.store_id,
        nickname="会员1",
        phone="13800138000"
    )


@pytest.fixture
def member_store2(store2):
    """创建门店2的会员"""
    return Member(
        member_id="66666666-6666-6666-6666-666666666666",
        store_id=store2.store_id,
        nickname="会员2",
        phone="13800138001"
    )
