<template>
  <div class="notification-page">
    <div class="header">
      <h1 class="page-title">消息中心</h1>
      <button class="read-all-btn" @click="markAllRead">全部已读</button>
    </div>

    <div class="notification-list">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="list.length === 0" class="empty">暂无消息</div>
      <div
        v-for="item in list"
        :key="item.id"
        class="notification-card"
        :class="{ unread: !item.is_read }"
        @click="markRead(item)"
      >
        <div class="card-title">{{ item.title }}</div>
        <div class="card-content">{{ item.content }}</div>
        <div class="card-time">{{ item.created_at }}</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { notificationAPI, type NotificationItem } from '@/api/notifications'

const list = ref<NotificationItem[]>([])
const loading = ref(false)

async function loadData() {
  loading.value = true
  try {
    const res = await notificationAPI.getList()
    list.value = res.data.data.items
  } catch (e) {
    console.error('[Notifications] loadData failed:', e)
    ElMessage.error('加载消息失败')
  } finally {
    loading.value = false
  }
}

async function markRead(item: NotificationItem) {
  if (item.is_read) return
  try {
    await notificationAPI.markRead(item.id)
    item.is_read = true
  } catch (e) {
    console.error('[Notifications] markRead failed:', e)
    ElMessage.error('标记已读失败')
  }
}

async function markAllRead() {
  try {
    await notificationAPI.markAllRead()
    list.value.forEach((item) => (item.is_read = true))
  } catch (e) {
    console.error('[Notifications] markAllRead failed:', e)
    ElMessage.error('全部已读失败')
  }
}

onMounted(loadData)
</script>

<style scoped>
.notification-page {
  padding: 16px;
  padding-bottom: 24px;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0;
}

.read-all-btn {
  background: transparent;
  border: none;
  color: #FB0079;
  font-size: 13px;
  cursor: pointer;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.loading,
.empty {
  text-align: center;
  color: #7A7C80;
  padding: 32px;
}

.notification-card {
  background: #111111;
  border: 1px solid #333333;
  border-radius: 12px;
  padding: 12px;
  cursor: pointer;
}

.notification-card.unread {
  border-left: 3px solid #FB0079;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: #FFFFFF;
  margin-bottom: 4px;
}

.card-content {
  font-size: 12px;
  color: #C8C8C8;
  line-height: 1.5;
  white-space: pre-line;
}

.card-time {
  font-size: 11px;
  color: #7A7C80;
  margin-top: 6px;
}
</style>
