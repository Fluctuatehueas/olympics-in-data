<script setup>
defineProps({
  items: { type: Array, default: () => [] }
})
</script>

<template>
  <div class="kpi-strip">
    <div v-for="item in items" :key="item.label" class="kpi-item">
      <div class="kpi-label">{{ item.label }}</div>
      <div class="kpi-value">
        {{ item.value }}
        <small v-if="item.unit">{{ item.unit }}</small>
      </div>
      <div v-if="item.hint" class="kpi-hint">{{ item.hint }}</div>
    </div>
  </div>
</template>
