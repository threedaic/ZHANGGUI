# Crush 2.0 系统规范文档（SPEC）

> 日期：2026-06-25 | 版本：2.3 | 状态：修正版
>
> 修正说明：基于完整阅读全部12份项目文档后，对比v1.0发现30个矛盾点和13项遗漏，经逐条确认后修正。
> v2.1 补充：新增att_*/wage_*/hr_*完整表结构（24张表）、工资公式引擎、薪资规则时间线、工资异常处理流程。
> v2.2 补充：新增收件箱消息系统统一规范、统一模块自查清单（5项待统一）。
> v2.3 补充：明确连锁品牌四级权限体系（system_admin/boss/store_manager/staff），新增"总店网页"全局管理规范。

---

## 〇、角色与权限体系（连锁品牌核心规范）

### 0.1 四级角色定义

| 角色 | 中文 | 管辖范围 | 典型用户 | 是否绑定门店 |
|------|------|----------|----------|--------------|
| `system_admin` | 系统管理员 | 全品牌全部门店 | Crush管理群成员（周鹏飞/卡西/王柏霄等） | ❌ 不绑定 |
| `boss` | 单店老板 | 一家门店 | 各店投资人/老板 | ✅ 绑定一家 |
| `store_manager` | 店长 | 一家门店的日常运营 | 各店店长 | ✅ 绑定一家 |
| `staff` | 员工 | 自己的数据 | 各店员工 | ✅ 绑定一家 |

### 0.2 系统管理员识别规则（重要！不可遗忘）

**规则：企微「Crush 管理」部门（部门名含"管理"关键字，parentid=1）的所有成员，自动识别为 `system_admin`，不参与单店角色分配。**

```
企微部门结构示例：
Crush 跨时 (根部门 id=1)
├─ 北京店 (id=3)       → boss/store_manager/staff
├─ 无锡店 (id=4)       → boss/store_manager/staff
└─ Crush 管理 (id=5)   → 全部 system_admin ★
    ├─ 周鹏飞 (ZhouPengFei)
    ├─ 卡西 (ZhangHanTing)
    └─ 王柏霄 (bbmayo)
```

### 0.3 配置方式

```env
# .env 配置（与 BOSS_WEWORK_USERIDS 并存，优先级更高）
SYSTEM_ADMIN_USERIDS=ZhouPengFei,ZhangHanTing,bbmayo
```

### 0.4 system_admin 的特殊能力

1. **不绑定门店**：store_id 可为空，登录后进入「总店网页」（全局视角）
2. **可访问全部门店**：通过顶部门店切换进入任意门店
3. **可建新门店**：在总店网页的「门店管理」页面新增门店
4. **全局看板**：可查看全品牌汇总数据（总营收/总客流/各店对比）
5. **RLS 豁免**：数据库策略 `current_setting('app.current_user_role', true) = ANY (ARRAY['admin','system_admin'])` 放行（同时兼容旧 admin 值与新 system_admin 值）

### 0.5 总店网页规范

| 页面 | 路径 | 权限 | 功能 |
|------|------|------|------|
| 总店首页 | `/hq` | system_admin | 全品牌数据看板（各店营收/客流/人数对比） |
| 门店管理 | `/hq/stores` | system_admin | 新增/编辑/停业门店，绑定企微部门 |
| 全局员工 | `/hq/employees` | system_admin | 查看全品牌员工，跨店调拨 |

### 0.6 账号管理规范（铁律）

> **核心原则：调试和开发统一使用唯一管理员账号，禁止私自创建新账号。**

#### 0.6.1 唯一调试账号

| 项 | 值 |
|----|-----|
| 用户名 | `admin` |
| 密码 | `admin123` |
| 角色 | `system_admin`（最高权限） |
| 绑定员工 | 周鹏飞（wecom_user_id: `ZhouPengFei`） |
| 绑定门店 | 总部 |
| 用途 | 网页登录调试、开发测试、运维管理 |

**铁律：**
1. **禁止创建新账号用于调试/开发**。所有开发、测试、调试场景一律使用 `admin/admin123`。
2. **禁止为 system_admin 角色创建多个账号**。Crush 管理群成员（周鹏飞/卡西/王柏霄等）通过企微 OAuth 免密登录即可，不需要密码账号。
3. **禁止把 admin 账号绑定给其他员工**。admin 账号固定绑定周鹏飞，不得更改。
4. **禁止修改 admin 账号密码**。如需修改必须先经项目经理确认并在本文档同步更新。

#### 0.6.2 登录方式对照表

| 场景 | 登录方式 | 入口 |
|------|---------|------|
| 网页调试/开发 | 账号密码：`admin` / `admin123` | `/login` 页面 → 「使用密码登录」 |
| 企微内打开 | OAuth 免密 | 企微工作台点击应用 → 自动跳转授权 |
| 普通员工日常 | OAuth 免密 | 企微内打开自动登录，无密码账号 |

#### 0.6.3 账号创建边界

仅以下三种情况允许创建新的 sys_users 账号：
1. **新门店老板**需要网页登录管理后台时，由 system_admin 在「角色管理」页创建 boss 账号。
2. **特定岗位**（如会计）需要网页登录且无法通过企微 OAuth 满足时。
3. **临时测试账号**需在 PR 说明中注明用途，测试完立即删除。

任何其他情况创建账号视为违规。

### 0.7 权限检查规范（铁律）

> **核心原则：system_admin 是最高权限，必须能访问所有功能。所有 require_role 调用必须包含 system_admin。**

#### 0.7.1 角色值统一

数据库实际只存在以下三种 role 值（**禁止使用 `admin` 这个值**，统一用 `system_admin`）：

| 角色 | 值 | 权限范围 |
|------|-----|---------|
| 系统管理员 | `system_admin` | **所有功能**（最高权限，通吃） |
| 老板 | `boss` | 本店全部功能 |
| 店长 | `store_manager` | 本店日常管理（不含工资配置等敏感操作） |
| 员工 | `staff` | 只看自己的数据 |

> 历史代码中出现的 `'admin'` 角色值已废弃，统一为 `'system_admin'`。RLS 策略为向后兼容仍同时放行 `admin` 和 `system_admin`。

#### 0.7.2 require_role 编写规范

后端所有 `require_role(request, [...])` 调用**必须**包含 `system_admin`，确保管理员账号能调试所有功能。

| 场景 | 正确写法 | 错误写法 |
|------|---------|---------|
| 仅老板可操作 | `["system_admin", "boss"]` | `["boss"]` ❌ |
| 老板+店长 | `["system_admin", "boss", "store_manager"]` | `["boss", "store_manager"]` ❌ |
| 老板+会计 | `["system_admin", "boss", "accountant"]` | `["boss", "accountant"]` ❌ |
| 老板+店长+会计 | `["system_admin", "boss", "store_manager", "accountant"]` | `["boss", "store_manager", "accountant"]` ❌ |

#### 0.7.3 前端路由守卫规范

前端 `router/index.ts` 的 `meta.roles` 同样**禁止**使用 `'admin'`，统一用 `'system_admin'`：

| 路由 | 允许角色 |
|------|---------|
| `/hq` (总店端) | `['system_admin']` |
| `/management` (管理端) | `['system_admin', 'boss', 'store_manager']` |
| `/settings` (设置端) | `['system_admin', 'boss']` |
| `/daily` (日常端) | 无限制（所有人可访问） |
| `/profile` (员工端) | 无限制（所有人可访问） |

#### 0.7.4 修改 require_role 的检查清单

新增或修改 API 权限时，必须：
1. 确认 `require_role` 列表包含 `system_admin`
2. 确认不使用 `'admin'` 这个值
3. 用 `Grep` 搜索 `require_role\(request, \["(?!system_admin)` 确认无遗漏（注：ripgrep 不支持先行断言，改为搜索 `require_role\(request, \["boss"` 后人工核对每行都含 system_admin）

---

## 一、项目背景

### 1.1 项目定位

Crush是中国陌生社交酒吧连锁品牌（加盟模式），目标2028年达30家店。Crush掌柜2.0是一套**加盟酒吧全流程运营管理系统**，覆盖人员管理、排班考勤、点单收银、库存进销存、厨房显示、智能桌灯社交、对账报表、加盟费计算、企微工作台。

### 1.2 重构原因

| 原因 | 说明 |
|------|------|
| 安全漏洞 | 旧系统7个CRITICAL安全漏洞（C1: 22个收银API无认证，C3: 门店隔离依赖客户端Header可被绕过） |
| 外包依赖 | 旧系统代码为外包持有，无Git、无源码管理 |
| 技术栈过时 | PHP ThinkPHP 5.1 EOL、MySQL 5.7 EOL |
| 无法支撑连锁扩张 | 应用层隔离已被证明可绕过，扩到5家店时数据会串 |

### 1.3 核心决策

| 决策 | 理由 |
|------|------|
| 收银核心全部重写 | 旧系统7个CRITICAL漏洞+外包依赖+EOL技术栈 |
| 掌柜现有11个模块全部保留 | 排班/考勤/审批/订桌/存酒/KPI/工资/签收等已在运营中验证 |
| 模块化单体架构 | 一个FastAPI应用 + 一个PostgreSQL数据库，按模块隔离 |
| CRMEB临时过渡 | 旧CRMEB继续运营，新收银核心完成后切换 |
| 双跑并行，不停旧系统 | 降低切换风险 |
| 技术栈：FastAPI+PostgreSQL+Vue3+Uniapp+Kotlin | AI友好+RLS多租户+现代化 |

### 1.4 员工端保留的11个模块

以下模块为掌柜1期已完成代码，2.0全部保留，在此基础上开发收银模块：

