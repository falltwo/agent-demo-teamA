<script setup lang="ts">
import { RouterView } from "vue-router";

import AppShell from "@/components/layout/AppShell.vue";
import ToastHost from "@/components/ui/ToastHost.vue";
</script>

<template>
  <div class="ds-a app-root">
    <AppShell>
      <RouterView />
    </AppShell>
    <ToastHost />
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
}
</style>
