-- ===========================================================================
-- Crush 2.0 数据�?Schema 建表脚本�?6张表�?-- 依据：SPEC 2.0 第三�?-- 通用规则�?--   * 所有业务表�?store_id UUID NOT NULL（系统表/全局字典除外�?--   * 所有业务表启用 RLS 策略（session 变量方式�?--   * 所有表�?created_at / updated_at 审计字段
--   * 主键统一 UUID
--   * 金额统一 NUMERIC(12,2)
-- ===========================================================================

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS "pgcrypto";   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- updated_at 自动更新触发器函�?CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================================================
-- 一、共享基础�?shared_*�?张）
-- ===========================================================================

-- 1. 门店�?CREATE TABLE IF NOT EXISTS shared_stores (
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
DROP TRIGGER IF EXISTS trg_shared_stores_updated ON shared_stores;
CREATE TRIGGER trg_shared_stores_updated BEFORE UPDATE ON shared_stores
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 2. 加盟商表
CREATE TABLE IF NOT EXISTS shared_franchisees (
    franchisee_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    company_name VARCHAR(128) NOT NULL,
    contact_name VARCHAR(64),
    contact_phone VARCHAR(32),
    brand_fee_rate NUMERIC(5,4) DEFAULT 0.05,
    contract_start DATE,
    contract_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 3. 员工�?CREATE TABLE IF NOT EXISTS shared_employees (
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
DROP TRIGGER IF EXISTS trg_shared_employees_updated ON shared_employees;
CREATE TRIGGER trg_shared_employees_updated BEFORE UPDATE ON shared_employees
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE shared_employees ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON shared_employees;
CREATE POLICY store_isolation ON shared_employees
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON shared_employees;
CREATE POLICY admin_all_access ON shared_employees
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 4. 会员�?CREATE TABLE IF NOT EXISTS shared_members (
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
DROP TRIGGER IF EXISTS trg_shared_members_updated ON shared_members;
CREATE TRIGGER trg_shared_members_updated BEFORE UPDATE ON shared_members
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE shared_members ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON shared_members;
CREATE POLICY store_isolation ON shared_members
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON shared_members;
CREATE POLICY admin_all_access ON shared_members
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 5. 会员等级配置�?CREATE TABLE IF NOT EXISTS shared_member_levels (
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

-- 6. 商品分类�?CREATE TABLE IF NOT EXISTS shared_categories (
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

-- 7. 商品�?CREATE TABLE IF NOT EXISTS shared_products (
    product_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    category_id UUID REFERENCES shared_categories(category_id),
    name VARCHAR(100) NOT NULL,
    code VARCHAR(32),
    price NUMERIC(12,2) NOT NULL,
    cost_price NUMERIC(12,2),
    unit VARCHAR(16) DEFAULT '�?,
    image_url TEXT,
    description TEXT,
    stock INTEGER,
    stock_warn INTEGER,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
DROP TRIGGER IF EXISTS trg_shared_products_updated ON shared_products;
CREATE TRIGGER trg_shared_products_updated BEFORE UPDATE ON shared_products
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE shared_products ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON shared_products;
CREATE POLICY store_isolation ON shared_products
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON shared_products;
CREATE POLICY admin_all_access ON shared_products
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 8. 桌台�?CREATE TABLE IF NOT EXISTS shared_tables (
    table_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    table_no VARCHAR(16) NOT NULL,
    area VARCHAR(50) DEFAULT '大厅',
    capacity INTEGER DEFAULT 4,
    min_spend NUMERIC(10,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'active',
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, table_no)
);
DROP TRIGGER IF EXISTS trg_shared_tables_updated ON shared_tables;
CREATE TRIGGER trg_shared_tables_updated BEFORE UPDATE ON shared_tables
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE shared_tables ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON shared_tables;
CREATE POLICY store_isolation ON shared_tables
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON shared_tables;
CREATE POLICY admin_all_access ON shared_tables
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 9. 设备注册表（桌灯/打印机等�?CREATE TABLE IF NOT EXISTS shared_devices (
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

-- 10. 门店配置表（平铺结构，每店一行；extra_config JSONB 承载未来扩展�?CREATE TABLE IF NOT EXISTS shared_store_settings (
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
    -- 扩展配置（未来新业务配置放这里，不用改表结构�?    extra_config JSONB DEFAULT '{}',
    -- 审计字段
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================================================
-- 二、收银模块表 pos_*�?0张）
-- ===========================================================================

-- 11. 订单主表
CREATE TABLE IF NOT EXISTS pos_orders (
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
DROP TRIGGER IF EXISTS trg_pos_orders_updated ON pos_orders;
CREATE TRIGGER trg_pos_orders_updated BEFORE UPDATE ON pos_orders
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE pos_orders ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_orders;
CREATE POLICY store_isolation ON pos_orders
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_orders;
CREATE POLICY admin_all_access ON pos_orders
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 12. 订单明细�?CREATE TABLE IF NOT EXISTS pos_order_items (
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
    claimed_by UUID,                     -- 认领人（按件提成关键�?    claimed_at TIMESTAMPTZ,
    ready_at TIMESTAMPTZ,
    served_at TIMESTAMPTZ,
    bar_employee_id UUID,               -- 出酒/制作归属员工（算佣金关键�?    is_add BOOLEAN DEFAULT FALSE,
    is_refund BOOLEAN DEFAULT FALSE,
    is_presented BOOLEAN DEFAULT FALSE,
    is_rush BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_order_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_order_items;
CREATE POLICY store_isolation ON pos_order_items
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_order_items;
CREATE POLICY admin_all_access ON pos_order_items
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 13. 支付记录表（支持拆分支付：一笔订单多条支付记录）
CREATE TABLE IF NOT EXISTS pos_payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    payment_method VARCHAR(20) NOT NULL,  -- wechat/cash/alipay/member/pos/enterprise_wecom
    amount NUMERIC(12,2) NOT NULL,
    transaction_id VARCHAR(100),
    wecom_txn_id VARCHAR(64),            -- 企微收款流水�?    employee_id UUID,                     -- 收款员工（企微收款归属）
    notes TEXT,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_payments;
CREATE POLICY store_isolation ON pos_payments
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_payments;
CREATE POLICY admin_all_access ON pos_payments
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 14. 支付方式配置�?CREATE TABLE IF NOT EXISTS pos_payment_methods (
    method_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    name VARCHAR(50) NOT NULL,
    code VARCHAR(20) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 15. 桌台会话�?CREATE TABLE IF NOT EXISTS pos_table_sessions (
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

-- 16. 退单表（双镜复核）
CREATE TABLE IF NOT EXISTS pos_refunds (
    refund_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    item_id UUID,                         -- 退的是哪一项（可空=整单退�?    amount NUMERIC(12,2) NOT NULL,
    operator_id UUID NOT NULL,            -- 退单人（店长申请）
    confirmer_id UUID,                    -- 双镜复核人（boss或bar_manager�?    reason TEXT NOT NULL,
    status VARCHAR(16) DEFAULT 'pending', -- pending/confirmed/approved/rejected
    created_at TIMESTAMPTZ DEFAULT NOW(),
    confirmed_at TIMESTAMPTZ
);
ALTER TABLE pos_refunds ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_refunds;
CREATE POLICY store_isolation ON pos_refunds
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_refunds;
CREATE POLICY admin_all_access ON pos_refunds
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 17. 免单/折扣审批�?CREATE TABLE IF NOT EXISTS pos_discount_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL REFERENCES pos_orders(order_id),
    type VARCHAR(16) NOT NULL,            -- free/discount
    amount NUMERIC(12,2) NOT NULL,
    operator_id UUID NOT NULL,            -- 申请收银员（店长申请�?    approver_id UUID,                     -- 审批人（boss审批�?    reason TEXT NOT NULL,
    status VARCHAR(16) DEFAULT 'pending', -- pending/approved/rejected
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ
);
ALTER TABLE pos_discount_approvals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_discount_approvals;
CREATE POLICY store_isolation ON pos_discount_approvals
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_discount_approvals;
CREATE POLICY admin_all_access ON pos_discount_approvals
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 18. 会员余额流水�?CREATE TABLE IF NOT EXISTS pos_member_transactions (
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
DROP POLICY IF EXISTS store_isolation ON pos_member_transactions;
CREATE POLICY store_isolation ON pos_member_transactions
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_member_transactions;
CREATE POLICY admin_all_access ON pos_member_transactions
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 19. 订单操作日志�?CREATE TABLE IF NOT EXISTS pos_order_logs (
    log_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    order_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,
    details JSONB,
    created_by UUID NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 20. 每日对账�?CREATE TABLE IF NOT EXISTS pos_daily_reconciliations (
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

-- 21. 纸条社交�?CREATE TABLE IF NOT EXISTS pos_desk_notes (
    note_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    from_table_id UUID NOT NULL,
    to_table_id UUID NOT NULL,
    message TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'sent',    -- sent/accepted/rejected
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE pos_desk_notes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON pos_desk_notes;
CREATE POLICY store_isolation ON pos_desk_notes
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON pos_desk_notes;
CREATE POLICY admin_all_access ON pos_desk_notes
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 三、游戏模块表 game_*�?张）
-- ===========================================================================

-- 22. 游戏模板�?CREATE TABLE IF NOT EXISTS game_templates (
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

-- 23. 游戏会话�?CREATE TABLE IF NOT EXISTS game_sessions (
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
DROP POLICY IF EXISTS store_isolation ON game_sessions;
CREATE POLICY store_isolation ON game_sessions
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON game_sessions;
CREATE POLICY admin_all_access ON game_sessions
    FOR ALL
    USING (current_setting('app.current_user_role', true) = 'admin');

-- 24. 游戏参与者表
CREATE TABLE IF NOT EXISTS game_participants (
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

-- 25. 游戏奖品�?CREATE TABLE IF NOT EXISTS game_prizes (
    prize_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES game_sessions(session_id),
    product_id UUID NOT NULL REFERENCES shared_products(product_id),
    product_name VARCHAR(100),
    quantity INTEGER DEFAULT 1,
    claimed_by UUID,
    claimed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- ===========================================================================
-- 四、系统配置表 sys_*�?张）
-- ===========================================================================

-- 26. 系统配置�?CREATE TABLE IF NOT EXISTS sys_configs (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID,
    config_key VARCHAR(100) NOT NULL,
    config_value JSONB NOT NULL,
    description TEXT,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, config_key)
);

-- 27. 审计日志�?CREATE TABLE IF NOT EXISTS sys_audit_logs (
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

-- 28. 打印机配置表
CREATE TABLE IF NOT EXISTS sys_printers (
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

-- ===========================================================================
-- 索引
-- ===========================================================================
CREATE INDEX IF NOT EXISTS idx_shared_employees_store ON shared_employees(store_id);
CREATE INDEX IF NOT EXISTS idx_shared_employees_wecom ON shared_employees(wecom_user_id);
CREATE INDEX IF NOT EXISTS idx_shared_members_store ON shared_members(store_id);
CREATE INDEX IF NOT EXISTS idx_shared_members_phone ON shared_members(phone);
CREATE INDEX IF NOT EXISTS idx_shared_products_store ON shared_products(store_id);
CREATE INDEX IF NOT EXISTS idx_shared_products_category ON shared_products(category_id);
CREATE INDEX IF NOT EXISTS idx_shared_tables_store ON shared_tables(store_id);
CREATE INDEX IF NOT EXISTS idx_pos_orders_store ON pos_orders(store_id);
CREATE INDEX IF NOT EXISTS idx_pos_orders_status ON pos_orders(status);
CREATE INDEX IF NOT EXISTS idx_pos_orders_table ON pos_orders(table_id);
CREATE INDEX IF NOT EXISTS idx_pos_order_items_order ON pos_order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_pos_order_items_kitchen ON pos_order_items(kitchen_status);
CREATE INDEX IF NOT EXISTS idx_pos_payments_order ON pos_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_pos_refunds_order ON pos_refunds(order_id);
CREATE INDEX IF NOT EXISTS idx_pos_member_transactions_member ON pos_member_transactions(member_id);
CREATE INDEX IF NOT EXISTS idx_game_sessions_store ON game_sessions(store_id);
CREATE INDEX IF NOT EXISTS idx_sys_audit_logs_user ON sys_audit_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_sys_audit_logs_store ON sys_audit_logs(store_id);

-- ===========================================================================
-- 完成提示
-- ===========================================================================
-- 表数量统计：
--   shared_* : 10 (门店/加盟�?员工/会员/等级/分类/商品/桌台/设备/配置)
--   pos_*    : 11 (订单/明细/支付/支付方式/会话/退�?审批/流水/日志/对账/纸条)
--   game_*   : 4  (模板/会话/参与�?奖品)
--   sys_*    : 3  (配置/审计/打印�?
--   合计     : 28 (�?shared_devices �?shared_store_settings)
-- ===========================================================================
