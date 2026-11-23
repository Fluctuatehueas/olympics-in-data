<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useDashboardStore } from '../stores/dashboard'

const store = useDashboardStore()
const route = useRoute()
const router = useRouter()

// 顶部菜单 = 页面切换；左侧口径 / 年份控制跨页面保留
const items = [
  { path: '/overview', label: '全局概览' },
  { path: '/medals', label: '奖牌格局' },
  { path: '/countries', label: '国家兴衰' },
  { path: '/gender', label: '她的奥运' },
  { path: '/sports', label: '项目演化' },
  { path: '/caliber', label: '口径的魔力' },
  { path: '/host', label: '东道主效应' },
  { path: '/small-teams', label: '小团突破' }
]

const activePath = computed(() => route.path)
const online = computed(() => !store.error && Boolean(store.data))

function goTo(path) {
  if (route.path !== path) router.push(path)
}
</script>

<template>
  <header class="topnav">
    <div class="topnav-inner">
      <button type="button" class="brand" @click="goTo('/overview')">
        <span class="brand-mark">数</span>
        <span class="brand-text">
          <strong>数说奥运</strong>
          <small>1896–2024 · SUMMER OLYMPICS</small>
        </span>
      </button>

      <nav class="topnav-menu">
        <button
          v-for="item in items"
          :key="item.path"
          type="button"
          class="topnav-item"
          :class="{ 'is-active': activePath === item.path }"
          @click="goTo(item.path)"
        >
          {{ item.label }}
        </button>
      </nav>

      <div class="topnav-right">
        <span class="conn" :class="{ 'is-error': !online }">
          <i></i>{{ online ? '数据已连接' : '数据未就绪' }}
        </span>
        <span class="topnav-meta">{{ store.meta.officialEditions || 30 }} 届官方届次</span>
      </div>
    </div>
  </header>
</template>
