-- 工资申诉表
CREATE TABLE IF NOT EXISTS wage_disputes (
    dispute_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES shared_stores(store_id),
    wage_id UUID NOT NULL REFERENCES wage_records(wage_id),
    employee_id UUID NOT NULL REFERENCES shared_employees(employee_id),
    period VARCHAR(7) NOT NULL,
    dispute_type VARCHAR(20) NOT NULL,
    original_amount NUMERIC(12,2),
    expected_amount NUMERIC(12,2),
    reason TEXT NOT NULL,
    evidence JSONB,
    status VARCHAR(20) DEFAULT 'pending',
    resolution TEXT,
    adjusted_amount NUMERIC(12,2),
    adjusted_in_period VARCHAR(7),
    reviewed_by UUID,
    reviewed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER trg_wage_disputes_updated BEFORE UPDATE ON wage_disputes
    FOR EACH ROW EXECUTE FUNCTION set_updated_at();

ALTER TABLE wage_disputes ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS store_isolation ON wage_disputes;
CREATE POLICY store_isolation ON wage_disputes
    USING (store_id = current_setting('app.current_store_id', true)::uuid);
DROP POLICY IF EXISTS admin_all_access ON wage_disputes;
CREATE POLICY admin_all_access ON wage_disputes
    FOR ALL USING (current_setting('app.current_user_role', true) = 'admin');
