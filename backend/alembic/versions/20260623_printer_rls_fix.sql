-- 打印机模块 RLS 策略修复 - 2026-06-23
-- 修复 SPEC 2.0 合规审查问题：C-1, C-2

-- C-1: 将 print_queue 表重命名为 sys_print_queue
ALTER TABLE IF EXISTS print_queue RENAME TO sys_print_queue;

-- C-2: 为三张打印机表添加 RLS 策略

-- 1. sys_printers 表启用 RLS
ALTER TABLE sys_printers ENABLE ROW LEVEL SECURITY;

-- sys_printers 的 RLS 策略：门店隔离
CREATE POLICY sys_printers_store_isolation ON sys_printers
    FOR ALL
    USING (store_id = current_setting('app.current_store_id')::UUID)
    WITH CHECK (store_id = current_setting('app.current_store_id')::UUID);

-- 2. sys_print_routes 表启用 RLS
ALTER TABLE sys_print_routes ENABLE ROW LEVEL SECURITY;

-- sys_print_routes 的 RLS 策略：门店隔离
CREATE POLICY sys_print_routes_store_isolation ON sys_print_routes
    FOR ALL
    USING (store_id = current_setting('app.current_store_id')::UUID)
    WITH CHECK (store_id = current_setting('app.current_store_id')::UUID);

-- 3. sys_print_queue 表启用 RLS
ALTER TABLE sys_print_queue ENABLE ROW LEVEL SECURITY;

-- sys_print_queue 的 RLS 策略：门店隔离
CREATE POLICY sys_print_queue_store_isolation ON sys_print_queue
    FOR ALL
    USING (store_id = current_setting('app.current_store_id')::UUID)
    WITH CHECK (store_id = current_setting('app.current_store_id')::UUID);

-- 修复视图中的表名
CREATE OR REPLACE VIEW v_printer_status AS
SELECT
    p.printer_id,
    p.store_id,
    p.name AS printer_name,
    p.printer_type,
    p.online_status,
    p.last_heartbeat,
    CASE
        WHEN p.last_heartbeat IS NULL THEN 'unknown'
        WHEN p.last_heartbeat < NOW() - INTERVAL '5 minutes' THEN 'offline'
        WHEN p.online_status = true THEN 'online'
        ELSE 'offline'
    END AS computed_status
FROM sys_printers p
WHERE p.is_active = true;

-- 完成
