# Crush 2.0 可运维性评估报告

**评估日期**: 2026-06-23  
**评估人员**: Rex (SRE工程师)  
**系统版本**: Crush掌柜 2.0  
**评估范围**: 部署、监控、告警、可靠性  

---

## 执行摘要

Crush 2.0 系统在可运维性方面已建立基础框架，但在生产环境就绪性方面存在**关键缺口**。系统缺少WebSocket实现、结构化日志、指标暴露和自动化告警，这些是支撑收银核心业务高可用性的必要条件。

**风险等级**: 🔴 高（缺失核心功能，需在上线前补全）

---

## 1. 部署评估

### 1.1 Docker 配置

#### ✅ 已完成
- 生产环境 `Dockerfile` 配置正确（监听 `0.0.0.0:8000`）
- 开发环境 `Dockerfile.dev` 配置正确（监听 `0.0.0.0:8001` + `--reload`）
- `docker-compose.dev.yml` 配置正确（使用Alpine镜像，配置热加载）
- 服务依赖健康检查（`condition: service_healthy`）
- 资源限制（CPU 0.5核、内存 512M）
- 自动重启策略（`restart: unless-stopped`）

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **后端监听地址错误** | 🔴 高 | `docker-compose.yml` 第38行：`--host 127.0.0.1`，容器内能访问，但跨容器通信会失败，应改为 `0.0.0.0` |
| **无前端容器配置** | 🟡 中 | SPEC定义六端架构，当前仅后端容器，前端（员工端/收银端）未配置 |
| **无多阶段构建** | 🟡 中 | `Dockerfile` 未使用多阶段构建，镜像体积大（~1GB） |
| **无日志驱动配置** | 🟡 中 | Docker日志默认json-file，未配置日志大小限制和轮转 |
| **数据库备份策略缺失** | 🔴 高 | 无自动备份配置，数据丢失风险高 |

#### 📋 修复建议

```yaml
# docker-compose.yml 修复后端监听地址（第38行）
backend:
  command: uvicorn app.main:app --host 0.0.0.0 --port 8001  # 修复
  
# 添加日志驱动配置
logging:
  driver: "json-file"
  options:
    max-size: "10m"
    max-file: "3"
    
# 添加数据库备份服务
services:
  postgres-backup:
    image: postgres:16-alpine
    environment:
      POSTGRES_HOST: postgres
      POSTGRES_USER: crush
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./backups:/backups
    command: |
      sh -c "while true; do
        pg_dump -h $$POSTGRES_HOST -U $$POSTGRES_USER crush_zhanggui | gzip > /backups/backup_$$(date +%Y%m%d_%H%M%S).sql.gz
        sleep 3600
      done"
```

---

### 1.2 环境变量管理

#### ✅ 已完成
- 使用 `.env` 文件管理环境变量
- `config.py` 使用 Pydantic Settings 自动加载
- 生产环境配置示例 `.env.production` 已提供
- JWT_SECRET 在生产环境有校验（拒绝默认值）

#### ⚠️ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **敏感信息明文存储** | 🔴 高 | `.env.production` 包含数据库密码、JWT密钥，应改用密钥管理服务（AWS Secrets Manager/腾讯云SSM） |
| **无环境变量版本管理** | 🟡 中 | `.env` 文件在 `.gitignore` 中，但 `.env.production` 可能误提交 |
| **SSL未启用** | 🔴 高 | `DATABASE_URL` 中 `ssl=disable`，生产环境应启用SSL |

#### 📋 修复建议

```python
# config.py 修复：生产环境强制SSL
@property
def DATABASE_URL(self) -> str:
    ssl_param = "" if self.APP_ENV == "production" else "?ssl=disable"
    return (
        f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
        f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        f"{ssl_param}"
    )
```

---

### 1.3 数据库迁移策略

#### ✅ 已完成
- 使用 Alembic 进行数据库迁移
- 迁移脚本目录 `alembic/versions/` 已建立
- 包含手动SQL迁移和自动生成迁移

#### ⚠️ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无迁移回滚策略** | 🔴 高 | 未定义迁移失败时的回滚流程 |
| **无预发布环境验证** | 🟡 中 | 迁移脚本未经预发布环境验证直接上生产 |
| **自动生成迁移风险** | 🟡 中 | `Base.metadata.create_all` 在启动时运行，可能和实际迁移脚本冲突 |

#### 📋 修复建议

