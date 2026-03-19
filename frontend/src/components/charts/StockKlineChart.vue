<template>
  <div class="chart-wrapper">
    <div ref="chartRef" class="kline-chart" :style="{ height }"></div>
    <div v-if="chartLoading" class="chart-loading">
      <n-spin size="small" />
      <span>加载行情数据…</span>
    </div>
    <div v-if="chartError" class="chart-error">{{ chartError }}</div>
  </div>
</template>

<script setup lang="ts">
import { nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import { NSpin } from 'naive-ui'
import {
  BarChart,
  CandlestickChart,
  LineChart,
  type BarSeriesOption,
  type CandlestickSeriesOption,
  type LineSeriesOption,
} from 'echarts/charts'
import {
  GridComponent,
  TooltipComponent,
  type GridComponentOption,
  type TooltipComponentOption,
} from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { init as initECharts, use, type ComposeOption, type EChartsType } from 'echarts/core'
import { apiService } from '@/services/api'

use([CandlestickChart, LineChart, BarChart, GridComponent, TooltipComponent, CanvasRenderer])

type StockChartOption = ComposeOption<
  | GridComponentOption
  | TooltipComponentOption
  | BarSeriesOption
  | CandlestickSeriesOption
  | LineSeriesOption
>

const props = withDefaults(
  defineProps<{
    stockCode: string
    marketType: string
    height?: string
  }>(),
  {
    height: '350px',
  },
)

const chartRef = ref<HTMLElement | null>(null)
const chartInstance = ref<EChartsType | null>(null)
const chartLoading = ref(false)
const chartError = ref('')

async function initChart() {
  if (!chartRef.value || !props.stockCode) return

  chartLoading.value = true
  chartError.value = ''
  try {
    const data = await apiService.getKlineData(props.stockCode, props.marketType)
    if (data.error) throw new Error(data.error)

    if (!chartInstance.value) {
      chartInstance.value = initECharts(chartRef.value)
    }

    const option: StockChartOption = {
      animation: false,
      silent: true,
      grid: [
        { left: '8%', right: '3%', height: '50%', top: '5%' },
        { left: '8%', right: '3%', top: '60%', height: '15%' },
        { left: '8%', right: '3%', top: '78%', height: '18%' },
      ],
      xAxis: [
        { type: 'category', data: data.dates, boundaryGap: false, axisLine: { lineStyle: { color: '#ccc' } } },
        { type: 'category', gridIndex: 1, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 2, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
      ],
      yAxis: [
        { scale: true, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
        { gridIndex: 1, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
        { gridIndex: 2, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
      ],
      series: [
        {
          name: 'KLine',
          type: 'candlestick',
          data: data.values,
          itemStyle: { color: '#ef4444', color0: '#10b981', borderColor: '#ef4444', borderColor0: '#10b981' },
        },
        { name: 'MA5', type: 'line', data: data.ma5, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#f59e0b' } },
        { name: 'MA20', type: 'line', data: data.ma20, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#6366f1' } },
        { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: data.volumes, itemStyle: { color: '#718096' } },
        { name: 'RSI', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: data.rsi, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#8b5cf6' } },
      ],
    }

    chartInstance.value.setOption(option, true)
  } catch (error) {
    chartError.value = '行情图表暂不可用'
    console.error('StockKlineChart 初始化图表失败:', error)
  } finally {
    chartLoading.value = false
  }
}

function handleResize() {
  chartInstance.value?.resize()
}

onMounted(async () => {
  await nextTick()
  await initChart()
  window.addEventListener('resize', handleResize)
})

watch(
  () => [props.stockCode, props.marketType],
  async () => {
    await nextTick()
    await initChart()
  },
)

onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  if (chartInstance.value) {
    chartInstance.value.dispose()
    chartInstance.value = null
  }
})
</script>

<style scoped>
.chart-wrapper {
  position: relative;
}

.kline-chart {
  width: 100%;
}

.chart-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(2px);
  gap: 8px;
  border-radius: 12px;
  z-index: 5;
}

.chart-loading span {
  font-size: 0.75rem;
  color: #64748b;
}

.chart-error {
  position: absolute;
  left: 12px;
  bottom: 12px;
  padding: 4px 8px;
  border-radius: 8px;
  font-size: 12px;
  color: #b91c1c;
  background: rgba(254, 226, 226, 0.85);
  border: 1px solid rgba(252, 165, 165, 0.6);
}
</style>
