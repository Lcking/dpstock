/**
 * 将后端 /api/kline 返回的 pattern_overlay 转换为 ECharts markLine/markPoint 配置，
 * 让文字里的「颈线 / 双顶 / 金叉」在 K 线图上可见。
 *
 * 支持双窗口：recent（近期）+ history（全历史），默认 dataZoom 看近期，
 * 图例提示可用缩放切换查看另一套形态。
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
  scope?: 'recent' | 'history' | string
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
  note?: string
}

const RECENT_COLOR = '#f97316'
const HISTORY_COLOR = '#0ea5e9'
const LINE_COLORS_RECENT = ['#f97316', '#ea580c', '#c2410c']
const LINE_COLORS_HISTORY = ['#0ea5e9', '#0284c7', '#0369a1']

function scopeLabel(scope?: string): string {
  if (scope === 'history') return '全历史'
  return '近期'
}

function scopeColor(scope?: string): string {
  return scope === 'history' ? HISTORY_COLOR : RECENT_COLOR
}

function lineColors(scope?: string): string[] {
  return scope === 'history' ? LINE_COLORS_HISTORY : LINE_COLORS_RECENT
}

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

  const hasRecent = overlay.patterns?.some((p) => (p.scope || 'recent') === 'recent')
  const hasHistory = overlay.patterns?.some((p) => p.scope === 'history')

  overlay.patterns?.forEach((pattern, pi) => {
    const scope = pattern.scope || 'recent'
    const color = scopeColor(scope)
    const colors = lineColors(scope)
    if (pattern.label) {
      legendParts.push(`${scopeLabel(scope)}·${pattern.label}（置信度 ${pattern.confidence}）`)
    }
    pattern.lines?.forEach((line, li) => {
      const lineColor = colors[(pi + li) % colors.length]
      lineData.push({
        yAxis: line.price,
        name: `${scopeLabel(scope)} ${line.label}`,
        lineStyle: {
          color: lineColor,
          type: scope === 'history' ? 'dotted' : 'dashed',
          width: 1.5,
        },
        label: {
          formatter: `${scopeLabel(scope)} ${line.label} ${line.price}`,
          position: 'insideEndTop',
          fontSize: 10,
          color: lineColor,
        },
      })
    })
    pattern.points?.forEach((point) => {
      pointData.push({
        coord: [point.date, point.price],
        name: point.label,
        value: point.label,
        symbol: scope === 'history' ? 'diamond' : 'circle',
        symbolSize: scope === 'history' ? 8 : 7,
        itemStyle: { color, borderColor: '#fff', borderWidth: 1.5 },
        label: {
          formatter: `${scopeLabel(scope)} ${point.label}`,
          position: scope === 'history' ? 'bottom' : 'top',
          fontSize: 10,
          color: scope === 'history' ? '#075985' : '#9a3412',
          backgroundColor: scope === 'history' ? 'rgba(240,249,255,0.92)' : 'rgba(255,247,237,0.9)',
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

  let legendText = legendParts.join(' · ')
  if (overlay.note) {
    legendText = legendText ? `${legendText}。${overlay.note}` : overlay.note
  } else if (hasRecent && hasHistory) {
    legendText = `${legendText}。默认展示近期形态；另有全历史形态，可用滚轮/滑条缩小查看`
  } else if (legendText) {
    legendText = `${legendText} · 滚轮/拖动下方滑条可缩放查看`
  }

  return {
    markLine: lineData.length
      ? { silent: true, symbol: 'none', data: lineData, animation: false }
      : undefined,
    markPoint: pointData.length
      ? { data: pointData, animation: false }
      : undefined,
    legendText,
  }
}
