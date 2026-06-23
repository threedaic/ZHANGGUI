-- ============================================================
-- 修复 RLS 策略合规性
-- 1. 修复3张表 admin 策略错误模式（authenticated_role → current_setting 判断）
-- 2. 补7张业务表 RLS 策略
-- ============================================================

-- ===== P0-2: 修复3张表 admin 策略 =====

-- shared_store_settings
DROP POLICY IF EXISTS shared_store_settings_admin_all_access ON shared_store_settings;
CREATE POLICY shared_store_settings_admin_all_access ON shared_store_settings
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- sys_users
DROP POLICY IF EXISTS sys_users_admin_all_access ON sys_users;
CREATE POLICY sys_users_admin_all_access ON sys_users
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- pos_bookings
DROP POLICY IF EXISTS pos_bookings_admin_all_access ON pos_bookings;
CREATE POLICY pos_bookings_admin_all_access ON pos_bookings
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- ===== P1-1: 补7张业务表 RLS 策略 =====

-- shared_devices
ALTER TABLE shared_devices ENABLE ROW LEVEL SECURITY;
CREATE POLICY shared_devices_store_isolation ON shared_devices
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY shared_devices_admin_all_access ON shared_devices
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- shared_categories
ALTER TABLE shared_categories ENABLE ROW LEVEL SECURITY;
CREATE POLICY shared_categories_store_isolation ON shared_categories
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY shared_categories_admin_all_access ON shared_categories
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- shared_member_levels
ALTER TABLE shared_member_levels ENABLE ROW LEVEL SECURITY;
CREATE POLICY shared_member_levels_store_isolation ON shared_member_levels
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY shared_member_levels_admin_all_access ON shared_member_levels
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- pos_payment_methods
ALTER TABLE pos_payment_methods ENABLE ROW LEVEL SECURITY;
CREATE POLICY pos_payment_methods_store_isolation ON pos_payment_methods
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY pos_payment_methods_admin_all_access ON pos_payment_methods
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- pos_table_sessions
ALTER TABLE pos_table_sessions ENABLE ROW LEVEL SECURITY;
CREATE POLICY pos_table_sessions_store_isolation ON pos_table_sessions
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY pos_table_sessions_admin_all_access ON pos_table_sessions
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- pos_order_logs
ALTER TABLE pos_order_logs ENABLE ROW LEVEL SECURITY;
CREATE POLICY pos_order_logs_store_isolation ON pos_order_logs
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY pos_order_logs_admin_all_access ON pos_order_logs
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- pos_daily_reconciliations
ALTER TABLE pos_daily_reconciliations ENABLE ROW LEVEL SECURITY;
CREATE POLICY pos_daily_reconciliations_store_isolation ON pos_daily_reconciliations
    USING (store_id = current_setting('app.current_store_id', true)::UUID);
CREATE POLICY pos_daily_reconciliations_admin_all_access ON pos_daily_reconciliations
    FOR ALL
    USING (current_setting('app.current_role', true) = 'admin')
    WITH CHECK (current_setting('app.current_role', true) = 'admin');

-- ===== P1-2: 确认 sys_users 有 must_change_password 列 =====
ALTER TABLE sys_users ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