1. **添加迁移回滚脚本**：
   ```bash
   # 迁移前自动备份
   pg_dump -h $PGHOST -U $PGUSER $PGDB > backup_$(date +%Y%m%d_%H%M%S).sql
   
   # 执行迁移
   alembic upgrade head
   
   # 如果失败，回滚
   alembic downgrade -1
   ```

2. **添加迁移验证步骤**：
   ```yaml
   # CI/CD pipeline
   stages:
     - test_migration: 在测试环境运行迁移
     - verify_schema: 对比迁移前后schema差异
     - approve: 人工审批后上生产
   ```

---

## 2. 监控评估

### 2.1 日志系统

#### ✅ 已完成
- 使用 `loguru` 进行日志记录
- 日志文件轮转（10 MB，保留7天）
- 日志路径可通过环境变量 `LOG_PATH` 配置
- 请求ID（`X-Request-ID`）和响应时间（`X-Response-Time`）跟踪

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无结构化日志** | 🔴 高 | 日志为文本格式，无法被ELK/Loki等日志系统自动解析 |
| **无集中式日志收集** | 🔴 高 | 日志存储在容器本地，容器重启后丢失 |
| **日志级别未区分环境** | 🟡 中 | 生产环境应只记录WARNING以上级别 |
| **无关键业务日志** | 🔴 高 | 订单创建/支付/退单等关键操作未记录审计日志 |

#### 📋 修复建议

```python
# 添加结构化日志（JSON格式）
import json
from datetime import datetime

def structured_log(level, event, **kwargs):
    log_record = {
        "timestamp": datetime.utcnow().isoformat(),
        "level": level,
        "event": event,
        "service": "crush-zhanggui",
        "environment": settings.APP_ENV,
        **kwargs
    }
    logger.log(level, json.dumps(log_record))

# 订单创建日志示例
async def create_order(...):
    structured_log("info", "order.create", 
                   order_id=order_id, 
                   store_id=store_id, 
                   employee_id=employee_id,
                   amount=total_amount)
```

---

### 2.2 性能监控

#### ✅ 已完成
- 响应时间通过中间件记录（`X-Response-Time`）
- 数据库连接池配置（`pool_size=10, max_overflow=0`）
- Redis连接池管理

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无Prometheus指标暴露** | 🔴 高 | 无法采集QPS、延迟、错误率等指标 |
| **无数据库性能监控** | 🔴 高 | 慢查询、连接数、锁等待未监控 |
| **无Redis监控** | 🟡 中 | 缓存命中率、内存使用率未监控 |
| **无应用性能监控(APM)** | 🟡 中 | 未集成Sentry/New Relic等APM工具 |

#### 📋 修复建议

```python
# 添加Prometheus指标端点
from prometheus_client import Counter, Histogram, generate_latest

REQUEST_COUNT = Counter('http_requests_total', 'Total HTTP requests', ['method', 'endpoint', 'status'])
REQUEST_LATENCY = Histogram('http_request_duration_seconds', 'Request latency')

@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    REQUEST_COUNT.labels(request.method, request.url.path, response.status_code).inc()
    REQUEST_LATENCY.observe(process_time)
    
    return response

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type="text/plain")
```

---

### 2.3 业务指标监控

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无业务指标定义** | 🔴 高 | 订单金额、支付成功率、翻台率等关键指标未定义 |
| **无实时业务监控** | 🔴 高 | 无法实时查看营收、订单量等业务数据 |
| **无异常检测** | 🔴 高 | 订单量骤降、支付失败率上升等异常未告警 |

#### 📋 修复建议

在 `shared_store_settings` 表中添加监控配置：

```sql
ALTER TABLE shared_store_settings ADD COLUMN monitoring_config JSONB DEFAULT '{}';

-- 配置示例
{
  "metrics": {
    "order_count": {"alert_threshold": 10, "window_minutes": 60},
    "payment_success_rate": {"alert_threshold": 0.95, "window_minutes": 30},
    "table_turnover_rate": {"alert_threshold": 2.0, "window_hours": 1}
  }
}
```

---

## 3. 告警评估

### 3.1 错误告警

#### ✅ 已完成
- 企微群机器人推送（`wecom_notify.py`）
- 老板可关闭通知开关（`wecom_bot_enabled`）

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无分级告警** | 🔴 高 | 所有错误一律推送，无SEV1-4分级 |
| **无告警收敛** | 🔴 高 | 同一错误重复推送，造成告警风暴 |
| **无告警升级** | 🔴 高 | 告警后无人工响应时未升级 |
| **无告警渠道冗余** | 🔴 高 | 仅依赖企微推送，企微故障时不生效 |