| 模块 | 状态 |
|------|------|
| 排班管理 | 已有 |
| 考勤管理 | 已有（对接方式待定：企微考勤API vs 自建） |
| 审批流 | 已有 |
| 订桌管理 | 已有 |
| 存酒管理 | 已有（180天保质期） |
| KPI管理 | 已有 |
| 工资计算 | 已有（9角色提成逻辑） |
| 签收管理 | 已有（Canvas手写签名） |
| 企微OAuth登录 | 已有 |
| 企微消息推送 | 已有 |
| 商品/酒水管理 | 已有 |

---

## 二、系统架构

### 2.1 六端架构

```
Crush 2.0 完整系统
├── 第1端：员工端（企微自建应用）—— 已完成85%
│   ├── 日常Tab：收银台入口、存酒、订桌、商品浏览、游戏发起
│   ├── 管理Tab：排班、考勤、KPI、工资、看板、审批
│   ├── 设置Tab：门店配置、商品管理、规则设置
│   └── 我的Tab：个人数据
│
├── 第2端：收银端（收银台后台）—— 待开发
│   ├── 桌台管理、订单管理、商品管理
│   ├── 霸屏管理、数据统计
│   └── 系统设置（打印机、支付方式、小票模板）
│
├── 第3端：厨师端（厨房大屏）—— 待开发
│   ├── 订单队列（等待/制作/完成）
│   └── 出酒确认、认领机制
│
├── 第4端：智能桌灯端（Android APK）—— 待开发
│   ├── 纸条社交、呼叫服务
│   └── LED控制、游戏报名
│
├── 第5端：客人端（微信小程序）—— 待开发
│   ├── 扫码点单、存酒查询、历史订单
│   └── 游戏参与
│
└── 第6端：全国端（Web管理后台）—— 待开发
    ├── 全国看板、门店对比
    └── 加盟商管理、品牌配置
```

> **修正点**：游戏发起入口从收银端移到员工端日常Tab。收银端不做游戏功能。

### 2.2 技术栈

| 层 | 选型 | 版本 |
|----|------|------|
| 后端框架 | FastAPI (Python) | 3.12+ |
| ORM | SQLAlchemy async + asyncpg | 2.0 |
| 数据库 | PostgreSQL | 16 |
| 缓存/消息 | Redis | 7 |
| 前端框架 | Vue3 + Vite + TypeScript | 3.x |
| 移动端 | Uniapp (Vue3编译) | - |
| 桌灯端 | Kotlin + Android | - |
| 部署 | Docker Compose | - |
| 认证 | JWT + 企微OAuth | - |

### 2.3 目录结构

```
crush-2.0/
├── backend/                    # FastAPI后端
│   ├── app/
│   │   ├── api/
│   │   │   └── v1/            # 统一API版本（所有模块共享）
│   │   ├── models/
│   │   │   ├── shared/        # 共享基础表（门店/员工/会员）
│   │   │   ├── pos/           # 收银模块（订单/支付）
│   │   │   ├── wage/          # 工资模块
│   │   │   ├── att/           # 考勤模块
│   │   │   ├── game/          # 游戏模块
│   │   │   └── sys/           # 系统表
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── middleware/
│   │   └── utils/
│   ├── alembic/
│   └── requirements.txt
├── frontend/                   # 员工端（企微H5）
│   └── src/
├── frontend-cashier/           # 收银端（电脑浏览器）
│   └── src/
├── frontend-kitchen/           # 厨师端（大屏浏览器）
│   └── src/
├── frontend-admin/             # 全国端（电脑浏览器）
│   └── src/
├── miniprogram/                # 客人端（微信小程序）
│   └── pages/
├── desk-lamp/                  # 桌灯端（Android APK）
│   └── app/
├── docker-compose.yml
├── AGENTS.md
└── SPEC.md                     # 本文档
```

> **修正点**：API目录从 `v1/` + `v2/` 双版本改为统一 `v1/`。

### 2.4 智能桌灯APK通信方式

> **修正点**：架构评估文档说"3秒HTTP轮询"是不准确的。APK反编译分析确认实际已是WebSocket长连接。

| 项 | 现状 |
|----|------|
| 通信方式 | WebSocket长连接（非HTTP轮询） |
| 现有地址 | ws://182.92.153.92:8061/ws?type=game |
| 通信协议 | game_status/game_start/game_result/game_invite等消息字段 |
| LED控制 | 串口帧：ledARGB(颜色) + ledOnMS(亮时长) + ledOffMS(灭时长) |
| 重写理由 | 无源码（核心），不是费电/安全 |

### 2.5 企微多商户号收款方案

> **补充点**：SPEC v1.0遗漏了企微多商户号收款方案。

- 企微对外收款支持绑定多个微信支付商户号（无上限）
- 每个门店可申请独立商户号，绑独立营业执照+独立对公账户
- 商户号按员工分配使用范围，各店员工收款资金进各自门店绑定的公户
- 商户号营业执照可以跟企微主体不一致（但公户必须跟执照同主体）
- 员工企微加客人微信，通过企微发起收款，资金进该员工所属门店的商户号公户

```
北京跨时餐饮企微
├── 商户号A:北京跨时餐饮执照 → 北京跨时公户（北京三里屯店员工使用）
├── 商户号B:无锡分公司执照 → 无锡公户（无锡店员工使用）
├── 商户号C:哈尔滨分公司执照 → 哈尔滨公户（哈尔滨店员工使用）
└── 商户号D:加盟商执照 → 加盟商公户（加盟店员工使用）
```

---

## 三、数据库设计

### 3.1 表前缀规范

```
shared_*     共享基础表（门店/员工/会员/商品/桌台）
pos_*        收银模块（订单/支付/桌台会话/退单/对账/纸条）
wage_*       工资模块（合同/工资主表/明细/工资项配置/薪资规则/账期）
att_*        考勤模块（排班/打卡/审批/调班/假期余额）
hr_*         人力资源模块（KPI模板/评分/结果/申诉/业绩/排名/评价/罚单）
sig_*        签收模块
game_*       游戏模块
sys_*        系统表（配置/日志/审计）
```

### 3.2 通用规则

- 所有业务表都有 `store_id UUID NOT NULL`（系统表/全局字典除外）
- 所有业务表都启用 RLS 策略
- 所有表都有 `created_at` / `updated_at` 审计字段
- **主键统一用 UUID**（例外：sys_audit_logs 用 BIGSERIAL 自增，审计日志量大，自增性能优）
- 金额统一用 `NUMERIC(12,2)`

### 3.3 RLS策略（session变量方式）

> **修正点**：从is_brand_admin字段改为session变量方式。

```sql
-- 所有业务表统一用这个策略
ALTER TABLE {表名} ENABLE ROW LEVEL SECURITY;

-- 门店隔离策略
CREATE POLICY store_isolation ON {表名}
    USING (store_id = current_setting('app.current_store_id')::uuid);

-- 管理员角色豁免（可看所有店）
CREATE POLICY admin_all_access ON {表名}
    FOR ALL
    USING (
        current_setting('app.current_user_role', true) = 'admin'
    );
```

后端连接时设置：
```python
# 每个请求开始时设置session变量
await session.execute(text(f"SET LOCAL app.current_store_id = '{store_id}'"))
await session.execute(text(f"SET LOCAL app.current_user_role = '{role}'"))
```

### 3.4 完整建表脚本

#### 3.4.1 共享基础表（shared_*）

