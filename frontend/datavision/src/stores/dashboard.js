import { computed, ref } from 'vue'
import { defineStore } from 'pinia'
import { fetchDashboard } from '../api'

/**
 * 全局看板状态
 * - 数据只拉取一次，所有筛选与联动在客户端完成
 * - caliber：event=小项口径 / athlete=运动员行口径
 * - selectedYear / selectedNOCs / selectedSport 是跨图表联动的共享选择
 */
export const useDashboardStore = defineStore('dashboard', () => {
  const data = ref(null)
  const loading = ref(false)
  const error = ref('')

  const caliber = ref('event')
  const range = ref([1896, 2024])
  const selectedNOCs = ref([])
  const selectedYear = ref(null)
  const selectedSport = ref(null)

  async function load(force = false) {
    if (data.value && !force) return
    loading.value = true
    error.value = ''
    try {
      data.value = await fetchDashboard()
      const meta = data.value.meta
      range.value = [meta.yearStart, meta.yearEnd]
    } catch (err) {
      error.value = err.message
    } finally {
      loading.value = false
    }
  }

  const meta = computed(() => data.value?.meta ?? {})
  const years = computed(() => data.value?.years ?? [])
  const countryYear = computed(() => data.value?.countryYear ?? [])
  const teams = computed(() => data.value?.teams ?? [])
  const sports = computed(() => data.value?.sports ?? [])
  const sportYear = computed(() => data.value?.sportYear ?? [])
  const hostRows = computed(() => data.value?.host ?? [])
  const womenSupply = computed(() => data.value?.womenSupply ?? [])
  const eventCount = computed(() => data.value?.eventCount ?? [])
  const highlights = computed(() => data.value?.highlights ?? {})

  const yearOptions = computed(() => years.value.map((item) => item.year))
  const minYear = computed(() => yearOptions.value[0] ?? 1896)
  const maxYear = computed(() => yearOptions.value[yearOptions.value.length - 1] ?? 2024)

  const inRange = (year) => year >= range.value[0] && year <= range.value[1]
  const filteredYears = computed(() => years.value.filter((item) => inRange(item.year)))

  const isEvent = computed(() => caliber.value === 'event')
  const medalKey = computed(() => (isEvent.value ? 'totalEvent' : 'totalAthlete'))
  const goldKey = computed(() => (isEvent.value ? 'goldEvent' : 'goldAthlete'))
  const silverKey = computed(() => (isEvent.value ? 'silverEvent' : 'silverAthlete'))
  const bronzeKey = computed(() => (isEvent.value ? 'bronzeEvent' : 'bronzeAthlete'))

  const filteredCountries = computed(() => countryYear.value.filter((row) => inRange(row.year)))

  /** 区间命中判断：优先用逐年数组，缺失时退化为首末届区间 */
  const inYears = (row) =>
    Array.isArray(row.years) && row.years.length
      ? row.years.some(inRange)
      : row.last >= range.value[0] && row.first <= range.value[1]

  const filteredTeams = computed(() => teams.value.filter(inYears))
  const filteredSports = computed(() => sports.value.filter(inYears))

  const latestYear = computed(() => filteredYears.value[filteredYears.value.length - 1] ?? null)

  const kpi = computed(() => {
    const rows = filteredYears.value
    const medals = rows.reduce((sum, row) => sum + row[medalKey.value], 0)
    const gold = rows.reduce((sum, row) => sum + row[goldKey.value], 0)
    const silver = rows.reduce((sum, row) => sum + row[silverKey.value], 0)
    const bronze = rows.reduce((sum, row) => sum + row[bronzeKey.value], 0)
    const records = rows.reduce((sum, row) => sum + row.records, 0)
    const female = rows.reduce((sum, row) => sum + row.female, 0)
    const nocSet = new Set(filteredCountries.value.map((row) => row.noc))
    return {
      medals,
      gold,
      silver,
      bronze,
      records,
      femaleRatio: records ? female / records : 0,
      editions: rows.length,
      teams: filteredTeams.value.length,
      sports: filteredSports.value.length,
      nocs: nocSet.size,
      year: latestYear.value?.year ?? null
    }
  })

  /** 每个国家在区间内拥有的不同团队（Team 字段去重）数量，供气泡图使用 */
  const teamByCountry = computed(() => {
    const map = new Map()
    for (const item of filteredTeams.value) {
      const bucket = map.get(item.noc) ?? {
        noc: item.noc,
        teams: 0,
        records: 0,
        first: item.first,
        last: item.last
      }
      bucket.teams += 1
      bucket.records += item.records
      bucket.first = Math.min(bucket.first, item.first)
      bucket.last = Math.max(bucket.last, item.last)
      map.set(item.noc, bucket)
    }
    return [...map.values()].sort((a, b) => b.teams - a.teams || b.records - a.records)
  })

  /** 团队名录：区间内按参赛记录排序 */
  const teamCatalog = computed(() =>
    [...filteredTeams.value].sort((a, b) => b.records - a.records || a.team.localeCompare(b.team))
  )

  /** 运动名录：区间内按参赛记录排序 */
  const sportCatalog = computed(() =>
    [...filteredSports.value].sort((a, b) => b.records - a.records || a.sport.localeCompare(b.sport))
  )

  const selectedNOC = computed(() => selectedNOCs.value[0] ?? null)

  /** 区间内国家累计，按当前口径排序 */
  const history = computed(() => {
    const map = new Map()
    for (const row of filteredCountries.value) {
      let item = map.get(row.noc)
      if (!item) {
        item = {
          noc: row.noc,
          team: row.team,
          goldEvent: 0, silverEvent: 0, bronzeEvent: 0, totalEvent: 0,
          goldAthlete: 0, silverAthlete: 0, bronzeAthlete: 0, totalAthlete: 0,
          records: 0, female: 0, hostCount: 0
        }
        map.set(row.noc, item)
      }
      item.goldEvent += row.goldEvent
      item.silverEvent += row.silverEvent
      item.bronzeEvent += row.bronzeEvent
      item.totalEvent += row.totalEvent
      item.goldAthlete += row.goldAthlete
      item.silverAthlete += row.silverAthlete
      item.bronzeAthlete += row.bronzeAthlete
      item.totalAthlete += row.totalAthlete
      item.records += row.records
      item.female += row.female
      item.hostCount += row.isHost ? 1 : 0
    }

    return [...map.values()]
      .map((item) => ({
        ...item,
        gold: item[goldKey.value],
        silver: item[silverKey.value],
        bronze: item[bronzeKey.value],
        total: item[medalKey.value],
        amplification: item.totalEvent ? +(item.totalAthlete / item.totalEvent).toFixed(2) : 0
      }))
      .filter((item) => item.total > 0 || item.totalAthlete > 0)
      .sort((a, b) => b.gold - a.gold || b.total - a.total || b.totalAthlete - a.totalAthlete)
      .map((item, index) => ({ ...item, rank: index + 1 }))
  })

  const historyByNoc = computed(() => new Map(history.value.map((item) => [item.noc, item])))

  /** 国家目录：用于下拉、图表默认值与排名 */
  const countryDirectory = computed(() => {
    const map = new Map()
    for (const row of countryYear.value) {
      let item = map.get(row.noc)
      if (!item) {
        item = {
          noc: row.noc,
          team: row.team,
          totalEvent: 0,
          totalAthlete: 0,
          goldEvent: 0,
          firstYear: row.year,
          lastYear: row.year
        }
        map.set(row.noc, item)
      }
      item.totalEvent += row.totalEvent
      item.totalAthlete += row.totalAthlete
      item.goldEvent += row.goldEvent
      item.firstYear = Math.min(item.firstYear, row.year)
      item.lastYear = Math.max(item.lastYear, row.year)
    }
    return [...map.values()]
      .filter((item) => item.totalEvent > 0)
      .sort((a, b) => b.totalEvent - a.totalEvent)
  })

  const topCountries = computed(() => countryDirectory.value.slice(0, 10))

  /** 左侧数据域下拉选项：按国家名排序，便于搜索 */
  const nocOptions = computed(() =>
    [...countryDirectory.value].sort((a, b) => a.team.localeCompare(b.team, 'zh-CN'))
  )

  /** 默认展示前 6 个代表团；用户选择后以选择为准 */
  const activeNOCs = computed(() => {
    if (selectedNOCs.value.length) return selectedNOCs.value
    return countryDirectory.value.slice(0, 6).map((item) => item.noc)
  })

  const nocLabel = (noc) => countryDirectory.value.find((item) => item.noc === noc)?.team || noc

  // 以 "year|noc" 建索引，避免每次展示都全表扫描
  const countryYearMap = computed(() => {
    const map = new Map()
    for (const row of countryYear.value) map.set(`${row.year}|${row.noc}`, row)
    return map
  })

  /** 指定国家在区间内的逐年序列 */
  const countrySeries = (noc) =>
    filteredYears.value.map((year) => {
      const row = countryYearMap.value.get(`${year.year}|${noc}`)
      return {
        year: year.year,
        gold: row ? row[goldKey.value] : 0,
        total: row ? row[medalKey.value] : 0,
        athletes: row ? row.records : 0,
        isHost: row?.isHost ?? 0
      }
    })

  const selectedYearRow = computed(() =>
    selectedYear.value ? filteredYears.value.find((item) => item.year === selectedYear.value) ?? null : null
  )

  function setCaliber(value) {
    caliber.value = value
  }

  function setRange(value) {
    if (!Array.isArray(value) || value.length !== 2) return
    range.value = [Math.min(value[0], value[1]), Math.max(value[0], value[1])]
    if (selectedYear.value && !inRange(selectedYear.value)) selectedYear.value = null
  }

  function toggleNOC(noc) {
    if (!noc) return
    const index = selectedNOCs.value.indexOf(noc)
    if (index >= 0) selectedNOCs.value.splice(index, 1)
    else selectedNOCs.value.push(noc)
  }

  function setNOC(noc) {
    selectedNOCs.value = noc ? [noc] : []
  }

  function setNOCs(list) {
    selectedNOCs.value = Array.isArray(list) ? [...list] : []
  }

  function setYear(year) {
    selectedYear.value = selectedYear.value === year ? null : year
  }

  function setSport(sport) {
    selectedSport.value = selectedSport.value === sport ? null : sport
  }

  function clearSelection() {
    selectedNOCs.value = []
    selectedYear.value = null
    selectedSport.value = null
  }

  function resetFilters() {
    caliber.value = 'event'
    range.value = [minYear.value, maxYear.value]
    clearSelection()
  }

  return {
    data, loading, error, meta, years, countryYear, teams, sports, sportYear, hostRows, womenSupply, eventCount, highlights,
    caliber, range, selectedNOCs, selectedYear, selectedSport,
    yearOptions, minYear, maxYear, filteredYears, latestYear, kpi,
    filteredCountries, filteredTeams, filteredSports, teamByCountry, teamCatalog, sportCatalog,
    medalKey, goldKey, silverKey, bronzeKey, isEvent,
    history, historyByNoc, countryDirectory, topCountries, activeNOCs, nocLabel, nocOptions, selectedNOC,
    countrySeries, selectedYearRow,
    load, setCaliber, setRange, toggleNOC, setNOC, setNOCs, setYear, setSport, clearSelection, resetFilters
  }
})
