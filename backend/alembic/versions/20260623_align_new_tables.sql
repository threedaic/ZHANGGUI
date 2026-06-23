-- ============================================================
-- 迁移脚本：补全新表缺失字段 + 新建缺失表
-- 目的：让新表能完全替代旧表
-- ============================================================

-- 1. shared_employees 补6字段
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS skill_tags TEXT[] DEFAULT '{}';
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS is_first_manager BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS is_second_manager BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS is_third_manager BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS shift_group VARCHAR(10);
ALTER TABLE shared_employees ADD COLUMN IF NOT EXISTS notes TEXT;

-- 2. shared_stores 补4字段
ALTER TABLE shared_stores ADD COLUMN IF NOT EXISTS daily_booking_limit INTEGER DEFAULT 50;
ALTER TABLE shared_stores ADD COLUMN IF NOT EXISTS wework_token VARCHAR(100);
ALTER TABLE shared_stores ADD COLUMN IF NOT EXISTS wework_aes_key VARCHAR(100);
ALTER TABLE shared_stores ADD COLUMN IF NOT EXISTS wework_status VARCHAR(20) DEFAULT 'pending';

-- 3. pos_table_sessions 补9字段（业绩闭环依赖）
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS crmeb_order_count INTEGER DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS crmeb_total_amount NUMERIC(12,2) DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS wework_pay_count INTEGER DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS wework_pay_amount NUMERIC(12,2) DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS commission_employee_id UUID REFERENCES shared_employees(employee_id);
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS commission_base NUMERIC(12,2) DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS commission_amount NUMERIC(12,2) DEFAULT 0;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS is_anomaly BOOLEAN DEFAULT FALSE;
ALTER TABLE pos_table_sessions ADD COLUMN IF NOT EXISTS anomaly_reason TEXT;

-- 4. wage_items_config 补3字段
ALTER TABLE wage_items_config ADD COLUMN IF NOT EXISTS default_value NUMERIC(12,2) DEFAULT 0;
ALTER TABLE wage_items_config ADD COLUMN IF NOT EXISTS is_system BOOLEAN DEFAULT FALSE;
ALTER TABLE wage_items_config ADD COLUMN IF NOT EXISTS note TEXT;

-- 5. sys_audit_logs 补3字段
ALTER TABLE sys_audit_logs ADD COLUMN IF NOT EXISTS old_value TEXT;
ALTER TABLE sys_audit_logs ADD COLUMN IF NOT EXISTS new_value TEXT;
ALTER TABLE sys_audit_logs ADD COLUMN IF NOT EXISTS request_id TEXT;

-- 6. 新建 sys_users 表（密码登录）
CREATE TABLE IF NOT EXISTS sys_users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID REFERENCES shared_employees(employee_id),
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(30) NOT NULL DEFAULT 'staff',
    region VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for sys_users
ALTER TABLE sys_users ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS sys_users_store_isolation ON sys_users
    USING (store_id = current_setting('app.current_store_id')::UUID);
CREATE POLICY IF NOT EXISTS sys_users_admin_all_access ON sys_users
    FOR ALL TO authenticated_role
    USING (TRUE) WITH CHECK (TRUE);

CREATE TRIGGER set_updated_at_sys_users
    BEFORE UPDATE ON sys_users
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 7. 新建 pos_bookings 表（订桌）
CREATE TABLE IF NOT EXISTS pos_bookings (
    booking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    table_id UUID REFERENCES shared_tables(table_id),
    customer_name VARCHAR(100) NOT NULL,
    phone VARCHAR(20),
    booking_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    party_size INTEGER DEFAULT 1,
    status VARCHAR(20) DEFAULT 'confirmed',
    created_by UUID REFERENCES shared_employees(employee_id),
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- RLS for pos_bookings
ALTER TABLE pos_bookings ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS pos_bookings_store_isolation ON pos_bookings
    USING (store_id = current_setting('app.current_store_id')::UUID);
CREATE POLICY IF NOT EXISTS pos_bookings_admin_all_access ON pos_bookings
    FOR ALL TO authenticated_role
    USING (TRUE) WITH CHECK (TRUE);

CREATE TRIGGER set_updated_at_pos_bookings
    BEFORE UPDATE ON pos_bookings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 8. shared_store_settings 需要保留平铺字段（兼容旧代码渐进迁移）
-- 旧表 store_settings 有40+字段，新表是KV结构
-- 为避免一次性重写所有配置读取逻辑，暂时给 shared_store_settings 加平铺字段
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS rest_days_per_month INTEGER DEFAULT 4;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS payroll_day_of_month INTEGER DEFAULT 10;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS kpi_coefficient_min NUMERIC(3,2) DEFAULT 0.80;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS kpi_coefficient_max NUMERIC(3,2) DEFAULT 1.20;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS ai_api_url TEXT;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS ai_api_key TEXT;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS ai_model VARCHAR(50);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS ai_temperature NUMERIC(3,2) DEFAULT 0.7;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS label_printer_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS receipt_printer_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_brand VARCHAR(50);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_api_url TEXT;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_sn VARCHAR(100);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_user VARCHAR(50);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_ukey VARCHAR(100);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_label_width INTEGER DEFAULT 40;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS printer_label_height INTEGER DEFAULT 30;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS wecom_bot_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS wecom_webhook_url TEXT;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS rest_allowed_weekdays VARCHAR(20) DEFAULT '[]';
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS rest_forbidden_weekdays VARCHAR(20) DEFAULT '[]';
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS max_same_position_off INTEGER DEFAULT 1;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS min_position_coverage_percent INTEGER DEFAULT 50;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS manager_order_constraint VARCHAR(20) DEFAULT 'strict';
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS holiday_policy VARCHAR(20) DEFAULT 'double';
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS auto_schedule_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS schedule_lock_after_publish BOOLEAN DEFAULT TRUE;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_initiator_ids VARCHAR(200) DEFAULT '[]';
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_company_name VARCHAR(100);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_company_phone VARCHAR(20);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_company_address VARCHAR(200);
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_base_salary NUMERIC(12,2) DEFAULT 3000;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_probation_months INTEGER DEFAULT 1;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_notice_days INTEGER DEFAULT 30;
ALTER TABLE shared_store_settings ADD COLUMN IF NOT EXISTS contract_duration_years INTEGER DEFAULT 1;
