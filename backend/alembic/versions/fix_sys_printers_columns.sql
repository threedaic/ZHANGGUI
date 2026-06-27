-- 修复 sys_printers 表结构：补齐 ORM 模型所需的所有列
-- 执行方式：docker exec -i crush-zhanggui-db psql -U postgres -d crush_zhanggui < fix_sys_printers_columns.sql

-- 安全添加列（IF NOT EXISTS 防止重复执行报错）

-- 打印机类型：label=标签机 / receipt=小票机 / order=出单机
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS printer_type VARCHAR(20) DEFAULT 'order';

-- API 账号（飞鹅用户名/芯烨user/佳博商户编码/各平台appid）
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS api_user VARCHAR(100);

-- API 密钥（飞鹅UKEY/芯烨UserKEY/佳博apiKey/各平台appsecret）
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS api_secret TEXT;

-- 纸宽（mm），58=窄纸/80=宽纸，用于打印内容自适应排版
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS paper_width INTEGER DEFAULT 80;

-- 在线状态
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS online_status BOOLEAN DEFAULT FALSE;

-- 最后心跳时间
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMPTZ;

-- 扩展配置（JSON，存放 devicesecret 等品牌特有字段）
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS extra_config JSONB DEFAULT '{}'::jsonb;

-- 更新时间
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();

-- 验证
SELECT column_name, data_type FROM information_schema.columns
WHERE table_name = 'sys_printers' ORDER BY ordinal_position;
