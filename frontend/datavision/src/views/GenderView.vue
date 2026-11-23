<script setup>
import { computed, ref, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, axisCommon, tooltipBase, gridBase, markLineYear, pct, number } from '../utils/chart'

const store = useDashboardStore()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)

watch(keyword, () => { page.value = 1 })

const genderRows = computed(() => store.filteredYears)

/* 弧线口径：小项口径看女性奖牌占比，行口径看女性参赛占比 */
const arcMetric = computed(() =>
  store.isEvent
    ? {
        label: '女性奖牌占比',
        short: '小项口径',
        hint: '女性获得的小项口径奖牌 ÷ 当届小项口径奖牌总数',
        value: (row) => (row.totalEvent ? row.femaleEvent / row.totalEvent : 0)
      }
    : {
        label: '女性参赛占比',
        short: '运动员行口径',
        hint: '女性参赛记录 ÷ 当届参赛记录总数',
        value: (row) => row.femaleRatio
      }
)

const kpis = computed(() => {
  const h = store.highlights.gender ?? {}
  const womenShare = store.womenSupply.find((row) => row.year === 2024)?.womenShare
  const first = genderRows.value[0]
  const last = genderRows.value[genderRows.value.length - 1]
  const value = arcMetric.value.value
  return [
    { label: `${first?.year ?? '—'} ${arcMetric.value.label}`, value: pct(value(first ?? {})), hint: arcMetric.value.short },
    { label: `${last?.year ?? '—'} ${arcMetric.value.label}`, value: pct(value(last ?? {})), hint: arcMetric.value.short },
    { label: '女性首次参赛', value: h['女性首次出现年份'] ?? 1900, unit: '年', hint: '巴黎奥运会' },
    { label: '女子小项占比', value: pct(h['女子小项占比2024'] ?? womenShare ?? 0), hint: '2024 巴黎' },
    { label: '占比阶跃次数', value: '3', unit: '次', hint: '1952 · 1976 · 1996' }
  ]
})

const arcOption = computed(() => {
  const rows = genderRows.value
  const metric = arcMetric.value
  return {
    animationDuration: 600,
    grid: gridBase({ top: 34, right: 24 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => `${params[0].name} 届<br/>${metric.label} <b>${pct(params[0].value)}</b><br/><span style="color:#64748b">${metric.hint}</span>`
    }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
    },
    yAxis: {
      type: 'value', max: 0.6, ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => `${Math.round(value * 100)}%` }
    },
    series: [
      {
        name: metric.label,
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 5,
        lineStyle: { width: 2, color: COLORS.blue },
        itemStyle: { color: COLORS.blue },
        areaStyle: {
          color: {
            type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
            colorStops: [
              { offset: 0, color: 'rgba(37,99,235,.22)' },
              { offset: 1, color: 'rgba(37,99,235,.02)' }
            ]
          }
        },
        data: rows.map((row) => metric.value(row)),
        markLine: markLineYear(store.selectedYear),
        markPoint: {
          symbolSize: 9,
          itemStyle: { color: COLORS.gold },
          label: { show: true, position: 'top', fontSize: 10, color: COLORS.warn, formatter: (params) => `${params.name}` },
          data: [1952, 1976, 1996].map((year) => {
            const index = rows.findIndex((item) => item.year === year)
            if (index < 0) return null
            const row = rows[index]
            const prev = rows[index - 1]
            const jump = prev ? (metric.value(row) - metric.value(prev)) * 100 : 0
            return { coord: [String(year), metric.value(row)], value: metric.value(row), name: `${year} +${jump.toFixed(1)}pp` }
          }).filter(Boolean)
        }
      }
    ]
  }
})

