-- 打印机路由引擎 - 数据库迁移脚本
-- 创建时间：2026-06-23

-- 1. 扩展 sys_printers 表（添加打印机类型、在线状态等字段）
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS printer_type VARCHAR(20) DEFAULT 'order';
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS api_user VARCHAR(100);
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS api_secret TEXT;
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS paper_width INTEGER DEFAULT 80;
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS online_status BOOLEAN DEFAULT false;
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS last_heartbeat TIMESTAMP WITH TIME ZONE;
ALTER TABLE sys_printers ADD COLUMN IF NOT EXISTS extra_config JSONB DEFAULT '{}';

-- 添加打印机类型注释
COMMENT ON COLUMN sys_printers.printer_type IS '打印机类型：label=标签机, receipt=小票机, order=出单机';

-- 2. 创建路由规则表 sys_print_routes
CREATE TABLE IF NOT EXISTS sys_print_routes (
    route_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    name VARCHAR(100) NOT NULL,
    trigger_event VARCHAR(50) NOT NULL DEFAULT 'order_created',
    document_type VARCHAR(50) NOT NULL DEFAULT 'order',
    filter_type VARCHAR(50) NOT NULL DEFAULT 'category',
    filter_value JSONB,
    printer_id UUID NOT NULL,
    priority INTEGER DEFAULT 1,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 添加注释
COMMENT ON TABLE sys_print_routes IS '打印路由规则表';
COMMENT ON COLUMN sys_print_routes.trigger_event IS '触发时机：order_created=订单创建, payment_completed=支付完成, manual=手动重打';
COMMENT ON COLUMN sys_print_routes.document_type IS '文档类型：order=出单, receipt=收据, label=标签';
COMMENT ON COLUMN sys_print_routes.filter_type IS '匹配条件：category=按分类, product=按商品, order_type=按订单类型, all=全部';
COMMENT ON COLUMN sys_print_routes.filter_value IS '匹配值：分类ID列表/商品ID列表/订单类型';
COMMENT ON COLUMN sys_print_routes.priority IS '优先级：数字越小优先级越高';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_print_routes_store ON sys_print_routes(store_id);
CREATE INDEX IF NOT EXISTS idx_print_routes_trigger ON sys_print_routes(trigger_event);

-- 3. 创建打印队列表 print_queue
CREATE TABLE IF NOT EXISTS print_queue (
    queue_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL,
    route_id UUID,
    printer_id UUID NOT NULL,
    content TEXT NOT NULL,
    status VARCHAR(20) DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    printed_at TIMESTAMP WITH TIME ZONE
);

-- 添加注释
COMMENT ON TABLE print_queue IS '打印任务队列';
COMMENT ON COLUMN print_queue.status IS '状态：pending=待打印, printing=打印中, completed=已完成, failed=失败';

-- 创建索引
CREATE INDEX IF NOT EXISTS idx_print_queue_status ON print_queue(status);
CREATE INDEX IF NOT EXISTS idx_print_queue_store ON print_queue(store_id);

-- 4. 为 shared_categories 添加打印机绑定字段
ALTER TABLE shared_categories ADD COLUMN IF NOT EXISTS printer_id UUID;
ALTER TABLE shared_categories ADD COLUMN IF NOT EXISTS backup_printer_id UUID;

COMMENT ON COLUMN shared_categories.printer_id IS '该分类商品的出单打印机ID';
COMMENT ON COLUMN shared_categories.backup_printer_id IS '备用打印机ID（主打印机离线时使用）';

-- 5. 创建打印机状态监控视图
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
