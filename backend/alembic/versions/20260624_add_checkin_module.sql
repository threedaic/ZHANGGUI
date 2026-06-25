-- 打卡模块：WiFi绑定 + 拍照打卡 + 班次智能归位
-- 1. att_records 增加打卡证据字段（照片URL、WiFi信息、拍照时间）
-- 2. 新建 att_checkin_wifis 表（门店WiFi绑定，支持多WiFi）
-- 3. shared_store_settings 增加打卡配置字段（是否强制WiFi/拍照、宽限分钟、照片保留天数）

-- 1. att_records 增加打卡证据字段
ALTER TABLE att_records
  ADD COLUMN IF NOT EXISTS photo_url Text,
  ADD COLUMN IF NOT EXISTS wifi_bssid VARCHAR(32),
  ADD COLUMN IF NOT EXISTS wifi_ssid VARCHAR(64),
  ADD COLUMN IF NOT EXISTS photo_taken_at TIMESTAMPTZ;

-- 2. 门店WiFi绑定表（一个门店可绑多个WiFi）
CREATE TABLE IF NOT EXISTS att_checkin_wifis (
  wifi_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  store_id UUID NOT NULL REFERENCES shared_stores(store_id) ON DELETE CASCADE,
  ssid VARCHAR(64) NOT NULL,
  bssid VARCHAR(32) NOT NULL,
  label VARCHAR(32),
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now(),
  updated_at TIMESTAMPTZ DEFAULT now(),
  UNIQUE (store_id, bssid)
);

-- 3. shared_store_settings 增加打卡配置
ALTER TABLE shared_store_settings
  ADD COLUMN IF NOT EXISTS checkin_require_wifi BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS checkin_require_photo BOOLEAN DEFAULT true,
  ADD COLUMN IF NOT EXISTS checkin_grace_minutes INTEGER DEFAULT 5,
  ADD COLUMN IF NOT EXISTS checkin_photo_retention_days INTEGER DEFAULT 90;

-- 索引：按门店+日期查询打卡记录
CREATE INDEX IF NOT EXISTS idx_att_records_store_date ON att_records(store_id, date);
CREATE INDEX IF NOT EXISTS idx_att_records_wifi_bssid ON att_records(wifi_bssid);
