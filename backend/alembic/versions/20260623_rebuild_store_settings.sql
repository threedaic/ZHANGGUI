-- 重建 shared_store_settings（平铺结构，UUID主键，与旧 store_settings 字段一致）
CREATE TABLE IF NOT EXISTS shared_store_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    rest_days_per_month INTEGER NOT NULL DEFAULT 4,
    rest_allowed_weekdays TEXT,
    rest_forbidden_weekdays TEXT,
    max_same_position_off INTEGER NOT NULL DEFAULT 1,
    min_position_coverage_percent INTEGER NOT NULL DEFAULT 50,
    manager_order_constraint BOOLEAN NOT NULL DEFAULT TRUE,
    holiday_policy VARCHAR(20) NOT NULL DEFAULT 'comp_leave',
    auto_schedule_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    schedule_lock_after_publish BOOLEAN NOT NULL DEFAULT TRUE,
    payroll_day_of_month INTEGER NOT NULL DEFAULT 5,
    kpi_coefficient_min DOUBLE PRECISION NOT NULL DEFAULT 0.60,
    kpi_coefficient_max DOUBLE PRECISION NOT NULL DEFAULT 1.50,
    contract_initiator_ids TEXT,
    contract_company_name VARCHAR(100),
    contract_company_phone VARCHAR(20),
    contract_company_address TEXT,
    contract_base_salary DOUBLE PRECISION NOT NULL DEFAULT 3000.0,
    contract_probation_months INTEGER NOT NULL DEFAULT 6,
    contract_notice_days INTEGER NOT NULL DEFAULT 45,
    contract_duration_years INTEGER NOT NULL DEFAULT 3,
    ai_api_url TEXT,
    ai_api_key TEXT,
    ai_model VARCHAR(100),
    ai_temperature DOUBLE PRECISION NOT NULL DEFAULT 0.7,
    printer_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    label_printer_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    receipt_printer_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    printer_brand VARCHAR(50),
    printer_api_url TEXT,
    printer_sn VARCHAR(100),
    printer_user VARCHAR(100),
    printer_ukey TEXT,
    printer_label_width INTEGER NOT NULL DEFAULT 80,
    printer_label_height INTEGER NOT NULL DEFAULT 50,
    wecom_bot_enabled BOOLEAN NOT NULL DEFAULT FALSE,
    wecom_webhook_url TEXT,
    extra_config JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

ALTER TABLE shared_store_settings ENABLE ROW LEVEL SECURITY;
CREATE POLICY IF NOT EXISTS shared_store_settings_store_isolation ON shared_store_settings
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY IF NOT EXISTS shared_store_settings_admin_all_access ON shared_store_settings
    FOR ALL TO authenticated_role
    USING (TRUE) WITH CHECK (TRUE);

CREATE TRIGGER set_updated_at_shared_store_settings
    BEFORE UPDATE ON shared_store_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
