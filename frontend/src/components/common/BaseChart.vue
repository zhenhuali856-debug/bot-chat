<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, shallowRef, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  options: {
    type: Object,
    required: true
  },
  height: {
    type: String,
    default: '100%'
  },
  width: {
    type: String,
    default: '100%'
  },
  loading: {
    type: Boolean,
    default: false
  }
})

const chartRef = ref(null)
const chartInstance = shallowRef(null)
let resizeObserver = null

const initChart = () => {
  if (!chartRef.value) return
  if (chartInstance.value) {
    chartInstance.value.dispose()
  }

  chartInstance.value = echarts.init(chartRef.value)
  if (props.loading) {
    chartInstance.value.showLoading({
      text: '加载中...',
      color: '#3b82f6',
      textColor: '#94a3b8',
      maskColor: 'rgba(0, 0, 0, 0.2)'
    })
  } else if (props.options) {
    chartInstance.value.setOption(props.options, true)
  }
}

const resize = () => {
  if (chartInstance.value) {
    chartInstance.value.resize()
  }
}

watch(
  () => props.options,
  (newOpt) => {
    if (chartInstance.value && newOpt) {
      chartInstance.value.setOption(newOpt, true)
    }
  },
  { deep: true }
)

watch(
  () => props.loading,
  (val) => {
    if (!chartInstance.value) return
    if (val) {
      chartInstance.value.showLoading({
        text: '加载中...',
        color: '#3b82f6',
        textColor: '#94a3b8',
        maskColor: 'rgba(0, 0, 0, 0.2)'
      })
    } else {
      chartInstance.value.hideLoading()
    }
  }
)

onMounted(() => {
  nextTick(() => {
    initChart()
    if (window.ResizeObserver && chartRef.value) {
      resizeObserver = new ResizeObserver(() => resize())
      resizeObserver.observe(chartRef.value)
    } else {
      window.addEventListener('resize', resize)
    }
  })
})

onBeforeUnmount(() => {
  if (resizeObserver) {
    resizeObserver.disconnect()
    resizeObserver = null
  } else {
    window.removeEventListener('resize', resize)
  }
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
})

defineExpose({
  getInstance: () => chartInstance.value,
  resize
})
</script>

<template>
  <div
    ref="chartRef"
    class="base-echart-container"
    :style="{ width, height }"
  ></div>
</template>

<style scoped>
.base-echart-container {
  min-height: 120px;
}
</style>

