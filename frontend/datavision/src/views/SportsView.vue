<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, axisCommon, tooltipBase, gridBase, markLineYear, number } from '../utils/chart'

const store = useDashboardStore()
const keyword = ref('')
const page = ref(1)
const pageSize = ref(10)
const statusFilter = ref('all')

watch([keyword, statusFilter], () => { page.value = 1 })

const kpis = computed(() => {
  const retired = store.sports.filter((item) => item.retired)
  const art = store.sports.find((item) => item.sport === 'Art Competitions')
  return [
    { label: '运动大类', value: number(store.meta.sports), hint: '原始 76 类归一后' },
    { label: '已退场运动', value: number(retired.length), hint: '末次举办早于 2024' },
    { label: '2024 仍在办', value: number(store.meta.activeSports), hint: '巴黎奥运会' },
    { label: '艺术竞赛记录', value: number(art?.records ?? 3578), hint: '1912–1948 · 体量最大的消失项目' },
    { label: '最新入奥', value: '3 项新运动', hint: '滑板 / 冲浪 / 霹雳舞 · 2020–2024' }
  ]
})

/* ---------- 动态排序柱状图 ---------- */
const raceYears = computed(() => store.filteredYears.map((row) => row.year))

const raceByYear = computed(() => {
  const map = new Map()
  for (const row of store.sportYear) {
    if (!map.has(row.year)) map.set(row.year, [])
    map.get(row.year).push(row)
  }
  for (const rows of map.values()) rows.sort((a, b) => b.records - a.records)
  return map
})

const raceYear = ref(null)
const playing = ref(false)
const loop = ref(true)
// 年份切换间隔（毫秒）：越小推进越快，播放中调整会立即生效
const speed = ref(320)
let timer = null

watch(
  () => [store.range[0], store.range[1]],
  () => {
    stop()
    raceYear.value = store.range[1]
  },
  { immediate: true }
)

watch(raceYears, (years) => {
  if (years.length && !years.includes(raceYear.value)) raceYear.value = years[years.length - 1]
})

const raceRows = computed(() => {
  const rows = raceByYear.value.get(raceYear.value) ?? []
  return rows.slice(0, 12)
})

const raceOption = computed(() => {
  const rows = raceRows.value.slice().reverse() // 反转后第一名在顶部
  const max = Math.max(1, ...rows.map((row) => row.records))
  const selected = store.selectedSport
  const colorOf = (sport) => {
    if (sport === selected) return COLORS.host
    const item = store.sports.find((entry) => entry.sport === sport)
    return item?.retired ? '#94A3B8' : COLORS.blue
  }
  return {
    animation: true,
    animationDurationUpdate: 420,
    animationEasingUpdate: 'cubicOut',
    grid: { left: 118, right: 72, top: 18, bottom: 28 },
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        if (!row) return ''
        return `${row.sport}<br/>竞赛记录 <b>${number(row.records)}</b><br/>小项奖牌 ${number(row.totalEvent)}<br/>${row.sport === selected ? '已选中' : '点击可选中'}`
      }
    }),
    xAxis: {
      type: 'value',
      max: Math.ceil(max * 1.15),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => number(value) }
    },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.sport),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: {
        ...axisCommon.axisLabel,
        formatter: (value) => (value.length > 12 ? `${value.slice(0, 12)}…` : value)
      }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 16,
        label: { show: true, position: 'right', fontSize: 10, color: COLORS.muted, formatter: (params) => number(params.value) },
        data: rows.map((row) => ({ value: row.records, sport: row.sport, itemStyle: { color: colorOf(row.sport) } }))
      }
    ]
  }
})

function step() {
  const years = raceYears.value
  const index = years.indexOf(raceYear.value)
  if (index < 0) return
  if (index < years.length - 1) {
    raceYear.value = years[index + 1]
  } else if (loop.value) {
    raceYear.value = years[0]
  } else {
    stop()
  }
}

function stop() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
  playing.value = false
}

function togglePlay() {
  if (playing.value) {
    stop()
    return
  }
  if (!raceYears.value.length) return
  playing.value = true
  timer = setInterval(step, speed.value)
}

// 播放过程中调整间隔：重建定时器，避免新旧两个定时器同时推进
watch(speed, () => {
  if (!playing.value) return
  clearInterval(timer)
  timer = setInterval(step, speed.value)
})

onBeforeUnmount(stop)

function onRaceClick(params) {
  const sport = params.data?.sport
  if (sport) store.setSport(sport === store.selectedSport ? null : sport)
}

/* ---------- 小项数量与泛化占比 ---------- */
const eventCountOption = computed(() => {
  const rows = store.filteredYears
  const lookup = new Map(store.eventCount.map((row) => [row.year, row]))
  return {
    grid: gridBase({ top: 34, right: 46 }),
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
      { type: 'value', max: 0.4, ...axisCommon, splitLine: { show: false }, axisLabel: { ...axisCommon.axisLabel, formatter: (value) => `${Math.round(value * 100)}%` } }
    ],
    series: [
      {
        name: '小项数量',
        type: 'line',
        smooth: true,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { color: COLORS.blue, width: 2 },
        itemStyle: { color: COLORS.blue },
        areaStyle: { color: 'rgba(37,99,235,.10)' },
        data: rows.map((row) => lookup.get(row.year)?.uniqueEvents ?? 0),
        markLine: markLineYear(store.selectedYear)
      },
      {
        name: '泛化行占比',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 10,
        itemStyle: { color: '#FCA5A5' },
        data: rows.map((row) => lookup.get(row.year)?.genericShare ?? 0)
      }
    ]
  }
})

