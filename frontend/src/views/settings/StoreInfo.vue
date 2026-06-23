<template>
  <div class="store-info-page">
    <div class="page-header">
      <span class="page-title">门店信息</span>
    </div>

    <div class="section">
      <div class="section-header">
        <span>门店信息</span>
      </div>
      <div class="section-body">
        <div class="info-row">
          <span class="info-label">门店名</span>
          <span class="info-value">{{ storeInfo.name }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">编码</span>
          <span class="info-value">{{ storeInfo.store_code }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">地址</span>
          <span class="info-value">{{ storeInfo.address || '未设置' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">城市</span>
          <span class="info-value">{{ storeInfo.city || '未设置' }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">日订桌上限</span>
          <span class="info-value">{{ storeInfo.daily_booking_limit || 30 }}</span>
        </div>
        <div class="info-row">
          <span class="info-label">企微状态</span>
          <span class="info-value" :class="{ 'status-ok': storeInfo.wework_status === 'configured' }">
            {{ weworkStatusLabel }}
          </span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { storeAPI, type StoreInfo } from '@/api/store'

const storeInfo = ref<StoreInfo>({
  id: '', name: '加载中...', store_code: '', address: null, city: null,
  status: 'active', daily_booking_limit: 30,
  wework_status: null, wework_corp_id: null, wework_agent_id: null,
  wework_department_id: null,
} as StoreInfo)

const weworkStatusLabel = computed(() => {
  const map: Record<string, string> = {
    pending: '未配置', configured: '已配置', error: '配置错误',
  }
  return map[storeInfo.value.wework_status || ''] || '未知'
})

async function loadData() {
  try {
    const res = await storeAPI.getInfo()
    storeInfo.value = res.data.data
  } catch { /* silent */ }
}

onMounted(loadData)
</script>

<style scoped>
.store-info-page {
  padding: 16px;
  min-height: 100vh;
  background: #000000;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 20px;
}

.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #C8C8C8;
}

.section {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  margin-bottom: 12px;
  overflow: hidden;
}
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 16px;
  font-size: 14px;
  font-weight: 500;
  color: #C8C8C8;
}
.section-body {
  padding: 0 16px 16px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 0;
  border-bottom: 1px solid #222222;
}
.info-row:last-child { border-bottom: none; }
.info-label { font-size: 13px; color: #7A7C80; }
.info-value { font-size: 13px; color: #C8C8C8; }
.status-ok { color: #4CAF50; }
</style>
