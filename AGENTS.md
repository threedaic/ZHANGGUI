# Crush掌柜 — 项目上下文 (AGENTS.md v2.0)

> 新 AI 会话自动读取。本文是项目总宪章，包含产品定位、架构红线、角色权限、模块拆分原则、代码规范。任何改动必须先读本文，改完必须同步更新本文及相关 Obsidian 文档。
>
> 更新时间：2026-06-22（v2.3：按 SPEC §6.1 开发节奏推进，当前仅员工端，其他端待对应阶段创建；8角色体系，RLS session变量方式）

---

## 〇、Crush 2.0 架构总览（SPEC 2.0）

> 依据 `SPEC.md`，本项目升级为**六端架构**的加盟酒吧全流程运营管理系统。

### 六端架构（按 SPEC §6.1 开发节奏推进）

| 端 | 目录 | 端口 | 状态 | 阶段 |
|----|------|------|------|------|
| 员工端 | `frontend/` | 5173 | 当前开发 | 第1阶段（第1-2周） |
| 收银端 | `frontend-cashier/` | 5174 | 待创建 | 第2阶段（第3-12周） |
| 厨师端 | `frontend-kitchen/` | 5175 | 待创建 | 第3阶段（第13-14周） |
| 桌灯端 | `desk-lamp/` | - | 待创建 | 第4阶段（第15-18周） |
| 客人端 | `miniprogram/` | - | 待创建 | 第5阶段（第19-22周） |
| 全国端 | `frontend-admin/` | 5176 | 待创建 | 第6阶段（第23-26周） |

> **原则**：每个端在对应阶段开始时才创建目录，届时已有统一 UI 设计规范。当前阶段只完善员工端（游戏模块、商品管理）。

### 8角色体系（SPEC §5.1）

| 角色 | 代码 | 权限范围 |
|------|------|----------|
| 管理员 | admin | 全国所有门店 |
| 老板 | boss | 本店全部数据 |
| 店长 | store_manager | 本店运营数据（不含工资明细） |
| 会计 | accountant | 本店财务/工资 |
| 吧台负责人 | bar_manager | 出酒状态+退单复核 |
| 服务负责人 | service_manager | 服务相关 |
| 厨房负责人 | kitchen_manager | 厨房订单管理 |
| 店员 | staff | 日常操作 |

> 权限矩阵详见 `backend/app/utils/permissions.py` 的 `PERMISSION_MATRIX`

### 数据库 2.0 新增模块（SPEC §3.4）

- `shared_*`（10张）：门店/加盟商/员工/会员/等级/分类/商品/桌台/设备/配置
- `pos_*`（11张）：订单/明细/支付/支付方式/会话/退单/审批/流水/日志/对账/纸条
- `game_*`（4张）：模板/会话/参与者/奖品
- `sys_*`（3张）：配置/审计/打印机
- 建表脚本：`backend/alembic/versions/20260622_crush_2_0_schema.sql`
- ORM 模型：`backend/app/models/{shared,pos,game,sys}.py`

### RLS 策略（SPEC §3.3 session变量方式）

```sql
-- 门店隔离
CREATE POLICY store_isolation ON {表名}
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
-- admin 豁免
CREATE POLICY admin_all_access ON {表名}
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin');
```

后端 `database.py` 使用 `SET LOCAL app.current_store_id / app.current_role` 设置 session 变量。

### API 版本（SPEC §4.1）

- 统一 `/api/v1/*`（所有模块共享，通过路径区分模块）
- WebSocket `/ws/*`（cashier/kitchen/desk-lamp/game 四通道）

---

## 一、项目定位（不可动摇）

**Crush掌柜** 是 Crush 酒吧的企业内部管理平台，基于企微 H5 入口。

- **使用者分层**：
  - 员工（staff）：只查看个人信息
  - 店长（store_manager）：使用管理模块，不能改核心参数
  - 老板（boss）：设置核心参数、管理角色
- **设计铁律**：全自动、被动化、零门槛。员工操作 ≤ 2 步。数据能自动拉绝不手动输。
- **企微边界**：企微只同步通讯录（姓名、部门、userid）。员工的权限角色由 Crush掌柜 内部决定，老板可在设置里转授权限。
- **线上**: https://zhanggui.crushserver.cloud/（独立子域，HTTPS）
- **P0 已闭环模块**: 排班 / 考勤 / KPI / 工资 / 看板 / 评分码 / 合同 / 订桌 / 存酒 / 防飞单 / 小C AI助手
- **P1 待开发**: 实时营业推送 / 客户反馈闭环 / 低库存预警 / 员工培训考试 / 酒水销量排行

