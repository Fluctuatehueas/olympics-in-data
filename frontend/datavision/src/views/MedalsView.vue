<script setup>
import { computed, ref, watch } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, SERIES_BLUE, axisCommon, tooltipBase, gridBase, markLineYear, number } from '../utils/chart'

const store = useDashboardStore()

const keyword = ref('')
const page = ref(1)
const pageSize = ref(12)
const sortKey = ref('gold')
const sortOrder = ref('desc')

watch([() => store.range, keyword], () => { page.value = 1 })

const kpis = computed(() => {
  const rows = store.history
  const totalEvent = rows.reduce((sum, row) => sum + row.totalEvent, 0)
  const totalAthlete = rows.reduce((sum, row) => sum + row.totalAthlete, 0)
  return [
    { label: '区间奖牌总数', value: number(store.kpi.medals), hint: `${store.kpi.editions} 届 · ${store.isEvent ? '小项口径' : '行口径'}` },
    { label: '金牌', value: number(store.kpi.gold), hint: '同口径' },
    { label: '夺牌代表团', value: number(rows.length), hint: '区间内至少 1 枚奖牌' },
    { label: '平均放大倍数', value: totalEvent ? (totalAthlete / totalEvent).toFixed(2) : '—', hint: '行口径 ÷ 小项口径' }
  ]
})

const medalRows = computed(() => store.filteredYears)

const stackedOption = computed(() => ({
  grid: gridBase({ top: 36, right: 20 }),
  tooltip: tooltipBase({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
  legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
  xAxis: {
    type: 'category',
    data: medalRows.value.map((row) => row.year),
    ...axisCommon,
    axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
  },
  yAxis: { type: 'value', ...axisCommon },
  series: [
    { key: 'gold', name: '金牌', color: COLORS.gold },
    { key: 'silver', name: '银牌', color: COLORS.silver },
    { key: 'bronze', name: '铜牌', color: COLORS.bronze }
  ].map(({ key, name, color }) => {
    const field = store.isEvent ? `${key}Event` : `${key}Athlete`
    return {
      name,
      type: 'bar',
      stack: 'medal',
      barMaxWidth: 16,
      data: medalRows.value.map((row) => ({
        value: row[field],
        itemStyle: { color: row.year === store.selectedYear ? COLORS.host : color }
      })),
      markLine: name === '金牌' ? markLineYear(store.selectedYear) : undefined
    }
  })
}))

const topOption = computed(() => {
  const rows = store.history.slice(0, 12).slice().reverse()
  return {
    grid: gridBase({ left: 12, right: 46, top: 16, bottom: 8 }),
    tooltip: tooltipBase({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
    xAxis: { type: 'value', ...axisCommon },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.noc),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: {
        ...axisCommon.axisLabel,
        formatter: (value) => (store.selectedNOCs.includes(value) ? `{sel|${value}}` : value),
        rich: { sel: { color: COLORS.host, fontWeight: 'bold', fontSize: 11 } }
      }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 15,
        label: { show: true, position: 'right', fontSize: 10, color: COLORS.muted },
        data: rows.map((row) => ({
          value: row.total,
          noc: row.noc,
          itemStyle: {
            color: store.selectedNOCs.includes(row.noc) ? COLORS.host : COLORS.blue,
            opacity: store.selectedNOCs.length && !store.selectedNOCs.includes(row.noc) ? 0.45 : 1
          }
        }))
      }
    ]
  }
})

const focusNOCs = computed(() =>
  store.selectedNOCs.length ? store.selectedNOCs : store.history.slice(0, 5).map((row) => row.noc)
)

const trajectoryOption = computed(() => {
  const nocs = focusNOCs.value
  return {
    grid: gridBase({ top: 36, right: 20 }),
    tooltip: tooltipBase({ trigger: 'axis' }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: { type: 'category', data: store.filteredYears.map((row) => row.year), ...axisCommon },
    yAxis: { type: 'value', name: store.isEvent ? '小项奖牌' : '行口径奖牌', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon },
    series: nocs.map((noc, index) => ({
      name: store.nocLabel(noc),
      type: 'line',
      smooth: true,
      symbol: 'circle',
      symbolSize: 4,
      lineStyle: { width: 1.8, color: SERIES_BLUE[index % SERIES_BLUE.length] },
      itemStyle: { color: SERIES_BLUE[index % SERIES_BLUE.length] },
      // 悬停聚焦：鼠标所在系列保持高亮，其余系列整体变透明
      emphasis: { focus: 'series', lineStyle: { width: 2.6 } },
      blur: { lineStyle: { opacity: 0.12 }, itemStyle: { opacity: 0.12 } },
      data: store.countrySeries(noc).map((item) => item.total)
    }))
  }
})

const filteredRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  let rows = store.history
  if (text) {
    rows = rows.filter((row) => row.noc.toLowerCase().includes(text) || row.team.toLowerCase().includes(text))
  }
  const key = sortKey.value
  const direction = sortOrder.value === 'asc' ? 1 : -1
  return [...rows].sort((a, b) => {
    if (key === 'rank') return (a.rank - b.rank) * direction
    return ((a[key] ?? 0) - (b[key] ?? 0)) * direction
  })
})

