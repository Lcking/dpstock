<template>
  <div class="chart-wrapper">
    <div ref="chartRef" class="kline-chart"></div>
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

type ArticleChartOption = ComposeOption<
  | GridComponentOption
  | TooltipComponentOption
  | BarSeriesOption
  | CandlestickSeriesOption
  | LineSeriesOption
>

const props = defineProps<{
  stockCode: string
  marketType: string
}>()

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
    if (!data || data.error) {
      throw new Error(data?.error || 'No data')
    }

    await nextTick()
    await new Promise((resolve) => setTimeout(resolve, 60))

    if (chartInstance.value) {
      chartInstance.value.dispose()
    }
    chartInstance.value = initECharts(chartRef.value)

    const macdData = data.macd && data.macd.macd ? data.macd.macd : (data.macd || [])
    const option: ArticleChartOption = {
      backgroundColor: 'transparent',
      animation: true,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' },
      },
      grid: [
        { left: '8%', right: '3%', height: '55%', top: '5%' },
        { left: '8%', right: '3%', top: '65%', height: '15%' },
        { left: '8%', right: '3%', top: '85%', height: '10%' },
      ],
      xAxis: [
        { type: 'category', data: data.dates, boundaryGap: false, axisLine: { lineStyle: { color: '#94a3b8' } } },
        { type: 'category', gridIndex: 1, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 2, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
      ],
      yAxis: [
        { scale: true, splitArea: { show: false }, splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }, axisLabel: { fontSize: 10 } },
        { gridIndex: 1, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
        { gridIndex: 2, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data.values,
          itemStyle: { color: '#ef4444', color0: '#10b981', borderColor: '#ef4444', borderColor0: '#10b981' },
        },
        { name: 'MA5', type: 'line', data: data.ma5, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#f59e0b' } },
        { name: 'MA20', type: 'line', data: data.ma20, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#6366f1' } },
        {
          name: '成交量',
          type: 'bar',
          xAxisIndex: 1,
          yAxisIndex: 1,
          data: data.volumes,
          itemStyle: {
            color: (params: { dataIndex: number }) =>
              data.values[params.dataIndex][1] > data.values[params.dataIndex][0] ? '#ef4444' : '#10b981',
          },
        },
        { name: 'MACD', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: macdData, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#ec4899' } },
      ],
    }

    chartInstance.value.setOption(option, true)
  } catch (error) {
    chartError.value = '图表加载失败，请稍后重试'
    console.error('ArticleKlineChart 初始化图表失败:', error)
  } finally {
    chartLoading.value = false
  }
}

function handleResize() {
  chartInstance.value?.resize()
}

onMounted(async () => {
  await initChart()
  window.addEventListener('resize', handleResize)
})

watch(
  () => [props.stockCode, props.marketType],
  async () => {
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
  height: 400px;
  min-height: 400px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.chart-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
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
