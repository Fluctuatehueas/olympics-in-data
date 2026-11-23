<script setup>
import { computed, ref } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, axisCommon, tooltipBase, gridBase, number } from '../utils/chart'

const store = useDashboardStore()

// 各图的展示参数，放到右侧参数区，避免图表本身堆控件
const compareTop = ref(12)
const shiftThreshold = ref(15)
const ampTop = ref(15)

const rows2024 = computed(() =>
  store.countryYear
    .filter((row) => row.year === 2024 && row.totalEvent > 0)
    .slice()
    .sort((a, b) => b.goldEvent - a.goldEvent || b.goldAthlete - a.goldAthlete)
)

const kpis = computed(() => {
  const base = store.meta.totals ?? {}
  const usa = rows2024.value.find((row) => row.noc === 'USA')
  return [
    { label: '小项口径奖牌', value: number(base.eventMedals ?? 17901), hint: '同届 · 同小项 · 同奖牌色 · 同 NOC 计 1' },
    { label: '运动员行口径奖牌', value: number(base.athleteMedals ?? 38360), hint: '每条奖牌记录计 1' },
    { label: '换口径收缩', value: `${base.shrinkPct ?? 53.3}%`, hint: '差额全部来自团体项目成员复制' },
    { label: '平均放大倍数', value: '2.22×', hint: '2024 年各国行口径 ÷ 小项口径' },
    { label: 'USA 2024 金牌', value: usa ? `${usa.goldEvent} → ${usa.goldAthlete}` : '37 → 131', hint: '小项口径 → 行口径' }
  ]
})

const compareRows = computed(() => rows2024.value.slice(0, compareTop.value).slice().reverse())

