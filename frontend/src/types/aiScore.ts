export type AiScoreDimensionId = 'structure' | 'relative' | 'flow' | 'risk'

export interface AiScoreContribItem {
  key: string
  value: any
  impact: number
  note: string
}

export interface AiScoreDimension {
  id: AiScoreDimensionId
  name: string
  score: number
  weight: number
  contrib: AiScoreContribItem[]
  evidence: string[]
  available: boolean
  degraded: boolean
}

export interface AiScoreOverall {
  score: number
  label: string
  confidence: number
  degraded: boolean
}

export interface AiScoreExplain {
  one_liner: string
  notes: string[]
}

export interface AiScore {
  version: string
  overall: AiScoreOverall
  dimensions: AiScoreDimension[]
  explain: AiScoreExplain
  meta?: Record<string, any> | null
}

