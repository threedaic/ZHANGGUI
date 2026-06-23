-- ===========================================================================
-- 20260623_add_printer_split_switches.sql
-- 拆分云打印机开关：标签打印机 + 取酒单打印机
-- ===========================================================================

-- 增加 label_printer_enabled 列（标签打印机：存酒时出标签）
ALTER TABLE store_settings
    ADD COLUMN IF NOT EXISTS label_printer_enabled BOOLEAN DEFAULT FALSE;

-- 增加 receipt_printer_enabled 列（取酒单打印机：取酒时出小票）
ALTER TABLE store_settings
    ADD COLUMN IF NOT EXISTS receipt_printer_enabled BOOLEAN DEFAULT FALSE;

-- 数据迁移：如果原 printer_enabled 为 TRUE，则两个新开关也置为 TRUE
UPDATE store_settings
SET label_printer_enabled = TRUE,
    receipt_printer_enabled = TRUE
WHERE printer_enabled = TRUE
  AND (label_printer_enabled IS NULL OR label_printer_enabled = FALSE);
