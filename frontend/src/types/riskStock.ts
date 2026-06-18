export interface RiskStockItem {
  id: number
  trade_date: string
  ts_code: string
  name: string
  market?: string
  tags_json?: string
  tags: string[]
  risk_level: 'high' | 'medium' | 'low'
  reason: string
  limit_up_days: number
  is_st: number
  source?: string
  created_at?: string
  updated_at?: string
}

export interface RiskStockListResponse {
  trade_date: string | null
  count: number
  items: RiskStockItem[]
}
