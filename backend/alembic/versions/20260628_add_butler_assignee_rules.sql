-- ============================================================
-- 开闭店检查单执行人顺位表
-- 设计：每家店 × 每种会话类型（opening/closing）配置一组顺位
--       每日定时任务按请假数据自动指派（顺位1默认，请假跳下一个）
-- ============================================================

CREATE TABLE IF NOT EXISTS butler_assignee_rules (
    rule_id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id         UUID NOT NULL REFERENCES shared_stores(store_id) ON DELETE CASCADE,
    session_type     VARCHAR(10) NOT NULL,                 -- opening / closing
    employee_id      UUID NOT NULL REFERENCES shared_employees(employee_id) ON DELETE CASCADE,
    priority         INTEGER NOT NULL,                     -- 1=第一顺位，2=第二顺位...
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    updated_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (store_id, session_type, employee_id)
);

CREATE INDEX IF NOT EXISTS idx_butler_assignee_rules_lookup
    ON butler_assignee_rules (store_id, session_type, is_active, priority);

-- 当日指派记录表：记录今天最终派给谁，避免反复计算
CREATE TABLE IF NOT EXISTS butler_daily_assignments (
    assignment_id    UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id         UUID NOT NULL REFERENCES shared_stores(store_id) ON DELETE CASCADE,
    session_type     VARCHAR(10) NOT NULL,                 -- opening / closing
    assign_date      DATE NOT NULL,                        -- 指派日期
    employee_id      UUID NOT NULL REFERENCES shared_employees(employee_id) ON DELETE CASCADE,
    fallback_used    BOOLEAN NOT NULL DEFAULT FALSE,       -- 是否触发了兜底（第一顺位请假）
    fallback_reason  VARCHAR(100),                         -- 兜底原因
    created_at       TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (store_id, session_type, assign_date)
);

CREATE INDEX IF NOT EXISTS idx_butler_daily_assignments_lookup
    ON butler_daily_assignments (store_id, session_type, assign_date);

-- RLS 策略：管理员全权
ALTER TABLE butler_assignee_rules ENABLE ROW LEVEL SECURITY;
ALTER TABLE butler_daily_assignments ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS admin_all_access ON butler_assignee_rules;
CREATE POLICY admin_all_access ON butler_assignee_rules
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

DROP POLICY IF EXISTS admin_all_access ON butler_daily_assignments;
CREATE POLICY admin_all_access ON butler_daily_assignments
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');
