<template>
  <div class="tables-setting">
    <!-- 直接复用管理页的 Tables 组件 -->
    <Tables />
  </div>
</template>

<script setup lang="ts">
import Tables from '@/views/management/Tables.vue'
</script>

<style scoped>
.tables-setting {
  padding: 0;
}
</style>
