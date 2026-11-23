<script setup>
import { computed, ref } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, SERIES_BLUE, axisCommon, tooltipBase, gridBase, markLineYear, number } from '../utils/chart'

const store = useDashboardStore()
const metric = ref('total')

const metricOptions = [
  { label: '奖牌总数', value: 'total' },
  { label: '金牌', value: 'gold' },
  { label: '参赛记录', value: 'athletes' }
]

const activeNOCs = computed(() => store.activeNOCs)

/* ---------- 逐届曲线 ---------- */
const lineOption = computed(() => {
  const years = store.filteredYears.map((row) => row.year)
  const key = metric.value
  const series = activeNOCs.value.map((noc, index) => {
    const color = SERIES_BLUE[index % SERIES_BLUE.length]
    const data = store.countrySeries(noc)
    return {
      name: store.nocLabel(noc),
      type: 'line',
      smooth: false,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 1.8, color },
      itemStyle: { color },
      // 主办届直接做成该系列内的菱形数据点，悬停聚焦时不会与折线分离
      data: data.map((item) => (item.isHost
        ? {
            value: item[key],
            noc,
            year: item.year,
            symbol: 'diamond',
            symbolSize: 15,
            itemStyle: { color, borderColor: '#fff', borderWidth: 2 }
          }
        : item[key])),
      markLine: index === 0 ? markLineYear(store.selectedYear) : undefined,
      // 悬停聚焦：鼠标所在系列保持高亮，其余系列整体变透明
      emphasis: { focus: 'series', lineStyle: { width: 2.6 } },
      blur: { lineStyle: { opacity: 0.12 }, itemStyle: { opacity: 0.12 } }
    }
  })

  return {
    grid: gridBase({ top: 40, right: 24 }),
    tooltip: tooltipBase({ trigger: 'axis' }),
    legend: { top: 0, right: 0, type: 'scroll', itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: { type: 'category', data: years, ...axisCommon },
    yAxis: {
      type: 'value',
      name: metricOptions.find((item) => item.value === key)?.label,
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon
    },
    series
  }
})

/* ---------- 热力图 ---------- */
const maxCell = computed(() => {
  let max = 0
  for (const noc of activeNOCs.value) {
    for (const item of store.countrySeries(noc)) {
      if (item.total > max) max = item.total
    }
  }
  return Math.max(max, 1)
})

const heatmapOption = computed(() => {
  const nocs = activeNOCs.value
  const years = store.filteredYears
  // 数据项只保留 [x, y, value]，多余字段会让 visualMap 取值错位
  const data = []
  nocs.forEach((noc, yIndex) => {
    store.countrySeries(noc).forEach((item, xIndex) => {
      data.push([xIndex, yIndex, item.total])
    })
  })
  return {
    animationDuration: 500,
    grid: gridBase({ left: 76, right: 24, top: 16, bottom: 56 }),
    tooltip: tooltipBase({
      formatter: (params) => {
        const [xIndex, yIndex, value] = params.data
        const year = years[xIndex]?.year
        const noc = nocs[yIndex]
        return `${year} 届 · ${store.nocLabel(noc)}<br/>${store.isEvent ? '小项' : '行'}奖牌 <b>${value}</b>`
      }
    }),
    xAxis: {
      type: 'category',
      data: years.map((row) => row.year),
      ...axisCommon,
      splitArea: { show: false },
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
    },
    yAxis: {
      type: 'category',
      data: nocs.map((noc) => store.nocLabel(noc)),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (value.length > 10 ? `${value.slice(0, 10)}…` : value) }
    },
    visualMap: {
      min: 0,
      max: maxCell.value,
      dimension: 2,
      seriesIndex: 0,
      calculable: false,
      orient: 'horizontal',
      left: 'center',
      bottom: 4,
      itemWidth: 10,
      itemHeight: 90,
      text: ['多', '少'],
      textStyle: { fontSize: 10, color: COLORS.muted },
      inRange: { color: ['#EFF6FF', '#BFDBFE', '#60A5FA', '#2563EB', '#1E3A8A'] }
    },
    series: [
      {
        type: 'heatmap',
        data,
        itemStyle: { borderColor: '#fff', borderWidth: 1 },
        emphasis: { itemStyle: { borderColor: COLORS.host, borderWidth: 1 } }
      }
    ]
  }
})

