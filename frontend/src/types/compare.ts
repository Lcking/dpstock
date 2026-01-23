// Compare Types
// 对应后端 services/compare/bucketing.py

import type { WatchlistItemSummary } from './watchlist'

export interface CompareBucket {
    id: 'best' | 'conflict' | 'weak' | 'event'
    title: string
    reason: string
    items: WatchlistItemSummary[]
}

export interface CompareRequest {
    ts_codes: string[]
    asof?: string
    window?: number
    bench?: string
    use_industry?: boolean
}

export interface CompareResponse {
    meta: {
        asof: string
        window: number
        bench: string
        use_industry?: boolean
        total_count: number
    }
    buckets: CompareBucket[]
}
