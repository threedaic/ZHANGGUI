<script setup lang="ts">
import { useRouter } from 'vue-router'

const router = useRouter()

const menus = [
  { key: 'payroll-config', label: '工资项配置', desc: '配置工资项与计算公式', path: '/settings/payroll-config' },
]
</script>

<template>
  <div class="settings-home">
    <div
      v-for="m in menus"
      :key="m.key"
      class="menu-card"
      @click="router.push(m.path)"
    >
      <div class="menu-label">{{ m.label }}</div>
      <div class="menu-desc">{{ m.desc }}</div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.settings-home {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.menu-card {
  background-color: $color-bg;
  border-radius: $radius-md;
  padding: 16px;
  cursor: pointer;
  border: 1px solid $color-divider;

  &:hover {
    border-color: $brand-primary;
  }

  .menu-label {
    font-size: 15px;
    color: $brand-white;
    font-weight: 600;
    margin-bottom: 4px;
  }

  .menu-desc {
    font-size: 12px;
    color: #888;
  }
}
</style>
