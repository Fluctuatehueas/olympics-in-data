<script setup>
import { computed, ref, watch } from 'vue'
import { Search } from '@element-plus/icons-vue'
import { useDashboardStore } from '../stores/dashboard'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, axisCommon, tooltipBase, gridBase, markLineYear, pct, number } from '../utils/chart'

const store = useDashboardStore()

/* ------------------------------------------------------------------ *
 * 1. 总体统计
 * ------------------------------------------------------------------ */
const kpis = computed(() => [
  {
    label: `${store.isEvent ? '小项口径' : '运动员行口径'}奖牌数`,
    value: number(store.kpi.medals),
    hint: `金 ${number(store.kpi.gold)} · 银 ${number(store.kpi.silver)} · 铜 ${number(store.kpi.bronze)}`
  },
  { label: '参赛记录', value: number(store.kpi.records), hint: '运动员 × 小项的人次' },
  { label: '代表团（团队）数', value: number(store.kpi.teams), hint: 'Team 字段去重后的队伍数' },
  { label: '运动大类', value: number(store.kpi.sports), hint: `全量 ${store.meta.sports ?? 0} 类` },
  { label: '参赛国家 / 地区', value: number(store.kpi.nocs), hint: `全量 ${store.meta.nocs ?? 0} 个 NOC` }
])

/* ------------------------------------------------------------------ *
 * 2. 参赛团队名录（分页）
 * ------------------------------------------------------------------ */
const teamKeyword = ref('')
const teamPage = ref(1)
const teamSize = ref(20)

const teamRows = computed(() => {
  const keyword = teamKeyword.value.trim().toLowerCase()
  const list = store.teamCatalog
  if (!keyword) return list
  return list.filter((row) =>
    row.team.toLowerCase().includes(keyword) ||
    row.noc.toLowerCase().includes(keyword) ||
    store.nocLabel(row.noc).toLowerCase().includes(keyword)
  )
})

const teamPageRows = computed(() => {
  const start = (teamPage.value - 1) * teamSize.value
  return teamRows.value.slice(start, start + teamSize.value)
})

const teamRowClass = ({ row }) => (store.selectedNOCs.includes(row.noc) ? 'is-domain-row' : '')

/* ------------------------------------------------------------------ *
 * 3. 运动大类名录（分页）
 * ------------------------------------------------------------------ */
const sportKeyword = ref('')
const sportPage = ref(1)
const sportSize = ref(15)

const sportRows = computed(() => {
  const keyword = sportKeyword.value.trim().toLowerCase()
  const list = store.sportCatalog
  if (!keyword) return list
  return list.filter((row) => row.sport.toLowerCase().includes(keyword))
})

const sportPageRows = computed(() => {
  const start = (sportPage.value - 1) * sportSize.value
  return sportRows.value.slice(start, start + sportSize.value)
})

watch([teamKeyword, teamSize], () => { teamPage.value = 1 })
watch([sportKeyword, sportSize], () => { sportPage.value = 1 })
watch(() => [store.range[0], store.range[1]], () => {
  teamPage.value = 1
  sportPage.value = 1
})

/* ------------------------------------------------------------------ *
 * 4. 每个国家的团队数 · 气泡图
 * ------------------------------------------------------------------ */
const bubbleTop = ref(30)
const bubbleCount = computed(() => store.teamByCountry.length)
const bubbleRows = computed(() => store.teamByCountry.slice(0, bubbleTop.value))
const bubbleMax = computed(() => Math.max(1, ...bubbleRows.value.map((row) => row.teams)))

watch(bubbleCount, (count) => {
  if (!count) return
  if (bubbleTop.value > count) bubbleTop.value = count
})

