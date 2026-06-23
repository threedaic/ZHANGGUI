-- ============================================================
-- 修复 butler 模块：补全 store_id 列
-- 问题：ORM 模型已添加 store_id，但 DB 表可能缺少该列
--       （create_all 创建的表不含 store_id，SQL迁移创建的表有）
-- ============================================================

-- 1. butler_checklist_items 补 store_id
ALTER TABLE butler_checklist_items ADD COLUMN IF NOT EXISTS store_id UUID;

-- 从模板表回填 store_id
UPDATE butler_checklist_items SET store_id = (
    SELECT t.store_id FROM butler_checklist_templates t
    WHERE t.template_id = butler_checklist_items.template_id
) WHERE store_id IS NULL;

-- 设置 NOT NULL（回填完成后）
ALTER TABLE butler_checklist_items ALTER COLUMN store_id SET NOT NULL;

-- 2. butler_item_results 补 store_id
ALTER TABLE butler_item_results ADD COLUMN IF NOT EXISTS store_id UUID;

-- 从会话表回填 store_id
UPDATE butler_item_results SET store_id = (
    SELECT s.store_id FROM butler_sessions s
    WHERE s.session_id = butler_item_results.session_id
) WHERE store_id IS NULL;

-- 设置 NOT NULL
ALTER TABLE butler_item_results ALTER COLUMN store_id SET NOT NULL;

-- 3. 确保 RLS 策略使用正确的变量名（app.current_user_role 替代 app.current_role）
-- butler_checklist_templates
DROP POLICY IF EXISTS admin_all_access ON butler_checklist_templates;
CREATE POLICY admin_all_access ON butler_checklist_templates
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- butler_checklist_items
DROP POLICY IF EXISTS admin_all_access ON butler_checklist_items;
CREATE POLICY admin_all_access ON butler_checklist_items
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- butler_sessions
DROP POLICY IF EXISTS admin_all_access ON butler_sessions;
CREATE POLICY admin_all_access ON butler_sessions
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- butler_item_results
DROP POLICY IF EXISTS admin_all_access ON butler_item_results;
CREATE POLICY admin_all_access ON butler_item_results
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');
