import type { JournalConditionQualityItem } from '@/types/journal'

export interface PublicAccuracyStats {
  window_days: number
  reviewed_count: number
  support_rate: number | null
  falsified_rate?: number | null
  condition_quality_leaderboard?: JournalConditionQualityItem[]
  disclaimer?: string
}

export function topConditionQualityItem(
  leaderboard: JournalConditionQualityItem[] | undefined,
  minReviewed = 3,
): JournalConditionQualityItem | null {
  if (!leaderboard?.length) return null
  return leaderboard.find((item) => item.reviewed_count >= minReviewed) ?? null
}

export function buildTrustSummary(stats: PublicAccuracyStats | null | undefined): string {
  if (!stats || stats.reviewed_count <= 0 || stats.support_rate == null) {
    return ''
  }

  const parts = [
    `近 ${stats.window_days} 天历史验证：已复盘 ${stats.reviewed_count} 条，系统支持率 ${stats.support_rate}%（仅供参考，不构成投资建议）`,
  ]

  const topCondition = topConditionQualityItem(stats.condition_quality_leaderboard)
  if (topCondition?.support_rate != null) {
    parts.push(`条件质量参考：${topCondition.label} 支持率 ${topCondition.support_rate}%`)
  }

  return parts.join(' · ')
}