#### 📋 修复建议

```python
# 告警分级和收敛
from datetime import datetime, timedelta
from redis.asyncio import Redis

class AlertManager:
    def __init__(self, redis: Redis):
        self.redis = redis
    
    async def send_alert(self, alert_key: str, severity: str, message: str):
        # 告警收敛：相同告警10分钟内只发一次
        cache_key = f"alert:sent:{alert_key}"
        if await self.redis.exists(cache_key):
            return
        
        # 发送告警
        if severity == "SEV1":
            await self._send_to_pagerduty(message)  # 紧急告警
        elif severity == "SEV2":
            await self._send_to_wecom(message)  # 企微推送
        else:
            await self._send_to_slack(message)  # 日常通知
        
        # 记录已发送
        await self.redis.setex(cache_key, 600, "1")
```

---

### 3.2 性能告警

#### ❌ 存在问题

未实现任何性能告警机制。

#### 📋 修复建议

```python
# 添加性能告警
async def check_performance_metrics():
    # 检查数据库慢查询
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT query, mean_time, calls 
            FROM pg_stat_statements 
            WHERE mean_time > 1000 
            ORDER BY mean_time DESC 
            LIMIT 10
        """))
        slow_queries = result.fetchall()
        if slow_queries:
            await notify_alert(..., "数据库慢查询告警", f"发现{len(slow_queries)}条慢查询")
    
    # 检查Redis内存使用
    redis = await get_redis()
    info = await redis.info()
    if info['used_memory'] / info['total_system_memory'] > 0.8:
        await notify_alert(..., "Redis内存告警", "Redis内存使用率超过80%")
```

---

## 4. 可靠性评估

### 4.1 PostgreSQL RLS 策略

#### ✅ 已完成
- RLS策略通过session变量实现（`app.current_store_id` / `app.current_user_role`）
- session变量设置前进行了输入净化（`_sanitize_session_value`）
- 使用 `SET LOCAL` 确保变量仅在事务内生效
- admin角色豁免策略已配置

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **RLS策略未在实际表中启用** | 🔴 高 | SPEC定义了RLS策略SQL，但代码中未找到实际执行 `ALTER TABLE ENABLE ROW LEVEL SECURITY` 的脚本 |
| **session变量名不一致** | 🔴 高 | SPEC §3.3 使用 `app.current_role`，但 `database.py` 第78行使用 `app.current_user_role`，**策略SQL和代码不匹配** |
| **无RLS策略单元测试** | 🔴 高 | 未测试跨店数据泄露场景 |

#### 📋 修复建议

1. **统一session变量名**：
   ```sql
   -- 修改所有RLS策略中的变量名
   DROP POLICY IF EXISTS admin_all_access ON shared_employees;
   CREATE POLICY admin_all_access ON shared_employees
       FOR ALL
       USING (current_setting('app.current_user_role', true) = 'admin');
   ```

2. **添加RLS迁移脚本**：
   ```python
   # alembic/versions/enable_rls.py
   def upgrade():
       op.execute("ALTER TABLE shared_employees ENABLE ROW LEVEL SECURITY")
       op.execute("CREATE POLICY store_isolation ON shared_employees ...")
       # ... 所有表
   ```

3. **添加RLS测试**：
   ```python
   async def test_rls_isolation():
       # 设置store_id=store_A
       await set_session_context(session, store_id="store_A_uuid")
       
       # 查询员工表
       result = await session.execute(select(Employee).where(...))
       
       # 验证只返回store_A的员工
       assert all(emp.store_id == "store_A_uuid" for emp in result)
   ```

---

### 4.2 Redis缓存

#### ✅ 已完成
- Redis用于频率限制（滑动窗口算法）
- Redis连接池管理
- Redis不可用时的降级策略（fail-open）

#### ⚠️ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无缓存策略文档** | 🟡 中 | 未明确哪些数据需要缓存、缓存过期时间 |
| **无缓存预热** | 🟡 中 | 重启后缓存为空，首次访问慢 |
| **无缓存击穿/雪崩防护** | 🔴 高 | 未使用互斥锁或随机过期时间 |

#### 📋 修复建议