const pagedRows = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredRows.value.slice(start, start + pageSize.value)
})

function onSortChange({ prop, order }) {
  if (!order) return
  sortKey.value = prop
  sortOrder.value = order === 'ascending' ? 'asc' : 'desc'
}

function rowClassName({ row }) {
  return store.selectedNOCs.includes(row.noc) ? 'row-selected' : ''
}

function yearFromClick(params) {
  const year = Number(params.data?.year ?? params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
}

function nocFromClick(params) {
  if (params.data?.noc) store.toggleNOC(params.data.noc)
}
</script>

<template>
  <div>
    <PageHeader
      title="奖牌格局"
      subtitle="历史总榜、逐届构成与重点国家轨迹。顶部的口径开关会同时改写本页所有数字：小项口径去重团体项目，行口径保留每位成员。"
    />

    <KpiStrip :items="kpis" />

    <div class="panel-grid split-2-1">
      <PanelBlock
        title="逐届奖牌构成"
        note="金 / 银 / 铜堆叠。点击某年柱子，全站进入该届联动。"
      >
        <BaseChart :option="stackedOption" height="310px" @chart-click="yearFromClick" />
      </PanelBlock>

      <PanelBlock
        title="区间总榜前 12"
        note="按当前口径总奖牌排序；点击条形切换国家联动。"
      >
        <BaseChart :option="topOption" height="310px" @chart-click="nocFromClick" />
      </PanelBlock>
    </div>

    <PanelBlock
      title="历史总榜明细"
      :note="`区间 ${store.range[0]}–${store.range[1]} · 共 ${filteredRows.length} 个夺牌代表团。点击行可选中/取消国家。`"
      flush
    >
      <template #actions>
        <el-input v-model="keyword" size="small" placeholder="搜索 NOC / 代表团" clearable style="width: 190px" />
      </template>
      <el-table
        :data="pagedRows"
        size="small"
        max-height="430"
        :row-class-name="rowClassName"
        @row-click="(row) => store.toggleNOC(row.noc)"
        @sort-change="onSortChange"
      >
        <el-table-column prop="rank" label="#" width="52" sortable="custom" />
        <el-table-column prop="noc" label="NOC" width="72" />
        <el-table-column prop="team" label="代表团" min-width="150" />
        <el-table-column prop="gold" label="金" width="72" align="right" sortable="custom" />
        <el-table-column prop="silver" label="银" width="72" align="right" sortable="custom" />
        <el-table-column prop="bronze" label="铜" width="72" align="right" sortable="custom" />
        <el-table-column prop="total" label="合计" width="82" align="right" sortable="custom" />
        <el-table-column prop="amplification" label="放大" width="78" align="right" sortable="custom">
          <template #default="{ row }"><span class="num">{{ row.amplification.toFixed(2) }}×</span></template>
        </el-table-column>
        <el-table-column prop="records" label="参赛记录" width="96" align="right" sortable="custom" />
      </el-table>
      <div class="table-foot">
        <span class="small muted">当前口径：{{ store.isEvent ? '小项口径' : '运动员行口径' }}</span>
        <el-pagination
          v-model:current-page="page"
          :page-size="pageSize"
          :total="filteredRows.length"
          layout="prev, pager, next"
          small
        />
      </div>
    </PanelBlock>

    <PanelBlock
      title="重点国家逐届奖牌轨迹"
      :note="store.selectedNOCs.length ? '当前显示已选国家；清空联动后默认展示总榜前 5。' : '未选国家时默认展示总榜前 5；点击上方榜单可替换。'"
    >
      <BaseChart :option="trajectoryOption" height="300px" @chart-click="yearFromClick" />
    </PanelBlock>
  </div>
</template>

<style scoped>
.table-foot {
  display: flex; align-items: center; justify-content: space-between;
  padding: 8px 12px 4px;
  border-top: 1px solid var(--line);
}
:deep(.row-selected) { background: var(--brand-50) !important; }
:deep(.row-selected td) { color: var(--brand-800); }
:deep(.el-table__row) { cursor: pointer; }
</style>
