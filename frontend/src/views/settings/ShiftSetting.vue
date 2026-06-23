<template>
  <div class="shift-setting-page">
    <h1 class="page-title">班次设置</h1>
    <p class="page-tip">仅老板可修改门店班次时间</p>
    <ShiftSettingPanel @saved="router.back()" />
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import ShiftSettingPanel from '@/views/schedule/ShiftSettingPanel.vue'

const router = useRouter()
</script>

<style scoped>
.shift-setting-page {
  padding: 16px;
}

.page-title {
  font-size: 18px;
  font-weight: 700;
  color: #FFFFFF;
  margin: 0 0 4px;
}

.page-tip {
  font-size: 12px;
  color: #7A7C80;
  margin-bottom: 16px;
}
</style>