const bubbleOption = computed(() => {
  const rows = bubbleRows.value
  const max = bubbleMax.value
  const selected = new Set(store.selectedNOCs)
  return {
    animationDuration: 700,
    animationDurationUpdate: 500,
    grid: gridBase({ left: 56, right: 24, top: 30, bottom: 104 }),
    tooltip: tooltipBase({
      formatter: (params) => {
        const item = params.data || {}
        return `${item.fullName || params.name}<br/>团队数 <b>${item.value?.[1] ?? '—'}</b><br/>参赛记录 ${number(item.value?.[2])}`
      }
    }),
    visualMap: {
      min: 1,
      max,
      dimension: 1,
      seriesIndex: 0,
      orient: 'horizontal',
      left: 'center',
      bottom: 30,
      itemWidth: 10,
      itemHeight: 110,
      calculable: true,
      text: ['团队多', '团队少'],
      textStyle: { color: COLORS.muted, fontSize: 10 },
      inRange: { color: ['#dbeafe', '#93c5fd', '#3b82f6', '#1d4ed8', '#172554'] }
    },
    xAxis: {
      type: 'category',
      data: rows.map((row) => store.nocLabel(row.noc)),
      ...axisCommon,
      axisLabel: {
        ...axisCommon.axisLabel,
        interval: rows.length > 16 ? 1 : 0,
        rotate: 42,
        fontSize: 10,
        formatter: (value) => (value.length > 10 ? `${value.slice(0, 10)}…` : value)
      }
    },
    yAxis: {
      type: 'value',
      name: '团队数',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon
    },
    series: [
      {
        type: 'scatter',
        symbolSize: (value) => 12 + Math.sqrt(value[1] / max) * 30,
        itemStyle: {
          opacity: 0.82,
          borderColor: '#fff',
          borderWidth: 1
        },
        emphasis: { scale: 1.18, itemStyle: { opacity: 1 } },
        data: rows.map((row) => ({
          name: store.nocLabel(row.noc),
          fullName: `${store.nocLabel(row.noc)} · ${row.noc}`,
          noc: row.noc,
          value: [store.nocLabel(row.noc), row.teams, row.records],
          itemStyle: selected.size
            ? { opacity: selected.has(row.noc) ? 1 : 0.18, borderColor: selected.has(row.noc) ? COLORS.host : '#fff', borderWidth: selected.has(row.noc) ? 2 : 1 }
            : undefined
        }))
      }
    ]
  }
})

function bubbleClick(params) {
  const noc = params.data?.noc
  if (noc) store.toggleNOC(noc)
}

/* ------------------------------------------------------------------ *
 * 5. 奖牌膨胀：奖牌柱 + 团队数趋势线
 * ------------------------------------------------------------------ */
const showTrend = ref(true)

const inflationOption = computed(() => {
  const rows = store.filteredYears
  const selected = store.selectedYear
  const series = [
    {
      name: '小项口径',
      type: 'bar',
      barMaxWidth: 13,
      itemStyle: { color: COLORS.blue },
      emphasis: { itemStyle: { color: COLORS.deep } },
      data: rows.map((row) => row.totalEvent),
      markLine: markLineYear(selected)
    },
    {
      name: '运动员行口径',
      type: 'bar',
      barMaxWidth: 13,
      itemStyle: { color: COLORS.bluePale },
      emphasis: { itemStyle: { color: COLORS.blueLight } },
      data: rows.map((row) => row.totalAthlete)
    }
  ]
  if (showTrend.value) {
    series.push({
      name: '团队数',
      type: 'line',
      yAxisIndex: 1,
      smooth: false,
      symbol: 'circle',
      symbolSize: 3,
      lineStyle: { color: COLORS.warn, width: 1.4, type: 'solid' },
      itemStyle: { color: COLORS.warn },
      data: rows.map((row) => row.teams ?? row.nocs)
    })
  }
  return {
    animationDuration: 600,
    grid: gridBase({ top: 52, right: 58 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        return [
          `${row.year} 届`,
          `小项口径 <b>${number(row.totalEvent)}</b>`,
          `运动员行口径 <b>${number(row.totalAthlete)}</b>`,
          `差值（团体复制行）${number(row.totalAthlete - row.totalEvent)}`,
          `团队数 ${number(row.teams ?? row.nocs)}`
        ].join('<br/>')
      }
    }),
    legend: {
      top: 2, left: 4, itemWidth: 10, itemHeight: 8, itemGap: 12,
      textStyle: { fontSize: 11, color: COLORS.muted }
    },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
    },
    yAxis: [
      { type: 'value', name: '奖牌数', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon },
      { type: 'value', name: '团队数', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon, splitLine: { show: false } }
    ],
    series
  }
})

