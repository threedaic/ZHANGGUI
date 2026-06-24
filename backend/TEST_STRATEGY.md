# Crush 2.0 测试策略与评估报告

> 测试专家：泰莎（Tessa）| 日期：2026-06-22
> 评审对象：Crush 2.0 加盟酒吧全流程运营管理系统

---

## 执行摘要

### 关键发现
- **测试覆盖率：~0%** （仅有3个API连通性测试）
- **测试债：CRITICAL** （缺少所有关键业务逻辑的测试）
- **风险等级：HIGH** （系统涉及支付、退款、多租户隔离等高风险功能）

### 优先行动
1. 立即建立RLS策略测试（多租户数据隔离）
2. 建立权限模型测试（8角色权限矩阵）
3. 建立订单/支付核心流程测试
4. 建立退单双镜复核测试

---

## 一、现有测试覆盖评估

### 1.1 测试文件分析

| 文件 | 类型 | 测试数量 | 覆盖内容 | 质量评估 |
|------|------|---------|----------|----------|
| `tests/test_api.py` | API连通性 | 3 | health/docs/认证 | ⚠️ 基础 |
| `tests/conftest.py` | 测试配置 | - | async_client fixture | ✅ 可用 |
| `test_sync.py` | 同步脚本 | - | 企微考勤数据同步 | ❌ 非测试 |
| `init_test_data.py` | 数据初始化 | - | 测试数据 | ⚠️ 有用但未集成 |

**结论：有效测试覆盖率接近0%**

### 1.2 缺失测试清单（按优先级）

#### P0 - 关键业务功能（必须测试）
- [ ] RLS策略（多租户隔离）
- [ ] 权限模型（8角色权限矩阵）
- [ ] 订单状态机（open→paid/cancelled/transferred）
- [ ] 厨房状态机（waiting→claimed→preparing→ready→served）
- [ ] 支付流程（拆分支付、多种支付方式）
- [ ] 退单双镜复核（申请≠复核人）
- [ ] 免单/折扣审批（申请≠审批人）
- [ ] 会员余额流水（充值/消费/退款一致性）

#### P1 - 重要功能
- [ ] 桌台管理（开台/清台/转桌/拼桌）
- [ ] WebSocket连接（收银端/厨师端/桌灯端）
- [ ] 数据迁移（19,342条订单+22,216条会员数据）
- [ ] 对账功能（系统应收vs实收）
- [ ] 商品库存管理

#### P2 - 支撑功能
- [ ] 排班管理
- [ ] 考勤管理
- [ ] 工资计算（9角色提成逻辑）
- [ ] KPI计算
- [ ] 游戏模块
- [ ] 纸条社交

---

## 二、测试策略文档

### 2.1 测试金字塔

```
        /  E2E测试  \       10-15% | 关键业务流程自动化
       /  集成测试   \      20-25% | API+数据库+RLS+WebSocket
      /   单元测试    \     60-70% | 模型+服务+工具函数
```

### 2.2 单元测试策略

#### 2.2.1 模型层测试
**目标**：验证ORM模型和数据库约束
**覆盖**：
- 所有26张业务表的CRUD操作
- 字段约束（NOT NULL、UNIQUE、外键）
- 审计字段（created_at/updated_at）
- UUID主键生成

**示例测试用例**：
```python
@pytest.mark.anyio
async def test_create_order(session):
    """测试创建订单"""
    order = Order(
        store_id=store_id,
        order_sn="ORD202606220001",
        employee_id=employee_id,
        status="open"
    )
    session.add(order)
    await session.commit()
    
    assert order.order_id is not None
    assert order.status == "open"
    assert order.subtotal == 0
```

#### 2.2.2 服务层测试
**目标**：验证业务逻辑正确性
**覆盖**：
- 订单服务（创建/追加/结账/退单）
- 支付服务（拆分支付/余额计算）
- 厨房服务（状态转换/认领）
- 会员服务（余额/积分/等级）
- 权限服务（8角色权限判断）

**示例测试用例**：
```python
@pytest.mark.anyio
async def test_order_settle_with_split_payment(session, order_service):
    """测试拆分支付结账"""
    order = await create_test_order(session)
    await order_service.add_item(order.order_id, product_id, quantity=2)
    
    # 拆分支付：微信100 + 现金50
    payments = [
        {"method": "wechat", "amount": 100},
        {"method": "cash", "amount": 50}
    ]
    result = await order_service.settle(order.order_id, payments)
    
    assert result.status == "paid"
    assert result.paid_amount == 150
    assert len(result.payments) == 2
```

#### 2.2.3 工具函数测试
**目标**：验证纯函数正确性
**覆盖**：
- 订单号生成（唯一性）
- 金额计算（精度/四舍五入）
- 日期时间处理
- 权限判断逻辑

