// Journal Types
// 对应后端 services/journal/service.py

export interface JournalRecord {
    id: string
    user_id: string
    ts_code: string
    candidate: 'A' | 'B' | 'C'
    selected_premises?: string[]
    selected_risk_checks?: string[]
    constraints?: Record<string, any>
    snapshot?: Record<string, any>
    validation_date: string | null
    days_left: number | null
    status: 'active' | 'due' | 'reviewed' | 'archived'
    created_at: string
    review?: JournalReview
}

export interface JournalReview {
    reviewed_at: string
    outcome: 'supported' | 'falsified' | 'uncertain'
    triggers: ReviewTrigger[]
    notes?: string
}

export interface ReviewTrigger {
    check_id: string
    result: 'triggered' | 'passed' | 'skip'
    detail: string
}

export interface CreateRecordRequest {
    ts_code: string
    selected_candidate: 'A' | 'B' | 'C'
    selected_premises: string[]
    selected_risk_checks: string[]
    constraints: Record<string, any>
    validation_period_days: number
}

export interface ReviewRequest {
    notes?: string
}
