<script setup>
import { Odometer, Trophy, TrendCharts, Female, Grid, Switch, Flag } from '@element-plus/icons-vue'
import { useDashboardStore } from '../stores/dashboard'

const store = useDashboardStore()

const groups = [
  {
    label: '总览',
    items: [{ path: '/overview', label: '全局概览', icon: Odometer }]
  },
  {
    label: '任务二 · 四视角',
    items: [
      { path: '/medals', label: '奖牌格局', icon: Trophy },
      { path: '/countries', label: '国家兴衰', icon: TrendCharts },
      { path: '/gender', label: '她的奥运', icon: Female },
      { path: '/sports', label: '项目演化', icon: Grid }
    ]
  },
  {
    label: '任务三 · 专题',
    items: [
      { path: '/caliber', label: '口径的魔力', icon: Switch },
      { path: '/host', label: '东道主效应', icon: Flag }
    ]
  }
]
</script>

<template>
  <nav class="side-nav">
    <div v-for="group in groups" :key="group.label">
      <div class="side-nav-section">{{ group.label }}</div>
      <div class="side-nav-list">
        <router-link
          v-for="item in group.items"
          :key="item.path"
          :to="item.path"
          class="side-nav-item"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.label }}</span>
        </router-link>
      </div>
    </div>

    <div class="side-nav-foot">
      <strong>{{ store.meta.officialEditions || 30 }} 届官方奥运会</strong>
      1896–2024 · 排除 1906 届间奥运会<br />
      数据源 Kaggle · CC BY-NC-SA 4.0
    </div>
  </nav>
</template>
