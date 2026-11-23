<script setup>
import { computed, ref } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import { number } from '../utils/chart'

const store = useDashboardStore()
// 下拉只负责「添加」：选中后进入下方列表，清单本身负责多选与移除
const pendingNOC = ref(null)

const startOptions = computed(() => store.yearOptions.filter((year) => year <= store.range[1]))
const endOptions = computed(() => store.yearOptions.filter((year) => year >= store.range[0]))

// 数据域下拉用全量参赛国家（含从未夺牌的 NOC），按国家名排序
const nocChoices = computed(() => {
  const map = new Map()
  for (const row of store.countryYear) {
    if (!map.has(row.noc)) map.set(row.noc, { noc: row.noc, team: row.team })
  }
  return [...map.values()].sort((a, b) => a.team.localeCompare(b.team, 'zh-CN'))
})

// 用 2024 美国与全局总量做口径示例，数字全部来自当前数据
const usa2024 = computed(() =>
  store.countryYear.find((row) => row.year === 2024 && row.noc === 'USA') ?? null
)

function addNOC(noc) {
  if (noc && !store.selectedNOCs.includes(noc)) {
    store.setNOCs([...store.selectedNOCs, noc])
  }
  pendingNOC.value = null
}

function removeNOC(noc) {
  store.setNOCs(store.selectedNOCs.filter((item) => item !== noc))
}

function changeStart(year) {
  store.setRange([year, store.range[1]])
}

function changeEnd(year) {
  store.setRange([store.range[0], year])
}
</script>

<template>
  <aside class="rail">
    <div class="rail-block">
      <div class="rail-title">统计口径</div>
      <el-radio-group
        :model-value="store.caliber"
        class="rail-caliber"
        @change="store.setCaliber"
      >
        <el-radio-button value="event">小项口径</el-radio-button>
        <el-radio-button value="athlete">运动员行口径</el-radio-button>
      </el-radio-group>

      <div class="caliber-help">
        <div class="caliber-card" :class="{ 'is-active': store.isEvent }">
          <div class="caliber-card-head">
            <b>小项口径</b>
            <em>数“夺金点”</em>
          </div>
          <p>同一届 · 同一小项 · 同一奖牌色 · 同一 NOC 只计 1 枚，团体成员合并。</p>
        </div>
        <div class="caliber-card" :class="{ 'is-active': !store.isEvent }">
          <div class="caliber-card-head">
            <b>运动员行口径</b>
            <em>数“夺金人次”</em>
          </div>
          <p>每条奖牌记录计 1 枚，团体项目每位成员各计 1 枚。</p>
        </div>
        <p class="caliber-foot">
          同一批人：2024 USA 金牌
          {{ usa2024 ? `${usa2024.goldEvent} → ${usa2024.goldAthlete}` : '37 → 131' }}；
          全局 {{ number(store.meta.totals?.eventMedals ?? 17901) }} →
          {{ number(store.meta.totals?.athleteMedals ?? 38360) }}，相差
          {{ store.meta.totals?.shrinkPct ?? 53.3 }}%。
        </p>
      </div>
    </div>

    <div class="rail-block">
      <div class="rail-title">届次区间</div>
      <div class="rail-range">
        <el-select :model-value="store.range[0]" size="small" @change="changeStart">
          <el-option v-for="year in startOptions" :key="year" :label="String(year)" :value="year" />
        </el-select>
        <span class="rail-dash">—</span>
        <el-select :model-value="store.range[1]" size="small" @change="changeEnd">
          <el-option v-for="year in endOptions" :key="year" :label="String(year)" :value="year" />
        </el-select>
      </div>
      <div class="rail-presets">
        <button type="button" @click="store.setRange([store.minYear, store.maxYear])">全程</button>
        <button type="button" @click="store.setRange([1980, store.maxYear])">1980 后</button>
        <button type="button" @click="store.setRange([2000, store.maxYear])">2000 后</button>
      </div>
    </div>

    <div class="rail-block">
      <div class="rail-title">当前数据域 <span class="rail-title-hint">可多选</span></div>
      <el-select
        :model-value="pendingNOC"
        filterable
        clearable
        placeholder="搜索并添加国家 / 地区"
        size="small"
        @change="addNOC"
      >
        <el-option
          v-for="item in nocChoices"
          :key="item.noc"
          :label="`${item.team} · ${item.noc}`"
          :value="item.noc"
        />
      </el-select>

      <div v-if="store.selectedNOCs.length" class="domain-list">
        <div class="domain-list-head">
          <span>已选 {{ store.selectedNOCs.length }} 个国家 / 地区</span>
          <button type="button" @click="store.setNOCs([])">清空</button>
        </div>
        <button
          v-for="noc in store.selectedNOCs"
          :key="noc"
          type="button"
          class="domain-row"
          :title="`点击移除 ${store.nocLabel(noc)}`"
          @click="removeNOC(noc)"
        >
          <span class="domain-team">{{ store.nocLabel(noc) }}</span>
          <span class="domain-noc">{{ noc }}</span>
        </button>
      </div>
      <span v-else class="rail-empty">未锁定国家，图表按全部国家展示</span>

      <div v-if="store.selectedYear" class="rail-domain">
        <span class="chip is-year">
          {{ store.selectedYear }} 届
          <button type="button" title="取消届次" @click="store.setYear(store.selectedYear)">×</button>
        </span>
      </div>
    </div>

    <div class="rail-block rail-stats">
      <div><span>区间奖牌</span><strong>{{ number(store.kpi.medals) }}</strong></div>
      <div><span>参赛记录</span><strong>{{ number(store.kpi.records) }}</strong></div>
      <div><span>覆盖届次</span><strong>{{ store.kpi.editions }}</strong></div>
    </div>

    <div class="rail-foot">
      <el-button size="small" text @click="store.clearSelection()">清除联动</el-button>
      <el-button size="small" text @click="store.resetFilters()">重置全部</el-button>
    </div>
  </aside>
</template>
