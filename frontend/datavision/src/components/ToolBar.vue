<script setup>
import { computed } from 'vue'
import { useDashboardStore } from '../stores/dashboard'

const store = useDashboardStore()

const startOptions = computed(() => store.yearOptions.filter((year) => year <= store.range[1]))
const endOptions = computed(() => store.yearOptions.filter((year) => year >= store.range[0]))

const hasSelection = computed(
  () => Boolean(store.selectedYear) || store.selectedNOCs.length > 0 || Boolean(store.selectedSport)
)

function changeStart(year) {
  store.setRange([year, store.range[1]])
}

function changeEnd(year) {
  store.setRange([store.range[0], year])
}
</script>

<template>
  <div class="toolbar">
    <span class="toolbar-label">届次区间</span>
    <div class="toolbar-group">
      <el-select :model-value="store.range[0]" size="small" style="width: 92px" @change="changeStart">
        <el-option v-for="year in startOptions" :key="year" :label="String(year)" :value="year" />
      </el-select>
      <span class="toolbar-label">—</span>
      <el-select :model-value="store.range[1]" size="small" style="width: 92px" @change="changeEnd">
        <el-option v-for="year in endOptions" :key="year" :label="String(year)" :value="year" />
      </el-select>
    </div>

    <div class="toolbar-divider"></div>
    <span class="toolbar-label">联动</span>

    <template v-if="hasSelection">
      <div class="toolbar-group">
        <span v-if="store.selectedYear" class="chip is-year">
          {{ store.selectedYear }} 届
          <button type="button" title="取消届次" @click="store.setYear(store.selectedYear)">×</button>
        </span>
        <span v-for="noc in store.selectedNOCs" :key="noc" class="chip">
          {{ store.nocLabel(noc) }}
          <button type="button" title="移除国家" @click="store.toggleNOC(noc)">×</button>
        </span>
        <span v-if="store.selectedSport" class="chip">
          {{ store.selectedSport }}
          <button type="button" title="取消项目" @click="store.setSport(store.selectedSport)">×</button>
        </span>
      </div>
    </template>
    <span v-else class="toolbar-hint">点击图表中的届次 / 国家 / 项目即可联动</span>

    <div class="toolbar-spacer"></div>
    <el-button size="small" text @click="store.clearSelection()">清除联动</el-button>
    <el-button size="small" text @click="store.resetFilters()">重置全部</el-button>
  </div>
</template>