### 2.3 集成测试策略

#### 2.3.1 API端点测试
**目标**：验证HTTP接口正确性
**覆盖**：
- 所有API端点的请求/响应
- 认证和授权
- 参数校验
- 错误处理

**示例测试用例**：
```python
@pytest.mark.anyio
async def test_create_order_api(async_client, auth_headers):
    """测试创建订单API"""
    response = await async_client.post(
        "/api/v1/orders",
        json={
            "table_id": str(table_id),
            "guest_count": 4
        },
        headers=auth_headers
    )
    
    assert response.status_code == 201
    data = response.json()["data"]
    assert "order_id" in data
    assert data["status"] == "open"
```

#### 2.3.2 RLS策略测试 ⚠️ **关键**
**目标**：验证多租户数据隔离
**覆盖**：
- 普通员工只能看本店数据
- admin角色可以看所有店数据
- session变量正确设置和清除

**示例测试用例**：
```python
@pytest.mark.anyio
async def test_rls_store_isolation(session):
    """测试RLS门店隔离"""
    # 设置session变量为store1
    await session.execute(text("SET LOCAL app.current_store_id = :store_id", {"store_id": store1_id}))
    
    # 查询订单（应该只返回store1的订单）
    result = await session.execute(select(Order))
    orders = result.scalars().all()
    
    assert all(order.store_id == store1_id for order in orders)
```

#### 2.3.3 数据库集成测试
**目标**：验证数据库操作和事务
**覆盖**：
- 事务回滚
- 并发控制
- 数据库连接池

#### 2.3.4 WebSocket测试 ⚠️ **关键**
**目标**：验证实时通信
**覆盖**：
- 收银端多平板同步
- 厨师端订单推送
- 桌灯端消息接收
- 连接管理和重连

**示例测试用例**：
```python
@pytest.mark.anyio
async def test_kitchen_websocket_order_push(websocket_client):
    """测试厨师端WebSocket订单推送"""
    # 连接厨师端WebSocket
    await websocket_client.connect("/ws/kitchen")
    
    # 创建新订单
    order = await create_test_order()
    
    # 验证收到订单推送
    message = await websocket_client.receive_json()
    assert message["type"] == "new_order"
    assert message["order_id"] == str(order.order_id)
```

### 2.4 E2E测试策略

#### 2.4.1 关键业务流程
**覆盖场景**：
1. **开台→点单→结账**（happy path）
2. **退单双镜复核**（异常流程）
3. **免单审批**（权限验证）
4. **拆分支付**（复杂支付）
5. **转桌/拼桌**（桌台管理）
6. **会员充值消费**（余额一致性）

**示例测试场景**：
```gherkin
Feature: 退单双镜复核
  Scenario: 店长申请退单，吧台负责人复核
    Given 存在一个已支付的订单
    And 当前用户是店长
    When 店长申请退单
    Then 退单状态为"pending"
    When 吧台负责人复核退单
    Then 退单状态为"confirmed"
    And 订单状态变为"cancelled"
    And 会员余额已退款
```

### 2.5 性能测试策略

#### 2.5.1 高并发场景
**测试目标**：
- 多桌台同时下单（50并发）
- WebSocket连接数（100+）
- 数据库查询性能（RLS开销）
- API响应时间（<200ms）

**工具**：Locust / k6 / pytest-benchmark

#### 2.5.2 压力测试
- 订单创建：1000 orders/min
- 支付处理：500 payments/min
- WebSocket消息：5000 msg/min

---

## 三、测试计划（按模块、按优先级）

### 3.1 第1阶段：核心功能测试（Week 1-2）

| 模块 | 测试类型 | 用例数量 | 优先级 | 负责人 |
|------|----------|---------|--------|--------|
| RLS策略 | 集成测试 | 10 | P0 | 测试专家 |
| 权限模型 | 单元+集成 | 20 | P0 | 测试专家 |
| 订单管理 | 单元+集成 | 30 | P0 | 测试专家 |
| 支付流程 | 单元+集成 | 25 | P0 | 测试专家 |
| 退单复核 | 单元+集成+E2E | 15 | P0 | 测试专家 |

### 3.2 第2阶段：业务功能测试（Week 3-4）

| 模块 | 测试类型 | 用例数量 | 优先级 | 负责人 |
|------|----------|---------|--------|--------|
| 厨房管理 | 单元+集成+WS | 20 | P1 | 测试专家 |
| 桌台管理 | 单元+集成 | 15 | P1 | 测试专家 |
| 会员管理 | 单元+集成 | 20 | P1 | 测试专家 |
| 商品管理 | 单元+集成 | 15 | P1 | 测试专家 |
| WebSocket | 集成测试 | 10 | P1 | 测试专家 |

