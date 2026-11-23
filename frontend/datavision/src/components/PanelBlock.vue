<script setup>
defineProps({
  title: { type: String, default: '' },
  note: { type: String, default: '' },
  flush: { type: Boolean, default: false }
})
</script>

<template>
  <section class="panel">
    <header class="panel-head">
      <div>
        <div class="panel-title">{{ title }}</div>
        <div v-if="note" class="panel-note">{{ note }}</div>
      </div>
      <div class="panel-actions">
        <slot name="actions" />
      </div>
    </header>
    <div class="panel-body" :class="{ 'is-flush': flush }">
      <slot />
    </div>
  </section>
</template>
