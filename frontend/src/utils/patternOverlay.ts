/**
 * 将后端 /api/kline 返回的 pattern_overlay 转换为 ECharts markLine/markPoint 配置，
 * 让文字里的「颈线 / 双顶 / 金叉」在 K 线图上可见。
 */

export interface OverlayPoint {
  label: string
  price: number
  date: string
}

export interface OverlayLine {
  label: string
  price: number
}

export interface OverlayPattern {
  pattern_type: string
  label: string
  confidence: number
  completion_rate: number
  points: OverlayPoint[]
  lines: OverlayLine[]
}

export interface OverlayCrossover {
  date: string
  cross_type: 'golden_cross' | 'death_cross'
  fast_ma: string
  slow_ma: string
  price: number
}

export interface PatternOverlay {
  patterns: OverlayPattern[]
  crossovers: OverlayCrossover[]
  swing_points: { date: string; price: number; type: string }[]
}

const LINE_COLORS = ['#f97316', '#0ea5e9', '#a855f7', '#14b8a6']

export function buildOverlayMarks(overlay: PatternOverlay | null | undefined): {
  markLine: Record<string, unknown> | undefined
  markPoint: Record<string, unknown> | undefined
  legendText: string
} {
  if (!overlay || (!overlay.patterns?.length && !overlay.crossovers?.length)) {
    return { markLine: undefined, markPoint: undefined, legendText: '' }
  }

  const lineData: Record<string, unknown>[] = []
  const pointData: Record<string, unknown>[] = []
  const legendParts: string[] = []

  overlay.patterns?.forEach((pattern, pi) => {
    if (pattern.label) {
      legendParts.push(`${pattern.label}（置信度 ${pattern.confidence}）`)
    }
    pattern.lines?.forEach((line, li) => {
      lineData.push({
        yAxis: line.price,
        name: line.label,
        lineStyle: {
          color: LINE_COLORS[(pi + li) % LINE_COLORS.length],
          type: 'dashed',
          width: 1.5,
        },
        label: {
          formatter: `${line.label} ${line.price}`,
          position: 'insideEndTop',
          fontSize: 10,
          color: LINE_COLORS[(pi + li) % LINE_COLORS.length],
        },
      })
    })
    pattern.points?.forEach((point) => {
      pointData.push({
        coord: [point.date, point.price],
        name: point.label,
        value: point.label,
        symbol: 'circle',
        symbolSize: 7,
        itemStyle: { color: '#f97316', borderColor: '#fff', borderWidth: 1.5 },
        label: {
          formatter: point.label,
          position: 'top',
          fontSize: 10,
          color: '#9a3412',
          backgroundColor: 'rgba(255,247,237,0.9)',
          padding: [2, 4],
          borderRadius: 4,
        },
      })
    })
  })

  overlay.crossovers?.forEach((cross) => {
    const isGolden = cross.cross_type === 'golden_cross'
    pointData.push({
      coord: [cross.date, cross.price],
      name: isGolden ? '金叉' : '死叉',
      value: isGolden ? '金' : '死',
      symbol: 'pin',
      symbolSize: 26,
      itemStyle: { color: isGolden ? '#dc2626' : '#16a34a' },
      label: {
        formatter: isGolden ? '金' : '死',
        color: '#fff',
        fontSize: 10,
      },
    })
  })

  return {
    markLine: lineData.length
      ? { silent: true, symbol: 'none', data: lineData, animation: false }
      : undefined,
    markPoint: pointData.length
      ? { data: pointData, animation: false }
      : undefined,
    legendText: legendParts.join(' · '),
  }
}