---

## 二、4 Tab 定位（新增/调整页面时必须遵守）

| Tab | 定位 | 可见角色 | 当前模块 |
|-----|------|---------|---------|
| 日常 | 一线经营效率工具 | 全员 | 小C、订桌、存酒 |
| 管理 | 店长管理模块入口 | 店长及以上 | 排班、考勤、KPI、工资、看板、评分码、合同、防飞单 |
| 设置 | 老板配置核心参数 | 老板 | 门店配置、AI配置、角色管理 |
| 我的 | 员工个人数据查看 | 全员 | 我的排班、我的考勤、我的KPI、我的工资、我的合同 |

**红线**：不能把管理类模块放到日常 Tab，不能把设置类参数直接暴露给店长。

---

## 三、模块三端拆分原则（核心）

每个业务模块必须拆成三端视角：

| 视角 | 入口 | 谁能进 | 职责 |
|------|------|--------|------|
| 员工端 | 我的 Tab | 全员 | 只看自己的数据 |
| 店长端 | 管理 Tab | 店长及以上 | 使用模块做管理操作 |
| 老板端 | 设置 Tab | 老板 | 配置该模块的核心规则 |

**示例**：
- 考勤：员工看「我的考勤」、店长用「考勤管理」、老板设「考勤规则」
- 工资：员工看「我的工资」、店长用「工资计算」、老板设「工资计算规则」
- 排班：员工看「我的排班」、店长用「排班管理」、老板设「排班规则」

**新增模块时必须先回答**：这个模块的员工端/店长端/老板端分别是什么、放在哪个 Tab。

---

## 四、角色体系

| 角色 | 权限范围 | 来源 |
|------|---------|------|
| 老板 | 全部 Tab + 核心参数 + 角色管理 | 冷启动第一个登录者；可在设置里转让给同部门人员 |
| 店长 | 日常 + 管理 + 我的 | 老板/系统指定 |
| 会计 | 日常 + 管理（工资/合同/看板）+ 我的 | 老板指定 |
| 吧台负责人 | 日常 + 管理（存酒）+ 我的 | 老板指定 |
| 服务负责人 | 日常 + 管理（订桌/评分码）+ 我的 | 老板指定 |
| 厨房负责人 | 日常 + 管理（开闭店相关）+ 我的 | 老板指定 |
| 员工 | 日常 + 我的 | 默认 |

**角色管理页**：设置 Tab → 角色管理。老板在此给员工分配角色。角色只存在 Crush掌柜 系统内，不与企微标签/部门强绑定。

---

## 五、技术栈

| 层 | 技术 | 版本 |
|----|------|------|
| 后端 | FastAPI (Python 3.12) | 0.110+ |
| ORM | SQLAlchemy async + asyncpg | 2.0 |
| 数据库 | PostgreSQL 16 | Docker 容器 |
| 缓存/限流 | Redis 7 | DB 1 |
| 前端 | Vue 3 + Vite + TypeScript | 3.x |
| UI | Vant 4 (H5 主) + Element Plus (管理后台类页面) | — |
| 状态管理 | Pinia | — |
| 图表 | ECharts | 5.x |
| 定时任务 | APScheduler | 3.10+ |
| 认证 | JWT (python-jose) + bcrypt | — |
| 日志 | loguru | 0.7+ |
| 部署 | Docker Compose + Nginx | — |

**核心依赖**: pydantic-settings, httpx, tenacity, sqlparse, alembic, python-multipart

---

## 六、项目结构

```
crush-zhanggui/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口，路由注册，中间件
│   │   ├── config.py            # 环境变量 + 配置项
│   │   ├── database.py          # AsyncSession 工厂 + RLS 上下文
│   │   ├── api/v1/              # 13 个路由模块
│   │   │   ├── auth.py          # /api/v1/auth
│   │   │   ├── store.py         # /api/v1/store
│   │   │   └── ...              # 其余11模块
│   │   ├── models/              # SQLAlchemy ORM 模型 (14文件)
│   │   ├── schemas/             # Pydantic 请求/响应模型
│   │   ├── services/            # 业务逻辑层
│   │   ├── repositories/        # 数据访问层 (CRUD + 聚合)
│   │   ├── middleware/           # RLS / 审计 / 限流
│   │   │   └── rls.py           # 新增免登录路由必须加 RLS_WHITELIST
│   │   ├── utils/               # deps / exceptions / pagination / security / redis / http_client
│   │   └── tasks/               # APScheduler 定时任务
│   ├── alembic/                 # 数据库迁移
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── views/               # 按模块分目录
│   │   │   ├── HomePage.vue     # 日常 Tab 入口
│   │   │   ├── management/      # 管理 Tab 入口及子页
│   │   │   ├── settings/        # 设置 Tab 入口及子页
│   │   │   ├── profile/         # 我的 Tab 入口及子页
│   │   │   └── ...              # 各业务模块
│   │   ├── components/          # AppShell / BottomNav / ChatWidget
│   │   ├── api/                 # axios 封装，按模块分文件
│   │   ├── stores/auth.ts       # Pinia 认证状态
│   │   └── router/index.ts      # 懒加载路由 + 权限守卫
│   └── vite.config.ts
├── docker-compose.yml
├── .gitignore
└── AGENTS.md                    # 本文档
```