### 3.3 第3阶段：支撑功能测试（Week 5-6）

| 模块 | 测试类型 | 用例数量 | 优先级 | 负责人 |
|------|----------|---------|--------|--------|
| 排班管理 | 单元测试 | 15 | P2 | 开发团队 |
| 考勤管理 | 单元测试 | 15 | P2 | 开发团队 |
| 工资计算 | 单元+集成 | 20 | P2 | 开发团队 |
| 游戏模块 | 单元测试 | 10 | P2 | 开发团队 |
| 数据迁移 | 集成测试 | 10 | P1 | 测试专家 |

### 3.4 第4阶段：E2E和性能测试（Week 7-8）

| 测试类型 | 场景数量 | 优先级 | 负责人 |
|----------|---------|--------|--------|
| E2E测试 | 10 | P0 | 测试专家 |
| 性能测试 | 5 | P1 | 测试专家 |
| 安全测试 | 8 | P0 | 安全专家 |
| 兼容性测试 | 5 | P2 | 测试专家 |

---

## 四、测试债清单（按优先级排序）

### 4.1 CRITICAL（立即处理）

| # | 测试债 | 风险 | 修复成本 | 建议 |
|---|--------|------|---------|------|
| 1 | RLS策略未测试 | 数据泄露 | 高 | 立即建立RLS测试套件 |
| 2 | 权限模型未测试 | 越权操作 | 高 | 建立8角色权限矩阵测试 |
| 3 | 支付流程未测试 | 资金损失 | 高 | 建立支付完整性测试 |
| 4 | 退单复核未测试 | 财务漏洞 | 高 | 建立双镜复核测试 |

### 4.2 HIGH（本周内处理）

| # | 测试债 | 风险 | 修复成本 | 建议 |
|---|--------|------|---------|------|
| 5 | 订单状态机未测试 | 状态不一致 | 中 | 建立状态转换测试 |
| 6 | 厨房状态机未测试 | 出餐混乱 | 中 | 建立状态转换测试 |
| 7 | WebSocket未测试 | 实时性故障 | 中 | 建立WebSocket测试 |
| 8 | 会员余额未测试 | 余额不一致 | 高 | 建立余额一致性测试 |

### 4.3 MEDIUM（本月内处理）

| # | 测试债 | 风险 | 修复成本 | 建议 |
|---|--------|------|---------|------|
| 9 | 数据迁移未测试 | 数据丢失 | 高 | 建立迁移验证测试 |
| 10 | 对账功能未测试 | 财务差异 | 中 | 建立对账测试 |
| 11 | 商品库存未测试 | 库存不准 | 低 | 建立库存测试 |
| 12 | 排班考勤未测试 | 管理混乱 | 低 | 建立排班考勤测试 |

### 4.4 LOW（后续迭代处理）

| # | 测试债 | 风险 | 修复成本 | 建议 |
|---|--------|------|---------|------|
| 13 | 游戏模块未测试 | 功能故障 | 低 | 建立游戏逻辑测试 |
| 14 | 纸条社交未测试 | 功能故障 | 低 | 建立社交功能测试 |
| 15 | KPI计算未测试 | 考核不准 | 中 | 建立KPI测试 |
| 16 | 工资计算未测试 | 工资错误 | 高 | 建立工资计算测试 |

---

## 五、测试环境和技术栈

### 5.1 测试环境
- **本地开发环境**：SQLite（快速单元测试）
- **集成测试环境**：PostgreSQL + Redis（Docker Compose）
- **E2E测试环境**：Staging环境（类生产配置）
- **性能测试环境**：独立环境（避免影响开发）

### 5.2 测试工具栈
- **单元测试**：pytest + pytest-asyncio
- **API测试**：httpx + FastAPI TestClient
- **数据库测试**：SQLAlchemy + pytest-postgresql
- **WebSocket测试**：websockets + pytest
- **E2E测试**：Playwright / Selenium
- **性能测试**：Locust / k6
- **覆盖率**：pytest-cov + coverage.py

