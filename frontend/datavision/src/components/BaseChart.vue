<script setup>
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  option: { type: Object, required: true },
  height: { type: String, default: '320px' },
  chartId: { type: String, default: '' },
  // false 时保留旧配置做增量合并，排行榜等需要过渡动画的图用它
  notMerge: { type: Boolean, default: true }
})
const emit = defineEmits(['chart-click'])

const root = ref(null)
let chart = null
let observer = null
let resizeFrame = 0

function render() {
  if (!chart) return
  chart.setOption(props.option, { notMerge: props.notMerge, lazyUpdate: true })
}

onMounted(() => {
  chart = echarts.init(root.value)
  chart.on('click', (params) => emit('chart-click', params))
  render()
  // 侧栏折叠 / 窗口缩放时同步尺寸；放进 rAF 避免 ResizeObserver 循环告警
  observer = new ResizeObserver(() => {
    cancelAnimationFrame(resizeFrame)
    resizeFrame = requestAnimationFrame(() => chart && chart.resize())
  })
  observer.observe(root.value)
})

watch(() => props.option, render, { deep: true })

onBeforeUnmount(() => {
  cancelAnimationFrame(resizeFrame)
  observer?.disconnect()
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="root" class="chart-box" :data-chart="chartId || null" :style="{ height }"></div>
</template>