**分层调用链**: `Route → Service → Repository → ORM → Database`

---

## 七、API 规范（铁律）

### 路由格式
```
/api/v1/{module}/{resource}[/{id}]
```
- **Prefix 与 route path 不得重复模块名**（否则生成双重前缀 404）
- 正确: `prefix="/api/v1/wines"` + `@router.get("")` → `/api/v1/wines`
- 错误: `prefix="/api/v1/wines"` + `@router.get("/wines")` → `/api/v1/wines/wines`

### 响应格式
```json
{"code": 0, "message": "ok", "data": {...}, "request_id": "uuid"}
```
- 成功 `code=0`；业务错误 `code=4xxxx`
- 认证失败 `40100` / 授权失败 `40300` / 资源不存在 `40400` / 冲突 `40900` / 参数错误 `40001` / 服务异常 `50000` / 外部服务失败 `50200` / 限流 `42900`
- **所有接口必须使用 `make_response(data=..., request=request)` 返回**（自动注入 request_id），禁止直接 `return {"code":0, ...}` 手写 dict
- `make_response` 定义在 `app/utils/deps.py`，支持 `code`/`message`/`data`/`request` 参数

### 分页
```json
{"items": [...], "total": N, "page": 1, "page_size": 20, "total_pages": N}
```

### 数据库查询
- PostgreSQL 日期比较用 `cast(col, Date) >= date对象`（`func.date()` 返回 text 导致类型错误）
- 防 N+1 查询：Repository 层用 `selectinload`/`joinedload`；批量查询用 `IN` 子句
- **PG SET 命令不支持参数绑定**：`SET LOCAL app.current_store_id = {int(store_id)}` 用 f-string 但值必须 `int()` 净化

### 新增免登录路由
必须在 `backend/app/middleware/rls.py` 的 `RLS_WHITELIST` 中显式声明，例如 `auth/wework/login`。

---

## 八、代码规范

### 异常处理
- 只用 `AppError` 子类，禁止裸 `raise Exception`/`ValueError`/`RuntimeError`
- 所有异常类在文件顶部导入
- 全局 handler 兜底 500
- 异常子类清单（`app/utils/exceptions.py`）：
  - `NotFoundError` (40400) / `UnauthorizedError` (40100) / `ForbiddenError` (40300)
  - `ValidationError` (40001) / `ConflictError` (40900) / `RateLimitError` (42900)
  - `ExternalServiceError` (50200) — 外部服务调用失败（企微/云打印机/SMS 等）
- `except Exception` 不得 `pass` 静默吞异常，至少 `logger.warning(...)` 记录日志

### 外部调用
- 外部 API 一律走 `app/utils/http_client.py`（含重试），禁止直接 `import httpx` 或 `import urllib`
- 企微 API 调用统一走 `app/services/wework.py`（含 `get_access_token`/`get_userid_by_code`/`sync_contacts` 等）
- 企微群机器人推送走 `app/services/wecom_notify.py`（`send_to_group`）
- 企微应用消息推送暂由 `notification_service.py` 直接调用（`wecom_notify.py` 未覆盖此场景）
- 路由层禁止直接调用外部 API，必须通过 Service 层

