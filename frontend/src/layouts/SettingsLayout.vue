<script setup lang="ts">
import AppShell from '@/components/AppShell.vue'
</script>

<template>
  <AppShell>
    <Transition name="page-fade" mode="out-in">
      <RouterView />
    </Transition>
  </AppShell>
</template>
