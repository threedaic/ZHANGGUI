-- ===========================================================================
-- Crush 2.0 员工�?Schema 建表脚本�?5张表�?-- 依据：SPEC 2.0 + 现有旧表字段映射
-- 覆盖模块：考勤/排班/审批/工资/合同/KPI/绩效/排名/评价/罚单/签收/收档/存酒/通知/营收
-- 通用规则（与 20260622_crush_2_0_schema.sql 一致）�?--   * 所有业务表�?store_id UUID NOT NULL（全局字典除外�?--   * 所有业务表启用 RLS 策略
--   * 所有表�?created_at / updated_at 审计字段
--   * 主键统一 UUID
--   * 金额统一 NUMERIC(12,2)
--   * employee_id 引用 shared_employees(employee_id)
-- ===========================================================================

-- updated_at 触发器函数（如已存在则跳过）
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- ===========================================================================
-- 一、考勤排班审批模块 att_*�?张）
-- ===========================================================================

-- 1. 班次配置
CREATE TABLE IF NOT EXISTS att_shift_configs (
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
CREATE TRIGGER trg_att_shift_configs_updated BEFORE UPDATE ON att_shift_configs
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_shift_configs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_shift_configs;
CREATE POLICY store_isolation ON att_shift_configs
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_shift_configs;
CREATE POLICY admin_all_access ON att_shift_configs
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 2. 考勤记录（排�?打卡+判定一体）
CREATE TABLE IF NOT EXISTS att_records (
    record_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    date DATE NOT NULL,
    -- 排班信息
    scheduled_shift VARCHAR(20),
    shift_start_time VARCHAR(8),
    shift_end_time VARCHAR(8),
    is_overnight BOOLEAN DEFAULT FALSE,
    -- 打卡信息
    clock_in TIMESTAMPTZ,
    clock_out TIMESTAMPTZ,
    -- 考勤判定
    status VARCHAR(20) DEFAULT 'unknown',     -- normal/late/early/absent/leave/makeup/unknown
    late_minutes INTEGER DEFAULT 0,
    early_minutes INTEGER DEFAULT 0,
    source VARCHAR(20) DEFAULT 'manual',      -- manual / wecom
    note TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, date)
);
CREATE TRIGGER trg_att_records_updated BEFORE UPDATE ON att_records
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_records;
CREATE POLICY store_isolation ON att_records
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_records;
CREATE POLICY admin_all_access ON att_records
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 3. 排班�?CREATE TABLE IF NOT EXISTS att_schedules (
    schedule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    date DATE NOT NULL,
    shift_type VARCHAR(20) NOT NULL,           -- day / night / rest / leave
    note TEXT,
    created_by UUID,                            -- 操作人（shared_employees.employee_id�?    version INTEGER DEFAULT 1,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(employee_id, date)
);
CREATE TRIGGER trg_att_schedules_updated BEFORE UPDATE ON att_schedules
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_schedules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_schedules;
CREATE POLICY store_isolation ON att_schedules
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_schedules;
CREATE POLICY admin_all_access ON att_schedules
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 4. 排班规则
CREATE TABLE IF NOT EXISTS att_schedule_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    rule_type VARCHAR(50) NOT NULL,
    rule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_att_schedule_rules_updated BEFORE UPDATE ON att_schedule_rules
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_schedule_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_schedule_rules;
CREATE POLICY store_isolation ON att_schedule_rules
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_schedule_rules;
CREATE POLICY admin_all_access ON att_schedule_rules
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 5. 排班快照
CREATE TABLE IF NOT EXISTS att_schedule_snapshots (
    snapshot_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    period VARCHAR(7) NOT NULL,                 -- YYYY-MM
    snapshot_data JSONB NOT NULL,
    version INTEGER NOT NULL,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE att_schedule_snapshots ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_schedule_snapshots;
CREATE POLICY store_isolation ON att_schedule_snapshots
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_schedule_snapshots;
CREATE POLICY admin_all_access ON att_schedule_snapshots
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 6. 调班申请
CREATE TABLE IF NOT EXISTS att_swap_requests (
    swap_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    requester_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    swap_with_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    swap_date DATE NOT NULL,
    swap_shift VARCHAR(20) NOT NULL,
    reason TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending_swap_with', -- pending_swap_with / swap_with_confirmed / approved / rejected
    swap_with_confirmed_at TIMESTAMPTZ,
    approved_by UUID,
    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_att_swap_requests_updated BEFORE UPDATE ON att_swap_requests
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_swap_requests ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_swap_requests;
CREATE POLICY store_isolation ON att_swap_requests
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_swap_requests;
CREATE POLICY admin_all_access ON att_swap_requests
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 7. 审批申请（请�?补卡/调班/报销统一表）
CREATE TABLE IF NOT EXISTS att_approvals (
    approval_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    type VARCHAR(20) NOT NULL,                  -- leave / makeup / swap / expense
    status VARCHAR(20) DEFAULT 'pending',       -- pending / approved / rejected
    start_date DATE,
    end_date DATE,
    reason TEXT,
    extra JSONB,                                -- 各类型自定义字段（请假类�?补卡时间/报销金额等）
    approver_id UUID,                           -- 审批人（shared_employees.employee_id�?    approved_at TIMESTAMPTZ,
    reject_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_att_approvals_updated BEFORE UPDATE ON att_approvals
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_approvals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_approvals;
CREATE POLICY store_isolation ON att_approvals
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_approvals;
CREATE POLICY admin_all_access ON att_approvals
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 8. 假期余额
CREATE TABLE IF NOT EXISTS att_leave_balances (
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
CREATE TRIGGER trg_att_leave_balances_updated BEFORE UPDATE ON att_leave_balances
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE att_leave_balances ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON att_leave_balances;
CREATE POLICY store_isolation ON att_leave_balances
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON att_leave_balances;
CREATE POLICY admin_all_access ON att_leave_balances
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 二、工资合同模�?wage_*�?张）
-- ===========================================================================

-- 9. 账期管理
CREATE TABLE IF NOT EXISTS wage_periods (
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
CREATE TRIGGER trg_wage_periods_updated BEFORE UPDATE ON wage_periods
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_periods ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_periods;
CREATE POLICY store_isolation ON wage_periods
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_periods;
CREATE POLICY admin_all_access ON wage_periods
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 10. 薪资矩阵�?岗位 x 4档）
CREATE TABLE IF NOT EXISTS wage_salary_matrix (
    matrix_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    position VARCHAR(30) NOT NULL,               -- 店长/吧员/服务�?厨师/保洁
    grade VARCHAR(20) NOT NULL,                  -- 学徒/正式/副职/正职
    monthly_salary NUMERIC(12,2) NOT NULL,
    base_salary NUMERIC(12,2) DEFAULT 3000.00,
    meal_allowance NUMERIC(12,2) DEFAULT 400.00,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, position, grade)
);
CREATE TRIGGER trg_wage_salary_matrix_updated BEFORE UPDATE ON wage_salary_matrix
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_salary_matrix ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_salary_matrix;
CREATE POLICY store_isolation ON wage_salary_matrix
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_salary_matrix;
CREATE POLICY admin_all_access ON wage_salary_matrix
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 11. 劳动合同
CREATE TABLE IF NOT EXISTS wage_contracts (
    contract_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    contract_no VARCHAR(50) UNIQUE NOT NULL,
    position VARCHAR(30) NOT NULL,
    grade VARCHAR(20) NOT NULL,
    monthly_salary NUMERIC(12,2) NOT NULL,
    base_salary NUMERIC(12,2) DEFAULT 3000.00,
    meal_allowance NUMERIC(12,2) DEFAULT 400.00,
    allowance NUMERIC(12,2) DEFAULT 0.00,        -- 月薪 - 基本工资
    start_date DATE NOT NULL,
    end_date DATE,
    status VARCHAR(30) DEFAULT 'draft',          -- draft/pending_sign/signed/expired/terminated
    esign_flow_id VARCHAR(100),                  -- 腾讯电子签流程ID
    signed_at TIMESTAMPTZ,
    signed_by UUID,
    template_data JSONB,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_wage_contracts_updated BEFORE UPDATE ON wage_contracts
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_contracts ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_contracts;
CREATE POLICY store_isolation ON wage_contracts
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_contracts;
CREATE POLICY admin_all_access ON wage_contracts
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 12. 工资主表
CREATE TABLE IF NOT EXISTS wage_records (
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
CREATE TRIGGER trg_wage_records_updated BEFORE UPDATE ON wage_records
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_records ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_records;
CREATE POLICY store_isolation ON wage_records
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_records;
CREATE POLICY admin_all_access ON wage_records
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 13. 工资明细子表
CREATE TABLE IF NOT EXISTS wage_record_items (
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
ALTER TABLE wage_record_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_record_items;
CREATE POLICY store_isolation ON wage_record_items
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_record_items;
CREATE POLICY admin_all_access ON wage_record_items
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 14. 工资项配�?CREATE TABLE IF NOT EXISTS wage_items_config (
    config_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    item_code VARCHAR(50) NOT NULL,
    item_name VARCHAR(50) NOT NULL,
    item_type VARCHAR(20) NOT NULL,              -- income / deduction
    data_source VARCHAR(30) NOT NULL,
    formula JSONB,
    is_active BOOLEAN DEFAULT TRUE,
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, item_code)
);
CREATE TRIGGER trg_wage_items_config_updated BEFORE UPDATE ON wage_items_config
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_items_config ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_items_config;
CREATE POLICY store_isolation ON wage_items_config
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_items_config;
CREATE POLICY admin_all_access ON wage_items_config
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 15. 薪资规则
CREATE TABLE IF NOT EXISTS wage_salary_rules (
    rule_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    rule_code VARCHAR(50) NOT NULL,
    rule_name VARCHAR(100) NOT NULL,
    rule_type VARCHAR(30) NOT NULL,              -- late_penalty / early_penalty / absent_penalty / bonus
    rule_config JSONB NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, rule_code)
);
CREATE TRIGGER trg_wage_salary_rules_updated BEFORE UPDATE ON wage_salary_rules
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_salary_rules ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_salary_rules;
CREATE POLICY store_isolation ON wage_salary_rules
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_salary_rules;
CREATE POLICY admin_all_access ON wage_salary_rules
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 16. 企微收款同步
CREATE TABLE IF NOT EXISTS wage_wework_payments (
    payment_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    transaction_id VARCHAR(100) NOT NULL,
    employee_id UUID REFERENCES shared_employees(employee_id),
    table_session_id UUID,                      -- 关联 pos_table_sessions
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
CREATE TRIGGER trg_wage_wework_payments_updated BEFORE UPDATE ON wage_wework_payments
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wage_wework_payments ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_wework_payments;
CREATE POLICY store_isolation ON wage_wework_payments
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_wework_payments;
CREATE POLICY admin_all_access ON wage_wework_payments
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 三、KPI/绩效/排名/评价/罚单模块 hr_*�?张）
-- ===========================================================================

-- 17. KPI 模板
CREATE TABLE IF NOT EXISTS hr_kpi_templates (
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
CREATE TRIGGER trg_hr_kpi_templates_updated BEFORE UPDATE ON hr_kpi_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE hr_kpi_templates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_kpi_templates;
CREATE POLICY store_isolation ON hr_kpi_templates
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_kpi_templates;
CREATE POLICY admin_all_access ON hr_kpi_templates
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 18. KPI 维度评分
CREATE TABLE IF NOT EXISTS hr_kpi_scores (
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
ALTER TABLE hr_kpi_scores ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_kpi_scores;
CREATE POLICY store_isolation ON hr_kpi_scores
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_kpi_scores;
CREATE POLICY admin_all_access ON hr_kpi_scores
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 19. KPI 汇总结�?CREATE TABLE IF NOT EXISTS hr_kpi_results (
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
ALTER TABLE hr_kpi_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_kpi_results;
CREATE POLICY store_isolation ON hr_kpi_results
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_kpi_results;
CREATE POLICY admin_all_access ON hr_kpi_results
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 20. KPI 申诉
CREATE TABLE IF NOT EXISTS hr_kpi_appeals (
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
ALTER TABLE hr_kpi_appeals ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_kpi_appeals;
CREATE POLICY store_isolation ON hr_kpi_appeals
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_kpi_appeals;
CREATE POLICY admin_all_access ON hr_kpi_appeals
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 21. 员工月度业绩汇�?CREATE TABLE IF NOT EXISTS hr_performance (
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
CREATE TRIGGER trg_hr_performance_updated BEFORE UPDATE ON hr_performance
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE hr_performance ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_performance;
CREATE POLICY store_isolation ON hr_performance
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_performance;
CREATE POLICY admin_all_access ON hr_performance
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 22. 员工排名
CREATE TABLE IF NOT EXISTS hr_rankings (
    ranking_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    rank_type VARCHAR(30) NOT NULL,               -- performance/kpi/attendance/rating
    rank_value NUMERIC(12,2) DEFAULT 0,
    rank_position INTEGER NOT NULL,
    detail TEXT,                                  -- JSON 排名明细
    calculated_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, employee_id, period, rank_type)
);
ALTER TABLE hr_rankings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_rankings;
CREATE POLICY store_isolation ON hr_rankings
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_rankings;
CREATE POLICY admin_all_access ON hr_rankings
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 23. 客户评价
CREATE TABLE IF NOT EXISTS hr_guest_ratings (
    rating_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID REFERENCES shared_employees(employee_id),
    table_no VARCHAR(16),
    food_quality INTEGER,                         -- 1-5
    food_speed INTEGER,
    drink_quality INTEGER,
    drink_speed INTEGER,
    service_attitude INTEGER,
    service_speed INTEGER,
    cleanliness INTEGER,
    overall_score NUMERIC(3,1) NOT NULL,
    comment TEXT,
    source VARCHAR(20) DEFAULT 'qr_code',
    is_low_score BOOLEAN DEFAULT FALSE,
    notified BOOLEAN DEFAULT FALSE,
    notified_at TIMESTAMPTZ,
    store_response TEXT,
    response_by UUID,
    responded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE hr_guest_ratings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_guest_ratings;
CREATE POLICY store_isolation ON hr_guest_ratings
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_guest_ratings;
CREATE POLICY admin_all_access ON hr_guest_ratings
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 24. 罚单
CREATE TABLE IF NOT EXISTS hr_penalty_notices (
    penalty_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    penalty_type VARCHAR(30) NOT NULL,            -- late_fine/absent_fine/early_fine/complaint/antifraud/other
    amount NUMERIC(12,2) DEFAULT 0,
    reason TEXT NOT NULL,
    issued_by UUID NOT NULL REFERENCES shared_employees(employee_id),
    issued_at TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) DEFAULT 'draft',           -- draft / issued / acknowledged
    extra JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_hr_penalty_notices_updated BEFORE UPDATE ON hr_penalty_notices
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE hr_penalty_notices ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON hr_penalty_notices;
CREATE POLICY store_isolation ON hr_penalty_notices
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON hr_penalty_notices;
CREATE POLICY admin_all_access ON hr_penalty_notices
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 四、签收模�?sig_*�?张）
-- ===========================================================================

-- 25. 签收任务
CREATE TABLE IF NOT EXISTS sig_tasks (
    task_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    type VARCHAR(30) NOT NULL,                    -- salary_slip / penalty_notice / attendance_confirm
    title VARCHAR(200) NOT NULL,
    ref_type VARCHAR(30) NOT NULL,               -- 关联业务表名
    ref_id UUID NOT NULL,                        -- 关联业务记录 ID
    status VARCHAR(20) DEFAULT 'pending',        -- pending / signed / disputed / revoked
    signed_at TIMESTAMPTZ,
    signature_data TEXT,                         -- base64 PNG 手写签名
    dispute_reason TEXT,
    disputed_at TIMESTAMPTZ,
    issued_by UUID NOT NULL REFERENCES shared_employees(employee_id),
    issued_at TIMESTAMPTZ NOT NULL,
    notes TEXT,
    extra JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_sig_tasks_updated BEFORE UPDATE ON sig_tasks
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE sig_tasks ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON sig_tasks;
CREATE POLICY store_isolation ON sig_tasks
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON sig_tasks;
CREATE POLICY admin_all_access ON sig_tasks
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 五、收档检查模�?butler_*�?张）
-- ===========================================================================

-- 26. 清单模板
CREATE TABLE IF NOT EXISTS butler_checklist_templates (
    template_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    name VARCHAR(50) NOT NULL,
    session_type VARCHAR(10) NOT NULL,           -- opening / closing
    role_tag VARCHAR(30) DEFAULT 'all',
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_by UUID,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_butler_templates_updated BEFORE UPDATE ON butler_checklist_templates
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE butler_checklist_templates ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON butler_checklist_templates;
CREATE POLICY store_isolation ON butler_checklist_templates
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON butler_checklist_templates;
CREATE POLICY admin_all_access ON butler_checklist_templates
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 27. 模板明细�?CREATE TABLE IF NOT EXISTS butler_checklist_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    template_id UUID NOT NULL REFERENCES butler_checklist_templates(template_id) ON DELETE CASCADE,
    item_name VARCHAR(100) NOT NULL,
    item_type VARCHAR(20) DEFAULT 'checkbox',     -- checkbox / photo
    device_id UUID,                               -- 预留 IoT（shared_devices�?    required_photo BOOLEAN DEFAULT FALSE,
    sort_order INTEGER DEFAULT 0,
    ai_prompt VARCHAR(500),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE butler_checklist_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON butler_checklist_items;
CREATE POLICY store_isolation ON butler_checklist_items
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON butler_checklist_items;
CREATE POLICY admin_all_access ON butler_checklist_items
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 28. 开闭店会话
CREATE TABLE IF NOT EXISTS butler_sessions (
    session_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    session_type VARCHAR(10) NOT NULL,            -- opening / closing
    operator_user_id UUID NOT NULL,
    status VARCHAR(20) DEFAULT 'in_progress',    -- in_progress / completed / abnormal
    started_at TIMESTAMPTZ DEFAULT NOW(),
    completed_at TIMESTAMPTZ,
    total_items INTEGER DEFAULT 0,
    completed_items INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_butler_sessions_updated BEFORE UPDATE ON butler_sessions
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE butler_sessions ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON butler_sessions;
CREATE POLICY store_isolation ON butler_sessions
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON butler_sessions;
CREATE POLICY admin_all_access ON butler_sessions
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 29. 检查项结果
CREATE TABLE IF NOT EXISTS butler_item_results (
    result_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    session_id UUID NOT NULL REFERENCES butler_sessions(session_id) ON DELETE CASCADE,
    template_id UUID REFERENCES butler_checklist_templates(template_id) ON DELETE SET NULL,
    item_id UUID REFERENCES butler_checklist_items(item_id) ON DELETE SET NULL,
    item_name VARCHAR(100),
    item_type VARCHAR(20),
    completed_by UUID,
    photo_url TEXT,
    ai_result JSONB,
    review_status VARCHAR(20) DEFAULT 'pending',  -- pending/passed/manual_reviewing/manual_passed/manual_rejected
    review_user_id UUID,
    review_comment TEXT,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE butler_item_results ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON butler_item_results;
CREATE POLICY store_isolation ON butler_item_results
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON butler_item_results;
CREATE POLICY admin_all_access ON butler_item_results
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 六、存酒模�?wine_*�?张）
-- ===========================================================================

-- 30. 存酒记录
CREATE TABLE IF NOT EXISTS wine_stored_bottles (
    wine_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    customer_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    wine_name VARCHAR(100) NOT NULL,
    bottle_label VARCHAR(50),
    date_stored DATE NOT NULL,
    initial_ml INTEGER DEFAULT 0,
    remaining_ml INTEGER,
    cabinet_no VARCHAR(20),
    table_no VARCHAR(16),
    status VARCHAR(20) DEFAULT 'stored',           -- stored / retrieved
    expiry_date DATE,
    retrieved_at TIMESTAMPTZ,
    retrieved_by UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_wine_stored_bottles_updated BEFORE UPDATE ON wine_stored_bottles
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wine_stored_bottles ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wine_stored_bottles;
CREATE POLICY store_isolation ON wine_stored_bottles
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wine_stored_bottles;
CREATE POLICY admin_all_access ON wine_stored_bottles
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 31. 盘点�?CREATE TABLE IF NOT EXISTS wine_stocktakes (
    stocktake_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    period VARCHAR(7) NOT NULL,                   -- YYYY-MM
    status VARCHAR(20) DEFAULT 'pending',         -- pending / in_progress / completed
    assigned_to VARCHAR(50),
    total_count INTEGER DEFAULT 0,
    checked_count INTEGER DEFAULT 0,
    matched_count INTEGER DEFAULT 0,
    missing_count INTEGER DEFAULT 0,
    extra_count INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE TRIGGER trg_wine_stocktakes_updated BEFORE UPDATE ON wine_stocktakes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE wine_stocktakes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wine_stocktakes;
CREATE POLICY store_isolation ON wine_stocktakes
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wine_stocktakes;
CREATE POLICY admin_all_access ON wine_stocktakes
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 32. 盘点明细
CREATE TABLE IF NOT EXISTS wine_stocktake_items (
    item_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    stocktake_id UUID NOT NULL REFERENCES wine_stocktakes(stocktake_id) ON DELETE CASCADE,
    wine_id UUID REFERENCES wine_stored_bottles(wine_id),
    bottle_label VARCHAR(50) NOT NULL,
    customer_name VARCHAR(50) NOT NULL,
    phone VARCHAR(20) NOT NULL,
    wine_name VARCHAR(100) NOT NULL,
    expected_ml INTEGER,
    actual_ml INTEGER,
    check_status VARCHAR(20) DEFAULT 'pending',   -- pending/matched/missing/mismatch
    checked_at TIMESTAMPTZ,
    checked_by UUID,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE wine_stocktake_items ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wine_stocktake_items;
CREATE POLICY store_isolation ON wine_stocktake_items
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wine_stocktake_items;
CREATE POLICY admin_all_access ON wine_stocktake_items
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 七、通知模块 sys_*�?张，扩展已有 sys_* 系列�?-- ===========================================================================

-- 33. 通知
CREATE TABLE IF NOT EXISTS sys_notifications (
    notification_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    employee_id UUID REFERENCES shared_employees(employee_id),
    type VARCHAR(40) NOT NULL,                    -- daily_report/attendance_alert/shift_change/approval/reminder
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    channel VARCHAR(20) DEFAULT 'in_app',         -- in_app / wecom / all
    is_read BOOLEAN DEFAULT FALSE,
    extra JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
ALTER TABLE sys_notifications ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON sys_notifications;
CREATE POLICY store_isolation ON sys_notifications
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON sys_notifications;
CREATE POLICY admin_all_access ON sys_notifications
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- 34. 通知配置
CREATE TABLE IF NOT EXISTS sys_notification_settings (
    setting_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    setting_key VARCHAR(40) NOT NULL,
    enabled BOOLEAN DEFAULT TRUE,
    channel VARCHAR(20) DEFAULT 'all',
    push_to_group BOOLEAN DEFAULT FALSE,
    target_roles JSONB DEFAULT '[]',
    schedule_time VARCHAR(8),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, setting_key)
);
CREATE TRIGGER trg_sys_notif_settings_updated BEFORE UPDATE ON sys_notification_settings
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE sys_notification_settings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON sys_notification_settings;
CREATE POLICY store_isolation ON sys_notification_settings
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON sys_notification_settings;
CREATE POLICY admin_all_access ON sys_notification_settings
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 八、营收模�?fin_*�?张）
-- ===========================================================================

-- 35. 每日营收
CREATE TABLE IF NOT EXISTS fin_daily_revenue (
    revenue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    date DATE NOT NULL,
    pos_revenue NUMERIC(12,2) DEFAULT 0,          -- POS收银收入
    wecom_revenue NUMERIC(12,2) DEFAULT 0,        -- 企微收款收入
    cash_revenue NUMERIC(12,2) DEFAULT 0,         -- 现金收入
    member_revenue NUMERIC(12,2) DEFAULT 0,       -- 会员卡收�?    total_revenue NUMERIC(12,2) DEFAULT 0,        -- 总收�?    guest_count INTEGER DEFAULT 0,
    avg_spend NUMERIC(12,2) DEFAULT 0,
    details JSONB,                                -- 明细（各品类收入等）
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(store_id, date)
);
CREATE TRIGGER trg_fin_daily_revenue_updated BEFORE UPDATE ON fin_daily_revenue
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();
ALTER TABLE fin_daily_revenue ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON fin_daily_revenue;
CREATE POLICY store_isolation ON fin_daily_revenue
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON fin_daily_revenue;
CREATE POLICY admin_all_access ON fin_daily_revenue
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');

-- ===========================================================================
-- 索引
-- ===========================================================================
CREATE INDEX IF NOT EXISTS idx_att_records_store ON att_records(store_id);
CREATE INDEX IF NOT EXISTS idx_att_records_employee ON att_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_att_records_date ON att_records(date);
CREATE INDEX IF NOT EXISTS idx_att_schedules_store ON att_schedules(store_id);
CREATE INDEX IF NOT EXISTS idx_att_schedules_employee ON att_schedules(employee_id);
CREATE INDEX IF NOT EXISTS idx_att_approvals_store ON att_approvals(store_id);
CREATE INDEX IF NOT EXISTS idx_att_approvals_employee ON att_approvals(employee_id);
CREATE INDEX IF NOT EXISTS idx_att_approvals_status ON att_approvals(status);
CREATE INDEX IF NOT EXISTS idx_att_leave_balances_employee ON att_leave_balances(employee_id);
CREATE INDEX IF NOT EXISTS idx_wage_records_store ON wage_records(store_id);
CREATE INDEX IF NOT EXISTS idx_wage_records_employee ON wage_records(employee_id);
CREATE INDEX IF NOT EXISTS idx_wage_records_period ON wage_records(period);
CREATE INDEX IF NOT EXISTS idx_wage_record_items_wage ON wage_record_items(wage_id);
CREATE INDEX IF NOT EXISTS idx_wage_contracts_employee ON wage_contracts(employee_id);
CREATE INDEX IF NOT EXISTS idx_wage_wework_payments_employee ON wage_wework_payments(employee_id);
CREATE INDEX IF NOT EXISTS idx_hr_kpi_scores_employee ON hr_kpi_scores(employee_id);
CREATE INDEX IF NOT EXISTS idx_hr_kpi_results_employee ON hr_kpi_results(employee_id);
CREATE INDEX IF NOT EXISTS idx_hr_performance_employee ON hr_performance(employee_id);
CREATE INDEX IF NOT EXISTS idx_hr_rankings_store ON hr_rankings(store_id);
CREATE INDEX IF NOT EXISTS idx_hr_guest_ratings_store ON hr_guest_ratings(store_id);
CREATE INDEX IF NOT EXISTS idx_hr_penalty_notices_employee ON hr_penalty_notices(employee_id);
CREATE INDEX IF NOT EXISTS idx_sig_tasks_employee ON sig_tasks(employee_id);
CREATE INDEX IF NOT EXISTS idx_sig_tasks_status ON sig_tasks(status);
CREATE INDEX IF NOT EXISTS idx_butler_sessions_store ON butler_sessions(store_id);
CREATE INDEX IF NOT EXISTS idx_wine_stored_bottles_store ON wine_stored_bottles(store_id);
CREATE INDEX IF NOT EXISTS idx_wine_stored_bottles_phone ON wine_stored_bottles(phone);
CREATE INDEX IF NOT EXISTS idx_sys_notifications_store ON sys_notifications(store_id);
CREATE INDEX IF NOT EXISTS idx_sys_notifications_employee ON sys_notifications(employee_id);
CREATE INDEX IF NOT EXISTS idx_fin_daily_revenue_store ON fin_daily_revenue(store_id);

-- ===========================================================================
-- 完成提示
-- ===========================================================================
-- 表数量统计：
--   att_*    : 8  (班次配置/考勤记录/排班/排班规则/排班快照/调班/审批/假期余额)
--   wage_*   : 8  (账期/薪资矩阵/合同/工资主表/工资明细/工资项配�?薪资规则/企微收款)
--   hr_*     : 8  (KPI模板/KPI评分/KPI结果/KPI申诉/月度业绩/排名/客户评价/罚单)
--   sig_*    : 1  (签收任务)
--   butler_* : 4  (清单模板/模板明细/开闭店会话/检查结�?
--   wine_*   : 3  (存酒记录/盘点�?盘点明细)
--   sys_*    : 2  (通知/通知配置)
--   fin_*    : 1  (每日营收)
--   合计     : 35
--
-- �?20260622_crush_2_0_schema.sql �?28 张表合并后：
--   shared_* : 10
--   pos_*    : 11
--   game_*   : 4
--   sys_*    : 3 + 2 = 5
--   att_*    : 8
--   wage_*   : 8
--   hr_*     : 8
--   sig_*    : 1
--   butler_* : 4
--   wine_*   : 3
--   fin_*    : 1
--   总合�?  : 63 张表
-- ===========================================================================