### 前端
- 品牌 6 色值: `#000000` / `#111111` / `#222222` / `#333333` / `#FB0079` / `#FFFFFF`
- 字体: 思源黑体 (Source Han Sans SC) + Poppins (数字/英文)
- 卡片底色 `#111111`，分隔线 `#222222`，主色 `#FB0079`
- 列表接口返回统一分页格式
- Pinia store 读取需 localStorage fallback（页面刷新后恢复）
- 路由懒加载 `() => import('@/views/xxx/index.vue')`
- 权限守卫: `router.beforeEach` 检查 token + role + token 过期；`/auth-callback` 必须放行
- **API 调用必须通过 `src/api/*.ts` 封装层**，禁止视图层直接 `fetch()` 或 `import apiClient`
- **共享类型定义在 `src/api/types.ts`**（`ApiResponse<T>`/`PageResult<T>`/`EmployeeBrief`），各 API 文件 import 引用，禁止重复定义
- **`client.ts` 统一处理业务错误码**（40100/40300/40400/40900/40001/50000/50200），视图层无需重复 `if (res.data.code === 0)` 校验
- 错误提示统一使用 `ElMessage.error()`（Element Plus）
- 禁止生产环境 `console.log` 输出 token/用户信息等敏感数据

### 通用
- 每个 raise 的异常必须有 import
- 不写死路径，用环境变量
- 新增路由后同时更新 `frontend/src/api/*.ts` 确保前后端路径一致
- **配置项统一在 `app/config.py`**：`WECOM_API_BASE`/`FRONTEND_BASE_URL`/`UPLOAD_DIR` 等环境变量
- **防 N+1 查询**：Repository 层用 `selectinload`/`joinedload`；批量查询用 `IN` 子句；禁止 `for id in ids: await repo.get(id)` 模式
- **Pydantic v2 风格统一**：使用 `model_config = {"from_attributes": True}`，禁止旧式 `class Config:`

### 收件箱消息推送规范（铁律）
> 所有需要推送到员工收件箱签收的消息，**必须**统一走 `sign_service.send_to_inbox()` 入口。

**类型注册表**：`backend/app/services/inbox_types.py`
- 新增类型只需在 `INBOX_TYPES` 字典加一条，不用改调用代码
- 当前已注册：`salary_slip`(工资单) / `attendance_confirm`(考勤确认单) / `penalty_notice`(处罚通知)

**标准调用模板**：
```python
from app.services.sign_task import SignTaskService
from app.services.inbox_types import InboxType

sign_service = SignTaskService(session, store_id)
await sign_service.send_to_inbox(
    employee_id=员工ID,
    msg_type=InboxType.PENALTY_NOTICE,   # 用枚举，禁止硬编码字符串
    ref_id=关联记录ID,
    issued_by=发送人员工ID,
    extra={                              # 必须包含标题模板所需字段
        "category": "处罚",
        "penalty_label": "服务投诉",
    },
)
```

**标题自动填充**：`send_to_inbox` 会从注册表读取 `title_template`，用 `extra` 里的字段自动替换占位符。

**禁止**：
- 禁止直接硬编码 `msg_type="penalty_notice"` 字符串，必须用 `InboxType.XXX` 枚举
- 禁止手写 `title` 变量，标题由注册表模板自动生成
- 禁止绕过 `send_to_inbox` 直接调用 `create_task`

---

## 九、认证与权限

- JWT access_token 480 分钟，refresh_token 7 天
- RLS 中间件: 解码 JWT → request.state.store_id/user_id/role
- 黑名单机制: 登出后 token 写入 Redis，刷新时校验
- 登录锁定: 5 次失败锁 30 分钟
- 企微 OAuth 免登录：`LoginPage.vue` 检测企微浏览器 → 跳转企微授权 → 回调 `/api/v1/auth/wework/login` → 签发 JWT → 重定向 `/auth-callback`

---

## 十、部署

| 项 | 值 |
|----|-----|
| 服务器 | 腾讯云 49.233.181.87 (Ubuntu 22.04) |
| SSH | `ssh -i Crush3dai.pem root@49.233.181.87` |
| 后端源码 | `/opt/crush-zhanggui/backend/` |
| 前端部署 | `/var/www/zhanggui-sub/` (Nginx 静态) |
| 容器 | crush-zhanggui-api (8001), crush-zhanggui-db (5433), crush-redis (6379) |
| 生产地址 | https://zhanggui.crushserver.cloud |
| 本地前端 | http://localhost:5173/zhanggui/ (vite dev) |
| 本地后端 | http://localhost:8001 (uvicorn) |

### 部署铁律（不可违反）

1. **禁止 `docker cp` 直接改容器内代码**（热修补）—— 容器重建后修复会丢失，且无法追踪
2. **禁止在服务器上直接改代码** —— 服务器 git 仓库只做 pull，不做编辑
3. **所有改动必须走 git 流程**：本地改 → `git commit` → `git push` → 服务器 `git pull` → `docker build`
4. **紧急修复也走这个流程**，不允许跳过。宁可多花 2 分钟走流程，也不要用 docker cp 留隐患
5. **部署后必须验证**：`git log -1` 确认 commit 一致 + 健康检查 `curl /api/v1/health`

