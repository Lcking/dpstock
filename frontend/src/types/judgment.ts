/**
 * Judgment Types
 * Types for judgment tracking and verification
 */

export interface JudgmentSnapshot {
    stock_code: string;
    snapshot_time: string;
    structure_premise: {
        structure_type: string;
        ma200_position?: string;
        phase?: string;
        pattern_type?: string;
        [key: string]: any;
    };
    selected_candidates: string[];
    key_levels_snapshot: Array<{
        price: number;
        label: string;
    }>;
    structure_type: string;
    ma200_position: string;
    phase: string;
}

export interface JudgmentCheck {
    check_time: string;
    current_price: number;
    price_change_pct: number;
    current_structure_status: 'maintained' | 'weakened' | 'broken';
    status_description: string;
    reasons: string[];
    verification_time?: string;  // For compatibility with API response
}

export interface Judgment {
    judgment_id: string;
    user_id?: string;
    stock_code: string;
    stock_name?: string;
    snapshot_time: string;
    structure_type: string;
    ma200_position: string;
    phase: string;
    selected_candidates: string[];
    created_at: string;
    latest_check?: JudgmentCheck;
    structure_premise?: any;
    key_levels_snapshot?: any[];
}

export interface SaveJudgmentRequest {
    snapshot: JudgmentSnapshot;
}

export interface SaveJudgmentResponse {
    judgment_id: string;
    user_id: string;
    created_at: string;
}

export interface GetJudgmentsResponse {
    user_id: string;
    total: number;
    judgments: Judgment[];
}