/* ---------- 国家档案（表格前置） ---------- */
const dossier = computed(() =>
  activeNOCs.value.map((noc) => {
    const row = store.historyByNoc.get(noc)
    const directory = store.countryDirectory.find((item) => item.noc === noc)
    const best = store.countrySeries(noc).reduce((acc, item) => (item.total > acc.total ? item : acc), { year: '—', total: 0 })
    const hostYears = store.countrySeries(noc).filter((item) => item.isHost).map((item) => item.year)
    return {
      noc,
      team: store.nocLabel(noc),
      rank: row?.rank ?? '—',
      gold: row?.gold ?? 0,
      total: row?.total ?? 0,
      amplification: row?.amplification ?? 0,
      first: directory?.firstYear ?? '—',
      last: directory?.lastYear ?? '—',
      bestYear: best.year,
      bestTotal: best.total,
      hostYears: hostYears.length ? hostYears.join(' / ') : '—'
    }
  }).sort((a, b) => b.total - a.total)
)

function onLineClick(params) {
  const year = Number(params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
  // 主办菱形额外带上国家，点击可一并锁定该国
  if (params.data?.noc) store.toggleNOC(params.data.noc)
}

function onCellClick(params) {
  const [xIndex, yIndex] = params.data
  const noc = activeNOCs.value[yIndex]
  const year = store.filteredYears[xIndex]?.year
  if (noc) store.toggleNOC(noc)
  if (year) store.setYear(year)
}
</script>

<template>
  <div>
    <PageHeader
      title="国家兴衰"
      subtitle="代表国家的逐届轨迹：美国长盛、苏联骤起骤落、两德分立与统一、中国自 1984 年陡升。所有图表共享左侧口径与年份区间。"
    />

    <!-- 统计表格最先展示 -->
    <PanelBlock title="国家档案" note="统计范围跟随左侧届次区间；点击行可切换国家选择，红色高亮同步到下方图表。" flush>
      <el-table :data="dossier" size="small" max-height="320" @row-click="(row) => store.toggleNOC(row.noc)">
        <el-table-column prop="rank" label="排名" width="66" align="center" />
        <el-table-column prop="noc" label="NOC" width="72" align="center" />
        <el-table-column prop="team" label="代表团" min-width="140" show-overflow-tooltip />
        <el-table-column prop="total" label="奖牌" width="80" align="center" />
        <el-table-column prop="gold" label="金牌" width="72" align="center" />
        <el-table-column label="放大倍数" width="100" align="center">
          <template #default="{ row }">{{ row.amplification.toFixed(2) }}×</template>
        </el-table-column>
        <el-table-column prop="first" label="首次" width="72" align="center" />
        <el-table-column prop="last" label="末次" width="72" align="center" />
        <el-table-column label="区间最佳" width="120" align="center">
          <template #default="{ row }">{{ row.bestYear }} · {{ row.bestTotal }}</template>
        </el-table-column>
        <el-table-column prop="hostYears" label="主办届" width="120" align="center" />
      </el-table>
    </PanelBlock>

    <!-- 图 1：逐届曲线 + 右侧说明/参数 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="重点国家逐届奖牌曲线"
          note="菱形为该系列的主办届，尺寸更大并带白描边；鼠标移到任意一条线上，其余国家会自动变透明。点击曲线上的点可锁定届次。"
        >
          <BaseChart :option="lineOption" height="380px" @chart-click="onLineClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>参数设置</h3>
        <div class="side-field">
          <label>统计指标</label>
          <el-radio-group v-model="metric" size="small">
            <el-radio-button v-for="item in metricOptions" :key="item.value" :value="item.value">
              {{ item.label }}
            </el-radio-button>
          </el-radio-group>
        </div>
        <div class="side-field">
          <label>展示国家（默认总榜前 6，可多选）</label>
          <el-select
            :model-value="store.selectedNOCs"
            multiple
            filterable
            collapse-tags
            collapse-tags-tooltip
            size="small"
            placeholder="默认总榜前 6"
            @change="store.setNOCs"
          >
            <el-option
              v-for="item in store.countryDirectory"
              :key="item.noc"
              :label="`${item.team} · ${item.noc}`"
              :value="item.noc"
            />
          </el-select>
        </div>
        <p class="side-hint">
          当前口径：{{ store.isEvent ? '小项口径' : '运动员行口径' }}；
          已选 {{ activeNOCs.length }} 个国家。
        </p>
      </aside>
    </section>

    <!-- 图 2：热力图 + 右侧说明 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="国家 × 届次奖牌热力"
          note="颜色越深奖牌越多；点击任意格子同时选中该届与该国。"
        >
          <BaseChart :option="heatmapOption" height="340px" @chart-click="onCellClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>读数说明</h3>
        <p>
          横轴为届次，纵轴为所选国家。空白格表示该国未参加或未获奖，
          颜色按当前区间内的最大奖牌数归一化。
        </p>
        <div class="side-field">
          <label>当前展示</label>
          <span class="side-hint">{{ activeNOCs.map((noc) => store.nocLabel(noc)).join('、') }}</span>
        </div>
        <p class="side-hint">点击格子会把「届次 + 国家」同步到全站联动。</p>
      </aside>
    </section>
  </div>
</template>