const supplyOption = computed(() => {
  const rows = store.filteredYears
  const supply = new Map(store.womenSupply.map((row) => [row.year, row]))
  return {
    grid: gridBase({ top: 36, right: 46 }),
    tooltip: tooltipBase({ trigger: 'axis' }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
    },
    yAxis: [
      { type: 'value', ...axisCommon },
      { type: 'value', max: 0.6, ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, formatter: (value) => `${Math.round(value * 100)}%` } }
    ],
    series: [
      {
        name: '全部小项',
        type: 'bar',
        barMaxWidth: 12,
        itemStyle: { color: COLORS.bluePale },
        data: rows.map((row) => supply.get(row.year)?.allEvents ?? 0)
      },
      {
        name: '女子小项',
        type: 'bar',
        barMaxWidth: 12,
        itemStyle: { color: COLORS.blue },
        data: rows.map((row) => supply.get(row.year)?.womenEvents ?? 0)
      },
      {
        name: '女子小项占比',
        type: 'line',
        yAxisIndex: 1,
        smooth: true,
        symbol: 'none',
        lineStyle: { color: COLORS.gold, width: 1.6 },
        data: rows.map((row) => supply.get(row.year)?.womenShare ?? 0)
      }
    ]
  }
})

/* 饼图：默认按左侧区间汇总，也可选具体年份；年份选项受区间约束（单向） */
const pieMode = ref('range')

watch(
  () => [store.range[0], store.range[1]],
  () => { pieMode.value = 'range' },
  { immediate: true }
)

const pieYears = computed(() => store.filteredYears.map((row) => row.year))

const pieLabel = computed(() =>
  pieMode.value === 'range' ? `区间汇总 ${store.range[0]}–${store.range[1]}` : `${pieMode.value} 届`
)

const pieRows = computed(() => {
  if (pieMode.value === 'range') {
    const map = new Map()
    for (const row of store.filteredCountries) {
      const bucket = map.get(row.noc) ?? { noc: row.noc, team: row.team, records: 0, female: 0 }
      bucket.records += row.records
      bucket.female += row.female
      map.set(row.noc, bucket)
    }
    return [...map.values()]
      .filter((row) => row.records >= 20 && row.female > 0)
      .map((row) => ({ ...row, femaleRatio: row.records ? row.female / row.records : 0 }))
      .sort((a, b) => b.female - a.female)
  }
  return store.countryYear
    .filter((row) => row.year === pieMode.value && row.records >= 20 && row.female > 0)
    .map((row) => ({ ...row }))
    .sort((a, b) => b.female - a.female)
})

const pieOption = computed(() => {
  const rows = pieRows.value
  const total = rows.reduce((sum, row) => sum + row.female, 0)
  const top = rows.slice(0, 8)
  const rest = rows.slice(8).reduce((sum, row) => sum + row.female, 0)
  const data = top.map((row) => ({
    name: `${row.team} · ${row.noc}`,
    value: row.female,
    noc: row.noc
  }))
  if (rest > 0) data.push({ name: '其他代表团', value: rest, noc: null })

  return {
    animationDuration: 600,
    tooltip: tooltipBase({
      formatter: (params) => {
        const row = params.data
        return `${params.name}<br/>女性参赛记录 <b>${number(row.value)}</b><br/>占当年女性总量 ${pct(total ? row.value / total : 0)}`
      }
    }),
    legend: {
      type: 'scroll',
      bottom: 0,
      itemWidth: 9,
      itemHeight: 8,
      textStyle: { fontSize: 10, color: COLORS.muted }
    },
    series: [
      {
        type: 'pie',
        radius: ['34%', '64%'],
        center: ['50%', '44%'],
        avoidLabelOverlap: true,
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        label: { fontSize: 10, color: COLORS.muted, formatter: '{b}\n{d}%' },
        labelLine: { length: 8, length2: 6 },
        data
      }
    ]
  }
})

const filteredRatioRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return pieRows.value
  return pieRows.value.filter((row) => row.noc.toLowerCase().includes(text) || row.team.toLowerCase().includes(text))
})

const pagedRatioRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRatioRows.value.slice(start, start + pageSize.value)
})

