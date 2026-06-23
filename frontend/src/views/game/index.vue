<template>
  <div class="game-page">
    <div class="page-header">
      <h1 class="page-title">游戏</h1>
      <span class="page-subtitle">发起游戏、管理参与者、发放奖品</span>
    </div>
    <div class="empty-state">
      <p>游戏模块开发中...</p>
      <p class="hint">依据 SPEC 2.0 §9.1 员工端验收标准</p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped lang="scss">
.game-page {
  padding: 16px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: $brand-white;
  margin: 0 0 4px;
}

.page-subtitle {
  color: #7A7C80;
  font-size: 13px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  color: #7A7C80;
  font-size: 14px;
}

.empty-state .hint {
  font-size: 12px;
  margin-top: 8px;
  color: #555;
}
</style>