```python
# 添加缓存装饰器
from functools import wraps

def cached(key_pattern: str, ttl: int = 300):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 生成缓存key
            cache_key = key_pattern.format(**kwargs)
            
            # 尝试从缓存读取
            redis = await get_redis()
            cached_value = await redis.get(cache_key)
            if cached_value:
                return json.loads(cached_value)
            
            # 缓存未命中，执行原函数
            result = await func(*args, **kwargs)
            
            # 写入缓存（使用随机TTL防止雪崩）
            import random
            actual_ttl = ttl + random.randint(0, 60)
            await redis.setex(cache_key, actual_ttl, json.dumps(result))
            
            return result
        return wrapper
    return decorator

# 使用示例
@cached("store:{store_id}:employees", ttl=600)
async def get_store_employees(store_id: str):
    ...
```

---

### 4.3 WebSocket连接管理

#### ❌ 存在问题

**🔴 关键发现：代码中未实现WebSocket**

SPEC §4.4 定义了4个WebSocket通道：
- `/ws/cashier` - 收银端同步
- `/ws/kitchen` - 厨师端订单推送
- `/ws/desk-lamp` - 桌灯端通信
- `/ws/game` - 游戏控台同步

但在 `backend/app` 目录下**未找到任何WebSocket实现代码**。

#### 📋 修复建议

```python
# app/api/v1/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict
import json

class ConnectionManager:
    def __init__(self):
        # 按门店/角色管理连接
        self.active_connections: Dict[str, List[WebSocket]] = {}
    
    async def connect(self, websocket: WebSocket, store_id: str, role: str):
        await websocket.accept()
        key = f"{store_id}:{role}"
        if key not in self.active_connections:
            self.active_connections[key] = []
        self.active_connections[key].append(websocket)
    
    def disconnect(self, websocket: WebSocket, store_id: str, role: str):
        key = f"{store_id}:{role}"
        if key in self.active_connections:
            self.active_connections[key].remove(websocket)
    
    async def broadcast_to_store(self, store_id: str, message: dict):
        # 向指定门店的所有连接广播
        for role in ["cashier", "kitchen", "desk_lamp"]:
            key = f"{store_id}:{role}"
            if key in self.active_connections:
                for connection in self.active_connections[key]:
                    await connection.send_json(message)

manager = ConnectionManager()

@router.websocket("/ws/cashier")
async def websocket_cashier(
    websocket: WebSocket,
    token: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    # 验证token
    payload = decode_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return
    
    store_id = payload.get("store_id")
    role = payload.get("role")
    
    await manager.connect(websocket, store_id, "cashier")
    
    try:
        while True:
            # 接收客户端消息
            data = await websocket.receive_json()
            
            # 处理消息（如订单状态更新）
            if data["type"] == "order_update":
                # 广播给同门店的其他收银端
                await manager.broadcast_to_store(store_id, {
                    "type": "order_updated",
                    "order_id": data["order_id"],
                    "status": data["status"]
                })
    except WebSocketDisconnect:
        manager.disconnect(websocket, store_id, "cashier")
```

---

### 4.4 企微推送可靠性

#### ✅ 已完成
- 企微群机器人推送服务（`wecom_notify.py`）
- 老板可关闭通知开关

#### ❌ 存在问题

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **无重试机制** | 🔴 高 | 推送失败时直接返回False，未重试 |
| **无推送队列** | 🔴 高 | 高并发时企微API限流（20次/分钟） |
| **无推送失败告警** | 🔴 高 | 推送失败后无告警，老板可能错过关键通知 |
| **无推送日志** | 🟡 中 | 无法追溯推送历史 |

#### 📋 修复建议

```python
# 添加推送队列和重试
import asyncio
from celery import Celery

celery_app = Celery("crush", broker=settings.REDIS_URL)

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
async def send_wecom_notification(self, webhook_url: str, content: str):
    try:
        await send_to_group(webhook_url, content)
    except Exception as exc:
        # 指数退避重试
        raise self.retry(exc=exc, countdown=2 ** self.request.retries * 60)

# 添加推送限流
class WecomRateLimiter:
    def __init__(self, redis: Redis):
        self.redis = redis
        self.max_per_minute = 20
    
    async def acquire(self, webhook_url: str) -> bool:
        key = f"wecom:ratelimit:{webhook_url}"
        current = await self.redis.incr(key)
        if current == 1:
            await self.redis.expire(key, 60)
        
        if current > self.max_per_minute:
            return False
        return True
```

---

### 4.5 对账系统可靠性

#### ❌ 存在问题

SPEC定义了 `pos_daily_reconciliations` 表，但代码中未找到对账逻辑实现。