```sql
-- 门店表
CREATE TABLE shared_stores (
    store_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_code VARCHAR(32) UNIQUE NOT NULL,
    store_name VARCHAR(64) NOT NULL,
    franchisee_id UUID,
    region VARCHAR(32),
    address TEXT,
    phone VARCHAR(32),
    status VARCHAR(20) DEFAULT 'active',
    opened_at DATE,
    brand_fee_rate NUMERIC(5,4) DEFAULT 0.05,
    wecom_department_id INTEGER,
    wecom_corp_id VARCHAR(100),
    wecom_agent_id VARCHAR(20),
    wecom_secret TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 加盟商表
CREATE TABLE shared_franchisees (
    franchisee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(128) NOT NULL,
    contact_name VARCHAR(64),
    contact_phone VARCHAR(32),
    brand_fee_rate NUMERIC(5,4) DEFAULT 0.05,
    contract_start DATE,
    contract_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 员工表
CREATE TABLE shared_employees (
    employee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_code VARCHAR(20) UNIQUE NOT NULL,
    wecom_user_id VARCHAR(100) UNIQUE,
    name VARCHAR(64) NOT NULL,
    phone VARCHAR(32),
    role VARCHAR(32) NOT NULL,           -- admin/boss/store_manager/accountant/
                                        -- bar_manager/service_manager/kitchen_manager/staff
    department VARCHAR(32),             -- bar/water/kitchen/service/dj/finance/cleaner/coffee
    base_salary NUMERIC(12,2),
    hire_date DATE,
    status VARCHAR(16) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE shared_employees ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON shared_employees
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON shared_employees
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 会员表
CREATE TABLE shared_members (
    member_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    nickname VARCHAR(64),
    phone VARCHAR(32),
    openid VARCHAR(255),
    wecom_user_id VARCHAR(64),
    balance NUMERIC(12,2) DEFAULT 0,
    points INTEGER DEFAULT 0,
    growth INTEGER DEFAULT 0,
    level VARCHAR(20) DEFAULT 'silver',
    total_consumption NUMERIC(12,2) DEFAULT 0,
    status VARCHAR(16) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE shared_members ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON shared_members
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON shared_members
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 会员等级配置表
CREATE TABLE shared_member_levels (
    level_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    level_code VARCHAR(20) NOT NULL,
    level_name VARCHAR(50) NOT NULL,
    growth_threshold INTEGER NOT NULL,
    discount_rate NUMERIC(5,2) DEFAULT 1.00,
    benefits JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 商品分类表
CREATE TABLE shared_categories (
    category_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    parent_id UUID,
    name VARCHAR(100) NOT NULL,
    commission_rule VARCHAR(32) NOT NULL,  -- personal/department_avg/fixed
    department VARCHAR(32),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 商品表
CREATE TABLE shared_products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    category_id UUID REFERENCES shared_categories(category_id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(32),
    price NUMERIC(12,2) NOT NULL,
    cost_price NUMERIC(12,2),
    unit VARCHAR(16) DEFAULT '杯',
    image_url TEXT,
    description TEXT,
    stock INTEGER,
    stock_warn INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE shared_products ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON shared_products
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON shared_products
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 桌台表
CREATE TABLE shared_tables (
    table_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    table_no VARCHAR(16) NOT NULL,
    area VARCHAR(50) DEFAULT '大厅',
    capacity INTEGER DEFAULT 4,
    min_spend NUMERIC(10,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'idle',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, table_no)
);
ALTER TABLE shared_tables ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON shared_tables
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON shared_tables
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 设备注册表（桌灯/打印机等）
CREATE TABLE shared_devices (
    device_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    device_type VARCHAR(20) NOT NULL,     -- desk_lamp/printer/kitchen_display
    device_sn VARCHAR(100) UNIQUE,
    table_id UUID REFERENCES shared_tables(table_id),
    status VARCHAR(20) DEFAULT 'online',
    firmware_version VARCHAR(20),
    last_seen TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 门店配置表（平铺结构，v2.0 变更：原 KV 结构改为平铺字段以简化 ORM 映射）
-- 注：原 SPEC 设计为 KV 结构（config_key + config_value JSONB），
-- 实施时发现 KV 结构会破坏 ORM 属性访问（settings.rest_days_per_month），
-- 且增加读写复杂度。经评估改为平铺结构，每店一行，主键 id（UUID）。
-- 字段涵盖：排班规则、工资配置、合同默认、AI配置、打印机配置、群机器人等。
CREATE TABLE shared_store_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id) UNIQUE,
    -- 排班规则
    rest_days_per_month INTEGER DEFAULT 4,
    rest_allowed_weekdays TEXT,
    rest_forbidden_weekdays TEXT,
    max_same_position_off INTEGER DEFAULT 1,
    min_position_coverage_percent INTEGER DEFAULT 50,
    manager_order_constraint BOOLEAN DEFAULT TRUE,
    holiday_policy VARCHAR(20) DEFAULT 'comp_leave',
    auto_schedule_enabled BOOLEAN DEFAULT FALSE,
    schedule_lock_after_publish BOOLEAN DEFAULT TRUE,
    -- 工资配置
    payroll_day_of_month INTEGER DEFAULT 5,
    kpi_coefficient_min NUMERIC(3,2) DEFAULT 0.60,
    kpi_coefficient_max NUMERIC(3,2) DEFAULT 1.50,
    -- 合同默认配置
    contract_initiator_ids TEXT,
    contract_company_name VARCHAR(100),
    contract_company_phone VARCHAR(20),
    contract_company_address TEXT,
    contract_base_salary NUMERIC(12,2) DEFAULT 3000.00,
    contract_probation_months INTEGER DEFAULT 6,
    contract_notice_days INTEGER DEFAULT 45,
    contract_duration_years INTEGER DEFAULT 3,
    -- AI 小C 配置
    ai_api_url TEXT,
    ai_api_key TEXT,
    ai_model VARCHAR(100),
    ai_temperature NUMERIC(3,2) DEFAULT 0.70,
    -- 云打印机配置
    printer_enabled BOOLEAN DEFAULT FALSE,
    label_printer_enabled BOOLEAN DEFAULT FALSE,
    receipt_printer_enabled BOOLEAN DEFAULT FALSE,
    printer_brand VARCHAR(50),
    printer_api_url TEXT,
    printer_sn VARCHAR(100),
    printer_user VARCHAR(100),
    printer_ukey TEXT,
    printer_label_width INTEGER DEFAULT 80,
    printer_label_height INTEGER DEFAULT 50,
    -- 群机器人
    wecom_bot_enabled BOOLEAN DEFAULT FALSE,
    wecom_webhook_url TEXT,
    -- 扩展配置（未来新业务配置放这里，不用改表结构）
    extra_config JSONB DEFAULT '{}',
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3.4.2 收银模块表（pos_*）

```sql
-- 订单主表
CREATE TABLE pos_orders (
    order_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    order_sn VARCHAR(32) UNIQUE NOT NULL,
    table_id UUID REFERENCES shared_tables(table_id),
    table_no VARCHAR(16),
    member_id UUID REFERENCES shared_members(member_id),
    employee_id UUID NOT NULL,            -- 开台收银员
    guest_count INTEGER DEFAULT 1,
    status VARCHAR(16) NOT NULL DEFAULT 'open',
                                         -- open/paid/cancelled/transferred
    subtotal NUMERIC(12,2) DEFAULT 0,
    discount_amount NUMERIC(12,2) DEFAULT 0,
    free_amount NUMERIC(12,2) DEFAULT 0,
    total_amount NUMERIC(12,2) DEFAULT 0,
    paid_amount NUMERIC(12,2) DEFAULT 0,
    is_merge BOOLEAN DEFAULT FALSE,
    parent_order_id UUID,
    is_free BOOLEAN DEFAULT FALSE,
    free_reason TEXT,
    notes TEXT,
    created_by UUID NOT NULL,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_orders ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_orders
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_orders
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 订单明细表
CREATE TABLE pos_order_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    product_id UUID REFERENCES shared_products(product_id),
    product_name VARCHAR(100) NOT NULL,
    category VARCHAR(32),
    unit_price NUMERIC(12,2) NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    total_price NUMERIC(12,2) NOT NULL,
    kitchen_status VARCHAR(20) DEFAULT 'waiting',
                                         -- waiting/claimed/preparing/ready/served
    claimed_by UUID,                     -- 认领人（按件提成关键）
    claimed_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    served_at TIMESTAMPTZ,
    bar_employee_id UUID,               -- 出酒/制作归属员工（算佣金关键）
    is_add BOOLEAN DEFAULT FALSE,
    is_refund BOOLEAN DEFAULT FALSE,
    is_presented BOOLEAN DEFAULT FALSE,
    is_rush BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_order_items ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_order_items
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_order_items
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 支付记录表（支持拆分支付：一笔订单多条支付记录）
CREATE TABLE pos_payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    payment_method VARCHAR(20) NOT NULL,  -- wechat/cash/alipay/member/pos/enterprise_wecom
    amount NUMERIC(12,2) NOT NULL,
    transaction_id VARCHAR(100),
    wecom_txn_id VARCHAR(64),            -- 企微收款流水号
    employee_id UUID,                     -- 收款员工（企微收款归属）
    notes TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_payments ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_payments
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_payments
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 支付方式配置表
CREATE TABLE pos_payment_methods (
    method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 桌台会话表
CREATE TABLE pos_table_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    table_id UUID NOT NULL REFERENCES shared_tables(table_id),
    table_no VARCHAR(16) NOT NULL,
    order_id UUID REFERENCES pos_orders(order_id),
    opened_by UUID NOT NULL,
    opened_at TIMESTAMPTZ DEFAULT NOW(),
    closed_by UUID,
    closed_at TIMESTAMPTZ,
    guest_count INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'open',
    notes TEXT
);

-- 退单表（双镜复核）
CREATE TABLE pos_refunds (
    refund_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    item_id UUID,                         -- 退的是哪一项（可空=整单退）
    amount NUMERIC(12,2) NOT NULL,
    operator_id UUID NOT NULL,            -- 退单人（店长申请）
    confirmer_id UUID,                    -- 双镜复核人（boss或bar_manager）
    reason TEXT NOT NULL,
    status VARCHAR(16) DEFAULT 'pending', -- pending/confirmed/approved/rejected
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);
ALTER TABLE pos_refunds ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_refunds
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_refunds
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 免单/折扣审批表
CREATE TABLE pos_discount_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    type VARCHAR(16) NOT NULL,            -- free/discount
    amount NUMERIC(12,2) NOT NULL,
    operator_id UUID NOT NULL,            -- 申请收银员（店长申请）
    approver_id UUID,                     -- 审批人（boss审批）
    reason TEXT NOT NULL,
    status VARCHAR(16) DEFAULT 'pending', -- pending/approved/rejected
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);
ALTER TABLE pos_discount_approvals ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_discount_approvals
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_discount_approvals
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 会员余额流水表
CREATE TABLE pos_member_transactions (
    transaction_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    member_id UUID NOT NULL REFERENCES shared_members(member_id),
    type VARCHAR(20) NOT NULL,            -- recharge/consume/refund
    amount NUMERIC(12,2) NOT NULL,       -- 正数=充值，负数=消费
    balance_after NUMERIC(12,2) NOT NULL,
    order_id UUID,
    payment_method VARCHAR(20),
    operator_id UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_member_transactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_member_transactions
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_member_transactions
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 订单操作日志表
CREATE TABLE pos_order_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 每日对账表
CREATE TABLE pos_daily_reconciliations (
    reconciliation_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    date DATE NOT NULL,
    system_receivable NUMERIC(12,2),
    actual_pos NUMERIC(12,2),
    actual_cash NUMERIC(12,2),
    actual_wechat NUMERIC(12,2),
    actual_alipay NUMERIC(12,2),
    difference NUMERIC(12,2),
    difference_note TEXT,
    status VARCHAR(20) DEFAULT 'pending',
    reconciled_by UUID,
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 纸条社交表
CREATE TABLE pos_desk_notes (
    note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    from_table_id UUID NOT NULL,
    to_table_id UUID NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'sent',    -- sent/accepted/rejected
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_desk_notes ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON pos_desk_notes
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON pos_desk_notes
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');
```

#### 3.4.3 游戏模块表（game_*）

```sql
-- 游戏模板表
CREATE TABLE game_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100) NOT NULL,
    game_type VARCHAR(50) NOT NULL,
    description TEXT,
    min_participants INTEGER DEFAULT 2,
    max_participants INTEGER DEFAULT 10,
    rules JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 游戏会话表
CREATE TABLE game_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    template_id UUID REFERENCES game_templates(template_id),
    topic VARCHAR(200),
    status VARCHAR(20) DEFAULT 'waiting',
    max_participants INTEGER,
    current_participants INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    ended_at TIMESTAMPTZ,
    winner_id UUID,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE game_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY store_isolation ON game_sessions
    USING (store_id = current_setting('app.current_store_id')::uuid);
CREATE POLICY admin_all_access ON game_sessions
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 游戏参与者表
CREATE TABLE game_participants (
    participant_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(session_id),
    table_id UUID,
    member_id UUID,
    device_id UUID,
    choice VARCHAR(50),
    result VARCHAR(20),
    prize_claimed BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 游戏奖品表
CREATE TABLE game_prizes (
    prize_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(session_id),
    product_id UUID NOT NULL REFERENCES shared_products(product_id),
    product_name VARCHAR(100),
    quantity INTEGER DEFAULT 1,
    claimed_by UUID,
    claimed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3.4.4 系统配置表（sys_*）

```sql
-- 系统配置表
CREATE TABLE sys_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, config_key)
);

-- 审计日志表
CREATE TABLE sys_audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    store_id UUID,
    user_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    resource_type VARCHAR(50),
    resource_id UUID,
    details JSONB,
    ip_address VARCHAR(50),
    user_agent TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 打印机配置表
CREATE TABLE sys_printers (
    printer_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    name VARCHAR(50) NOT NULL,
    printer_type VARCHAR(20) DEFAULT 'order',  -- label=标签机, receipt=小票机, order=出单机
    brand VARCHAR(50),
    device_sn VARCHAR(100),
    api_url TEXT,
    api_key TEXT,
    api_user VARCHAR(100),
    api_secret TEXT,
    paper_width INTEGER DEFAULT 80,
    online_status BOOLEAN DEFAULT FALSE,
    last_heartbeat TIMESTAMPTZ,
    extra_config JSONB DEFAULT '{}',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 打印路由规则表
CREATE TABLE sys_print_routes (
    route_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    trigger_event VARCHAR(50) DEFAULT 'order_created',  -- order_created/payment_completed/manual
    document_type VARCHAR(50) DEFAULT 'order',  -- order/receipt/label
    filter_type VARCHAR(50) DEFAULT 'category',  -- category/product/order_type/all
    filter_value JSONB,  -- 匹配值：分类ID列表/商品ID列表
    printer_id UUID NOT NULL,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 打印任务队列表（故障转移+离线重试）
CREATE TABLE print_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    route_id UUID,
    printer_id UUID NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',  -- pending/printing/completed/failed
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    printed_at TIMESTAMPTZ
);
```

#### 3.4.5 考勤排班审批模块表（att_*）

> **v2.1 补充**：原SPEC标注"掌柜已有"，现补充完整表结构定义（8张表）。

```sql
-- 班次配置表
CREATE TABLE att_shift_configs (
    shift_config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    shift_code VARCHAR(20) NOT NULL,          -- day / night / custom1
    shift_name VARCHAR(20) NOT NULL,          -- 白班 / 晚班
    start_time VARCHAR(8) NOT NULL,           -- 12:00
    end_time VARCHAR(8) NOT NULL,             -- 20:00
    is_overnight BOOLEAN DEFAULT FALSE,
    color VARCHAR(8) DEFAULT '#FB0079',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, shift_code)
);

-- 考勤记录表（排班+打卡+判定一体）
CREATE TABLE att_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    date DATE NOT NULL,
    scheduled_shift VARCHAR(20),
    shift_start_time VARCHAR(8),
    shift_end_time VARCHAR(8),
    is_overnight BOOLEAN DEFAULT FALSE,
    clock_in TIMESTAMPTZ,
    clock_out TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'unknown',     -- normal/late/early/absent/leave/makeup/unknown
    late_minutes INTEGER DEFAULT 0,
    early_minutes INTEGER DEFAULT 0,
    source VARCHAR(20) DEFAULT 'manual',      -- manual/wecom/wifi_photo/makeup
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, date)
);

-- 排班表
CREATE TABLE att_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,           -- day / night / rest / leave
    note TEXT,
    created_by UUID,
    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, date)
);

-- 排班规则表
CREATE TABLE att_schedule_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    rule_type VARCHAR(50) NOT NULL,
    rule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 排班快照表
CREATE TABLE att_schedule_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    period VARCHAR(7) NOT NULL,                 -- YYYY-MM
    snapshot_data JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 调班申请表
CREATE TABLE att_swap_requests (
    swap_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    requester_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    swap_with_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    swap_date DATE NOT NULL,
    swap_shift VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending_swap_with', -- pending_swap_with/swap_with_confirmed/approved/rejected
    swap_with_confirmed_at TIMESTAMPTZ,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 审批申请表（请假/补卡/调班/报销统一）
CREATE TABLE att_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    type VARCHAR(20) NOT NULL,                  -- leave / makeup / swap / expense
    status VARCHAR(20) DEFAULT 'pending',       -- pending / approved / rejected
    start_date DATE,
    end_date DATE,
    reason TEXT,
    extra JSONB,                                -- 各类型自定义字段
    approver_id UUID,
    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 假期余额表
CREATE TABLE att_leave_balances (
    balance_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    year INTEGER NOT NULL,
    leave_type VARCHAR(20) NOT NULL,             -- comp_off / sick / personal / annual
    total_days NUMERIC(5,1) DEFAULT 0,
    used_days NUMERIC(5,1) DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, year, leave_type)
);
```

#### 3.4.6 工资合同模块表（wage_*）

> **v2.1 补充**：原SPEC标注"掌柜已有"，现补充完整表结构定义（8张表）。

```sql
-- 账期管理表
CREATE TABLE wage_periods (
    period_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    period VARCHAR(7) NOT NULL,                 -- YYYY-MM
    status VARCHAR(20) DEFAULT 'open',           -- open / locked / closed
    locked_at TIMESTAMPTZ,
    locked_by UUID,
    closed_at TIMESTAMPTZ,
    closed_by UUID,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, period)
);

-- 薪资矩阵表（岗位 x 档位）
CREATE TABLE wage_salary_matrix (
    matrix_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    position VARCHAR(30) NOT NULL,               -- 店长/吧员/服务员/厨师/保洁
    grade VARCHAR(20) NOT NULL,                  -- 学徒/正式/副职/正职
    monthly_salary NUMERIC(12,2) NOT NULL,
    base_salary NUMERIC(12,2) DEFAULT 3000.00,
    meal_allowance NUMERIC(12,2) DEFAULT 400.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, position, grade)
);

-- 劳动合同表
CREATE TABLE wage_contracts (
    contract_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    contract_no VARCHAR(50) UNIQUE NOT NULL,
    position VARCHAR(30) NOT NULL,
    grade VARCHAR(20) NOT NULL,
    monthly_salary NUMERIC(12,2) NOT NULL,
    base_salary NUMERIC(12,2) DEFAULT 3000.00,
    meal_allowance NUMERIC(12,2) DEFAULT 400.00,
    allowance NUMERIC(12,2) DEFAULT 0.00,
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'draft',          -- draft/pending_sign/signed/expired/terminated
    esign_flow_id VARCHAR(100),
    signed_at TIMESTAMPTZ,
    signed_by UUID,
    template_data JSONB,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 工资主表
CREATE TABLE wage_records (
    wage_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,                  -- YYYY-MM
    total_income NUMERIC(12,2) DEFAULT 0,
    total_deduction NUMERIC(12,2) DEFAULT 0,
    net_pay NUMERIC(12,2) DEFAULT 0,
    kpi_coefficient NUMERIC(5,2) DEFAULT 1.00,
    snapshot JSONB,
    status VARCHAR(20) DEFAULT 'draft',          -- draft / confirmed / paid
    generated_at TIMESTAMPTZ,
    finalized_at TIMESTAMPTZ,
    finalized_by UUID,
    paid_at TIMESTAMPTZ,
    paid_by UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, period)
);

-- 工资明细子表
CREATE TABLE wage_record_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    wage_id UUID NOT NULL REFERENCES wage_records(wage_id) ON DELETE CASCADE,
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(50) NOT NULL,
    item_type VARCHAR(20) NOT NULL,              -- income / deduction
    amount NUMERIC(12,2) DEFAULT 0,
    data_source VARCHAR(30) NOT NULL,            -- contract/attendance/performance/kpi/rule/manual
    sort_order INTEGER DEFAULT 0,
    detail JSONB
);

-- 工资项配置表（公式引擎核心）
CREATE TABLE wage_items_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(50) NOT NULL,
    item_type VARCHAR(20) NOT NULL,              -- income / deduction
    data_source VARCHAR(30) NOT NULL,
    formula JSONB,                               -- 公式AST（拖拽式可视化编辑器生成）
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, item_code)
);

-- 薪资规则表
CREATE TABLE wage_salary_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    rule_code VARCHAR(50) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(30) NOT NULL,              -- late_penalty/early_penalty/absent_penalty/bonus
    rule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, rule_code)
);

-- 企微收款同步表
CREATE TABLE wage_wework_payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    transaction_id VARCHAR(100) NOT NULL,
    employee_id UUID REFERENCES shared_employees(employee_id),
    table_session_id UUID,
    amount NUMERIC(12,2) NOT NULL,
    pay_time TIMESTAMPTZ NOT NULL,
    payer_name VARCHAR(100),
    payer_account VARCHAR(100),
    remark TEXT,
    raw_data JSONB,
    sync_status VARCHAR(20) DEFAULT 'synced',
    sync_error TEXT,
    is_settled BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, transaction_id)
);
```

#### 3.4.7 人力资源模块表（hr_*）

> **v2.1 补充**：KPI/绩效/排名/评价/罚单模块完整表结构定义（7张表）。

```sql
-- KPI 模板表（维度配置）
CREATE TABLE hr_kpi_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    role VARCHAR(30) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    dimension_label VARCHAR(50) NOT NULL,
    weight NUMERIC(5,2) NOT NULL,
    formula_type VARCHAR(30) DEFAULT 'ratio',
    formula_config JSONB DEFAULT '{}',
    data_source VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- KPI 维度评分表
CREATE TABLE hr_kpi_scores (
    score_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    dimension VARCHAR(50) NOT NULL,
    raw_value NUMERIC(12,2),
    raw_description TEXT,
    normalized_score NUMERIC(12,2) NOT NULL,
    weight NUMERIC(5,2) NOT NULL,
    weighted_score NUMERIC(12,2) NOT NULL,
    data_source VARCHAR(50),
    source_reference JSONB,
    calculated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, period, dimension)
);

-- KPI 汇总结果表
CREATE TABLE hr_kpi_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    total_score NUMERIC(12,2) NOT NULL,
    coefficient NUMERIC(5,2) DEFAULT 1.00,
    coefficient_reason TEXT,
    rank_in_store INTEGER,
    status VARCHAR(20) DEFAULT 'pending',
    confirmed_by UUID,
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, period)
);

-- KPI 申诉表
CREATE TABLE hr_kpi_appeals (
    appeal_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    result_id UUID NOT NULL REFERENCES hr_kpi_results(result_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    dimension VARCHAR(50),
    reason TEXT NOT NULL,
    evidence JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    reviewed_by UUID,
    resolution TEXT,
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 员工月度业绩汇总表
CREATE TABLE hr_performance (
    perf_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    performance_type VARCHAR(30) NOT NULL,        -- booking/wework_payment/bottle/card/manual
    total_amount NUMERIC(12,2) DEFAULT 0,
    detail_count INTEGER DEFAULT 0,
    source VARCHAR(20) DEFAULT 'auto',           -- auto / manual
    source_ref JSONB,
    calculated_at TIMESTAMPTZ,
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, employee_id, period, performance_type)
);

-- 员工排名表
CREATE TABLE hr_rankings (
    ranking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    rank_type VARCHAR(30) NOT NULL,               -- performance/kpi/attendance/rating
    rank_value NUMERIC(12,2) DEFAULT 0,
    rank_position INTEGER NOT NULL,
    detail TEXT,
    calculated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, employee_id, period, rank_type)
);

-- 客户评价表
CREATE TABLE hr_guest_ratings (
    rating_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID REFERENCES shared_employees(employee_id),
    table_no VARCHAR(16),
    food_quality INTEGER,
    food_speed INTEGER,
    drink_quality INTEGER,
    drink_speed INTEGER,
    service_attitude INTEGER,
    service_speed INTEGER,
    cleanliness INTEGER,
    overall_score NUMERIC(3,1) NOT NULL,
    comment TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

#### 3.4.8 工资申诉表（wage_disputes）

> **v2.1 新增**：工资异常处理流程所需表（1张表）。

```sql
-- 工资申诉表
CREATE TABLE wage_disputes (
    dispute_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    wage_id UUID NOT NULL REFERENCES wage_records(wage_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    dispute_type VARCHAR(20) NOT NULL,            -- less/more/wrong_formula/other
    original_amount NUMERIC(12,2),
    expected_amount NUMERIC(12,2),
    reason TEXT NOT NULL,
    evidence JSONB,
    status VARCHAR(20) DEFAULT 'pending',         -- pending/confirmed/rejected/adjusted
    resolution TEXT,
    adjusted_amount NUMERIC(12,2),
    adjusted_in_period VARCHAR(7),
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.5 表数量统计

| 模块 | 表数量 | 说明 |
|------|:---:|------|
| shared_* | 10 | 门店/加盟商/员工/会员/等级/分类/商品/桌台/设备/配置 |
| pos_* | 11 | 订单/明细/支付/支付方式/会话/退单/审批/流水/日志/对账/纸条 |
| att_* | 8 | 班次配置/考勤记录/排班/排班规则/排班快照/调班申请/审批/假期余额 |
| wage_* | 9 | 账期/薪资矩阵/合同/工资主表/工资明细/工资项配置/薪资规则/企微收款/工资申诉 |
| hr_* | 7 | KPI模板/KPI评分/KPI结果/KPI申诉/业绩/排名/客户评价 |
| game_* | 4 | 模板/会话/参与者/奖品 |
| sys_* | 5 | 配置/审计/打印机/路由规则/打印队列 |
| **合计** | **54** | 全部表（v2.1更新） |

---

## 四、API设计

### 4.1 API版本策略

> **修正点**：从双版本(v1+v2)改为统一版本。

```
/api/v1/*      统一API（所有模块共享，通过路径区分模块）
/ws/*          WebSocket（实时通信）
```

### 4.2 员工端API

| 模块 | 接口 | 说明 |
|------|------|------|
| 认证 | POST /api/v1/auth/wework/login | 企微OAuth登录 |
| 门店 | GET /api/v1/stores | 门店列表 |
| 员工 | GET/POST/PUT/DELETE /api/v1/employees | 员工CRUD |
| 商品 | GET/POST/PUT/DELETE /api/v1/products | 商品CRUD |
| 桌台 | GET/POST/PUT/DELETE /api/v1/tables | 桌台CRUD |
| 排班 | GET/POST/PUT/DELETE /api/v1/schedules | 排班CRUD |
| 考勤 | GET/POST /api/v1/attendance | 考勤管理 |
| 工资 | GET/POST /api/v1/payroll | 工资管理 |
| 审批 | GET/POST/PUT /api/v1/approvals | 审批管理 |
| 游戏 | GET/POST/PUT /api/v1/games | 游戏发起（日常Tab） |
| 存酒 | GET/POST /api/v1/wine-storage | 存酒管理 |
| 订桌 | GET/POST /api/v1/reservations | 订桌管理 |
| **打印机** | GET /api/v1/printers | 打印机列表 |
| | POST /api/v1/printers | 添加打印机 |
| | PUT /api/v1/printers/{id} | 更新打印机 |
| | DELETE /api/v1/printers/{id} | 删除打印机 |
| | POST /api/v1/printers/{id}/test | 测试打印 |
| | **POST /api/v1/printers/print** | **统一打印接口（自动路由）** |
| | POST /api/v1/printers/print/direct | 直接打印到指定打印机 |
| | GET/POST /api/v1/printers/routes | 路由规则管理 |
| | GET /api/v1/printers/categories | 分类打印机绑定 |
| | PUT /api/v1/printers/categories/{id}/printer | 更新分类绑定 |

### 4.3 收银端API

| 模块 | 接口 | 说明 |
|------|------|------|
| 订单 | POST /api/v1/orders | 创建订单 |
| | GET /api/v1/orders | 订单列表 |
| | GET /api/v1/orders/{id} | 订单详情 |
| | POST /api/v1/orders/{id}/items | 追加商品 |
| | POST /api/v1/orders/{id}/settle | 结账（支持拆分支付） |
| | POST /api/v1/orders/{id}/cancel | 取消订单 |
| | POST /api/v1/orders/{id}/transfer | 转桌 |
| 桌台 | GET /api/v1/tables | 桌台列表（含状态） |
| | POST /api/v1/tables/{id}/open | 开台 |
| | POST /api/v1/tables/{id}/close | 清台 |
| 厨房 | GET /api/v1/kitchen/orders | 厨房订单队列 |
| | POST /api/v1/kitchen/items/{id}/claim | 认领 |
| | POST /api/v1/kitchen/items/{id}/ready | 完成 |
| | POST /api/v1/kitchen/items/{id}/served | 上桌 |
| 支付 | GET /api/v1/payment-methods | 支付方式列表 |
| | POST /api/v1/payment-methods | 添加支付方式 |
| 退单 | POST /api/v1/refunds | 退单申请（店长） |
| | PUT /api/v1/refunds/{id}/confirm | 退单复核（boss/bar_manager） |
| 免单 | POST /api/v1/discount-approvals | 免单/折扣申请（店长） |
| | PUT /api/v1/discount-approvals/{id}/approve | 免单审批（boss） |
| 对账 | GET /api/v1/reconciliation/daily | 每日对账 |
| | POST /api/v1/reconciliation/submit | 提交实收 |
| 统计 | GET /api/v1/dashboard/today | 今日统计 |
| 霸屏 | POST /api/v1/overlay/broadcast | 霸屏推送 |
| 纸条 | GET/POST /api/v1/desk-notes | 纸条社交 |

### 4.4 打印机路由引擎（统一打印服务）

> **设计理念**：一次配置，全局调用。所有涉及打印的模块（收银台、存酒、取酒、厨房出单等）都通过统一接口调用，无需单独配置。

#### 路由优先级

```
1. 自定义路由规则（高级模式）→ 匹配则使用
   ↓ 未匹配
2. 分类绑定打印机（简单模式）→ 查找分类绑定的打印机
   ↓ 未绑定
3. 按打印机类型自动路由 → 找同类型第一台打印机
   ↓ 未找到
4. 提示"没有可用打印机"
```

#### 打印机类型

| 类型 | 代码 | 用途 | 典型场景 |
|------|------|------|----------|
| 出单机 | `order` | 厨房/吧台出单 | 订单创建时，餐食→厨房，酒水→吧台 |
| 小票机 | `receipt` | 客户收据 | 支付完成时打印小票 |
| 标签机 | `label` | 标签打印 | 存酒标签、商品标签 |

#### 支持的云打印机品牌

> **开发者注意**：各品牌的认证参数和调用方式不同，前端配置页面需根据品牌动态显示字段。

| 品牌 | 标识 | 认证参数 | API地址 | 签名方式 | 官方文档 |
|------|------|----------|---------|----------|----------|
| **易联云** | `yilianyun` | client_id, client_secret | api.10ss.net | OAuth2.0 Bearer Token | [文档](https://www.kancloud.cn/ly6886/oauth-api/3170299) |
| **飞鹅** | `feie` | user, ukey | api.feieyun.com | MD5(user+ukey+stime) | [文档](http://help.feieyun.com/document.php) |
| **芯烨** | `xpyun` | user, userKey | open.xpyun.net | SHA1(user+userKey+timestamp) | [文档](https://www.xpyun.net/open/index.html) |
| **佳博** | `gainscha` | memberCode, apiKey | api.poscom.cn | MD5(memberCode+apiKey+msgId+timestamp) | [文档](https://dev.poscom.cn/) |
| **映美云** | `jolimark` | app_id, app_key | open.jolimark.com | REST API | [文档](http://open.jolimark.com) |
| **中午云** | `zhongwu` | appid, appsecret, deviceid, devicesecret | api.zhongwuyun.com | MD5(appid+deviceid+timestamp+appsecret) | [文档](http://open.zhongwu.co/) |
| **优声云** | `ushengyun` | appId, appSecret, deviceid, devicesecret | api.ushengyun.com | MD5(appId+deviceid+timestamp+appSecret) | [文档](https://www.kancloud.cn/fage/us_api/content) |
| **快递100** | `kuaidi100` | key, secret | api.kuaidi100.com | MD5(key+secret+timestamp) | [文档](https://api.kuaidi100.com/document) |
| **365智能云** | `printcenter` | deviceNo, key | open.printcenter.cn:8080 | 无签名，直接传key | [文档](https://developer.aliyun.com/article/242257) |

#### 各品牌认证参数配置

> **前端配置页面**：根据选择的品牌，动态显示需要填写的字段。

```typescript
// 品牌配置字段映射
const brandFields = {
  yilianyun: ['client_id', 'client_secret'],           // 易联云
  feie: ['user', 'ukey'],                               // 飞鹅
  xpyun: ['user', 'userKey'],                           // 芯烨
  gainscha: ['memberCode', 'apiKey'],                   // 佳博
  jolimark: ['app_id', 'app_key'],                      // 映美云
  zhongwu: ['appid', 'appsecret', 'deviceid', 'devicesecret'],  // 中午云
  ushengyun: ['appId', 'appSecret', 'deviceid', 'devicesecret'], // 优声云
  kuaidi100: ['key', 'secret'],                         // 快递100
  printcenter: ['deviceNo', 'key'],                     // 365智能云
}
```

#### 调用方式

**方式一：根据分类自动路由（推荐）**

```typescript
// 任何模块都可以这样调用
await printersAPI.printByCategory({
  category_id: 'xxx',           // 商品分类ID
  content: '打印内容',
  document_type: 'order',       // order=出单 / receipt=收据 / label=标签
  trigger: 'order_created'      // order_created / payment_completed / manual
})
```

**方式二：直接打印到指定打印机**

```typescript
await printersAPI.printDirect({
  printer_id: 'xxx',
  content: '打印内容'
})
```

#### 故障转移机制

- 打印机离线 → 自动使用备用打印机
- 打印失败 → 自动加入队列，每30秒重试
- 重试3次仍失败 → 记录日志，可手动重打

#### 配置入口

**设置端 → 打印机管理**

- 打印机列表：添加/编辑/删除打印机
- 路由规则：高级自定义路由（按订单类型、时间段等）
- 分类绑定：简单模式，为每个分类指定打印机

#### 涉及打印的模块清单

> **开发者注意**：以下模块在开发时必须集成打印功能，调用统一打印接口。

| 模块 | 打印场景 | 文档类型 | 触发时机 | 说明 |
|------|----------|----------|----------|------|
| **收银台** | 订单小票 | `receipt` | `payment_completed` | 支付完成后打印客户收据 |
| **收银台** | 厨房/吧台出单 | `order` | `order_created` | 根据商品分类自动路由到对应打印机 |
| **存酒** | 存酒标签 | `label` | `order_created` | 存酒时打印标签贴在酒瓶上 |
| **取酒** | 取酒凭证 | `receipt` | `manual` | 取酒时打印取酒凭证 |
| **库存管理** | 盘点单 | `receipt` | `manual` | 盘点完成后打印盘点单 |
| **员工管理** | 签收单 | `receipt` | `manual` | 工资条/处罚通知等签收打印 |
| **订桌** | 预订确认 | `receipt` | `manual` | 预订成功后打印确认单 |

#### AI开发检查清单

> **AI开发者必读**：开发新模块时，必须检查是否涉及打印场景。

```markdown
## 打印功能检查清单

开发新模块时，请逐项检查：

- [ ] 该模块是否有需要打印的场景？
- [ ] 打印时机是什么？（订单创建/支付完成/手动）
- [ ] 文档类型是什么？（出单/收据/标签）
- [ ] 是否需要根据商品分类路由到不同打印机？
- [ ] 是否调用了统一打印接口 `printersAPI.printByCategory`？
- [ ] 是否处理了打印失败的情况？

## 调用模板

// 订单类打印（出单）
await printersAPI.printByCategory({
  category_id: item.category_id,
  content: generateOrderContent(item),
  document_type: 'order',
  trigger: 'order_created'
})

// 收据类打印（小票）
await printersAPI.printByCategory({
  category_id: order.items[0].category_id,
  content: generateReceipt(order),
  document_type: 'receipt',
  trigger: 'payment_completed'
})

// 标签类打印
await printersAPI.printByCategory({
  category_id: item.category_id,
  content: generateLabel(item),
  document_type: 'label',
  trigger: 'order_created'
})
```

---

### 4.5 WebSocket通道

| 通道 | 说明 |
|------|------|
| /ws/cashier | 收银端（多平板同步） |
| /ws/kitchen | 厨师端（订单推送） |
| /ws/desk-lamp | 桌灯端（呼叫服务、订单提醒、游戏报名） |
| /ws/game | 游戏控台（霸屏推送、游戏状态同步） |

### 4.6 收件箱消息系统（统一推送服务）

> **v2.2 新增**：所有推送到员工首页收件箱的消息，统一走 `send_to_inbox()` 入口。

#### 设计理念

类似打印机路由引擎（4.4），收件箱也是"一次定义，全局调用"。所有需要员工签收的消息（工资单、考勤确认单、处罚通知等）都通过统一入口推送，类型集中在注册表管理。

#### 类型注册表

所有收件箱消息类型在 `backend/app/services/inbox_types.py` 集中定义：

| 类型代码 | 中文名 | 标题模板 | 关联表 | 卡片颜色 |
|---------|--------|---------|--------|---------|
| `salary_slip` | 工资单 | `{period}年工资单 - {employee_name}` | wage_record | 粉色 #FB0079 |
| `attendance_confirm` | 考勤确认单 | `{period}考勤确认单 - {employee_name}` | attendance | 蓝色 #3B82F6 |
| `penalty_notice` | 处罚通知 | `{category}通知 - {penalty_label}` | penalty_notice | 红色 #EF4444 |

> 新增类型时只需在 `INBOX_TYPES` 字典里加一条，不用改调用代码。

#### 标准调用模板

```python
from app.services.sign_task import SignTaskService
from app.services.inbox_types import InboxType

sign_service = SignTaskService(session, store_id)

# 单条推送
await sign_service.send_to_inbox(
    employee_id=员工ID,
    msg_type=InboxType.SALARY_SLIP,   # 类型代码
    ref_id=关联记录ID,                  # 工资单ID/考勤ID/罚单ID
    issued_by=发送人员工ID,
    extra={                            # 填充标题模板 + 详情页展示
        "period": "2026-07",
        "employee_name": "张吧员",
        "net_pay": 3250.00,
    },
)

# 批量推送（一个员工一条）
await sign_service.send_batch_to_inbox(
    employee_ids=[emp1, emp2, emp3],
    msg_type=InboxType.ATTENDANCE_CONFIRM,
    ref_ids=[ref1, ref2, ref3],
    issued_by=boss_id,
    extra_list=[
        {"period": "2026-07", "employee_name": "张吧员"},
        {"period": "2026-07", "employee_name": "李服务员"},
        {"period": "2026-07", "employee_name": "王厨师"},
    ],
)
```

#### 已接入的调用点

| 模块 | 文件 | 类型 |
|------|------|------|
| 工资单发送 | `api/v1/payroll.py` | salary_slip |
| 处罚通知发送 | `services/penalty.py` | penalty_notice |
| 考勤确认单发送 | `tasks/notification_jobs.py` | attendance_confirm |

#### AI开发检查清单

```markdown
## 收件箱推送检查清单

开发新功能时，如果需要推消息给员工签收，请逐项检查：

- [ ] 消息类型是否已在 inbox_types.py 注册？
- [ ] 是否调用了 sign_service.send_to_inbox()？
- [ ] extra 里是否包含标题模板所需的所有占位字段？
- [ ] ref_id 是否指向正确的业务记录？
```

---

## 四-B、统一模块自查清单

> **v2.2 新增**：代码库自查发现的重复/散落模式，按优先级排列。

### 4B.1 待统一模块总览

| # | 模块 | 是否统一 | 优先级 | 问题 |
|---|------|:-------:|:------:|------|
| 1 | 收件箱消息 | ✅ 已统一 | — | v2.2已完成，见4.6节 |
| 2 | 打印机路由 | ✅ 已统一 | — | 见4.4节 |
| 3 | 通知推送 | ❌ 两套并存 | 高 | wecom_notify.py 旧代码未删 |
| 4 | 审批流 | ❌ 部分统一 | 高 | 退单/申诉未走ApprovalService |
| 5 | 审计日志 | ❌ 模型重复 | 中 | 两个AuditLog类映射同表 |
| 6 | 分页 | ❌ 工具有但没人用 | 中 | 10+个Repository手写分页 |
| 7 | 门店配置读取 | ❌ 无缓存 | 低 | 13+处每次直查数据库 |

### 4B.2 通知推送（优先级：高）

**现状**：`NotificationService` 已建为统一入口，但旧的 `wecom_notify.py` 未删除，`notifications.py` 仍走旧路径。

| 文件 | 状态 |
|------|------|
| `services/notification_service.py` | ✅ 统一入口（send/send_alert/send_group_text） |
| `services/wecom_notify.py` | ❌ 旧实现，应删除 |
| `api/v1/notifications.py:240` | ❌ 仍调旧 `send_to_group` |

**建议**：删除 `wecom_notify.py`，`notifications.py` 改调 `NotificationService.send_group_text`。

### 4B.3 审批流（优先级：高）

**现状**：请假/补卡/调班/报销已统一走 `ApprovalService`，但退单/免单/工资申诉各自实现审批状态机。

| 文件 | 状态 |
|------|------|
| `services/approval_service.py` | ✅ 统一审批引擎（leave/makeup/swap/expense） |
| `api/v1/disputes.py` | ❌ 自带 confirm/reject/adjust，未走统一引擎 |

**建议**：`disputes` 的审批收敛进 `ApprovalService`，新增 `dispute` 类型。

### 4B.4 审计日志（优先级：中）

**现状**：SQLAlchemy 事件切面已统一，但有两个 `AuditLog` 模型映射同一张表，字段名不一致。

| 文件 | 字段名 |
|------|--------|
| `utils/audit_logger.py` | entity_type / entity_id / old_value / new_value |
| `models/audit.py` | entity_type / entity_id / old_value / new_value |
| `models/sys.py:33` | resource_type / resource_id / details（❌ 冲突） |

**建议**：删除 `models/audit.py` 或 `models/sys.py` 中的一个 AuditLog，保留与 `audit_logger.py` 一致的那版。

### 4B.5 分页（优先级：中）

**现状**：`utils/pagination.py` 提供了 `paginate_query()` 工具，但只有 `booking.py` 在用，其余 10+ 个 Repository 手写 count + offset + limit。

**建议**：所有 Repository 列表查询统一改调 `paginate_query(session, stmt, params)`。

### 4B.6 门店配置读取（优先级：低）

**现状**：13+ 处各自 `select(StoreSettings).where(store_id==...)` 直查数据库，无缓存，同一请求内可能重复查同一行。

**建议**：增加 `get_store_settings_cached(store_id)`（基于 request-scoped 缓存），所有读取改为调它。

---

## 四-A、工资计算流程与公式引擎

> **v2.1 新增**：工资自动化计算完整流程设计。

### 4A.1 工资计算数据流

```
合同 (wage_contracts) ──→ _get_contract_data() 取最新 signed 合同
    ↓                      monthly_salary / base_salary / meal_allowance
打卡 (att_records)    ──→ _get_attendance_data() SQL 聚合
    ↓                      late_count / total_late_minutes / absent_count
审批 (att_approvals)  ──→ _apply_approval() 改写 att_records
    ↓                      请假→不参与缺勤 / 补卡→改写打卡
业绩 (hr_performance) ──→ performance_service 取业绩数据
KPI (hr_kpi_results)  ──→ _get_kpi_data() 取系数(0.60~1.50)
    ↓
公式引擎 (PayrollEngine)
    ↓ evaluate(formula_ast) 逐项计算
工资表 (wage_records + wage_record_items)
    → 老板确认 → 推送企微工资条 → 员工签收
```

### 4A.2 工资公式引擎（PayrollEngine）

#### 公式AST格式

工资项配置表 `wage_items_config.formula` 使用 JSON AST 存储公式，由前端拖拽式可视化编辑器生成：

```json
{
  "type": "binary",
  "op": "*",
  "left": {
    "type": "variable",
    "source": "contract",
    "field": "base_salary",
    "label": "底薪"
  },
  "right": {
    "type": "variable",
    "source": "kpi",
    "field": "coefficient",
    "label": "KPI系数"
  }
}
```

#### 支持的数据源（变量）

| 数据源 | 变量 | 说明 |
|--------|------|------|
| contract | monthly_salary | 月薪 |
| contract | base_salary | 基本工资 |
| contract | meal_allowance | 餐补 |
| contract | allowance | 津贴 |
| attendance | present_days | 出勤天数 |
| attendance | total_days | 应出勤天数 |
| attendance | late_count | 迟到次数 |
| attendance | total_late_minutes | 迟到总分钟 |
| attendance | absent_count | 缺勤天数 |
| attendance | early_count | 早退次数 |
| attendance | total_early_minutes | 早退总分钟 |
| performance | wework_payment | 企微收款业绩 |
| performance | booking | 订桌业绩 |
| performance | bottle | 瓶装酒业绩 |
| performance | card | 开卡业绩 |
| kpi | coefficient | KPI系数(0.60~1.50) |
| kpi | total_score | KPI总分 |

#### 支持的运算符与函数

| 类型 | 名称 | 说明 |
|------|------|------|
| 运算符 | +, -, *, / | 四则运算 |
| 函数 | IF(cond, a, b) | 条件判断 |
| 函数 | ROUND(x, n) | 四舍五入 |
| 函数 | MAX(a, b) | 取最大值 |
| 函数 | MIN(a, b) | 取最小值 |
| 函数 | FLOOR(x) | 向下取整 |
| 函数 | CEIL(x) | 向上取整 |
| 常量 | 数字 | 固定数值 |

#### 预设公式模板

| 模板名称 | 公式 |
|----------|------|
| 底薪计算 | 底薪 × KPI系数 × (出勤天数/应出勤天数) |
| 餐补 | 餐补 × (出勤天数/应出勤天数) |
| 企微提成 | 企微收款业绩 × 提成比例 |
| 订桌提成 | 订桌业绩 × 提成比例 |
| 瓶装提成 | 瓶装酒业绩 × 提成比例 |
| 迟到扣款 | 迟到总分钟 × 每分钟单价 |
| 缺勤扣款 | 缺勤天数 × 日薪 |
| 早退扣款 | 早退总分钟 × 每分钟单价 |

### 4A.3 薪资规则时间线（可配置）

> **v2.1 新增**：自动化流程时间线，每个步骤可开关、日期可自定义。

以5号发薪日为例的6步流程：

| # | 步骤 | 默认日期 | 可关闭 | 说明 |
|---|------|---------|--------|------|
| 1 | 考勤锁定 | 每月2日 | ✅ | 锁定上月考勤，不再接受补卡 |
| 2 | KPI评分截止 | 每月3日 | ✅ | 店长完成上月员工KPI评分（不用KPI可关） |
| 3 | 业绩确认截止 | 每月3日 | ✅ | 业绩数据录入截止（无业绩可关） |
| 4 | 自动生成工资 | 每月4日 | ✅ | 系统自动计算工资草稿 |
| 5 | 老板审核 | 4日~发薪日 | ❌ 固定 | 老板检查确认工资（不可关闭） |
| 6 | 发薪日 | 每月5日 | ❌ 固定 | 推送工资条给员工，锁定账期（不可关闭） |

#### 薪资规则配置表（wage_salary_rules）

规则存储在 `rule_config` JSONB 字段中：

```json
{
  "day_of_month": 5,
  "is_enabled": true,
  "description": "每月5日发放工资"
}
```

#### 规则类型（rule_code）

| rule_code | 说明 | 默认值 |
|-----------|------|--------|
| pay_day | 发薪日 | 每月5日 |
| auto_generate | 自动生成工资 | 提前1天 |
| attendance_lock | 考勤锁定 | 每月2日 |
| auto_lock_period | 自动锁定账期 | 开启 |
| kpi_deadline | KPI评分截止 | 每月3日 |
| late_penalty_rate | 迟到每分钟扣款 | 2元/分钟 |
| early_penalty_rate | 早退每分钟扣款 | 2元/分钟 |
| absent_penalty_rate | 缺勤每日扣款 | 日薪 |

### 4A.4 工资状态流转

```
draft（草稿）
  ↓ 老板确认
confirmed（已确认）
  ↓ 发放工资
paid（已发放）
  ↓ 员工发现异常
disputed（有申诉）→ 老板核实 → adjusted（已调整）→ 差额并入下月工资
```

### 4A.5 工资异常处理流程

> **v2.1 新增**：员工对工资有异议时的处理流程。

#### 流程步骤

```
1. 员工查看工资条 → 发现异常
2. 在员工端提交工资申诉（选择类型：少发/多发/公式错误/其他）
3. 填写申诉原因 + 期望金额 + 上传证据
4. 老板/店长在管理端收到申诉通知
5. 核查原始数据（考勤/合同/KPI/业绩）
6. 确认有误 → 修改工资 → 差额并入下月工资
   确认无误 → 驳回申诉 → 说明原因
7. 员工收到处理结果通知
```

#### 申诉类型（dispute_type）

| 类型 | 说明 | 处理方式 |
|------|------|---------|
| less | 少发了 | 补发差额到下月工资 |
| more | 多发了 | 从下月工资扣回差额 |
| wrong_formula | 公式算错 | 修改公式 → 重新计算 → 补发/扣回 |
| other | 其他 | 人工协商处理 |

#### 申诉状态（status）

| 状态 | 说明 |
|------|------|
| pending | 待处理 |
| confirmed | 已确认有误 |
| rejected | 已驳回 |
| adjusted | 已调整（差额已并入工资） |

#### 权限规则

| 操作 | 角色 |
|------|------|
| 提交申诉 | 员工（仅限自己的工资） |
| 查看申诉 | boss / store_manager |
| 处理申诉 | boss |
| 修改工资 | boss |

---

## 五、权限模型

### 5.1 角色体系（8个角色）

> **修正点**：从7角色(cashier/bartender等岗位名称)改为8角色(管理层级名称)，去掉brand_admin，新增admin。

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

### 5.2 多门店归属方案

> **修正点**：不需要单独的franchisee角色，通过企微部门多归属解决。

- 企微组织架构：Crush品牌（一级）→ 各门店（二级部门）
- 一个wecom_user_id可以关联多个store_id（shared_employees多条记录）
- 通过企微API获取用户部门列表，自动确定可见门店
- boss角色可以看到自己所属的所有门店数据

### 5.3 权限矩阵

| 操作 | admin | boss | store_manager | accountant | bar_manager | service_manager | kitchen_manager | staff |
|------|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 开台/点单/加单/结账 | ✓ | ✓ | ✓ | -- | -- | -- | -- | ✓ |
| 出酒状态切换 | ✓ | ✓ | -- | -- | ✓ | -- | -- | ✓ |
| 退菜/退款申请 | ✓ | ✓ | ✓ | -- | -- | -- | -- | -- |
| 退菜/退款复核 | ✓ | ✓ | -- | -- | ✓ | -- | -- | -- |
| 免单/折扣/改价申请 | ✓ | ✓ | ✓ | -- | -- | -- | -- | -- |
| 免单/折扣/改价审批 | ✓ | ✓ | -- | -- | -- | -- | -- | -- |
| 查看本店历史订单 | ✓ | ✓ | ✓ | -- | -- | -- | -- | 自己班次 |
| 查看营收报表 | 全国 | 本店 | 本店 | 本店 | -- | -- | -- | -- |
| 门店配置 | ✓ | ✓ | ✓ | -- | -- | -- | -- | -- |
| 菜单管理 | ✓ | ✓ | ✓ | -- | -- | -- | -- | -- |
| 员工管理 | ✓ | ✓ | -- | -- | -- | -- | -- | -- |
| 系统配置 | ✓ | ✓ | -- | -- | -- | -- | -- | -- |
| 工资计算/确认 | ✓ | ✓ | -- | ✓ | -- | -- | -- | -- |
| 老板看板 | ✓ | ✓ | -- | -- | -- | -- | -- | -- |
| 阳光运营看板 | ✓ | ✓ | -- | -- | -- | -- | -- | -- |
| 游戏发起 | ✓ | ✓ | ✓ | -- | -- | -- | -- | ✓ |
| 签收 | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**关键规则**：
1. 退单：店长申请 + boss或bar_manager复核（双镜，申请与复核必须不同人）
2. 免单/折扣/改价：店长申请 + boss审批（店长不能自审）
3. admin可看全国，boss看本店（或通过企微部门多归属看多家店）

### 5.4 四Tab权限

| Tab | 可见角色 | 模块 |
|-----|----------|------|
| 日常 | 全员 | 收银台入口、存酒、订桌、商品浏览、**游戏发起** |
| 管理 | 店长及以上 | 排班、考勤、KPI、工资、看板、审批 |
| 设置 | boss/admin | 门店配置、商品管理、规则设置 |
| 我的 | 全员 | 个人排班、考勤、KPI、工资、合同 |

### 5.5 工资保密规则

| 角色 | 可看内容 |
|------|----------|
| admin | 全国工资汇总 |
| boss | 本店工资明细 |
| store_manager | 本店工资汇总（不含明细） |
| 员工 | 只看自己的工资 |

---

## 六、开发计划

### 6.1 总体计划

| 阶段 | 端口 | 时间 | 目标 |
|------|------|------|------|
| 第1阶段 | 员工端完善 | 第1-2周 | 游戏模块、商品管理 |
| 第2阶段 | 收银端 | 第3-12周 | 桌台、订单、商品、统计 |
| 第3阶段 | 厨师端 | 第13-14周 | 订单队列、出酒确认 |
| 第4阶段 | 桌灯端 | 第15-18周 | 纸条、呼叫、LED |
| 第5阶段 | 客人端 | 第19-22周 | 扫码点单、存酒查询 |
| 第6阶段 | 全国端 | 第23-26周 | 全国看板、加盟商管理 |

### 6.2 收银端详细计划

| 周次 | 模块 | 功能 |
|------|------|------|
| 第3周 | 骨架 | 登录、菜单、权限、桌台管理 |
| 第4周 | 商品管理 | 商品CRUD、分类、规格 |
| 第5周 | 订单管理 | 创建订单、追加商品、订单列表 |
| 第6周 | 结账功能 | 结账、拆分支付、小票打印 |
| 第7周 | 桌台操作 | 转桌、拼桌、免单、折扣 |
| 第8周 | 厨房状态 | 认领、完成、出餐时间统计 |
| 第9周 | 退单/审批 | 退单双镜复核、免单审批 |
| 第10周 | 霸屏管理 | 活动推送、游戏画面 |
| 第11周 | 数据统计 | 营收、客流、热销商品 |
| 第12周 | 系统设置 | 打印机、支付方式配置 |

### 6.3 数据迁移计划

> **补充点**：CRMEB临时过渡方案。

| 阶段 | 内容 | 时机 |
|------|------|------|
| 第1步 | 开发收银端功能 | 第3-12周 |
| 第2步 | 灰度测试（白班） | 第13周 |
| 第3步 | 编写迁移脚本 | 第14周 |
| 第4步 | 全量迁移数据（19张P0表） | 第15周 |
| 第5步 | 正式切换（夜班） | 第16周 |

**过渡策略**：
- CRMEB（运营中）→ 新收银核心（最终）
- 旧CRMEB在新收银核心完全开发完成前继续在生产环境运营
- 所有开发在本地进行，不涉及实际运营
- 迁移范围：P0必迁19张表，P1选迁3张，P2不迁106张

---

## 七、技术规范

### 7.1 代码规范

- Python：遵循PEP8，使用type hints
- TypeScript：遵循ESLint + Prettier
- 命名：snake_case（Python）、camelCase（TypeScript）
- 注释：关键逻辑必须注释

### 7.2 API规范

```json
{
  "code": 0,
  "message": "ok",
  "data": {...},
  "request_id": "uuid"
}
```

- 成功 code=0
- 业务错误 code=4xxxx
- 服务异常 code=5xxxx

### 7.3 Git规范

```
main (生产分支)
  ↑
develop (开发分支)
  ↑
feat/xxx (功能分支)
```

---

## 八、关键设计决策汇总

| 决策 | 内容 |
|------|------|
| 订单状态 | **open → paid / cancelled / transferred** |
| 厨房状态 | **waiting → claimed → preparing → ready → served** |
| 支付方式 | 后台自定义添加，支持**拆分支付** |
| 会员等级 | 白银/黄金/白金/黑金（季度保级制） |
| 游戏平台化 | 游戏模板+游戏实例 |
| 游戏入口 | **员工端日常Tab** |
| 数据迁移 | 先开发后迁移，P0必迁19张表 |
| 主键 | **全部UUID**（sys_audit_logs 例外用 BIGSERIAL 自增） |
| 多租户隔离 | **应用层+PostgreSQL RLS双层隔离** |
| RLS豁免 | **session变量(current_setting('app.current_user_role'))** |
| 架构 | **模块化单体** |
| API版本 | **统一/api/v1/** |
| ORM | **SQLAlchemy async** |
| 表前缀 | shared_/pos_/wage_/att_/sig_/game_/sys_ |
| 角色体系 | **8角色：admin/boss/store_manager/accountant/bar_manager/service_manager/kitchen_manager/staff** |
| 品牌管理员 | **admin角色看全国，不需要单独brand_admin** |
| 加盟商 | **不需要franchisee，企微部门多归属解决** |

---

## 九、验收标准

### 9.1 员工端验收

- [ ] 游戏模块：发起游戏、管理参与者、发放奖品（日常Tab）
- [ ] 商品管理：新增商品、修改价格、管理分类
- [ ] 所有API正常响应
- [ ] 所有页面正常显示

### 9.2 收银端验收

- [ ] 桌台管理：开台、清台、转桌、拼桌
- [ ] 订单管理：创建订单、追加商品、结账
- [ ] 拆分支付：一笔订单多种支付方式
- [ ] 厨房状态：认领、完成、出餐时间统计
- [ ] 退单双镜复核：店长申请 + boss/bar_manager复核
- [ ] 免单审批：店长申请 + boss审批
- [ ] 数据统计：营收、客流、热销商品
- [ ] 系统设置：打印机、支付方式配置

### 9.3 数据迁移验收

- [ ] 订单数据完整迁移（19,342条）
- [ ] 商品数据完整迁移（347条）
- [ ] 会员数据完整迁移（22,216条）
- [ ] 会员余额逐人对账（22,216人）
- [ ] 桌台数据完整迁移（82条）
- [ ] 数据一致性校验通过

---

## 十、附录

### 10.1 参考文档

- Crush-POS-数据库分析报告.md（131张表分析）
- Crush-POS-CodeReview-2026-06-21.docx（7个CRITICAL漏洞）
- Crush掌柜-2.0-整体架构方案.md（五端架构+技术选型）
- Crush-2.0-全部重写架构评估.md（118人天工作量估算）
- Crush-2.0-思想对齐记录.md（决策记录）
- Crush-2.0-数据库结构设计-D方案.md（19张核心表）
- Crush-2.0-旧库迁移风险分析.md（迁移风险评估）
- Crush-2.0-智能桌灯APK反编译分析.md（APK结构分析）
- Crush-2.0-系统重建分析与建议.md（三条路径对比）
- Crush-2.0-长期运行策略与开发计划.md（16周计划）

### 10.2 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| 1.0 | 2026-06-22 | 初版 |
| 2.0 | 2026-06-22 | 修正版：修正30个矛盾点+补充13项遗漏 |
| 2.1 | 2026-06-24 | 补充att_*/wage_*/hr_*完整表结构（24张）、工资公式引擎、薪资规则时间线（6步可配置）、工资异常处理流程、工资申诉表 |
