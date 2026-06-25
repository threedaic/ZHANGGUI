-- 添加智能班次归位的时间窗口配置
ALTER TABLE shared_store_settings
  ADD COLUMN IF NOT EXISTS checkin_time_window_minutes INTEGER DEFAULT 120;
