/**
 * Lazy-load ECharts modules on first chart render (keeps vendor-echarts out of initial route chunk).
 */
import type { EChartsType } from 'echarts/core'

export type StockChartOption = Record<string, unknown>

let initPromise: Promise<{
  initECharts: (el: HTMLElement) => EChartsType
}> | null = null

async function loadEchartsRuntime() {
  const [
    { BarChart, CandlestickChart, LineChart },
    { GridComponent, TooltipComponent },
    { CanvasRenderer },
    { init, use },
  ] = await Promise.all([
    import('echarts/charts'),
    import('echarts/components'),
    import('echarts/renderers'),
    import('echarts/core'),
  ])

  use([
    CandlestickChart,
    LineChart,
    BarChart,
    GridComponent,
    TooltipComponent,
    CanvasRenderer,
  ])

  return {
    initECharts: (el: HTMLElement) => init(el),
  }
}

export async function createStockChart(el: HTMLElement, option: StockChartOption) {
  if (!initPromise) {
    initPromise = loadEchartsRuntime()
  }
  const { initECharts } = await initPromise
  const chart = initECharts(el)
  chart.setOption(option)
  return chart
}
