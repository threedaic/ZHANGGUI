# Crush 2.0 系统规范文档（SPEC）

> 日期：2026-06-22 | 版本：2.0 | 状态：修正版
>
> 修正说明：基于完整阅读全部12份项目文档后，对比v1.0发现30个矛盾点和13项遗漏，经逐条确认后修正。

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
wage_*       工资模块
att_*        考勤模块
sig_*        签收模块
game_*       游戏模块
sys_*        系统表（配置/日志/审计）
```

### 3.2 通用规则

- 所有业务表都有 `store_id UUID NOT NULL`（系统表/全局字典除外）
- 所有业务表都启用 RLS 策略
- 所有表都有 `created_at` / `updated_at` 审计字段
- **主键统一用 UUID**
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
        current_setting('app.current_role', true) = 'admin'
    );
```

后端连接时设置：
```python
# 每个请求开始时设置session变量
await session.execute(text(f"SET LOCAL app.current_store_id = '{store_id}'"))
await session.execute(text(f"SET LOCAL app.current_role = '{role}'"))
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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');

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
    USING (current_setting('app.current_role', true) = 'admin');
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
    USING (current_setting('app.current_role', true) = 'admin');

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
    brand VARCHAR(50),
    device_sn VARCHAR(100),
    api_url TEXT,
    api_key TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 3.5 表数量统计

| 模块 | 表数量 | 说明 |
|------|:---:|------|
| shared_* | 9 | 门店/加盟商/员工/会员/等级/分类/商品/桌台/设备/配置 |
| pos_* | 10 | 订单/明细/支付/支付方式/会话/退单/审批/流水/日志/对账/纸条 |
| game_* | 4 | 模板/会话/参与者/奖品 |
| sys_* | 3 | 配置/审计/打印机 |
| **合计** | **26** | 不含掌柜已有的wage_*/att_*/sig_*/app_* |

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

### 4.4 WebSocket通道

| 通道 | 说明 |
|------|------|
| /ws/cashier | 收银端（多平板同步） |
| /ws/kitchen | 厨师端（订单推送） |
| /ws/desk-lamp | 桌灯端（呼叫服务、订单提醒、游戏报名） |
| /ws/game | 游戏控台（霸屏推送、游戏状态同步） |

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
| 主键 | **全部UUID** |
| 多租户隔离 | **应用层+PostgreSQL RLS双层隔离** |
| RLS豁免 | **session变量(current_setting('app.current_role'))** |
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
