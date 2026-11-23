<script setup>
import { onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import AppHeader from './components/AppHeader.vue'
import ControlRail from './components/ControlRail.vue'
import StickyNotes from './components/StickyNotes.vue'
import { useDashboardStore } from './stores/dashboard'

const store = useDashboardStore()

onMounted(async () => {
  await store.load()
  if (store.error) ElMessage.error(`数据加载失败：${store.error}`)
})
</script>

<template>
  <div class="app-shell">
    <AppHeader />
    <div class="app-body">
      <ControlRail />
      <main class="flow">
        <div v-if="store.loading" class="state-panel">正在从 Python 后端加载数据…</div>
        <div v-else-if="store.error" class="state-panel state-error">
          <div>数据加载失败：{{ store.error }}</div>
          <el-button size="small" @click="store.load(true)">重试</el-button>
        </div>
        <router-view v-else />
      </main>
      <StickyNotes />
    </div>
  </div>
</template>
