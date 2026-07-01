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
    evaluation_preview?: JournalSystemEvaluation
    review?: JournalReview
}

export interface JournalReview {
    reviewed_at: string
    outcome: 'supported' | 'falsified' | 'uncertain'
    triggers: ReviewTrigger[]
    system_evaluation?: JournalSystemEvaluation
    notes?: string
    lesson?: string
    failure_reason?: JournalFailureReason
}

export type JournalFailureReason =
    | 'direction_wrong'
    | 'timing_wrong'
    | 'volume_unconfirmed'
    | 'reverse_path'
    | 'logic_broken'
    | 'other'

export interface JournalSystemEvaluation {
    outcome?: 'supported' | 'falsified' | 'uncertain'
    actual_path?: string | null
    summary?: string
    selected_condition?: Record<string, any>
    candidate_results?: Record<string, any>
}

export interface JournalListResponse {
    records: JournalRecord[]
    page: number
    is_temporary: boolean
    trial_message: string | null
}

export interface JournalStockTimeline {
    ts_code: string
    stock_name: string | null
    total_count: number
    reviewed_count: number
    due_count: number
    active_count: number
    support_rate: number | null
    records: JournalRecord[]
}

export interface JournalReviewStats {
    limit: number
    sample_size: number
    reviewed_count: number
    pending_count: number
    outcome_counts: {
        supported: number
        falsified: number
        uncertain: number
    }
    support_rate: number | null
    selected_candidate_counts: Record<string, number>
    actual_path_counts: Record<string, number>
    most_common_actual_path: string | null
    failure_reason_counts: Record<string, number>
    most_common_failure_reason: string | null
    most_common_failure_reason_label: string | null
    condition_quality_leaderboard: JournalConditionQualityItem[]
}

export interface JournalConditionQualityItem {
    key: string
    label: string
    reviewed_count: number
    supported_count: number
    falsified_count: number
    uncertain_count: number
    support_rate: number | null
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
    lesson?: string
    failure_reason?: JournalFailureReason
}
