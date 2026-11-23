<script setup>
import { computed, ref } from 'vue'
import { useDashboardStore } from '../stores/dashboard'
import PageHeader from '../components/PageHeader.vue'
import KpiStrip from '../components/KpiStrip.vue'
import PanelBlock from '../components/PanelBlock.vue'
import BaseChart from '../components/BaseChart.vue'
import { COLORS, axisCommon, tooltipBase, gridBase, number, pct } from '../utils/chart'

const store = useDashboardStore()
const keyword = ref('')

const rawRows = computed(() => store.hostRows)

/** 派生指标：比率统一以「主办届奖牌」为分母，保证与奖牌数同量级、可比较 */
const rows = computed(() =>
  rawRows.value.map((row) => {
    const prev = row.prevMedals
    const next = row.nextMedals
    const host = row.hostMedals
    return {
      ...row,
      // 比率只描述「有增益 / 有下降」：反向变化记为 0，具体幅度看表格
      gainRatio: prev !== null && host ? Math.max(0, (host - prev) / host) : null,
      dropRatio: next !== null && host ? Math.max(0, (host - next) / host) : null,
      deltaNext: next !== null ? next - host : null
    }
  })
)

const kpis = computed(() => {
  const h = store.highlights.host ?? {}
  return [
    { label: '东道主届次', value: number(rows.value.length), hint: '1896–2024' },
    { label: '有可比数据', value: number(h['有可比数据的主办国数'] ?? 29), hint: '同时有上届与赛后' },
    { label: '主办届正增长', value: number(h['奖牌正增长的主办国数'] ?? 26), hint: '较上届奖牌增加' },
    { label: '赛后回落', value: number(h['主办后回落的国家数'] ?? 26), hint: '赛后一届下降' },
    { label: '赛后平均回落', value: '-29.2', unit: '枚', hint: '一次性脉冲，而非能力跃迁' }
  ]
})

const tableRows = computed(() => {
  const text = keyword.value.trim().toLowerCase()
  if (!text) return rows.value
  return rows.value.filter((row) => row.noc.toLowerCase().includes(text) || row.team.toLowerCase().includes(text))
})

/** 三指标趋势：增益比率（绿）、下降比率（紫）、主办届奖牌（右轴） */
const trendOption = computed(() => {
  const data = rows.value
  const selected = store.selectedYear
  const buildLine = (name, key, color, axisIndex = 0, areaOpacity = 0.16) => ({
    name,
    type: 'line',
    smooth: false,
    symbol: 'circle',
    symbolSize: 4,
    yAxisIndex: axisIndex,
    connectNulls: false,
    lineStyle: { width: 2, color },
    itemStyle: { color },
    areaStyle: { opacity: areaOpacity, color },
    emphasis: { focus: 'series' },
    // 缺失值保持 null 形成缺口；其余点携带届次与国家，点击可联动
    data: data.map((row) => (row[key] === null
      ? null
      : {
          value: row[key],
          year: row.year,
          noc: row.noc,
          symbolSize: row.year === selected ? 7 : 4
        }))
  })

  return {
    animationDuration: 600,
    grid: gridBase({ top: 44, right: 58, bottom: 40 }),
    tooltip: tooltipBase({
      trigger: 'axis',
      formatter: (params) => {
        const row = data[params[0].dataIndex]
        if (!row) return ''
        return [
          `${row.year} · ${row.team}`,
          `上届 ${row.prevMedals ?? '—'} → 主办 <b>${row.hostMedals}</b> → 赛后 ${row.nextMedals ?? '—'}`,
          `增益比率 ${row.gainRatio === null ? '—' : pct(row.gainRatio)}`,
          `下降比率 ${row.dropRatio === null ? '—' : pct(row.dropRatio)}`,
          `金牌 ${row.hostGold} · 金牌排名 第 ${row.goldRank}`
        ].join('<br/>')
      }
    }),
    legend: { top: 0, right: 0, itemWidth: 10, itemHeight: 8, textStyle: { fontSize: 11, color: COLORS.muted } },
    xAxis: {
      type: 'category',
      data: data.map((row) => row.year),
      ...axisCommon,
      axisLabel: { ...axisCommon.axisLabel, interval: 1, rotate: 45, fontSize: 9 }
    },
    yAxis: [
      {
        type: 'value',
        name: '比率',
        min: 0,
        max: 1,
        nameTextStyle: { fontSize: 10, color: COLORS.muted },
        ...axisCommon,
        axisLabel: { ...axisCommon.axisLabel, formatter: (value) => `${Math.round(value * 100)}%` }
      },
      {
        type: 'value',
        name: '奖牌数',
        min: 0,
        nameTextStyle: { fontSize: 10, color: COLORS.muted },
        ...axisCommon,
        splitLine: { show: false }
      }
    ],
    series: [
      buildLine('增益比率', 'gainRatio', '#0E9F6E', 0, 0.18),
      buildLine('下降比率', 'dropRatio', '#7C3AED', 0, 0.18),
      {
        name: '主办届奖牌',
        type: 'bar',
        yAxisIndex: 1,
        barMaxWidth: 10,
        z: 1,
        itemStyle: { color: 'rgba(201,162,39,.5)' },
        emphasis: { itemStyle: { color: COLORS.gold } },
        // 奖牌数用柱形，避免与两条比率曲线的面积叠在一起
        data: data.map((row) => ({
          value: row.hostMedals,
          year: row.year,
          noc: row.noc,
          itemStyle: { color: row.year === selected ? COLORS.host : 'rgba(201,162,39,.5)' }
        }))
      }
    ]
  }
})