| 问题 | 严重程度 | 说明 |
|------|---------|------|
| **对账逻辑未实现** | 🔴 高 | 系统应收 vs 实际收款的对账未实现 |
| **无数据不一致检测** | 🔴 高 | 订单金额和支付记录不匹配时未告警 |
| **无对账失败处理** | 🔴 高 | 对账失败时无人工介入流程 |

#### 📋 修复建议

```python
# app/services/reconciliation.py
async def daily_reconciliation(store_id: str, date: date):
    async with AsyncSessionLocal() as session:
        # 计算系统应收
        result = await session.execute(select(
            func.sum(pos_orders.total_amount)
        ).where(
            and_(
                pos_orders.store_id == store_id,
                func.date(pos_orders.closed_at) == date,
                pos_orders.status == 'paid'
            )
        ))
        system_receivable = result.scalar() or 0
        
        # 读取实际收款（从支付记录聚合）
        result = await session.execute(select(
            pos_payments.payment_method,
            func.sum(pos_payments.amount)
        ).where(
            and_(
                pos_payments.store_id == store_id,
                func.date(pos_payments.created_at) == date
            )
        ).group_by(pos_payments.payment_method))
        actual_payments = {row[0]: row[1] for row in result}
        
        # 计算差异
        difference = system_receivable - sum(actual_payments.values())
        
        # 记录对账结果
        reconciliation = pos_daily_reconciliations(
            store_id=store_id,
            date=date,
            system_receivable=system_receivable,
            actual_pos=actual_payments.get('pos', 0),
            actual_cash=actual_payments.get('cash', 0),
            actual_wechat=actual_payments.get('wechat', 0),
            actual_alipay=actual_payments.get('alipay', 0),
            difference=difference,
            status='pending' if abs(difference) > 0.01 else 'approved'
        )
        session.add(reconciliation)
        await session.commit()
        
        # 如果对账不平，发送告警
        if abs(difference) > 0.01:
            await notify_alert(store_id, "对账异常", 
                             f"日期：{date}\n差异金额：{difference}元")
```

---

## 5. 总体评估

### 5.1 成熟度评级

| 维度 | 成熟度 | 评分 | 说明 |
|------|--------|------|------|
| **部署** | 🟡 中等 | 6/10 | 基础Docker配置完成，但缺少多阶段构建、日志驱动、备份策略 |
| **监控** | 🔴 低 | 3/10 | 无结构化日志、无指标暴露、无APM集成 |
| **告警** | 🔴 低 | 2/10 | 仅有基础的企微推送，无分级、无收敛、无升级 |
| **可靠性** | 🔴 低 | 4/10 | RLS实现有bug、WebSocket未实现、企微推送不可靠 |

**总体评分**: 4/10 （生产环境不可用）

---

### 5.2 关键风险清单

| 序号 | 风险 | 影响 | 优先级 |
|------|------|------|--------|
| 1 | RLS策略未启用 + session变量名不一致 | 数据泄露（跨店访问） | P0 |
| 2 | WebSocket未实现 | 收银端/厨房端无法实时同步 | P0 |
| 3 | 无结构化日志 + 无集中式收集 | 故障排查困难 | P0 |
| 4 | 无Prometheus指标暴露 | 无法监控性能、容量规划困难 | P0 |
| 5 | 后端监听地址错误（127.0.0.1 in docker-compose.yml） | 跨容器通信失败 | P0 |
| 6 | 企微推送无重试 + 无队列 | 关键告警丢失 | P1 |
| 7 | 无数据库自动备份 | 数据丢失风险 | P1 |
| 8 | SSL未启用 | 数据传输不安全 | P1 |

---

### 5.3 上线前必做清单

- [ ] **P0-1**: 修复RLS策略（统一变量名 + 执行ENABLE RLS脚本）
- [ ] **P0-2**: 实现WebSocket端点（收银端/厨房端/桌灯端）
- [ ] **P0-3**: 添加Prometheus指标端点（`/metrics`）
- [ ] **P0-4**: 配置结构化日志（JSON格式）+ 集中式收集（Loki/ELK）
- [ ] **P0-5**: 修复 `docker-compose.yml` 后端监听地址（127.0.0.1 → 0.0.0.0）
- [ ] **P1-1**: 添加企微推送重试机制和队列
- [ ] **P1-2**: 配置数据库自动备份
- [ ] **P1-3**: 启用数据库连接SSL

---

## 6. 附录：部署检查清单

详见独立文档：[DEPLOYMENT_CHECKLIST.md](./DEPLOYMENT_CHECKLIST.md)

---

**评估人**: Rex (SRE工程师)  
**日期**: 2026-06-23  
**版本**: 2.0