function yearClick(params) {
  const year = Number(params.data?.year ?? params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
}

/* ------------------------------------------------------------------ *
 * 6. 奖牌排行榜：金/银/铜堆叠 + 前 N 可选择
 * ------------------------------------------------------------------ */
const rankingTop = ref(15)
const rankingMax = computed(() => Math.max(1, store.history.length))
const rankingRows = computed(() => store.history.slice(0, rankingTop.value).slice().reverse())
const rankingHeight = computed(() => `${Math.min(780, Math.max(380, rankingTop.value * 26 + 90))}px`)

watch(rankingMax, (max) => {
  if (rankingTop.value > max) rankingTop.value = max
})

const rankingOption = computed(() => {
  const rows = rankingRows.value
  const selected = new Set(store.selectedNOCs)
  const dim = (noc) => (selected.size && !selected.has(noc) ? 0.28 : 1)
  const series = [
    ['gold', '金牌', COLORS.gold],
    ['silver', '银牌', COLORS.silver],
    ['bronze', '铜牌', COLORS.bronze]
  ].map(([key, name, color]) => ({
    name,
    type: 'bar',
    stack: 'medal',
    barMaxWidth: 18,
    data: rows.map((row) => ({ value: row[key], itemStyle: { color, opacity: dim(row.noc) } })),
    emphasis: { focus: 'series' }
  }))

  return {
    animation: true,
    animationDuration: 700,
    animationDurationUpdate: 600,
    animationEasingUpdate: 'cubicOut',
    grid: gridBase({ left: 16, right: 36, top: 30, bottom: 12 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        return `${store.nocLabel(row.noc)} · ${row.noc}<br/>排名 <b>#${row.rank}</b><br/>` +
          params.map((item) => `${item.marker}${item.seriesName} ${number(item.value)}`).join('<br/>') +
          `<br/>合计 ${number(row.total)}`
      }
    }),
    legend: {
      top: 0, right: 4, itemWidth: 10, itemHeight: 8,
      textStyle: { fontSize: 11, color: COLORS.muted }
    },
    xAxis: { type: 'value', ...axisCommon },
    yAxis: {
      type: 'category',
      data: rows.map((row) => row.noc),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: {
        ...axisCommon.axisLabel,
        formatter: (value) => {
          const label = store.nocLabel(value)
          const short = label.length > 9 ? `${label.slice(0, 9)}…` : label
          return selected.has(value) ? `{sel|${short}}` : short
        },
        rich: { sel: { color: COLORS.host, fontWeight: 'bold', fontSize: 11 } }
      }
    },
    series
  }
})

function rankingClick(params) {
  const noc = params.name
  if (typeof noc === 'string' && noc.length <= 4) store.toggleNOC(noc)
}

function setRankingQuick(value) {
  rankingTop.value = value === 'all' ? rankingMax.value : Math.min(value, rankingMax.value)
}
</script>

