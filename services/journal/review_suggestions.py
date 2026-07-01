"""
Rule-based review prompts derived from system evaluation (no LLM call).
"""
from __future__ import annotations

from typing import Any, Dict, Optional


def build_review_suggestions(
    candidate: Optional[str],
    evaluation: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    evaluation = evaluation or {}
    outcome = evaluation.get("outcome") or "uncertain"
    actual_path = evaluation.get("actual_path")
    candidate_key = str(candidate or "").upper()
    actual_key = str(actual_path or "").upper() if actual_path else None

    suggestions: Dict[str, Any] = {
        "title": "复盘引导",
        "bullets": [],
        "suggested_failure_reason": None,
        "lesson_prompt": "用一句话总结：下次遇到类似结构，你会怎么调整？",
        "notes_prompt": "补充当时忽略的关键信息或执行偏差。",
    }

    if outcome == "supported":
        suggestions["title"] = "判断得到支持，可以沉淀有效做法"
        suggestions["bullets"] = [
            "这次哪些前提被市场验证了？",
            "如果重来一次，你会更早还是更晚行动？",
        ]
        suggestions["lesson_prompt"] = "写下这次判断中最值得复用的一个条件或节奏。"
        return suggestions

    if outcome == "falsified":
        if actual_key and candidate_key and actual_key != candidate_key:
            suggestions["suggested_failure_reason"] = "reverse_path"
            suggestions["bullets"] = [
                f"你选择候选 {candidate_key}，但市场更接近 {actual_key}。",
                "是方向判断错了，还是路径选错但逻辑仍有参考价值？",
            ]
        else:
            suggestions["suggested_failure_reason"] = "direction_wrong"
            suggestions["bullets"] = [
                "原判断前提被证伪，重点回顾是哪条条件先失效。",
                "当时是否忽视了更强的反向信号？",
            ]
        suggestions["lesson_prompt"] = "写下这次证伪给你最重要的一个提醒。"
        return suggestions

    selected = evaluation.get("selected_condition") or {}
    volume = selected.get("volume") or {}
    price = selected.get("price") or {}
    if volume and not volume.get("triggered") and price.get("triggered"):
        suggestions["suggested_failure_reason"] = "volume_unconfirmed"
        suggestions["bullets"] = [
            "价格条件接近触发，但量能未确认。",
            "是否验证窗口太短，或放量标准设得过高？",
        ]
    elif actual_key and candidate_key and actual_key != candidate_key:
        suggestions["suggested_failure_reason"] = "timing_wrong"
        suggestions["bullets"] = [
            f"结构尚未明确指向 {candidate_key}，市场仍在 {actual_key} 附近。",
            "是否入场过早，或需要更长验证期？",
        ]
    else:
        suggestions["suggested_failure_reason"] = "logic_broken"
        suggestions["bullets"] = [
            "结果不确定，更可能是条件未触发或信息不足。",
            "下次会补哪一条确认信号再下判断？",
        ]
    suggestions["lesson_prompt"] = "写下这次「不确定」教会你的验证规则。"
    return suggestions