function pickHost(params) {
  const item = params.data
  const year = Number(item?.year ?? params.name)
  if (Number.isFinite(year) && year > 1800) store.setYear(year)
  if (item?.noc) store.setNOC(item.noc)
}

function rowClick(row) {
  store.setYear(row.year)
  store.setNOC(row.noc)
}
</script>

<template>
  <div>
    <PageHeader
      title="东道主效应"
      subtitle="东道主效应真实存在，但它是一次性脉冲：主办届普遍较上届增长，赛后一届又普遍回落；且早期增益远大于现代，制度性红利已经衰减。"
    />

    <!-- 先给结论 -->
    <KpiStrip :items="kpis" />
    <div class="host-thesis">
      <span class="tag is-red">核心结论</span>
      <p>
        30 个主办届里，26 个较上届正增长，26 个赛后回落，平均回落 <b>−29.2 枚</b>。
        早期东道主靠项目定义权与参赛成本优势拿到 +90 至 +176 枚，现代东道主只有 +16 至 +25 枚；
        增长越充分，回落越明显——这是守恒，不是诅咒。
      </p>
    </div>

    <!-- 再展示表格 -->
    <PanelBlock
      :title="`东道主明细 · ${tableRows.length} 届`"
      note="红涨绿跌（A 股习惯）：较上届 / 较下届为负时用绿色下箭头。空值表示缺少上届或赛后数据。点击行锁定该届与主办国。"
      flush
    >
      <template #actions>
        <el-input v-model="keyword" size="small" placeholder="搜索 NOC / 国家" clearable style="width: 190px" />
      </template>
      <el-table
        :data="tableRows"
        size="small"
        max-height="430"
        :row-class-name="({ row }) => (row.year === store.selectedYear ? 'row-selected' : '')"
        @row-click="rowClick"
      >
        <el-table-column prop="year" label="届次" width="78" align="center" sortable />
        <el-table-column prop="team" label="主办国" min-width="140" show-overflow-tooltip />
        <el-table-column prop="noc" label="NOC" width="66" align="center" />
        <el-table-column prop="prevMedals" label="上届" width="76" align="center" sortable />
        <el-table-column prop="hostMedals" label="主办届" width="86" align="center" sortable />
        <el-table-column prop="nextMedals" label="下届" width="76" align="center" sortable />
        <el-table-column prop="deltaMedals" label="较上届" width="100" align="center" sortable>
          <template #default="{ row }">
            <span v-if="row.deltaMedals === null" class="muted">—</span>
            <span v-else class="delta" :class="row.deltaMedals > 0 ? 'up' : row.deltaMedals < 0 ? 'down' : 'flat'">
              {{ row.deltaMedals > 0 ? '↑' : row.deltaMedals < 0 ? '↓' : '·' }} {{ Math.abs(row.deltaMedals) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="deltaNext" label="较下届" width="100" align="center" sortable>
          <template #default="{ row }">
            <span v-if="row.deltaNext === null" class="muted">—</span>
            <span v-else class="delta" :class="row.deltaNext > 0 ? 'up' : row.deltaNext < 0 ? 'down' : 'flat'">
              {{ row.deltaNext > 0 ? '↑' : row.deltaNext < 0 ? '↓' : '·' }} {{ Math.abs(row.deltaNext) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="hostGold" label="金牌数" width="82" align="center" sortable />
        <el-table-column prop="goldRank" label="金牌排名" width="94" align="center" sortable>
          <template #default="{ row }">第 {{ row.goldRank }}</template>
        </el-table-column>
      </el-table>
    </PanelBlock>

    <!-- 最后展示趋势图 -->
    <section class="chart-row">
      <div class="chart-main">
        <PanelBlock
          title="东道主赛前增益与赛后下降趋势"
          note="两条平滑曲线：增益比率（绿）、下降比率（紫）；金色柱为主办届奖牌数（右轴）。面积与柱形都做了半透明处理，用来观察整体趋势而不是单点噪声。点击任一届可联动。"
        >
          <BaseChart :option="trendOption" height="430px" @chart-click="pickHost" />
        </PanelBlock>
      </div>
      <aside class="chart-side">
        <h3>指标定义</h3>
        <div class="side-field">
          <label>增益比率</label>
          <span class="side-hint">（主办届奖牌 − 上届奖牌）÷ 主办届奖牌，衡量主办届奖牌里有多少是新增的；低于上届时记为 0，下降幅度见表格「较上届」。</span>
        </div>
        <div class="side-field">
          <label>下降比率</label>
          <span class="side-hint">（主办届奖牌 − 下届奖牌）÷ 主办届奖牌，衡量赛后一年回吐了多少；赛后反超时记为 0，上涨幅度见表格「较下届」。</span>
        </div>
        <div class="side-field">
          <label>缺口说明</label>
          <span class="side-hint">1896 没有上届、2024 没有赛后数据，对应曲线在该点为缺口，不补零。</span>
        </div>
        <p class="side-hint">早期比率被小基数放大，所以图上同时给出奖牌绝对数（右轴）。</p>
      </aside>
    </section>
  </div>
</template>

<style scoped>
.host-thesis {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  margin: 14px 0 2px;
  padding: 12px 14px;
  background: #fff7f7;
  border-left: 3px solid var(--danger);
}
.host-thesis p { font-size: 12.5px; line-height: 1.8; color: var(--ink-2); }
.host-thesis b { color: var(--danger); }
.delta { font-variant-numeric: tabular-nums; font-weight: 600; }
.delta.up { color: #dc2626; }
.delta.down { color: #0e9f6e; }
.delta.flat { color: var(--muted); }
:deep(.row-selected) { background: var(--brand-50) !important; }
:deep(.el-table__row) { cursor: pointer; }
</style>
