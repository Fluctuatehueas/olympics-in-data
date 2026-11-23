import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchS4 } from '../api'

/**
 * Task3 · S4「小代表团的大突破」专题数据
 * - 与主看板分开拉取，避免把 1.2 MB 的主数据再放大
 * - 页面内所有阈值、口径判断都由本 store 的只读数据派生
 */
export const useS4Store = defineStore('s4', () => {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')

  async function load(force = false) {
    if (data.value && !force) return
    loading.value = true
    error.value = ''
    try {
      data.value = await fetchS4()
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const meta = computed(() => data.value?.meta ?? {})
  const kpi = computed(() => data.value?.kpi ?? {})
  const sizeDistribution = computed(() => data.value?.sizeDistribution ?? [])
  const sizeClassByYear = computed(() => data.value?.sizeClassByYear ?? [])
  const smallRateByYear = computed(() => data.value?.smallRateByYear ?? [])
  const efficiency = computed(() => data.value?.efficiency ?? [])
  const strategyBySize = computed(() => data.value?.strategyBySize ?? [])
  const strategyBySizeModern = computed(() => data.value?.strategyBySizeModern ?? [])
  const scatter = computed(() => data.value?.scatter ?? [])
  const caseCountries = computed(() => data.value?.caseCountries ?? [])
  const caseSports = computed(() => data.value?.caseSports ?? [])
  const caseDetail = computed(() => data.value?.caseDetail ?? {})
  const persistence = computed(() => data.value?.persistence ?? {})
  const smallNocBoard = computed(() => data.value?.smallNocBoard ?? [])
  const structure = computed(() => data.value?.structure ?? {})
  const sensitivity = computed(() => data.value?.sensitivity ?? {})
  const analysis = computed(() => data.value?.analysis ?? {})
  const verification = computed(() => data.value?.verification ?? [])

  const modernScatter = computed(() => scatter.value.filter((row) => row.year >= (meta.value.modernFrom ?? 1980)))
  const scatterCoverage = computed(() => ({
    all: scatter.value.length,
    modern: modernScatter.value.length
  }))

  /** 八国案例按总奖牌降序，供表格和图表共用 */
  const caseCountriesSorted = computed(() =>
    [...caseCountries.value].sort((a, b) => b.totalMedal - a.totalMedal)
  )

  /** 小团型 / 大团型持续性对比，固定顺序便于表格读数 */
  const persistenceByType = computed(() => {
    const order = ['小团型(峰值≤50)', '大团型(峰值>50)']
    const map = new Map(persistence.value.byType?.map((row) => [row.teamType, row]) ?? [])
    return order.map((key) => map.get(key)).filter(Boolean)
  })

  /** 一次性突破国：默认剔除政体更替样本（EUN / ROC），与报告 6.3 一致 */
  const oneHitWonder = computed(() => {
    const rows = persistence.value.oneHit ?? []
    return rows.filter((row) => !['EUN', 'ROC'].includes(row.noc))
  })

  return {
    data, loading, error,
    meta, kpi, sizeDistribution, sizeClassByYear, smallRateByYear,
    efficiency, strategyBySize, strategyBySizeModern, scatter, modernScatter, scatterCoverage,
    caseCountries, caseCountriesSorted, caseSports, caseDetail,
    persistence, persistenceByType, oneHitWonder,
    smallNocBoard, structure, sensitivity, analysis, verification,
    load
  }
})