<template>
  <div class="flow-page">
    <header class="flow-hero">
      <div>
        <h1>全局概览</h1>
        <p>
          1896–2024 夏季奥运会全量记录。左侧锁定口径与年份后，本页所有统计量与图表同步变化；
          点击图表中的国家可把该国家设为「当前数据域」。
        </p>
        <div class="hero-tags">
          <span>{{ store.range[0] }}–{{ store.range[1] }}</span>
          <span>{{ store.kpi.editions }} 届</span>
          <span>{{ number(store.kpi.records) }} 条参赛记录</span>
          <span>{{ store.isEvent ? '小项口径' : '运动员行口径' }}</span>
        </div>
      </div>
    </header>

    <!-- 1. 总体统计 -->
    <section id="stats" class="flow-section">
      <div class="section-head">
        <div>
          <h2>数据总体统计</h2>
          <p>五项总量指标随左侧年份区间与统计口径实时变化。</p>
        </div>
        <div class="section-actions">
          <el-radio-group :model-value="store.caliber" size="small" @change="store.setCaliber">
            <el-radio-button value="event">小项口径</el-radio-button>
            <el-radio-button value="athlete">运动员行口径</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <KpiStrip :items="kpis" />
    </section>

    <!-- 2. 参赛团队名录 -->
    <section id="teams" class="flow-section">
      <div class="section-head">
        <div>
          <h2>参赛团队名录</h2>
          <p>
            Team 字段去重后共 <b>{{ number(teamRows.length) }}</b> 支队伍（含 China-1 这类分队与帆船船名）。
            表格按当前年份区间与口径统计奖牌；团队层级按 Team 去重，同一国家的多支队伍会分别计数，
            因此合计（17,923）略高于国家层级的 17,901。
          </p>
        </div>
      </div>
      <PanelBlock title="全部团队" note="搜索团队名 / NOC / 国家，分页浏览。" flush>
        <div class="table-toolbar">
          <el-input
            v-model="teamKeyword"
            size="small"
            clearable
            placeholder="搜索团队、国家或 NOC"
            :prefix-icon="Search"
            style="width: 260px"
          />
          <span class="table-count">共 {{ number(teamRows.length) }} 支队伍</span>
        </div>
        <el-table
          :data="teamPageRows"
          size="small"
          stripe
          max-height="440"
          :row-class-name="teamRowClass"
        >
          <el-table-column prop="team" label="团队" min-width="170" show-overflow-tooltip />
          <el-table-column label="国家 / 地区" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <div>{{ store.nocLabel(row.noc) }}</div>
              <div class="cell-sub">{{ row.noc }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="first" label="首次" width="78" align="right" />
          <el-table-column prop="last" label="末次" width="78" align="right" />
          <el-table-column prop="editions" label="届数" width="72" align="right" />
          <el-table-column label="参赛记录" width="96" align="right">
            <template #default="{ row }">{{ number(row.records) }}</template>
          </el-table-column>
          <el-table-column label="女子占比" width="92" align="right">
            <template #default="{ row }">{{ pct(row.femaleRatio) }}</template>
          </el-table-column>
          <el-table-column label="奖牌" width="84" align="right">
            <template #default="{ row }">{{ number(row[store.medalKey]) }}</template>
          </el-table-column>
          <el-table-column label="金牌" width="76" align="right">
            <template #default="{ row }">{{ number(row[store.goldKey]) }}</template>
          </el-table-column>
        </el-table>
        <div class="table-foot">
          <el-pagination
            v-model:current-page="teamPage"
            v-model:page-size="teamSize"
            :page-sizes="[10, 20, 50, 100]"
            :total="teamRows.length"
            size="small"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </PanelBlock>
    </section>

    <!-- 3. 运动大类名录 -->
    <section id="sports" class="flow-section">
      <div class="section-head">
        <div>
          <h2>运动大类名录</h2>
          <p>
            已按归一映射表把 76 个原始写法合并为 <b>{{ number(sportRows.length) }}</b> 个大类（区间内）。
            状态区分在办与已停办项目。
          </p>
        </div>
      </div>
      <PanelBlock title="全部运动大类" note="按参赛记录排序，支持搜索与分页。" flush>
        <div class="table-toolbar">
          <el-input
            v-model="sportKeyword"
            size="small"
            clearable
            placeholder="搜索运动大类"
            :prefix-icon="Search"
            style="width: 240px"
          />
          <span class="table-count">共 {{ number(sportRows.length) }} 个大类</span>
        </div>
        <el-table :data="sportPageRows" size="small" stripe max-height="380">
          <el-table-column prop="sport" label="运动大类" min-width="180" show-overflow-tooltip />
          <el-table-column prop="first" label="首次" width="80" align="right" />
          <el-table-column prop="last" label="末次" width="80" align="right" />
          <el-table-column prop="editions" label="举办届数" width="92" align="right" />
          <el-table-column label="参赛记录" width="100" align="right">
            <template #default="{ row }">{{ number(row.records) }}</template>
          </el-table-column>
          <el-table-column label="奖牌" width="88" align="right">
            <template #default="{ row }">{{ number(row[store.medalKey]) }}</template>
          </el-table-column>
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <span class="tag" :class="row.retired ? 'is-red' : 'is-blue'">
                {{ row.retired ? '已停办' : '在办' }}
              </span>
            </template>
          </el-table-column>
        </el-table>
        <div class="table-foot">
          <el-pagination
            v-model:current-page="sportPage"
            v-model:page-size="sportSize"
            :page-sizes="[10, 15, 30, 60]"
            :total="sportRows.length"
            size="small"
            layout="total, sizes, prev, pager, next"
          />
        </div>
      </PanelBlock>
    </section>

    <!-- 4. 每个国家的团队数 · 气泡图 -->
    <section id="bubble" class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="每个国家拥有的团队数"
          note="横轴国家 / 地区，纵轴为 Team 字段去重后的团队数；泡泡越大、颜色越深代表团队越多。点击泡泡可加入或移出左侧数据域。"
        >
          <BaseChart :option="bubbleOption" chart-id="bubble" height="430px" @chart-click="bubbleClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>读图与参数</h3>
        <p>
          同一国家可能派出多支队伍（分队、帆船船名、混合队等）。团队数越多，
          说明该国在该区间内的参赛组织越分散。
        </p>
        <div class="side-field">
          <label>展示国家数：{{ bubbleTop }} / {{ bubbleCount }}</label>
          <el-slider v-model="bubbleTop" :min="5" :max="Math.max(5, bubbleCount)" :step="5" size="small" />
          <span class="side-hint">按团队数从高到低排序，拖动可扩展名单。</span>
        </div>
        <div class="side-field">
          <label>颜色与大小</label>
          <span class="side-hint">连续色阶由浅蓝到深海军蓝，尺寸按团队数平方根缩放。</span>
        </div>
      </aside>
    </section>

    <!-- 5. 奖牌膨胀趋势 -->
    <section id="inflation" class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="奖牌膨胀：双口径奖牌与团队数"
          note="两根柱对比两套奖牌口径，差值就是团体项目产生的复制行；折线为每届参赛团队数（非平滑，保留真实波动）。点击任意一届可联动其他图。"
        >
          <BaseChart :option="inflationOption" chart-id="inflation" height="380px" @chart-click="yearClick" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>参数设置</h3>
        <div class="side-field">
          <label>两套口径的差值</label>
          <span class="side-hint">浅色柱减深色柱，就是团体项目成员造成的复制行；二者差距随届次扩大。</span>
        </div>
        <div class="side-field is-inline">
          <label>显示团队数趋势线</label>
          <el-switch v-model="showTrend" size="small" />
        </div>
        <p class="side-hint">
          小项口径更接近官方奖牌榜，运动员行口径更接近「多少人次登上领奖台」。
          两套口径的差距在项目扩张后持续放大。
        </p>
      </aside>
    </section>

    <!-- 6. 奖牌排行榜 -->
    <section id="ranking" class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="奖牌排行榜"
          note="金银铜堆叠，按金牌数排序。切换名次范围时图表带过渡动画；点击国家可加入或移出左侧数据域。"
        >
          <BaseChart
            :option="rankingOption"
            chart-id="ranking"
            :height="rankingHeight"
            :not-merge="false"
            @chart-click="rankingClick"
          />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>排行范围</h3>
        <div class="side-field">
          <label>显示前 {{ rankingTop }} 名（最大 {{ rankingMax }}）</label>
          <el-input-number
            v-model="rankingTop"
            :min="1"
            :max="rankingMax"
            :step="5"
            size="small"
            controls-position="right"
          />
          <el-slider v-model="rankingTop" :min="1" :max="rankingMax" :step="1" size="small" />
        </div>
        <div class="side-quick">
          <button type="button" @click="setRankingQuick(10)">前 10</button>
          <button type="button" @click="setRankingQuick(20)">前 20</button>
          <button type="button" @click="setRankingQuick(50)">前 50</button>
          <button type="button" @click="setRankingQuick('all')">全部</button>
        </div>
        <p class="side-hint">
          上限为当前区间内产生奖牌的国家数。改口径或年份区间后会自动收敛到新上限。
        </p>
      </aside>
    </section>

    <!-- 7. 数据处理说明 -->
    <section id="notes" class="flow-section">
      <div class="section-head">
        <div>
          <h2>数据处理说明</h2>
          <p>影响全局数字的四类处理规则，完整说明见页面右上角的粘滞卡片。</p>
        </div>
      </div>
      <div class="notes-grid">
        <article class="notes-card">
          <h3>奖牌双口径</h3>
          <p>运动员行口径把每条奖牌记录计 1 枚；小项口径按「届次 × 小项 × 奖牌色 × NOC」去重，两者相差 53.3%。</p>
        </article>
        <article class="notes-card">
          <h3>体育大类归一</h3>
          <p>76 个原始 Sport 取值合并为 57 个大类；逗号拼接的跨项写法取首项归一，完整拆分另存字段。</p>
        </article>
        <article class="notes-card">
          <h3>小项命名泛化</h3>
          <p>2020 / 2024 两届 21.62% 的记录无法还原具体小项，保留原始值并降维到「大类 × 性别」统计。</p>
        </article>
        <article class="notes-card">
          <h3>历史特殊记录</h3>
          <p>1906 届间奥运标记为非官方；1956 双城不合并；政体继承链仅用于长周期曲线；EOR 独立保留。</p>
        </article>
      </div>
    </section>

    <!-- 任务二图表（女性弧线 / 东道主效应 / 关键洞察）暂未接入，后续在此追加 -->
  </div>
</template>