function onYearClick(params) {
  const year = Number(params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
}

function onPieClick(params) {
  if (params.data?.noc) store.toggleNOC(params.data.noc)
}
</script>

<template>
  <div>
    <PageHeader
      title="她的奥运"
      subtitle="女性参赛占比从 1896 年的 0% 走到 2024 年的约 49%。弧线会随左侧口径切换：小项口径看女性奖牌占比，运动员行口径看女性参赛占比。"
    />

    <KpiStrip :items="kpis" />

    <!-- 统计表格最先展示 -->
    <PanelBlock
      :title="`各代表团女性参赛明细 · ${pieLabel}`"
      :note="`共 ${filteredRatioRows.length} 个代表团（参赛记录 ≥ 20 且范围内有女性参赛）。点击行可加入国家联动。`"
      flush
    >
      <template #actions>
        <el-input v-model="keyword" size="small" placeholder="搜索 NOC / 代表团" clearable style="width: 190px" />
      </template>
      <el-table
        :data="pagedRatioRows"
        size="small"
        max-height="360"
        :row-class-name="({ row }) => (store.selectedNOCs.includes(row.noc) ? 'row-selected' : '')"
        @row-click="(row) => store.toggleNOC(row.noc)"
      >
        <el-table-column prop="noc" label="NOC" width="80" align="center" />
        <el-table-column prop="team" label="代表团" min-width="170" />
        <el-table-column prop="records" label="参赛记录" width="110" align="center" />
        <el-table-column prop="female" label="女性记录" width="110" align="center" />
        <el-table-column prop="femaleRatio" label="女性占比" width="110" align="center">
          <template #default="{ row }">{{ pct(row.femaleRatio) }}</template>
        </el-table-column>
      </el-table>
      <div class="table-foot">
        <span class="small muted">口径：运动员行（每一行 = 一人次 × 一小项）</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="filteredRatioRows.length"
          layout="prev, pager, next"
          small
        />
      </div>
    </PanelBlock>

    <!-- 图 1：百年弧线 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock :title="`${arcMetric.label}百年弧线`" :note="`${arcMetric.hint}；金色标记为三次最大阶跃，红色虚线为当前选中届次。`">
          <BaseChart :option="arcOption" height="360px" @chart-click="onYearClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>口径与读图</h3>
        <p>图表跟随左上角统计口径自动切换指标，切换后无需重新加载。</p>
        <div class="side-field">
          <label>统计口径</label>
          <el-radio-group :model-value="store.caliber" size="small" @change="store.setCaliber">
            <el-radio-button value="event">小项口径</el-radio-button>
            <el-radio-button value="athlete">运动员行口径</el-radio-button>
          </el-radio-group>
        </div>
        <div class="side-field">
          <label>当前指标</label>
          <span class="tag is-blue">{{ arcMetric.label }} · {{ arcMetric.short }}</span>
        </div>
        <p class="side-hint">{{ arcMetric.hint }}</p>
        <p class="side-hint">1952、1976、1996 三届出现明显阶跃，可点击曲线锁定届次。</p>
      </aside>
    </section>

    <!-- 图 2：女子小项供给 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="女子小项供给"
          note="柱为小项数量（浅色=全部，深色=女子），线为女子小项占比。2020/2024 的泛化命名会影响小项计数。"
        >
          <BaseChart :option="supplyOption" height="340px" @chart-click="onYearClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>读图说明</h3>
        <p>供给端先于参与端变化：女子小项数增加，才会带来女性参赛记录的增长。</p>
        <p class="side-hint">2020 / 2024 两届的 Event 泛化会让女子小项计数偏低，比较时只看趋势。</p>
      </aside>
    </section>

    <!-- 图 3：国别女性占比饼图 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          :title="`各国女性参赛占比 · ${pieLabel}`"
          note="饼图按女性参赛记录量分配；默认汇总左侧年份区间，也可切到单届查看。仅统计参赛记录 ≥ 20 的代表团。"
        >
          <BaseChart :option="pieOption" height="380px" @chart-click="onPieClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>年份选择</h3>
        <div class="side-field">
          <label>统计范围（受左侧区间约束）</label>
          <el-select v-model="pieMode" size="small">
            <el-option label="区间汇总" value="range" />
            <el-option v-for="year in pieYears" :key="year" :label="`${year} 届`" :value="year" />
          </el-select>
          <span class="side-hint">切换此处范围不会修改左侧全局区间；左侧区间变化时，这里会自动回到「区间汇总」。</span>
        </div>
        <p class="side-hint">占比分母为所选年份的女性参赛记录总量，扇区越大代表该国当年女性参赛规模越大。</p>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.table-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px 4px;
  border-top: 1px solid var(--line);
}
:deep(.row-selected) { background: var(--brand-50) !important; }
:deep(.el-table__row) { cursor: pointer; }
</style>