function onYearClick(params) {
  const year = Number(params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
}

/* ---------- 运动明细表（前置） ---------- */
const filteredSports = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  return store.sports.filter((item) => {
    if (text && !item.sport.toLowerCase().includes(text)) return false
    if (statusFilter.value === 'retired') return item.retired
    if (statusFilter.value === 'active') return !item.retired
    return true
  })
})

const pagedSports = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredSports.value.slice(start, start + pageSize.value)
})

const selectedSport = computed(() => store.sports.find((item) => item.sport === store.selectedSport) ?? null)
</script>

<template>
  <div>
    <PageHeader
      title="项目演化"
      subtitle="57 个运动大类中已有 21 项退场：拔河 1900–1920、槌球只办过一届、艺术竞赛 1912–1948 累积 3,578 条记录。滑板、冲浪、霹雳舞正在登场。"
    />

    <KpiStrip :items="kpis" />

    <!-- 统计表格最先展示 -->
    <PanelBlock
      :title="`运动明细 · ${filteredSports.length} 项`"
      note="点击行选中运动，红色高亮会同步到下方动态排名与其它图表。"
      flush
    >
      <template #actions>
        <el-input v-model="keyword" size="small" placeholder="搜索运动名称" clearable style="width: 180px" />
        <el-select v-model="statusFilter" size="small" style="width: 110px">
          <el-option label="全部" value="all" />
          <el-option label="仍在办" value="active" />
          <el-option label="已退场" value="retired" />
        </el-select>
      </template>
      <el-table
        :data="pagedSports"
        size="small"
        max-height="360"
        :row-class-name="({ row }) => (row.sport === store.selectedSport ? 'row-selected' : '')"
        @row-click="(row) => store.setSport(row.sport)"
      >
        <el-table-column prop="sport" label="运动" min-width="180" sortable />
        <el-table-column prop="first" label="首办" width="80" align="center" sortable />
        <el-table-column prop="last" label="末办" width="80" align="center" sortable />
        <el-table-column prop="editions" label="届数" width="76" align="center" sortable />
        <el-table-column prop="records" label="记录数" width="100" align="center" sortable />
        <el-table-column prop="span" label="跨度" width="80" align="center" sortable />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <span class="tag" :class="row.retired ? '' : 'is-blue'">{{ row.retired ? '已退场' : '在办' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <div class="table-foot">
        <span class="small muted">归一后 57 类；原始 76 类含逗号拼接的跨项写法</span>
        <el-pagination v-model:current-page="page" :page-size="pageSize" :total="filteredSports.length" layout="prev, pager, next" small />
      </div>
    </PanelBlock>

    <!-- 图 1：动态排序柱状图 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          :title="`运动竞赛记录量动态排名 · ${raceYear ?? '—'}`"
          note="按当年竞赛记录数排序，保留前 12 名；播放时逐年推进，条形位置与长度带过渡动画。"
        >
          <BaseChart :option="raceOption" height="470px" :not-merge="false" @chart-click="onRaceClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>播放控制</h3>
        <div class="side-field is-inline">
          <label>动画播放</label>
          <el-button size="small" :type="playing ? 'danger' : 'primary'" @click="togglePlay">
            {{ playing ? '暂停' : '播放' }}
          </el-button>
        </div>
        <div class="side-field is-inline">
          <label>循环播放</label>
          <el-switch v-model="loop" size="small" />
        </div>
        <div class="side-field">
          <label>切换间隔：{{ speed }} ms</label>
          <el-slider v-model="speed" :min="200" :max="2000" :step="50" size="small" />
          <span class="side-hint">数值越小，年份推进越快；播放中调整会立即生效。</span>
        </div>
        <div class="side-field">
          <label>查看年份</label>
          <el-select v-model="raceYear" size="small">
            <el-option v-for="year in raceYears" :key="year" :label="String(year)" :value="year" />
          </el-select>
        </div>
        <p class="side-hint">
          当前届：{{ raceYear ?? '—' }}；共 {{ raceYears.length }} 届可选。
          {{ selectedSport ? `已选中：${selectedSport.sport}（${selectedSport.first}–${selectedSport.last}）` : '点击条形可选中运动。' }}
        </p>
      </aside>
    </section>

    <!-- 图 2：小项数量与泛化占比 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="小项数量与泛化占比"
          note="2020/2024 的 Event 泛化使小项计数不可直接与历史比较；红色柱为泛化行占比。点击届次联动。"
        >
          <BaseChart :option="eventCountOption" height="360px" @chart-click="onYearClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>读数说明</h3>
        <p>折线为当届去重后的小项数量，红柱为泛化 Event 的占比。</p>
        <p class="side-hint">2020 / 2024 两届泛化比例超过 20%，所以小项数曲线末端不能与前届直接比较。</p>
        <div class="side-field">
          <label>当前届次</label>
          <span class="tag is-blue">{{ store.selectedYear ?? '未锁定' }}</span>
        </div>
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
:deep(.row-selected) { background: #fef2f2 !important; }
:deep(.el-table__row) { cursor: pointer; }
</style>
