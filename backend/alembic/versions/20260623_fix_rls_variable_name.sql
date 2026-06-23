-- 批量修复所有RLS策略：app.current_role → app.current_user_role
-- current_role 是PG保留字，SET app.current_role 会报语法错误

DO $$
DECLARE
    pol RECORD;
BEGIN
    FOR pol IN
        SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual, with_check
        FROM pg_policies
        WHERE qual LIKE '%app.current_role%' OR with_check LIKE '%app.current_role%'
    LOOP
        -- 删除旧策略
        EXECUTE format('DROP POLICY IF EXISTS %I ON %I.%I', pol.policyname, pol.schemaname, pol.tablename);
        
        -- 重建策略，替换 app.current_role → app.current_user_role
        IF pol.cmd = 'ALL' THEN
            IF pol.with_check IS NOT NULL THEN
                EXECUTE format(
                    'CREATE POLICY %I ON %I.%I FOR ALL USING (%s) WITH CHECK (%s)',
                    pol.policyname,
                    pol.schemaname,
                    pol.tablename,
                    REPLACE(pol.qual, 'app.current_role', 'app.current_user_role'),
                    REPLACE(pol.with_check, 'app.current_role', 'app.current_user_role')
                );
            ELSE
                EXECUTE format(
                    'CREATE POLICY %I ON %I.%I FOR ALL USING (%s)',
                    pol.policyname,
                    pol.schemaname,
                    pol.tablename,
                    REPLACE(pol.qual, 'app.current_role', 'app.current_user_role')
                );
            END IF;
        ELSIF pol.cmd = 'SELECT' THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I.%I FOR SELECT USING (%s)',
                pol.policyname,
                pol.schemaname,
                pol.tablename,
                REPLACE(pol.qual, 'app.current_role', 'app.current_user_role')
            );
        ELSIF pol.cmd = 'INSERT' THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I.%I FOR INSERT WITH CHECK (%s)',
                pol.policyname,
                pol.schemaname,
                pol.tablename,
                REPLACE(pol.with_check, 'app.current_role', 'app.current_user_role')
            );
        ELSIF pol.cmd = 'UPDATE' THEN
            EXECUTE format(
                'CREATE POLICY %I ON %I.%I FOR UPDATE USING (%s) WITH CHECK (%s)',
                pol.policyname,
                pol.schemaname,
                pol.tablename,
                REPLACE(pol.qual, 'app.current_role', 'app.current_user_role'),
                REPLACE(pol.with_check, 'app.current_role', 'app.current_user_role')
            );
        END IF;
    END LOOP;
END $$;

-- 验证
SELECT COUNT(*) as remaining FROM pg_policies WHERE qual LIKE '%app.current_role%' OR with_check LIKE '%app.current_role%';
SELECT COUNT(*) as fixed FROM pg_policies WHERE qual LIKE '%app.current_user_role%' OR with_check LIKE '%app.current_user_role%';
