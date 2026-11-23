// 图表通用配置：蓝白扁平风，无阴影、无圆角
export const COLORS = {
  blue: '#2563EB',
  blueLight: '#60A5FA',
  bluePale: '#BFDBFE',
  deep: '#1E3A8A',
  gold: '#C9A227',
  silver: '#94A3B8',
  bronze: '#B87333',
  ink: '#0F172A',
  muted: '#64748B',
  line: '#DCE5F0',
  grid: '#EDF2F8',
  host: '#DC2626',
  green: '#0E9F6E',
  bg: '#F5F8FC'
}

// 多国曲线需要足够区分度：深蓝 → 亮蓝 → 青 → 靛 → 金
export const SERIES_BLUE = ['#1E3A8A', '#2563EB', '#0EA5E9', '#0E7490', '#6366F1', '#C9A227', '#64748B', '#7C3AED']

export const axisCommon = {
  axisLine: { lineStyle: { color: COLORS.line } },
  axisTick: { show: false },
  axisLabel: { color: COLORS.muted, fontSize: 11 },
  splitLine: { lineStyle: { color: COLORS.grid, type: 'dashed' } }
}

export function tooltipBase(extra = {}) {
  return {
    backgroundColor: '#FFFFFF',
    borderColor: COLORS.line,
    borderWidth: 1,
    padding: [8, 12],
    textStyle: { color: COLORS.ink, fontSize: 12 },
    extraCssText: 'box-shadow:0 6px 20px rgba(30,58,138,.10);border-radius:0;',
    ...extra
  }
}

export function gridBase(extra = {}) {
  return { left: 48, right: 20, top: 36, bottom: 32, containLabel: true, ...extra }
}

/** 当前选中届次的竖直参考线，用于跨图联动 */
export function markLineYear(year, text = '当前届') {
  if (!year) return {}
  return {
    symbol: 'none',
    silent: true,
    lineStyle: { color: COLORS.host, width: 1, type: 'dashed' },
    label: { formatter: `${text} ${year}`, color: COLORS.host, fontSize: 10, position: 'insideEndTop' },
    data: [{ xAxis: year }]
  }
}

/** 当前选中届次的竖直高亮带 */
export function markAreaYear(year, color = 'rgba(37,99,235,.06)') {
  if (!year) return {}
  return {
    silent: true,
    itemStyle: { color },
    data: [[{ xAxis: year - 1 }, { xAxis: year + 1 }]]
  }
}

export function pct(value, digits = 1) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return `${(Number(value) * 100).toFixed(digits)}%`
}

export function number(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—'
  return Number(value).toLocaleString('zh-CN')
}
