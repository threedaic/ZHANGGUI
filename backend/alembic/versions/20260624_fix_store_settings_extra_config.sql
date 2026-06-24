-- 修复 shared_store_settings 缺少 extra_config 列的问题
-- 根因：20260623_align_new_tables.sql 补列时遗漏了此字段

ALTER TABLE shared_store_settings
  ADD COLUMN IF NOT EXISTS extra_config JSONB DEFAULT '{}';
