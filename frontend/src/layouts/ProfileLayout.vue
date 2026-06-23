<script setup lang="ts">
import AppShell from '@/components/AppShell.vue'
</script>

<template>
  <AppShell title="我的">
    <Transition name="page-fade" mode="out-in">
      <RouterView />
    </Transition>
  </AppShell>
</template>