const compareOption = computed(() => {
  const rows = compareRows.value
  const activeEvent = store.isEvent
  return {
    grid: gridBase({ left: 10, right: 46, top: 34, bottom: 8 }),
    tooltip: tooltipBase({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: { type: 'value', name: '金牌', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon },
    yAxis: { type: 'category', data: rows.map((row) => row.noc), ...axisCommon, splitLine: { show: false } },
    series: [
      {
        name: '小项口径金牌',
        type: 'bar',
        barMaxWidth: 9,
        itemStyle: { color: COLORS.gold },
        data: rows.map((row) => ({
          value: row.goldEvent,
          noc: row.noc,
          itemStyle: { color: store.selectedNOCs.includes(row.noc) ? COLORS.host : COLORS.gold, opacity: activeEvent ? 1 : 0.35 }
        }))
      },
      {
        name: '行口径金牌',
        type: 'bar',
        barMaxWidth: 9,
        itemStyle: { color: COLORS.blue },
        data: rows.map((row) => ({
          value: row.goldAthlete,
          noc: row.noc,
          itemStyle: { color: store.selectedNOCs.includes(row.noc) ? COLORS.host : COLORS.blue, opacity: activeEvent ? 0.35 : 1 }
        }))
      }
    ]
  }
})

function rankBy(list, key) {
  const sorted = [...list].sort((a, b) => b[key] - a[key])
  const map = new Map()
  sorted.forEach((item, index) => map.set(item.noc, index + 1))
  return map
}

const shiftRows = computed(() => {
  const rows = store.history
  if (!rows.length) return []
  const eventRank = rankBy(rows, 'goldEvent')
  const athleteRank = rankBy(rows, 'goldAthlete')
  return rows
    .map((row) => ({
      ...row,
      eventRank: eventRank.get(row.noc),
      athleteRank: athleteRank.get(row.noc),
      move: eventRank.get(row.noc) - athleteRank.get(row.noc)
    }))
    .filter((row) => row.eventRank <= 28 || Math.abs(row.move) >= shiftThreshold.value)
    .slice(0, 34)
})

const shiftOption = computed(() => {
  const rows = shiftRows.value
  const maxRank = Math.max(10, ...rows.map((row) => Math.max(row.eventRank, row.athleteRank)))
  return {
    grid: gridBase({ left: 46, right: 26, top: 26, bottom: 40 }),
    tooltip: tooltipBase({
      formatter: (params) => {
        const item = params.data
        return `${item.team}（${item.noc}）<br/>小项口径排名 <b>${item.eventRank}</b><br/>行口径排名 <b>${item.athleteRank}</b><br/>位移 ${item.move > 0 ? '+' : ''}${item.move} 位`
      }
    }),
    xAxis: {
      type: 'value', name: '小项口径排名', inverse: true, min: 1, max: maxRank,
      nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon
    },
    yAxis: {
      type: 'value', name: '行口径排名', inverse: true, min: 1, max: maxRank,
      nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon
    },
    series: [
      {
        type: 'line',
        silent: true,
        symbol: 'none',
        lineStyle: { color: '#CBD5E1', type: 'dashed', width: 1 },
        data: [[1, 1], [maxRank, maxRank]]
      },
      {
        type: 'scatter',
        symbolSize: (value, params) => (Math.abs(params.data.move) >= shiftThreshold.value ? 11 : 6),
        data: rows.map((row) => ({
          value: [row.eventRank, row.athleteRank],
          noc: row.noc,
          team: row.team,
          eventRank: row.eventRank,
          athleteRank: row.athleteRank,
          move: row.move,
          itemStyle: {
            color: store.selectedNOCs.includes(row.noc)
              ? COLORS.host
              : row.move > 0 ? COLORS.blue : row.move < 0 ? '#94A3B8' : COLORS.deep
          }
        })),
        label: {
          show: true,
          position: 'right',
          fontSize: 9,
          color: COLORS.muted,
          formatter: (params) => (Math.abs(params.data.move) >= shiftThreshold.value ? params.data.noc : '')
        }
      }
    ]
  }
})

const amplificationRows = computed(() =>
  store.history
    .filter((row) => row.totalEvent >= 2)
    .slice()
    .sort((a, b) => b.amplification - a.amplification)
    .slice(0, ampTop.value)
    .reverse()
)

const amplificationOption = computed(() => ({
  grid: gridBase({ left: 10, right: 46, top: 14, bottom: 8 }),
  tooltip: tooltipBase({
    trigger: 'axis',
    axisPointer: { type: 'shadow' },
    formatter: (params) => {
      const row = amplificationRows.value[params[0].dataIndex]
      return `${row.team}（${row.noc}）<br/>行口径 ${number(row.totalAthlete)} ÷ 小项 ${number(row.totalEvent)}<br/>放大 <b>${row.amplification.toFixed(2)}×</b>`
    }
  }),
  xAxis: { type: 'value', ...axisCommon },
  yAxis: { type: 'category', data: amplificationRows.value.map((row) => row.noc), ...axisCommon, splitLine: { show: false } },
  series: [
    {
      type: 'bar',
      barMaxWidth: 14,
      label: { show: true, position: 'right', fontSize: 10, color: COLORS.muted, formatter: (params) => `${params.value}×` },
      data: amplificationRows.value.map((row) => ({
        value: row.amplification,
        noc: row.noc,
        itemStyle: { color: store.selectedNOCs.includes(row.noc) ? COLORS.host : COLORS.blue }
      }))
    }
  ]
}))

const tableRows = computed(() => rows2024.value.slice(0, 20))

function onCountryClick(params) {
  if (params.data?.noc) store.toggleNOC(params.data.noc)
}
</script>

<template>
  <div>
    <PageHeader
      title="口径的魔力"
      subtitle="同一批记录、两套去重规则：把「一名运动员 × 一届 × 一个小项」按行计数，2024 年 USA 金牌从 37 变 131、NED 从 14 变 67。团体项目的成员复制，是奖牌榜最容易被忽略的放大器。"
    />

    <!-- 研究结论最先放置 -->
    <div class="caliber-thesis">
      <span class="tag is-blue">核心结论</span>
      <div class="thesis-body">
        <p>
          <b>口径不是精度差异，而是价值判断。</b>小项口径数的是「能在多少个项目上赢」，运动员行口径数的是「有多少人在赢」。
          同一届 2024，USA 金牌 <b>37 → 131</b>、NED <b>14 → 67</b>，平均放大 <b>2.22×</b>；
          全局奖牌 <b>17,901 → 38,360</b>，其中 <b>53.3%</b> 是团体项目成员的复制行。
        </p>
        <p>
          放大倍数由<strong>团体项目依赖度</strong>决定：依赖接力、大名单项目的国家被显著抬高，个人项目为主的国家几乎不变。
          近五届口径排名变动中，斐济 <b>↑42</b> 位、墨西哥 <b>↑24</b> 位，哈萨克斯坦、伊朗、肯尼亚各 <b>↓12</b> 位。
          因此任何「奖牌榜」都必须先声明自己在数夺金点还是夺金人次。
        </p>
      </div>
    </div>

    <KpiStrip :items="kpis" />

    <!-- 统计表格最先展示 -->
    <PanelBlock
      title="2024 双口径明细 · 前 20"
      note="统计固定为 2024 巴黎，不随顶部届次区间变化；点击行可选中/取消国家。"
      flush
    >
      <el-table
        :data="tableRows"
        size="small"
        max-height="420"
        :row-class-name="({ row }) => (store.selectedNOCs.includes(row.noc) ? 'row-selected' : '')"
        @row-click="(row) => store.toggleNOC(row.noc)"
      >
        <el-table-column prop="noc" label="NOC" width="76" align="center" />
        <el-table-column prop="team" label="代表团" min-width="150" />
        <el-table-column prop="goldEvent" label="金 · 小项" width="100" align="center" sortable />
        <el-table-column prop="goldAthlete" label="金 · 行" width="92" align="center" sortable />
        <el-table-column prop="totalEvent" label="总 · 小项" width="100" align="center" sortable />
        <el-table-column prop="totalAthlete" label="总 · 行" width="92" align="center" sortable />
        <el-table-column label="放大" width="90" align="center">
          <template #default="{ row }">{{ (row.totalAthlete / row.totalEvent).toFixed(2) }}×</template>
        </el-table-column>
        <el-table-column prop="records" label="参赛记录" width="100" align="center" sortable />
      </el-table>
    </PanelBlock>

    <!-- 图 1：双口径金牌对照 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="2024 巴黎：金牌双口径对照"
          note="金色为小项口径、蓝色为行口径；当前口径对应系列不透明，另一侧降为 35%。点击国家可联动。"
        >
          <BaseChart :option="compareOption" height="430px" @chart-click="onCountryClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>参数设置</h3>
        <div class="side-field">
          <label>统计口径（控制高亮）</label>
          <el-radio-group :model-value="store.caliber" size="small" @change="store.setCaliber">
            <el-radio-button value="event">小项口径</el-radio-button>
            <el-radio-button value="athlete">运动员行口径</el-radio-button>
          </el-radio-group>
        </div>
        <div class="side-field">
          <label>显示前 {{ compareTop }} 个国家</label>
          <el-slider v-model="compareTop" :min="5" :max="20" :step="1" size="small" />
        </div>
        <p class="side-hint">
          同一届、同一批人，差别只在去重键：小项口径数“夺金点”，行口径数“夺金人次”。
        </p>
      </aside>
    </section>

    <!-- 图 2：排名位移 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="排名位移：两种口径谁被抬高"
          note="横轴小项排名、纵轴行排名，虚线为名次不变的对角线；蓝点在行口径下上升，灰点下降。点越大、位移越大。"
        >
          <BaseChart :option="shiftOption" height="430px" @chart-click="onCountryClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>参数设置</h3>
        <div class="side-field">
          <label>标注阈值：位移 ≥ {{ shiftThreshold }} 位</label>
          <el-slider v-model="shiftThreshold" :min="5" :max="40" :step="5" size="small" />
          <span class="side-hint">达到阈值的点会放大并显示 NOC，避免整页都是标签。</span>
        </div>
        <p class="side-hint">
          向上移动代表行口径下排名更高：团体项目依赖度高的国家会被抬高，个人项目为主的国家会下沉。
        </p>
      </aside>
    </section>

    <!-- 图 3：放大倍数 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          :title="`放大倍数 Top ${ampTop}`"
          note="按行口径 ÷ 小项口径计算，过滤小项奖牌 ≥ 2 的代表团；点击条形选中该国。"
        >
          <BaseChart :option="amplificationOption" height="430px" @chart-click="onCountryClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>参数设置</h3>
        <div class="side-field">
          <label>显示前 {{ ampTop }} 个国家</label>
          <el-slider v-model="ampTop" :min="5" :max="30" :step="5" size="small" />
        </div>
        <p class="side-hint">
          放大倍数越高，说明该国奖牌越依赖团体项目；过滤掉小项奖牌 &lt; 2 的国家，避免小样本把榜单带偏。
        </p>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.caliber-thesis {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 0 0 16px;
  padding: 12px 14px;
  background: var(--brand-50);
  border-left: 3px solid var(--brand-600);
}
.thesis-body { display: flex; flex-direction: column; gap: 8px; }
.thesis-body p { font-size: 12.5px; line-height: 1.8; color: var(--ink-2); }
.thesis-body b { color: var(--brand-800); }
:deep(.row-selected) { background: var(--brand-50) !important; }
:deep(.el-table__row) { cursor: pointer; }
</style>
