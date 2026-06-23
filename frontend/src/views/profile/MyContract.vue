<template>
  <div class="my-contract-page">
    <div class="page-header">
      <h1 class="page-title">我的合同</h1>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="list.length === 0" class="empty">暂无合同记录</div>
    <div v-else class="contract-list">
      <div
        v-for="item in list"
        :key="item.id"
        class="contract-card"
        @click="view(item.id)"
      >
        <div class="contract-top">
          <span class="contract-name">{{ item.contract_name || '劳动合同' }}</span>
          <span class="contract-status" :class="item.status">{{ statusText(item.status) }}</span>
        </div>
        <div class="contract-info">
          <div class="info-row">
            <span class="label">合同类型</span>
            <span class="value">{{ item.contract_type || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="label">开始日期</span>
            <span class="value">{{ item.start_date || '--' }}</span>
          </div>
          <div class="info-row">
            <span class="label">结束日期</span>
            <span class="value">{{ item.end_date || '无固定期限' }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { contractsAPI } from '@/api/contracts'

const router = useRouter()
const loading = ref(false)
const list = ref<any[]>([])

function statusText(s: string) {
  const map: Record<string, string> = {
    draft: '草稿',
    signed: '已签署',
    expired: '已到期',
    terminated: '已终止',
  }
  return map[s] || s
}

function view(id: number) {
  router.push(`/management/contracts/${id}`)
}

async function load() {
  loading.value = true
  try {
    const res = await contractsAPI.listContracts({ page_size: 50 })
    list.value = res.data?.data?.items || []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.my-contract-page {
  min-height: 100vh;
  background: #000000;
  padding: 16px 16px 96px;
}
.page-header {
  margin-bottom: 20px;
}
.page-title {
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}
.loading, .empty {
  color: #7A7C80;
  text-align: center;
  padding: 40px 0;
}
.contract-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.contract-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 16px;
  cursor: pointer;
  transition: border-color 0.2s;
}
.contract-card:hover {
  border-color: #FB0079;
}
.contract-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}
.contract-name {
  font-size: 15px;
  font-weight: 600;
  color: #FFFFFF;
}
.contract-status {
  font-size: 12px;
  padding: 2px 8px;
  border-radius: 6px;
  background: #333333;
  color: #C8C8C8;
}
.contract-status.signed {
  background: rgba(0, 200, 83, 0.12);
  color: #00C853;
}
.contract-status.expired,
.contract-status.terminated {
  background: rgba(122, 124, 128, 0.12);
  color: #7A7C80;
}
.contract-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.info-row {
  display: flex;
  justify-content: space-between;
}
.label {
  font-size: 13px;
  color: #7A7C80;
}
.value {
  font-size: 13px;
  color: #C8C8C8;
}
</style>