### 5.3 CI/CD集成
```yaml
# .github/workflows/test.yml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16
      redis:
        image: redis:7
    
    steps:
      - uses: actions/checkout@v3
      - name: Run tests
        run: |
          pytest --cov=app --cov-report=html
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## 六、测试可交付成果

### 6.1 测试文档
- [ ] 测试策略文档（本文档）
- [ ] 测试计划（详细到用例级别）
- [ ] 测试报告模板
- [ ] 缺陷报告模板

### 6.2 测试代码
- [ ] 单元测试代码（目标覆盖率：70%）
- [ ] 集成测试代码（目标覆盖率：80%）
- [ ] E2E测试脚本（10个关键场景）
- [ ] 性能测试脚本（5个基准测试）

### 6.3 测试数据
- [ ] 测试数据生成脚本
- [ ] 测试 fixture 工厂
- [ ] Mock数据配置

---

## 七、风险和缓解措施

### 7.1 风险识别

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|---------|
| RLS策略测试复杂 | 高 | 高 | 优先建立RLS测试框架 |
| WebSocket测试困难 | 中 | 中 | 使用专门的WS测试库 |
| 测试数据准备耗时 | 中 | 高 | 建立测试数据工厂 |
| 性能测试环境成本 | 低 | 中 | 使用云上按需环境 |

### 7.2 质量门禁
- **单元测试覆盖率**：≥70%
- **集成测试覆盖率**：≥80%
- **E2E测试通过率**：100%
- **性能测试**：API响应时间<200ms（P95）
- **所有P0测试用例**：100%通过

---

## 八、附录：示例测试用例

### 8.1 RLS策略测试示例

```python
@pytest.mark.anyio
async def test_rls_admin_bypass(session):
    """测试admin角色绕过RLS"""
    # 设置session变量为admin
    await session.execute(text("SET LOCAL app.current_role = 'admin'"))
    
    # 查询所有门店的订单（应该能查到）
    result = await session.execute(select(Order))
    orders = result.scalars().all()
    
    # admin应该能看到所有店的订单
    # （具体断言根据实际情况）
    assert isinstance(orders, list)
```

### 8.2 权限模型测试示例

```python
@pytest.mark.parametrize("role,can_refund_apply,can_refund_confirm", [
    ("store_manager", True, False),
    ("bar_manager", False, True),
    ("boss", True, True),
    ("staff", False, False),
])
def test_refund_permissions(role, can_refund_apply, can_refund_confirm):
    """测试退单权限矩阵"""
    permissions = get_permissions(role)
    
    assert permissions.can("refund_apply") == can_refund_apply
    assert permissions.can("refund_confirm") == can_refund_confirm
```

### 8.3 订单状态机测试示例

```python
@pytest.mark.anyio
async def test_order_status_transitions(order_service):
    """测试订单状态转换"""
    # 创建订单
    order = await order_service.create(table_id)
    assert order.status == "open"
    
    # 追加商品
    await order_service.add_item(order.order_id, product_id, quantity=2)
    assert order.status == "open"  # 仍然是open
    
    # 结账
    await order_service.settle(order.order_id, payments)
    assert order.status == "paid"
    
    # 退款
    await order_service.refund(order.order_id, reason="客人不满意")
    assert order.status == "cancelled"
```

### 8.4 退单双镜复核测试示例

```python
@pytest.mark.anyio
async def test_refund_double_mirror(session, refund_service):
    """测试退单双镜复核（申请≠复核人）"""
    # 店长申请退单
    refund = await refund_service.apply(
        order_id=order_id,
        operator_id=store_manager_id,
        reason="商品质量问题"
    )
    assert refund.status == "pending"
    
    # 尝试用同一个人复核（应该失败）
    with pytest.raises(PermissionError):
        await refund_service.confirm(
            refund_id=refund.refund_id,
            confirmer_id=store_manager_id  # 同一个人
        )
    
    # 用吧台负责人复核（应该成功）
    refund = await refund_service.confirm(
        refund_id=refund.refund_id,
        confirmer_id=bar_manager_id  # 不同的人
    )
    assert refund.status == "confirmed"
```

---

## 九、总结和建议

### 9.1 关键发现总结
1. **测试覆盖率极低**（~0%），存在巨大质量风险
2. **缺少关键业务测试**（RLS/权限/支付/退单）
3. **测试基础设施不完整**（无CI/CD集成）
4. **测试债累积严重**（16项测试债，4项CRITICAL）

### 9.2 优先行动建议
1. **立即启动**：RLS策略测试开发（1周）
2. **并行启动**：权限模型测试开发（1周）
3. **第2周启动**：订单/支付流程测试（2周）
4. **第3周启动**：退单/免单审批测试（1周）
5. **第4周启动**：E2E测试框架搭建（2周）

### 9.3 资源需求
- **测试专家**：1人（全职，8周）
- **开发支持**：各模块开发协助（兼职）
- **测试环境**：Docker Compose配置
- **测试数据**：生产数据脱敏副本

### 9.4 成功指标
- 单元测试覆盖率 ≥70%
- 集成测试覆盖率 ≥80%
- P0测试用例通过率 = 100%
- 发现并修复所有CRITICAL级缺陷

---

**报告结束**

> 测试专家：泰莎（Tessa）
> 联系方式：[team-lead]
> 下一步：等待team-lead确认测试优先级和资源分配
