// Watchlist Types
// 对应后端 schemas/watchlist.py

export interface TrendResult {
    direction: 'up' | 'down' | 'sideways'
    strength: number // 0-100
    degraded: boolean
    evidence: string[]
}

export interface RelativeStrengthSummary {
    excess_20d_vs_000300: number | null
    label_20d: 'strong' | 'neutral' | 'weak' | null
    bench: string
}

export interface CapitalFlowSummary {
    label: '承接放量' | '分歧放量' | '中性' | '缩量观望' | '缩量潜伏' | '缩量阴跌' | '不可用'
    net_inflow_5d: number | null
    available: boolean
    degraded: boolean
}

export interface RiskSummary {
    level: 'low' | 'medium' | 'high'
    vol_percentile: number | null
}

export interface EventSummary {
    flag: 'none' | 'minor' | 'major' | 'unavailable'
    event_count_30d: number
    available: boolean
}

export interface JudgementSummary {
    has_active: boolean
    candidate: 'A' | 'B' | 'C' | null
    validation_period_days: number | null
    days_left: number | null
}

export interface RiskListHitItem {
    ts_code: string
    name: string
    trade_date: string
    tags: string[]
    risk_level: string
    reason: string
}

export interface WatchlistItemSummary {
    ts_code: string
    name: string
    asof: string
    price: number
    change_pct: number | null

    // 6 个必须字段
    trend: TrendResult
    relative_strength: RelativeStrengthSummary
    capital_flow: CapitalFlowSummary
    risk: RiskSummary
    events: EventSummary
    judgement: JudgementSummary
    weight_pct?: number | null
    is_skeleton?: boolean
    on_risk_list?: boolean
    risk_list_tags?: string[]
}

export interface IndustryExposureItem {
    industry: string
    count: number
    weight_pct: number
}

export interface WatchlistHealthOverview {
    total_count: number
    strong_count: number
    weak_count: number
    high_risk_count: number
    watch_count: number
    active_judgment_count: number
    health_score: number
    label: '偏强' | '均衡' | '偏弱' | '风险偏高'
    summary_line: string
    industry_count: number
    top_industries: IndustryExposureItem[]
    concentration_level: '分散' | '中等' | '偏高'
    concentration_note: string
    uses_position_weights: boolean
    risk_list_hits: RiskListHitItem[]
    risk_list_trade_date: string | null
}

export interface WatchlistSummary {
    watchlist_id: string
    asof: string
    items: WatchlistItemSummary[]
    total_count: number
    filtered_count: number
    health_overview: WatchlistHealthOverview
    is_temporary: boolean
    trial_message: string | null
}

export interface Watchlist {
    id: string
    user_id: string
    name: string
    created_at: string
    updated_at: string
    items_count: number
    is_temporary: boolean
    trial_message: string | null
}

export interface WatchlistRiskAlert {
    id: string
    user_id: string
    ts_code: string
    stock_name: string
    trade_date: string
    tags: string[]
    risk_level: string
    reason: string
    created_at: string
    read_at?: string | null
}

export interface WatchlistRiskAlertsResponse {
    unread_count: number
    items: WatchlistRiskAlert[]
}

export interface WatchlistSignalAlert {
    id: string
    user_id: string
    ts_code: string
    stock_name: string
    trade_date: string
    signal_type: string
    title: string
    detail: string
    created_at: string
    read_at?: string | null
}

export interface WatchlistSignalAlertsResponse {
    unread_count: number
    items: WatchlistSignalAlert[]
}
