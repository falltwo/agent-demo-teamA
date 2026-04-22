<script setup lang="ts">
defineProps<{
  icon?: string;
  title: string;
  description?: string;
  actionLabel?: string;
}>();

const emit = defineEmits<{
  (e: "action"): void;
}>();
</script>

<template>
  <div class="empty-state">
    <div v-if="icon" class="empty-state__icon" v-html="icon" />
    <h3 class="empty-state__title">{{ title }}</h3>
    <p v-if="description" class="empty-state__description">{{ description }}</p>
    <button
      v-if="actionLabel"
      type="button"
      class="empty-state__action btn-primary"
      @click="emit('action')"
    >
      {{ actionLabel }}
    </button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: var(--space-6) var(--space-4);
  background: var(--color-bg-surface);
  border: 1px dashed var(--color-border-strong);
  border-radius: var(--radius-lg);
  margin: var(--space-4) 0;
}

.empty-state__icon {
  color: var(--color-text-muted);
  margin-bottom: var(--space-3);
  width: 48px;
  height: 48px;
}
.empty-state__icon :deep(svg) {
  width: 100%;
  height: 100%;
  stroke-width: 1.5;
}

.empty-state__title {
  font-size: var(--text-heading-sm-size);
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 var(--space-2);
}

.empty-state__description {
  font-size: var(--text-body-md-size);
  color: var(--color-text-secondary);
  margin: 0 0 var(--space-4);
  max-width: 400px;
}

.empty-state__action {
  padding: var(--space-2) var(--space-4);
  background: var(--color-brand);
  color: #fff;
  border: none;
  border-radius: var(--radius-md);
  font-weight: 600;
  cursor: pointer;
  transition: opacity 0.2s;
}

.empty-state__action:hover {
  opacity: 0.9;
}
</style>
