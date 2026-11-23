<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { useS4Store } from '../stores/s4'
import { COLORS, SERIES_BLUE, axisCommon, tooltipBase, gridBase, pct, number } from '../utils/chart'

const store = useS4Store()

onMounted(async () => {
  await store.load()
  if (store.error) ElMessage.error(`S4 专题数据加载失败：${store.error}`)
})

/* ------------------------------------------------------------------ *
 * 通用格式化
 * ------------------------------------------------------------------ */
const SIZE_ORDER = ['微型(≤10)', '小型(11-50)', '中型(51-150)', '大型(>150)']

function pct2(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(2)}%`
}

function fmtP(value) {
  if (value === null || value === undefined) return '—'
  if (value === 0) return '≈0'
  if (value < 0.001) return Number(value).toExponential(1)
  return Number(value).toFixed(4)
}

function fmtMedian(key, value) {
  if (value === null || value === undefined) return '—'
  return ['top1_share', 'medal_per_athlete', 'hhi'].includes(key)
    ? Number(value).toFixed(3)
    : String(Math.round(Number(value)))
}

/* ------------------------------------------------------------------ *
 * KPI
 * ------------------------------------------------------------------ */
const kpis = computed(() => {
  const k = store.kpi
  return [
    {
      label: '微型团近代夺牌率',
      value: pct2(k.microModernRate),
      hint: `${number(k.microModernEditions)} 个 ≤10 人届次中 ${k.microModernWithMedal} 个拿牌；≤5 人极端样本 ${k.tinyCases} 个`
    },
    {
      label: '小团单项目依赖率',
      value: pct2(k.singleSportShare),
      hint: `全部奖牌来自一个大类；大团仅 ${pct2(k.singleSportBigShare)}`
    },
    {
      label: '小团型国家首牌后夺牌率',
      value: pct2(k.smallPostMedian),
      hint: `中位；大团型 ${pct2(k.bigPostMedian)}`
    },
    {
      label: '小团奖牌份额（2024）',
      value: pct2(k.smallShare2024),
      hint: `1980 年 ${pct2(k.smallShare1980)} → 2024 年 ${pct2(k.smallShare2024)}；占比上升的是产出，不是数量`
    },
    {
      label: '一次性突破国',
      value: pct2(k.oneHitShare),
      hint: `${k.oneHitCount} / ${k.medalNations} 个曾夺牌国只在一届拿牌`
    }
  ]
})

/* ------------------------------------------------------------------ *
 * 一、全景：规模 × 夺牌率
 * ------------------------------------------------------------------ */
const sizeMetric = ref('rate')
const sizeMetricOptions = [
  { label: '夺牌率', value: 'rate' },
  { label: '奖牌数', value: 'medal' },
  { label: '代表团届次', value: 'editions' }
]

const sizeRows = computed(() => {
  const classes = SIZE_ORDER
  const eras = ['早期(<1980)', '近代(1980+)']
  return classes.map((sizeClass) => {
    const row = { sizeClass }
    for (const era of eras) {
      const hit = store.sizeDistribution.find((item) => item.sizeClass === sizeClass && item.era === era)
      row[era] = hit ?? null
    }
    return row
  })
})

const sizeOption = computed(() => {
  const metric = sizeMetric.value
  const key = metric === 'rate' ? 'medalRate' : metric === 'medal' ? 'totalMedal' : 'editions'
  const isRate = metric === 'rate'
  const eras = [
    { era: '早期(<1980)', name: '早期（<1980）', color: COLORS.bluePale },
    { era: '近代(1980+)', name: '近代（1980+）', color: COLORS.blue }
  ]
  return {
    grid: gridBase({ top: 40, right: 24 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const first = params[0]
        const row = sizeRows.value[first.dataIndex]
        const lines = params.map((item) => {
          const hit = row[item.seriesName === '早期（<1980）' ? '早期(<1980)' : '近代(1980+)']
          const value = isRate ? pct2(hit?.[key]) : number(hit?.[key])
          return `${item.marker}${item.seriesName}：<b>${value}</b>（${number(hit?.withMedal)} / ${number(hit?.editions)} 届次）`
        })
        return `<b>${row.sizeClass}</b><br/>${lines.join('<br/>')}`
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: sizeRows.value.map((row) => row.sizeClass),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, interval: 0, fontSize: 10 }
    },
    yAxis: {
      type: 'value',
      name: isRate ? '夺牌率（%）' : metric === 'medal' ? '奖牌数' : '届次数',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: isRate ? '{value}%' : '{value}' }
    },
    series: eras.map((item) => ({
      name: item.name,
      type: 'bar',
      barMaxWidth: 26,
      itemStyle: { color: item.color },
      label: {
        show: true,
        position: 'top',
        fontSize: 10,
        color: COLORS.muted,
        formatter: (params) => (isRate ? `${Number(params.value).toFixed(1)}%` : params.value)
      },
      labelLayout: { hideOverlap: true },
      data: sizeRows.value.map((row) => {
        const hit = row[item.era]
        if (!hit) return null
        return isRate ? +(hit[key] * 100).toFixed(2) : hit[key]
      })
    }))
  }
})

/* ------------------------------------------------------------------ *
 * 二、趋势：小团夺牌率百年变化
 * ------------------------------------------------------------------ */
const trendOption = computed(() => {
  const rows = store.smallRateByYear
  return {
    grid: gridBase({ top: 40, right: 24 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => {
        const year = params[0]?.name
        const row = rows.find((item) => item.year === Number(year))
        if (!row) return year
        return [
          `<b>${year} 届</b>`,
          `小团夺牌率：<b>${pct2(row.smallMedalRate)}</b>（${row.smallMedalN} / ${row.smallN}）`,
          `大团夺牌率：${pct2(row.bigMedalRate)}（${row.bigMedalN} / ${row.bigN}）`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (Number(value) % 20 === 0 ? value : '') }
    },
    yAxis: {
      type: 'value',
      name: '夺牌率（%）',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }
    },
    series: [
      {
        name: '小团（≤50 人）',
        type: 'line',
        smooth: false,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 2, color: COLORS.blue },
        itemStyle: { color: COLORS.blue },
        areaStyle: { color: 'rgba(37,99,235,.06)' },
        data: rows.map((row) => +(row.smallMedalRate * 100).toFixed(2)),
        markLine: {
          symbol: 'none',
          lineStyle: { color: COLORS.host, width: 1, type: 'dashed' },
          label: { formatter: '断点 1980', color: COLORS.host, fontSize: 10, position: 'insideEndTop' },
          data: [{ xAxis: '1980' }]
        },
        markArea: {
          silent: true,
          itemStyle: { color: 'rgba(37,99,235,.05)' },
          data: [[{ xAxis: '1980' }, { xAxis: '2024' }]]
        }
      },
      {
        name: '大团（>150 人）',
        type: 'line',
        smooth: false,
        symbol: 'none',
        lineStyle: { width: 1.4, color: COLORS.silver, type: 'dashed' },
        itemStyle: { color: COLORS.silver },
        data: rows.map((row) => +(row.bigMedalRate * 100).toFixed(2))
      }
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 三、机制：集中度
 * ------------------------------------------------------------------ */
const scatterPeriod = ref('modern')
const scatterMetric = ref('top1Share')
const scatterMetricOptions = [
  { label: '最大单项份额', value: 'top1Share' },
  { label: '夺牌大类数', value: 'nSports' },
  { label: 'HHI', value: 'hhi' }
]

const scatterRows = computed(() => {
  const rows = scatterPeriod.value === 'modern' ? store.modernScatter : store.scatter
  return rows.filter((row) => row[scatterMetric.value] !== null && row[scatterMetric.value] !== undefined)
})

const scatterOption = computed(() => {
  const metric = scatterMetric.value
  const label = scatterMetricOptions.find((item) => item.value === metric)?.label ?? metric
  const classes = SIZE_ORDER.filter((sizeClass) => scatterRows.value.some((row) => row.sizeClass === sizeClass))
  return {
    grid: gridBase({ left: 56, right: 28, top: 36, bottom: 52 }),
    tooltip: tooltipBase({
      formatter: (params) => {
        const item = params.data
        if (!item) return params.name
        return [
          `<b>${item.team}（${item.noc}）</b> · ${item.year}`,
          `参赛人数：${number(item.athletes)}`,
          `${label}：<b>${metric === 'nSports' ? item.nSports : Number(item[metric]).toFixed(3)}</b>`,
          `奖牌：${item.total} 枚 · 主线项目：${item.topSport || '—'}`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'log',
      name: '参赛人数（对数轴）',
      nameLocation: 'middle',
      nameGap: 28,
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      min: 1,
      max: 1200,
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (value >= 1000 ? `${value / 1000}k` : value) }
    },
    yAxis: {
      type: 'value',
      name: label,
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      max: metric === 'top1Share' || metric === 'hhi' ? 1 : undefined
    },
    series: classes.map((sizeClass, index) => ({
      name: sizeClass,
      type: 'scatter',
      symbolSize: (value, params) => (params.data?.named ? 12 : 5),
      large: true,
      largeThreshold: 500,
      itemStyle: {
        color: SERIES_BLUE[index % SERIES_BLUE.length],
        opacity: 0.5,
        borderColor: 'transparent'
      },
      emphasis: { itemStyle: { opacity: 1, borderColor: COLORS.ink, borderWidth: 1 } },
      label: {
        show: true,
        position: 'right',
        fontSize: 9,
        color: COLORS.ink,
        formatter: (params) => (params.data?.named ? params.data.noc : '')
      },
      data: scatterRows.value
        .filter((row) => row.sizeClass === sizeClass)
        .map((row) => ({
          value: [row.athletes, row[metric]],
          ...row
        }))
    }))
  }
})

const scatterStats = computed(() => {
  const spearman = store.analysis?.B_strategy?.spearman ?? {}
  const map = {
    top1Share: { modern: 'athletes_vs_top1_share_1980plus', all: 'athletes_vs_top1_share_all_years' },
    nSports: { modern: 'athletes_vs_n_sports_medal_1980plus', all: 'athletes_vs_n_sports_medal_all_years' },
    hhi: { modern: 'athletes_vs_hhi_1980plus', all: null }
  }
  const key = map[scatterMetric.value]?.[scatterPeriod.value === 'modern' ? 'modern' : 'all']
  return key ? spearman[key] : null
})

const singleSport = computed(() => store.analysis?.B_strategy?.single_sport_dependence ?? {})

/** 小团 vs 大团的五项集中度检验，供表格使用 */
const groupRows = computed(() => {
  const results = store.analysis?.B_strategy?.group_compare_small50_vs_big150?.results ?? {}
  const labels = {
    top1_share: '最大单项份额',
    n_sports_medal: '夺牌大类数',
    medal_per_athlete: '奖牌 / 运动员',
    hhi: 'HHI',
    Total_event: '当届奖牌数'
  }
  return Object.entries(results).map(([key, row]) => ({ key, label: labels[key] ?? key, ...row }))
})

const singleSportOption = computed(() => {
  const rows = [
    { name: '小团（≤50）', value: singleSport.value.small_le50_share_top1_eq_1, n: singleSport.value.n_small, color: COLORS.blue },
    { name: '大团（>150）', value: singleSport.value.big_gt150_share_top1_eq_1, n: singleSport.value.n_big, color: COLORS.silver },
    { name: '近代全体', value: singleSport.value.all_modern_share_top1_eq_1, n: (singleSport.value.n_small ?? 0) + (singleSport.value.n_big ?? 0), color: COLORS.bluePale }
  ]
  return {
    grid: gridBase({ top: 28, right: 30, bottom: 28 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const item = rows[params[0].dataIndex]
        return `<b>${item.name}</b><br/>单项目依赖率：${pct2(item.value)}<br/>样本：${number(item.n)} 个夺牌届次`
      }
    }),
    xAxis: { type: 'category', data: rows.map((row) => row.name), ...axisCommon },
    yAxis: {
      type: 'value',
      name: '依赖率（%）',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      max: 100,
      axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 46,
        label: { show: true, position: 'top', fontSize: 11, formatter: (params) => `${Number(params.value).toFixed(1)}%` },
        data: rows.map((row) => ({
          value: +(row.value * 100).toFixed(2),
          itemStyle: { color: row.color }
        }))
      }
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 四、人效
 * ------------------------------------------------------------------ */
const effMetric = ref('median')
const effMetricOptions = [
  { label: '中位人效', value: 'median' },
  { label: '均值人效', value: 'mean' }
]

const efficiencyOption = computed(() => {
  const isMedian = effMetric.value === 'median'
  const rows = store.efficiency
  const bars = rows.map((row) => (isMedian ? row.mpaMedian : row.mpaMean))
  return {
    grid: gridBase({ top: 40, right: 26, bottom: 36 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = rows[params[0].dataIndex]
        const value = isMedian ? row.mpaMedian : row.mpaMean
        const ci = isMedian ? `<br/>95% CI：${row.ciLow?.toFixed(4)} – ${row.ciHigh?.toFixed(4)}` : ''
        return `<b>${row.bin} 人</b><br/>有奖牌届次：${row.withMedal}<br/>人效${isMedian ? '中位' : '均值'}：<b>${value?.toFixed(4)}</b>${ci}`
      }
    }),
    xAxis: { type: 'category', data: rows.map((row) => row.bin), ...axisCommon },
    yAxis: {
      type: 'value',
      name: '奖牌 / 参赛人数',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon
    },
    series: [
      {
        type: 'bar',
        barMaxWidth: 34,
        itemStyle: { color: COLORS.blue },
        label: { show: true, position: 'top', fontSize: 9, color: COLORS.muted, formatter: (params) => Number(params.value).toFixed(3) },
        data: bars
      },
      ...(isMedian
        ? [{
            type: 'custom',
            name: '95% CI',
            z: 6,
            encode: { x: 0, y: [1, 2] },
            data: rows.map((row, index) => [index, row.ciLow, row.ciHigh]),
            renderItem(params, api) {
              const index = api.value(0)
              const low = api.value(1)
              const high = api.value(2)
              if (low === null || high === null) return null
              const x = api.coord([index, low])[0]
              const yLow = api.coord([index, low])[1]
              const yHigh = api.coord([index, high])[1]
              const cap = 5
              return {
                type: 'group',
                children: [
                  { type: 'line', shape: { x1: x, y1: yLow, x2: x, y2: yHigh }, style: { stroke: COLORS.deep, lineWidth: 1 } },
                  { type: 'line', shape: { x1: x - cap, y1: yLow, x2: x + cap, y2: yLow }, style: { stroke: COLORS.deep, lineWidth: 1 } },
                  { type: 'line', shape: { x1: x - cap, y1: yHigh, x2: x + cap, y2: yHigh }, style: { stroke: COLORS.deep, lineWidth: 1 } }
                ]
              }
            }
          }]
        : [])
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 五、个案：八国构成与轨迹
 * ------------------------------------------------------------------ */
const caseCountries = computed(() => store.caseCountriesSorted)

const caseTopSports = computed(() => {
  const totals = new Map()
  for (const row of store.caseSports) {
    totals.set(row.sport, (totals.get(row.sport) ?? 0) + row.total)
  }
  return [...totals.entries()].sort((a, b) => b[1] - a[1]).slice(0, 6).map(([sport]) => sport)
})

const caseStackOption = computed(() => {
  const countriesDesc = caseCountries.value
  const countries = [...countriesDesc].reverse()
  const top = caseTopSports.value
  const totals = countries.map((country) =>
    store.caseSports.filter((row) => row.noc === country.noc).reduce((sum, row) => sum + row.total, 0)
  )
  const series = top.map((sport, index) => ({
    name: sport,
    type: 'bar',
    stack: 'medal',
    barMaxWidth: 18,
    itemStyle: { color: SERIES_BLUE[index % SERIES_BLUE.length] },
    data: countries.map((country) =>
      store.caseSports.filter((row) => row.noc === country.noc && row.sport === sport).reduce((sum, row) => sum + row.total, 0)
    )
  }))
  series.push({
    name: '其他',
    type: 'bar',
    stack: 'medal',
    barMaxWidth: 18,
    itemStyle: { color: '#CBD5E1' },
    label: {
      show: true,
      position: 'right',
      fontSize: 10,
      color: COLORS.muted,
      formatter: (params) => totals[params.dataIndex]
    },
    data: countries.map((country, index) => {
      const topSum = store.caseSports
        .filter((row) => row.noc === country.noc && top.includes(row.sport))
        .reduce((sum, row) => sum + row.total, 0)
      return Math.max(0, totals[index] - topSum)
    })
  })
  return {
    grid: gridBase({ left: 14, right: 48, top: 36, bottom: 20 }),
    tooltip: tooltipBase({ trigger: 'axis', axisPointer: { type: 'shadow' } }),
    legend: { top: 0, right: 0, type: 'scroll', itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: { type: 'value', ...axisCommon },
    yAxis: {
      type: 'category',
      data: countries.map((country) => `${country.team}（${country.noc}）`),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: { ...axisCommon.axisLabel, fontSize: 10 }
    },
    series
  }
})

const caseNOC = ref('HKG')
const caseNOCountries = computed(() =>
  caseCountries.value.filter((country) => ['HKG', 'SGP', 'TPE'].includes(country.noc))
)
const caseSummary = computed(() => caseCountries.value.find((country) => country.noc === caseNOC.value) ?? null)
const caseDetailRows = computed(() => store.caseDetail[caseNOC.value] ?? [])

const caseTrajectoryOption = computed(() => {
  const rows = caseDetailRows.value
  return {
    grid: gridBase({ top: 40, right: 48, bottom: 30 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => {
        const row = rows[params[0]?.dataIndex]
        if (!row) return ''
        return [
          `<b>${row.year} 届</b>`,
          `小项奖牌：<b>${row.total}</b>（金 ${row.gold} / 银 ${row.silver} / 铜 ${row.bronze}）`,
          `参赛人数：${row.athletes}`,
          row.hasMedal ? `夺牌大类：${row.medalSports || '—'}` : '当届无奖牌'
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: rows.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, fontSize: 10 }
    },
    yAxis: [
      { type: 'value', name: '小项奖牌', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon },
      { type: 'value', name: '参赛人数', nameTextStyle: { fontSize: 10, color: COLORS.muted }, ...axisCommon, splitLine: { show: false } }
    ],
    series: [
      {
        name: '金牌',
        type: 'bar',
        stack: 'medal',
        barMaxWidth: 16,
        itemStyle: { color: COLORS.gold },
        data: rows.map((row) => row.gold)
      },
      {
        name: '银牌',
        type: 'bar',
        stack: 'medal',
        barMaxWidth: 16,
        itemStyle: { color: COLORS.silver },
        data: rows.map((row) => row.silver)
      },
      {
        name: '铜牌',
        type: 'bar',
        stack: 'medal',
        barMaxWidth: 16,
        itemStyle: { color: COLORS.bronze },
        data: rows.map((row) => row.bronze)
      },
      {
        name: '参赛人数',
        type: 'line',
        yAxisIndex: 1,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.6, color: COLORS.host },
        itemStyle: { color: COLORS.host },
        data: rows.map((row) => row.athletes)
      }
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 六、持续性
 * ------------------------------------------------------------------ */
const persistenceOverview = computed(() => store.analysis?.D_persistence?.persistence_overview ?? {})

const persistenceOption = computed(() => {
  const rows = (store.persistence.detail ?? []).filter((row) => row.postRate !== null)
  const types = ['小团型(峰值≤50)', '大团型(峰值>50)']
  const colors = { '小团型(峰值≤50)': COLORS.gold, '大团型(峰值>50)': COLORS.blue }
  const labelNOCs = ['HKG', 'SGP', 'TPE', 'GEO', 'KOS', 'ARM', 'MGL', 'GRN']
  return {
    grid: gridBase({ left: 56, right: 30, top: 36, bottom: 52 }),
    tooltip: tooltipBase({
      formatter: (params) => {
        const item = params.data
        if (!item) return ''
        return [
          `<b>${item.team}（${item.noc}）</b>`,
          `峰值参赛：${item.maxAthletes} 人 · ${item.teamType}`,
          `首牌后夺牌率：<b>${pct2(item.postRate)}</b>`,
          `最长连续：${item.maxStreak} 届 · 历史奖牌：${item.totalMedal}`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 8, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'log',
      name: '历史峰值参赛人数（对数轴）',
      nameLocation: 'middle',
      nameGap: 28,
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      min: 1,
      max: 1300,
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => (value >= 1000 ? `${value / 1000}k` : value) }
    },
    yAxis: {
      type: 'value',
      name: '首牌后夺牌率',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      max: 1,
      axisLabel: { ...axisCommon.axisLabel, formatter: (value) => `${Math.round(value * 100)}%` }
    },
    series: types.map((type) => ({
      name: type,
      type: 'scatter',
      symbolSize: (value, params) => 4 + Math.sqrt(params.data?.total ?? 1),
      itemStyle: { color: colors[type], opacity: 0.55 },
      emphasis: { itemStyle: { opacity: 1, borderColor: COLORS.ink, borderWidth: 1 } },
      label: {
        show: true,
        position: 'right',
        fontSize: 9,
        color: COLORS.ink,
        formatter: (params) => (labelNOCs.includes(params.data?.noc) ? params.data.noc : '')
      },
      data: rows
        .filter((row) => row.teamType === type)
        .map((row) => ({ value: [Math.max(1, row.maxAthletes), row.postRate], ...row }))
    }))
  }
})

const boardOption = computed(() => {
  const rows = [...store.smallNocBoard].reverse()
  return {
    grid: gridBase({ left: 14, right: 56, top: 28, bottom: 20 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      axisPointer: { type: 'shadow' },
      formatter: (params) => {
        const row = store.smallNocBoard[store.smallNocBoard.length - 1 - params[0].dataIndex]
        if (!row) return ''
        return `<b>${row.team}（${row.noc}）</b><br/>总奖牌：${row.total}（金 ${row.gold}）<br/>峰值参赛：${row.peakAthletes} 人 · ${row.editions} 届`
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: { type: 'value', ...axisCommon },
    yAxis: {
      type: 'category',
      data: rows.map((row) => `${row.team}（${row.noc}）`),
      ...axisCommon,
      splitLine: { show: false },
      axisLabel: { ...axisCommon.axisLabel, fontSize: 10 }
    },
    series: [
      {
        name: '金牌',
        type: 'bar',
        stack: 'medal',
        barMaxWidth: 16,
        itemStyle: { color: COLORS.gold },
        data: rows.map((row) => row.gold)
      },
      {
        name: '银 + 铜',
        type: 'bar',
        stack: 'medal',
        barMaxWidth: 16,
        itemStyle: { color: COLORS.blue },
        label: {
          show: true,
          position: 'right',
          fontSize: 10,
          color: COLORS.muted,
          formatter: (params) => rows[params.dataIndex]?.total ?? ''
        },
        data: rows.map((row) => Math.max(0, row.total - row.gold))
      }
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 七、结构变化
 * ------------------------------------------------------------------ */
const structureTrend = computed(() => store.structure.trend ?? {})
const structureOls = computed(() => structureTrend.value.trend_1980_2024_ols ?? {})

const structureOption = computed(() => {
  const rows = store.structure.series ?? []
  return {
    grid: gridBase({ top: 40, right: 52, bottom: 30 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => {
        const row = rows[params[0]?.dataIndex]
        if (!row) return ''
        return [
          `<b>${row.year} 届</b>`,
          `参赛国：${row.nocCount} · 小团：${row.smallCount}`,
          `小团占参赛国：<b>${pct2(row.smallShareOfNoc)}</b>`,
          `小团奖牌份额：<b>${pct2(row.smallMedalShare)}</b>（${row.smallMedal} / ${row.totalMedal}）`,
          `小团夺牌国份额：${pct2(row.smallMedalNocShare)}`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: { type: 'category', data: rows.map((row) => row.year), ...axisCommon },
    yAxis: [
      {
        type: 'value',
        name: '小团奖牌份额（%）',
        nameTextStyle: { fontSize: 10, color: COLORS.muted },
        ...axisCommon,
        axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }
      },
      {
        type: 'value',
        name: '占比（%）',
        nameTextStyle: { fontSize: 10, color: COLORS.muted },
        ...axisCommon,
        max: 100,
        splitLine: { show: false },
        axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }
      }
    ],
    series: [
      {
        name: '小团奖牌份额',
        type: 'bar',
        barMaxWidth: 22,
        itemStyle: { color: COLORS.blue },
        label: { show: true, position: 'top', fontSize: 9, color: COLORS.muted, formatter: (params) => `${Number(params.value).toFixed(1)}%` },
        labelLayout: { hideOverlap: true },
        data: rows.map((row) => +(row.smallMedalShare * 100).toFixed(2))
      },
      {
        name: '小团占参赛国比例',
        type: 'line',
        yAxisIndex: 1,
        symbol: 'circle',
        symbolSize: 4,
        lineStyle: { width: 1.8, color: COLORS.gold },
        itemStyle: { color: COLORS.gold },
        data: rows.map((row) => +(row.smallShareOfNoc * 100).toFixed(1))
      },
      {
        name: '小团夺牌国份额',
        type: 'line',
        yAxisIndex: 1,
        symbol: 'none',
        lineStyle: { width: 1.4, color: COLORS.silver, type: 'dashed' },
        itemStyle: { color: COLORS.silver },
        data: rows.map((row) => +(row.smallMedalNocShare * 100).toFixed(1))
      }
    ]
  }
})

/* ------------------------------------------------------------------ *
 * 八、稳健性
 * ------------------------------------------------------------------ */
const thresholdRows = computed(() => store.sensitivity.threshold ?? [])
const caliberRows = computed(() => store.sensitivity.caliber ?? [])
const thresholdVerdict = computed(() => store.sensitivity.verdict ?? {})

const thresholdOption = computed(() => {
  const rows = thresholdRows.value
  return {
    grid: gridBase({ top: 42, right: 30, bottom: 28 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => {
        const row = rows[params[0]?.dataIndex]
        if (!row) return ''
        return [
          `<b>阈值 ≤${row.threshold} 人</b>`,
          `小团人效中位：<b>${row.smallMpaMedian?.toFixed(4)}</b>`,
          `大团人效中位：${row.bigMpaMedian?.toFixed(4)}`,
          `p = ${fmtP(row.mpaP)} · 效应量 r = ${row.mpaEffectR?.toFixed(3)}`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: { type: 'category', data: rows.map((row) => `≤${row.threshold}`), ...axisCommon },
    yAxis: {
      type: 'value',
      name: '人效中位',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon
    },
    series: [
      {
        name: '小团人效',
        type: 'line',
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 2, color: COLORS.blue },
        itemStyle: { color: COLORS.blue },
        label: { show: true, position: 'top', fontSize: 9, color: COLORS.muted, formatter: (params) => Number(params.value).toFixed(3) },
        data: rows.map((row) => row.smallMpaMedian),
        markLine: {
          symbol: 'none',
          lineStyle: { color: COLORS.host, type: 'dashed', width: 1 },
          label: { formatter: '方向翻转', color: COLORS.host, fontSize: 10, position: 'insideEndTop' },
          data: [{ xAxis: '≤150' }]
        }
      },
      {
        name: '大团人效',
        type: 'line',
        symbol: 'circle',
        symbolSize: 6,
        lineStyle: { width: 1.8, color: COLORS.gold },
        itemStyle: { color: COLORS.gold },
        label: { show: true, position: 'bottom', fontSize: 9, color: COLORS.muted, formatter: (params) => Number(params.value).toFixed(3) },
        data: rows.map((row) => row.bigMpaMedian)
      }
    ]
  }
})

const shareTrendRows = computed(() => store.sensitivity.shareTrendByThreshold ?? [])
const shareTrendOption = computed(() => {
  const rows = shareTrendRows.value
  if (!rows.length) return null
  const years = [...new Set(rows.map((row) => row.year))].sort((a, b) => a - b)
  const thresholds = [...new Set(rows.map((row) => row.threshold))].sort((a, b) => a - b)
  return {
    grid: gridBase({ top: 40, right: 30, bottom: 30 }),
    tooltip: tooltipBase({ trigger: 'axis', formatter: (params) => {
      const year = params[0]?.name
      return `<b>${year} 届</b><br/>${params.map((item) => `${item.marker}${item.seriesName}：${Number(item.value).toFixed(2)}%`).join('<br/>')}`
    } }),
    legend: { top: 0, right: 0, itemWidth: 9, itemHeight: 8, textStyle: { fontSize: 10, color: COLORS.muted } },
    xAxis: { type: 'category', data: years, ...axisCommon },
    yAxis: {
      type: 'value',
      name: '小团奖牌份额（%）',
      nameTextStyle: { fontSize: 10, color: COLORS.muted },
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, formatter: '{value}%' }
    },
    series: thresholds.map((threshold, index) => ({
      name: `≤${threshold} 人`,
      type: 'line',
      symbol: 'circle',
      symbolSize: threshold === 50 ? 5 : 3,
      lineStyle: { width: threshold === 50 ? 2.4 : 1.2, color: SERIES_BLUE[index % SERIES_BLUE.length] },
      itemStyle: { color: SERIES_BLUE[index % SERIES_BLUE.length] },
      data: years.map((year) => {
        const hit = rows.find((row) => row.year === year && row.threshold === threshold)
        return hit ? +(hit.share * 100).toFixed(2) : null
      })
    }))
  }
})

const verifiedCount = computed(() =>
  store.verification.filter((row) => row['结果'] === '通过').length
)
</script>

<template>
  <div>
    <PageHeader
      title="小团突破 · S4 专题"
      subtitle="参赛规模很小的代表团靠什么取得超出体量的突破？突破口是集中押注还是全面铺开？这种突破能否持续？本页把研究报告的六条结论拆成可交互的图表与数据表。"
    >
      <template #actions>
        <span class="tag is-blue">主口径 · 小项 17,901</span>
        <span class="tag">近代样本 · 1980+</span>
      </template>
    </PageHeader>

    <div v-if="store.loading" class="state-panel">正在加载 S4 专题数据…</div>
    <div v-else-if="store.error" class="state-panel state-error">
      <div>专题数据加载失败：{{ store.error }}</div>
      <el-button size="small" @click="store.load(true)">重试</el-button>
    </div>

    <template v-else>
      <KpiStrip :items="kpis" />

      <div class="hint-bar">
        本页固定使用 S4 专题口径：小项口径 17,901 枚，小团主阈值 ≤50 人，近代样本 1980 年起。
        左侧全局年份区间与数据域不影响本页；各图右侧提供专题自己的阈值、样本与指标切换。
      </div>

      <!-- ============================ 一、全景 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>一、全景：多小的团还能拿牌</h2>
            <p>
              规模是硬约束。近代微型团（≤10 人）夺牌率只有 <b>5.20%</b>，但仍有 48 个届次站上领奖台；
              小型团（11–50 人）稳定在 <b>37.84%</b>，是「能稳定参与竞争」的最小规模区间。
            </p>
          </div>
        </div>

        <PanelBlock
          title="四档规模 × 两个时代"
          note="夺牌率 = 当届有小项口径奖牌的代表团数 / 该档代表团届次总数。表格按微型 → 大型排列。"
          flush
        >
          <el-table :data="sizeRows" size="small">
            <el-table-column prop="sizeClass" label="规模档" min-width="120" />
            <el-table-column label="早期届次" width="96" align="center">
              <template #default="{ row }">{{ row['早期(<1980)']?.editions ?? '—' }}</template>
            </el-table-column>
            <el-table-column label="早期夺牌率" width="110" align="center">
              <template #default="{ row }">{{ pct2(row['早期(<1980)']?.medalRate) }}</template>
            </el-table-column>
            <el-table-column label="近代届次" width="96" align="center">
              <template #default="{ row }">{{ row['近代(1980+)']?.editions ?? '—' }}</template>
            </el-table-column>
            <el-table-column label="近代夺牌率" width="110" align="center">
              <template #default="{ row }">
                <b>{{ pct2(row['近代(1980+)']?.medalRate) }}</b>
              </template>
            </el-table-column>
            <el-table-column label="全期奖牌" width="96" align="center">
              <template #default="{ row }">
                {{ number((row['早期(<1980)']?.totalMedal ?? 0) + (row['近代(1980+)']?.totalMedal ?? 0)) }}
              </template>
            </el-table-column>
            <el-table-column label="最大样本提示" min-width="220">
              <template #default="{ row }">
                <span v-if="row.sizeClass === '微型(≤10)'">5.20% 的近代夺牌率，仍对应 48 个夺牌届次</span>
                <span v-else-if="row.sizeClass === '大型(>150)'">近代 282 个届次无一空手，规模已足以保证奖牌</span>
                <span v-else-if="row.sizeClass === '小型(11-50)'">HKG / SGP 所在区间，夺牌能力对时代不敏感</span>
                <span v-else>中型团是「小团」与「大团」之间的过渡带</span>
              </template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="四档规模的夺牌率对比"
              note="同一档位在早期与近代的差异。微型团近代夺牌率低于早期，是竞争密度变化，不是绝对退步。"
            >
              <BaseChart :option="sizeOption" height="360px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>参数设置</h3>
            <div class="side-field">
              <label>统计指标</label>
              <el-radio-group v-model="sizeMetric" size="small">
                <el-radio-button v-for="item in sizeMetricOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
            <p class="side-hint">
              早期 = 1980 年前；近代 = 1980 年及以后。悬停柱体可看该档的「有奖牌届次 / 总届次」。
            </p>
            <p>
              <b>读数提示：</b>大型团近代夺牌率 100%，说明「规模 >150」已足以保证至少一枚奖牌；
              微型团的 5.20% 才是「派一个极小的团去奥运会」的原始概率。
            </p>
          </aside>
        </section>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="小团夺牌率的百年趋势"
              note="1980 年是主断点：近代 OLS 斜率 +0.1938 pp/年、R² 0.6047、p 0.0029；全期 OLS 斜率为负。"
            >
              <BaseChart :option="trendOption" height="340px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>拐点 1980</h3>
            <p>
              1950–1970 年代小团夺牌率从三成跌到 12.5%，那是奥运会扩军阶段：新独立国家大批入会，分母暴涨。
              1980 年后进入平台期并回升。
            </p>
            <div class="side-fact"><span>1980 → 2024</span><b>16.67% → 25.33%</b></div>
            <div class="side-fact"><span>近代 OLS 斜率</span><b>+0.1938 pp/年</b></div>
            <div class="side-fact"><span>全期 OLS 斜率</span><b>−0.4115 pp/年</b></div>
            <p class="side-hint">
              同一份数据，切在 1980 得到「小团在变强」，不切得到「小团在变弱」。本页采用 1980 主断点，
              并把代价写在读数里。
            </p>
          </aside>
        </section>
      </section>

      <!-- ============================ 二、机制 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>二、机制：近乎必然的单一项目押注</h2>
            <p>
              小团 72.44% 的夺牌届次，全部奖牌来自同一个运动大类；大团只有 0.71%。
              参赛人数与最大单项份额的 Spearman ρ = −0.7903，两个群体的分布几乎不重叠。
            </p>
          </div>
        </div>

        <PanelBlock
          title="小团 vs 大团：集中度五项指标"
          note="样本：1980+ 有奖牌的代表团届次，小团 n=283，大团 n=282。效应量 r 接近 1 表示两组分布几乎不重叠。"
          flush
        >
          <el-table :data="groupRows" size="small">
            <el-table-column prop="label" label="指标" min-width="140" />
            <el-table-column label="小团中位" width="100" align="center">
              <template #default="{ row }">{{ fmtMedian(row.key, row.median1) }}</template>
            </el-table-column>
            <el-table-column label="大团中位" width="100" align="center">
              <template #default="{ row }">{{ fmtMedian(row.key, row.median2) }}</template>
            </el-table-column>
            <el-table-column label="Mann-Whitney U" width="130" align="center">
              <template #default="{ row }">{{ number(row.U) }}</template>
            </el-table-column>
            <el-table-column label="p 值" width="110" align="center">
              <template #default="{ row }">{{ fmtP(row.p) }}</template>
            </el-table-column>
            <el-table-column label="效应量 r" width="100" align="center">
              <template #default="{ row }">{{ row.effect_r?.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column prop="direction" label="方向" width="100" align="center" />
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="参赛规模 × 夺牌集中度"
              note="鼠标悬停可看具体国家、届次与主线项目；带标签的点是报告点名的案例。纵轴可切换三项指标。"
            >
              <BaseChart :option="scatterOption" height="400px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>参数设置</h3>
            <div class="side-field">
              <label>样本范围</label>
              <el-radio-group v-model="scatterPeriod" size="small">
                <el-radio-button value="modern">1980+ 有奖牌</el-radio-button>
                <el-radio-button value="all">全期有奖牌</el-radio-button>
              </el-radio-group>
            </div>
            <div class="side-field">
              <label>纵轴指标</label>
              <el-radio-group v-model="scatterMetric" size="small">
                <el-radio-button v-for="item in scatterMetricOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
            <div v-if="scatterStats" class="side-stats">
              <div><span>Spearman ρ</span><b>{{ scatterStats.rho?.toFixed(3) }}</b></div>
              <div><span>p 值</span><b>{{ fmtP(scatterStats.p) }}</b></div>
              <div><span>样本量</span><b>{{ scatterStats.n }}</b></div>
            </div>
            <p class="side-hint">
              当前显示 {{ scatterRows.length }} 个代表团届次。横轴为对数刻度，避免小团被挤在左端。
            </p>
          </aside>
        </section>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="单项目依赖率"
              note="「全部奖牌来自同一个运动大类」的届次占比。全体近代样本的 32.38% 是两个极端的加权平均，不能描述任一群体。"
            >
              <BaseChart :option="singleSportOption" height="300px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>为什么必然是集中</h3>
            <p>
              参赛 30 人通常只能覆盖 7–11 个大类，其中能进世界前三的通常只有 1 个。
              押注不是策略选择，是规模约束的必然产物。
            </p>
            <div class="side-fact"><span>小团依赖率</span><b>72.44%（205 / 283）</b></div>
            <div class="side-fact"><span>大团依赖率</span><b>0.71%（2 / 282）</b></div>
            <div class="side-fact"><span>全体近代</span><b>32.38%（283 / 874）</b></div>
            <p class="side-hint">
              HKG 2020（65 人、5 个大类、top1_share 0.333）是明确反例——「必然」是统计陈述，不是逻辑必然。
            </p>
          </aside>
        </section>
      </section>

      <!-- ============================ 三、人效 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>三、人效：U 形曲线与幸存者效应</h2>
            <p>
              1–5 人团人效中位 0.2917，是 201+ 人团的 4.1 倍。但分箱分母只统计「有奖牌的届次」，
              649 个「≤5 人且 0 奖牌」的届次被排除在外。曲线还是 U 形，不是单调下降。
            </p>
          </div>
        </div>

        <PanelBlock
          title="按参赛人数分箱的人效"
          note="人效 = 小项口径奖牌 / 参赛人数。95% CI 为 2,000 次 bootstrap（seed=42）的 percentile 区间。"
          flush
        >
          <el-table :data="store.efficiency" size="small">
            <el-table-column prop="bin" label="人数分箱" width="110" align="center" />
            <el-table-column prop="withMedal" label="有奖牌届次" width="110" align="center" />
            <el-table-column label="人效中位" width="110" align="center">
              <template #default="{ row }"><b>{{ row.mpaMedian?.toFixed(4) }}</b></template>
            </el-table-column>
            <el-table-column label="95% CI" min-width="180" align="center">
              <template #default="{ row }">{{ row.ciLow?.toFixed(4) }} – {{ row.ciHigh?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="人效均值" width="110" align="center">
              <template #default="{ row }">{{ row.mpaMean?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="读数" min-width="220">
              <template #default="{ row }">
                <span v-if="row.bin === '1-5'">最小团，分子省，人效极高</span>
                <span v-else-if="row.bin === '201+'">超级团回升：分母大，分子更大（USA / CHN）</span>
                <span v-else>中型团两头不靠</span>
              </template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="人效随规模的 U 形曲线"
              note="误差线为 95% bootstrap 区间。把曲线读成「越小越高效」是错的，正确读法是「两端高、中间低」。"
            >
              <BaseChart :option="efficiencyOption" height="360px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>参数设置</h3>
            <div class="side-field">
              <label>统计量</label>
              <el-radio-group v-model="effMetric" size="small">
                <el-radio-button v-for="item in effMetricOptions" :key="item.value" :value="item.value">
                  {{ item.label }}
                </el-radio-button>
              </el-radio-group>
            </div>
            <p>
              <b>幸存者效应：</b>参赛 ≤5 人的 679 个届次中只有 30 个有奖牌（4.42%），其余 649 个 0 奖牌届次
              不进入人效计算。人效衡量的是「成功者的产出效率」，不是「一个随机小团的期望产出」。
            </p>
            <div class="side-fact"><span>1–5 人团</span><b>0.2917</b></div>
            <div class="side-fact"><span>201+ 人团</span><b>0.0712</b></div>
            <div class="side-fact"><span>倍数</span><b>4.1×</b></div>
          </aside>
        </section>
      </section>

      <!-- ============================ 四、个案 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>四、个案：八个代表团</h2>
            <p>
              八个案例共享同一结构——前两个项目吃掉大部分奖牌。区别在于「有没有第二根支柱」：
              HKG 在 2020 年后形成双支柱，SGP 始终单点，TPE 是唯一把项目面持续扩宽的。
            </p>
          </div>
        </div>

        <PanelBlock
          title="八个代表团的构成"
          note="总奖牌为小项口径；峰值人数是该国单届参赛人数的历史最大值。GEO / ARM / MGL 的集中来自传统强项，HKG / SGP 的集中来自资源只够押少数几项。"
          flush
        >
          <el-table :data="caseCountries" size="small" max-height="360">
            <el-table-column prop="noc" label="NOC" width="68" align="center" />
            <el-table-column prop="team" label="代表团" min-width="130" show-overflow-tooltip />
            <el-table-column prop="firstOlympicYear" label="首赛" width="66" align="center" />
            <el-table-column prop="firstMedalYear" label="首牌" width="66" align="center" />
            <el-table-column prop="firstGoldYear" label="首金" width="66" align="center" />
            <el-table-column prop="appearances" label="参赛届" width="76" align="center" />
            <el-table-column prop="medalEditions" label="夺牌届" width="76" align="center" />
            <el-table-column label="夺牌率" width="84" align="center">
              <template #default="{ row }">{{ pct2(row.medalEditionRate) }}</template>
            </el-table-column>
            <el-table-column prop="totalMedal" label="总奖牌" width="76" align="center" />
            <el-table-column prop="totalGold" label="金牌" width="66" align="center" />
            <el-table-column prop="maxAthletes" label="峰值人数" width="82" align="center" />
            <el-table-column prop="topSports" label="Top 项目（奖牌数）" min-width="280" show-overflow-tooltip />
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="八国靠什么项目夺牌"
              note="取八国合计奖牌最多的 6 个运动大类，其余并入「其他」。条形越长、颜色越单一，项目面越窄。"
            >
              <BaseChart :option="caseStackOption" height="360px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>集中度实例</h3>
            <p>
              格鲁吉亚摔跤 + 柔道合计 37 / 47 = <b>78.7%</b>；格林纳达 100% 来自田径；
              科索沃 100% 来自柔道。
            </p>
            <p>
              HKG 的 Top 项目为游泳 4、击剑 3、单车 2、乒乓 2；SGP 为乒乓 3、帆船 1、游泳 1、举重 1；
              TPE 为举重 11、跆拳道 9、射箭 4、拳击 4。
            </p>
            <p class="side-hint">
              TPE 峰值 123 人，已越过小团阈值（≤50），它证明的是「规模升到 100 人量级、项目面扩到 15 个左右时，
              可以同时保持高夺牌率与高分散度」，不能当作「小团应该全面铺开」的论据。
            </p>
          </aside>
        </section>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="HKG / SGP / TPE 逐届轨迹"
              note="柱为小项奖牌（金 / 银 / 铜堆叠），折线为参赛人数。看「奖牌」与「人数」是否同步，比单看奖牌更有信息量。"
            >
              <BaseChart :option="caseTrajectoryOption" height="340px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>参数设置</h3>
            <div class="side-field">
              <label>案例</label>
              <el-radio-group v-model="caseNOC" size="small">
                <el-radio-button v-for="country in caseNOCountries" :key="country.noc" :value="country.noc">
                  {{ country.noc }}
                </el-radio-button>
              </el-radio-group>
            </div>
            <template v-if="caseSummary">
              <div class="side-fact"><span>参赛 / 夺牌届</span><b>{{ caseSummary.appearances }} / {{ caseSummary.medalEditions }}</b></div>
              <div class="side-fact"><span>总奖牌 / 金牌</span><b>{{ caseSummary.totalMedal }} / {{ caseSummary.totalGold }}</b></div>
              <div class="side-fact"><span>峰值人数</span><b>{{ caseSummary.maxAthletes }}</b></div>
              <div class="side-fact"><span>夺牌大类</span><b>{{ caseSummary.nMedalSports }}</b></div>
            </template>
            <p class="side-hint">
              HKG 1996–2012 每届只拿 1 枚且项目每届都在换；2020 年才第一次多项目开花，2024 年击剑与游泳形成双支柱。
              SGP 首牌（1960）到第二次夺牌（2008）间隔 48 年，是持续性最极端的一例。
            </p>
          </aside>
        </section>
      </section>

      <!-- ============================ 五、持续性 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>五、持续性：突破之后</h2>
            <p>
              小团的突破绝大多数是一次性的。小团型国家首牌后夺牌率中位 <b>0.1548</b>，大团型 <b>0.9259</b>；
              19.11% 的曾夺牌国只在一届拿过牌。超过一半的小团型国家，历史上从未连续两届拿牌。
            </p>
          </div>
        </div>

        <PanelBlock
          title="小团型 vs 大团型：持续性分组"
          note="小团型 = 历史峰值参赛 ≤50（国家属性）；大团型 = 峰值 >50。首牌后夺牌率的比较样本量为 56 / 91。"
          flush
        >
          <el-table :data="store.persistenceByType" size="small">
            <el-table-column prop="teamType" label="国家类型" min-width="150" />
            <el-table-column prop="nNoc" label="NOC 数" width="86" align="center" />
            <el-table-column label="首牌后夺牌率中位" width="150" align="center">
              <template #default="{ row }"><b>{{ pct2(row.postRateMedian) }}</b></template>
            </el-table-column>
            <el-table-column label="均值" width="90" align="center">
              <template #default="{ row }">{{ pct2(row.postRateMean) }}</template>
            </el-table-column>
            <el-table-column label="最长连续届数中位" width="150" align="center">
              <template #default="{ row }">{{ row.maxStreakMedian }}</template>
            </el-table-column>
            <el-table-column label="夺牌届数中位" width="130" align="center">
              <template #default="{ row }">{{ row.medalEditionsMedian }}</template>
            </el-table-column>
            <el-table-column label="历史总奖牌中位" width="140" align="center">
              <template #default="{ row }">{{ row.totalMedalMedian }}</template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="峰值参赛人数 × 首牌后夺牌率"
              note="每个点是一个曾夺牌 NOC；点大小表示历史总奖牌。带标签的是报告点名或对照案例。"
            >
              <BaseChart :option="persistenceOption" height="380px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>读数说明</h3>
            <p>
              <b>总体中位 0.7241 极具误导性</b>：大团把中位数拉高了。分组后小团型只有 0.1548。
            </p>
            <div class="side-fact"><span>曾夺牌 NOC</span><b>{{ persistenceOverview.n_noc_ever_medal }}</b></div>
            <div class="side-fact"><span>首牌后未再夺牌</span><b>{{ pct2(persistenceOverview.share_never_medal_again) }}（{{ persistenceOverview.n_never_medal_again }} 个）</b></div>
            <div class="side-fact"><span>首牌到第二牌中位间隔</span><b>{{ persistenceOverview.median_gap_first_to_second }} 年</b></div>
            <p class="side-hint">
              持续性不是规模决定的，而是项目深度决定的：GEO 8 届全部夺牌、KOS 3 届全部夺牌、ARM 8 届 7 夺牌，
              共同点是「单一项目 + 长期传统」。
            </p>
          </aside>
        </section>

        <PanelBlock
          title="一次性突破国"
          :note="`只在一届拿过小项口径奖牌的 NOC，共 ${store.oneHitWonder.length} 个（已剔除 EUN / ROC 政体更替样本）。`"
          flush
        >
          <el-table :data="store.oneHitWonder" size="small" max-height="300">
            <el-table-column prop="noc" label="NOC" width="72" align="center" />
            <el-table-column prop="team" label="代表团" min-width="150" show-overflow-tooltip />
            <el-table-column prop="firstMedalYear" label="首牌届" width="86" align="center" />
            <el-table-column prop="appearances" label="参赛届数" width="96" align="center" />
            <el-table-column prop="maxAthletes" label="峰值人数" width="96" align="center" />
            <el-table-column prop="totalMedal" label="总奖牌" width="86" align="center" />
            <el-table-column prop="teamType" label="国家类型" min-width="140" />
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="小团型国家的历史奖牌榜前 15"
              note="小团型 = 该国历史峰值参赛人数 ≤50；小项口径。金色为金牌部分。"
            >
              <BaseChart :option="boardOption" height="420px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>另一个极端</h3>
            <p>
              63 个小团型国家的奖牌合计只占总量 <b>1.97%</b>。但 ETH 以 48 人峰值拿下 61 枚（金 24），
              是小团型国家里的绝对第一，远超 GEO（47 枚）、ARM（24 枚）。
            </p>
            <p class="side-hint">
              埃塞俄比亚的长跑属于「项目深度极高」的另一类模式，与本节讨论的「资源只够押一项」不同，值得单独立题。
            </p>
          </aside>
        </section>
      </section>

      <!-- ============================ 六、结构变化 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>六、结构变化：小团份额真的在上升吗</h2>
            <p>
              小团拿到的奖牌份额从 1980 年 <b>2.54%</b> 升到 2024 年 <b>10.72%</b>。但小团占参赛国比例几乎没变
              （OLS p = 0.141，不显著）——上升的是产出，不是小团数量。
            </p>
          </div>
        </div>

        <PanelBlock
          title="小团份额逐届明细"
          note="1980 年起共 12 届。小团占参赛国比例从 60.0% 到 72.8%，看似也在涨，但 1984 年就已是 71.4%，此后 40 年小幅波动。"
          flush
        >
          <el-table :data="store.structure.series ?? []" size="small" max-height="340">
            <el-table-column prop="year" label="年份" width="76" align="center" />
            <el-table-column prop="nocCount" label="参赛国" width="80" align="center" />
            <el-table-column prop="smallCount" label="小团数" width="80" align="center" />
            <el-table-column label="小团占参赛国" width="120" align="center">
              <template #default="{ row }">{{ pct2(row.smallShareOfNoc) }}</template>
            </el-table-column>
            <el-table-column prop="smallMedal" label="小团奖牌" width="90" align="center" />
            <el-table-column label="小团奖牌份额" width="120" align="center">
              <template #default="{ row }"><b>{{ pct2(row.smallMedalShare) }}</b></template>
            </el-table-column>
            <el-table-column label="小团夺牌国份额" width="130" align="center">
              <template #default="{ row }">{{ pct2(row.smallMedalNocShare) }}</template>
            </el-table-column>
            <el-table-column label="读数" min-width="200">
              <template #default="{ row }">
                <span v-if="row.year === 2024">单届峰值 10.72%，比 2020 跳升 3.68 pp</span>
                <span v-else-if="row.year === 1980">起点 2.54%</span>
                <span v-else>前 15 年在 6–8% 区间震荡</span>
              </template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="小团奖牌份额 vs 小团占参赛国比例"
              note="柱为小团奖牌份额（左轴），实线为小团占参赛国比例（右轴），虚线为小团夺牌国份额（右轴）。"
            >
              <BaseChart :option="structureOption" height="360px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>三条趋势线</h3>
            <div class="side-fact"><span>奖牌份额 OLS</span><b>+{{ structureOls.small_medal_share?.slope ? (structureOls.small_medal_share.slope * 100).toFixed(3) : '—' }} pp/年</b></div>
            <div class="side-fact"><span>奖牌份额 R²</span><b>{{ structureOls.small_medal_share?.r2?.toFixed(3) ?? '—' }}</b></div>
            <div class="side-fact"><span>奖牌份额 p</span><b>{{ fmtP(structureOls.small_medal_share?.p) }}</b></div>
            <div class="side-fact"><span>小团占参赛国 p</span><b>{{ fmtP(structureOls.small_share_of_noc?.p) }}（不显著）</b></div>
            <p class="side-hint">
              若只看奖牌份额上升、不看占比不变，就会把结构变化误判为构成变化。
              2024 年的 10.72% 是单届峰值，前 15 年在 6–8% 震荡，趋势外推只有 1 个观测支撑。
            </p>
          </aside>
        </section>
      </section>

      <!-- ============================ 七、稳健性 ============================ -->
      <section class="flow-section">
        <div class="section-head">
          <div>
            <h2>七、这些结论有多稳</h2>
            <p>
              集中度结论极稳（5 个阈值方向全部一致），人效结论不稳（阈值 ≤150 时翻转，换行口径后四次比较全部翻转）。
              任何「小团人效更高」的说法都必须绑定小项口径。
            </p>
          </div>
        </div>

        <PanelBlock
          title="阈值敏感性：小团定义从 ≤10 换到 ≤150"
          note="人效在 ≤150 时方向翻转；最大单项份额与夺牌大类数在 5 个阈值下方向完全一致（p ≈ 0）。"
          flush
        >
          <el-table :data="thresholdRows" size="small">
            <el-table-column label="阈值" width="80" align="center">
              <template #default="{ row }">≤{{ row.threshold }}</template>
            </el-table-column>
            <el-table-column label="小团人效中位" width="120" align="center">
              <template #default="{ row }">{{ row.smallMpaMedian?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="大团人效中位" width="120" align="center">
              <template #default="{ row }">{{ row.bigMpaMedian?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="p 值" width="100" align="center">
              <template #default="{ row }">{{ fmtP(row.mpaP) }}</template>
            </el-table-column>
            <el-table-column label="效应量 r" width="96" align="center">
              <template #default="{ row }">{{ row.mpaEffectR?.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column label="小团 top1" width="96" align="center">
              <template #default="{ row }">{{ row.smallTop1Median?.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column label="大团 top1" width="96" align="center">
              <template #default="{ row }">{{ row.bigTop1Median?.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column label="大类数（小 / 大）" width="130" align="center">
              <template #default="{ row }">{{ row.smallNSportsMedian }} / {{ row.bigNSportsMedian }}</template>
            </el-table-column>
            <el-table-column label="方向" min-width="130" align="center">
              <template #default="{ row }">
                <span :class="row.smallMpaMedian > row.bigMpaMedian ? 'tag is-blue' : 'tag is-red'">
                  {{ row.smallMpaMedian > row.bigMpaMedian ? '小团更高' : '大团更高（翻转）' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="换一个阈值，人效结论就翻转"
              note="横轴为小团定义阈值；两条线交叉的位置就是结论翻转点。集中度两项指标在同图上不会交叉。"
            >
              <BaseChart :option="thresholdOption" height="340px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>阈值判定</h3>
            <div class="side-fact"><span>人效方向一致</span><b>{{ thresholdVerdict.mpa_sign_consistent ? '是' : '否（随阈值翻转）' }}</b></div>
            <div class="side-fact"><span>top1 方向一致</span><b>{{ thresholdVerdict.top1_share_sign_consistent ? '是' : '否' }}</b></div>
            <div class="side-fact"><span>大类数方向一致</span><b>{{ thresholdVerdict.n_sports_sign_consistent ? '是' : '否' }}</b></div>
            <p class="side-hint">
              翻转的机制：阈值抬到 150，141–150 人这一档从「大团」被划进「小团」，这些团多半只拿 1–3 枚奖牌
              却派了 140 人，人效极低，把「小团」整体拖下来。
            </p>
          </aside>
        </section>

        <PanelBlock
          title="口径敏感性：同一批数据换口径"
          note="小项口径问「一枚奖牌摊到多少人头上」，行口径问「一个运动员有多大概率拿牌」。前者对小团有利，后者对大团有利。"
          flush
        >
          <el-table :data="caliberRows" size="small">
            <el-table-column prop="sample" label="样本" min-width="130" />
            <el-table-column prop="caliber" label="口径" min-width="170" />
            <el-table-column label="小团人效" width="100" align="center">
              <template #default="{ row }">{{ row.smallMpaMedian?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="大团人效" width="100" align="center">
              <template #default="{ row }">{{ row.bigMpaMedian?.toFixed(4) }}</template>
            </el-table-column>
            <el-table-column label="p 值" width="100" align="center">
              <template #default="{ row }">{{ fmtP(row.p) }}</template>
            </el-table-column>
            <el-table-column label="效应量 r" width="96" align="center">
              <template #default="{ row }">{{ row.effectR?.toFixed(3) }}</template>
            </el-table-column>
            <el-table-column label="方向" width="120" align="center">
              <template #default="{ row }">
                <span :class="row.direction === '小团更高' ? 'tag is-blue' : 'tag is-red'">{{ row.direction }}</span>
              </template>
            </el-table-column>
          </el-table>
        </PanelBlock>

        <section v-if="shareTrendOption" class="chart-row">
          <div class="chart-main">
            <PanelBlock
              title="份额趋势 × 5 个阈值"
              note="5 个阈值全部上升且全部显著（p < 0.01），方向不随定义翻转。主阈值 ≤50 用更粗的线。"
            >
              <BaseChart :option="shareTrendOption" height="340px" />
            </PanelBlock>
          </div>
          <aside class="chart-side">
            <h3>为什么这条结论可以升级为「较稳」</h3>
            <p>
              阈值放宽时斜率变大，是因为把更多中团并入了「小团」，这是机械结果，不代表趋势更强；
              关键在于方向一致性。
            </p>
            <p class="side-hint">
              两个限定仍然成立：① 份额绝对值仍低（2024 年主阈值也只有 10.72%）；
              ② 2024 年是单届峰值，前 15 年在 6–8% 震荡，趋势外推只有 1 个观测支撑。
            </p>
          </aside>
        </section>

        <PanelBlock
          title="口径守恒自检"
          :note="`10 项校验全部通过（${verifiedCount} / ${store.verification.length}）。`"
          flush
        >
          <el-table :data="store.verification" size="small" max-height="280">
            <el-table-column prop="检查项" label="检查项" min-width="180" />
            <el-table-column prop="期望" label="期望" width="120" align="center" />
            <el-table-column prop="实测" label="实测" width="120" align="center" />
            <el-table-column prop="结果" label="结果" width="80" align="center" />
            <el-table-column prop="说明" label="说明" min-width="240" show-overflow-tooltip />
          </el-table>
        </PanelBlock>
      </section>
    </template>
  </div>
</template>

<style scoped>
.side-fact {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 11.5px;
  color: var(--muted);
}
.side-fact:last-of-type { border-bottom: 0; }
.side-fact b { color: var(--brand-800); font-weight: 600; font-variant-numeric: tabular-nums; }
.side-stats {
  margin-top: 12px;
  padding: 8px 10px;
  background: var(--surface-alt);
  border: 1px solid var(--line);
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.side-stats > div { display: flex; align-items: baseline; justify-content: space-between; font-size: 11.5px; color: var(--muted); }
.side-stats b { color: var(--brand-800); font-variant-numeric: tabular-nums; }
</style>
