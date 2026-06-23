-- Manual migration for environments where async alembic env fails
-- Equivalent to 20260615_add_shift_configs_expand_attendance_add_approval_notification

BEGIN;

-- 1. 扩展 attendance_records 表
ALTER TABLE attendance_records
    ADD COLUMN IF NOT EXISTS shift_start_time VARCHAR(8),
    ADD COLUMN IF NOT EXISTS shift_end_time VARCHAR(8),
    ADD COLUMN IF NOT EXISTS is_overnight BOOLEAN NOT NULL DEFAULT false;

-- 2. 新建 shift_configs 表
CREATE TABLE IF NOT EXISTS shift_configs (
    id SERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    shift_code VARCHAR(20) NOT NULL,
    shift_name VARCHAR(20) NOT NULL,
    start_time VARCHAR(8) NOT NULL,
    end_time VARCHAR(8) NOT NULL,
    is_overnight BOOLEAN NOT NULL DEFAULT false,
    color VARCHAR(8) NOT NULL DEFAULT '#FB0079',
    sort_order INTEGER NOT NULL DEFAULT 0,
    is_active BOOLEAN NOT NULL DEFAULT true,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (store_id, shift_code)
);

-- 3. 新建 approval_requests 表
CREATE TABLE IF NOT EXISTS approval_requests (
    id SERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    start_date DATE,
    end_date DATE,
    reason TEXT,
    extra JSONB,
    approver_id INTEGER REFERENCES users(id),
    approved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 4. 新建 notifications 表
CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    user_id INTEGER REFERENCES users(id),
    type VARCHAR(40) NOT NULL,
    title VARCHAR(200) NOT NULL,
    content TEXT NOT NULL,
    channel VARCHAR(20) NOT NULL DEFAULT 'in_app',
    is_read BOOLEAN NOT NULL DEFAULT false,
    extra JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 5. 新建 notification_settings 表
CREATE TABLE IF NOT EXISTS notification_settings (
    id SERIAL PRIMARY KEY,
    store_id INTEGER NOT NULL REFERENCES stores(id),
    setting_key VARCHAR(40) NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT true,
    channel VARCHAR(20) NOT NULL DEFAULT 'all',
    target_roles JSONB NOT NULL DEFAULT '["boss", "store_manager"]'::jsonb,
    schedule_time VARCHAR(8),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (store_id, setting_key)
);

-- 6. 初始化默认班次配置（store_id=1），显式指定所有非空列
INSERT INTO shift_configs (store_id, shift_code, shift_name, start_time, end_time, is_overnight, color, sort_order, is_active)
VALUES
    (1, 'day', '白班', '12:00', '20:00', false, '#FB0079', 1, true),
    (1, 'night', '晚班', '19:00', '03:00', true, '#333333', 2, true)
ON CONFLICT (store_id, shift_code) DO NOTHING;

-- 7. 初始化默认推送设置
INSERT INTO notification_settings (store_id, setting_key, enabled, channel, target_roles, schedule_time)
VALUES
    (1, 'daily_report', true, 'all', '["boss", "store_manager"]'::jsonb, '23:00'),
    (1, 'attendance_alert', true, 'all', '["boss", "store_manager"]'::jsonb, null),
    (1, 'shift_change', true, 'all', '["staff"]'::jsonb, null),
    (1, 'approval', true, 'all', '["boss", "store_manager", "staff"]'::jsonb, null),
    (1, 'reminder', false, 'all', '["staff"]'::jsonb, null)
ON CONFLICT (store_id, setting_key) DO NOTHING;

-- 8. 维护 Alembic 版本记录
CREATE TABLE IF NOT EXISTS alembic_version (
    version_num VARCHAR(32) NOT NULL PRIMARY KEY
);

DELETE FROM alembic_version WHERE version_num = '20260615';
INSERT INTO alembic_version (version_num) VALUES ('20260615');

COMMIT;