违反铁律的后果：容器内代码与 git 仓库脱节，排错困难，多人协作时互相覆盖。

### 本地调试 vs 服务器调试

- **日常开发调试：在本地**。浏览器输入 `http://localhost:5173/zhanggui/`
  - 前端 vite dev 热更新，后端 uvicorn --reload 热更新
  - 数据库连 docker postgres 容器（5433 端口），禁止连宿主机 postgres（5434）
- **验证生产环境：在服务器**。浏览器输入 `https://zhanggui.crushserver.cloud`
  - 只在本地验证通过后，才部署到服务器验证
  - 不要直接在生产环境上调代码

### 正规部署流程

```bash
# ========== 后端部署 ==========
# 1. 本地提交并推送
cd crush-zhanggui
git add backend/
git commit -m "fix: 描述本次修改"
git push origin trae/generated-code

# 2. 服务器拉取并重建
ssh -i Crush3dai.pem root@49.233.181.87
cd /opt/crush-zhanggui
git fetch origin
git reset --hard origin/trae/generated-code   # 强制对齐远程，丢弃本地脏改
cd backend && docker compose -f /opt/crush-zhanggui/docker-compose.yml up -d --build backend

# 3. 验证
curl http://localhost:8001/api/v1/health
git log -1 --oneline   # 确认 commit 与本地一致

# ========== 前端部署 ==========
# 1. 本地构建
cd crush-zhanggui/frontend
npx vite build

# 2. 上传到服务器（前端不走 git，直接传 dist）
tar czf - dist/ | ssh -i Crush3dai.pem root@49.233.181.87 \
  "cd /var/www/zhanggui-sub && rm -rf assets/ && tar xzf - && mv dist/* . && rm -rf dist/"

# 3. 验证
curl -s https://zhanggui.crushserver.cloud/ | grep -o '<title>[^<]*</title>'
```

> 前端不走 git 的原因：dist 是构建产物，体积大且每次变化，不适合纳入版本控制。前端源码在本地 git 仓库管理，部署时只传构建产物。

---

## 十一、新增模块检查清单

- [ ] 该模块的员工端/店长端/老板端已明确，分别放入 我的/管理/设置 Tab
- [ ] 后端路由已在 `main.py` 注册，prefix 与 route path 不重复模块名
- [ ] 前端页面在 `router/index.ts` 注册，并设置 `meta.roles`
- [ ] 前端 API 文件在 `src/api/xxx.ts`，路径与后端一致
- [ ] **所有 API 接口使用 `make_response(data=..., request=request)` 返回**（含 request_id）
- [ ] 异常用 AppError 子类，错误码语义正确
- [ ] 列表接口统一分页格式（含 `total_pages`）
- [ ] 颜色只用品牌 6 色值
- [ ] 新增免登录路由已加入 `RLS_WHITELIST`
- [ ] 新增 Model 列已同步 ALTER TABLE 或 Alembic 迁移
- [ ] **前端 API 类型从 `src/api/types.ts` 导入**（`ApiResponse`/`PageResult`），禁止重复定义
- [ ] **无 N+1 查询**：批量查询用 `IN` 子句或 `selectinload`
- [ ] **外部 URL 从 `config.py` 读取**，禁止硬编码
- [ ] **收件箱推送使用 `send_to_inbox()`**，类型在 `inbox_types.py` 注册，用 `InboxType` 枚举
- [ ] **已同步更新本文档及 Obsidian 相关文档**

---

## 十二、AI 工作流（必读）

1. **动手前先读**：`AGENTS.md` → `功能依赖地图.md` → `API接口规范.md` → `上线排雷经验-2026-06-14.md`
2. **涉及 UI 再读**：`UI设计规范-交付标准.md`
3. **每改一个核心约定**，必须同步更新 `AGENTS.md` 和对应 Obsidian 文档
4. **不确定时**：先停下来问用户，不要猜测
5. **禁止**：私自改变 4 Tab 定位、私自把设置类参数暴露给店长、私自让企微标签决定系统角色

---

## 十三、关联文档

Obsidian 库位置：`C:\WorkBuddy\workbuddy_obsidian\Crush酒吧\Crush掌柜\`

- `功能依赖地图.md` — 模块归属、依赖关系、文件清单
- `API接口规范.md` — 80 条路由完整清单
- `UI设计规范-交付标准.md` — 视觉规范
- `上线排雷经验-2026-06-14.md` — 部署/踩坑铁律
- `项目框架规范.md` — 技术框架说明
