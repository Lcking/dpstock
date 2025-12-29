"""
Judgment Verifier Service
Calculates structure status (maintained/weakened/broken) based on price movement
"""
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from schemas.analysis_v1 import (
    JudgmentSnapshot,
    StructureType,
    StructureStatus,
    MA200Position,
    PriceLevel
)
from utils.logger import get_logger

logger = get_logger()


# Reasons templates - structure language only
class ReasonTemplates:
    """Reason templates using structure language (no trading signals)"""
    
    # Consolidation
    CONSOLIDATION_IN_RANGE = "价格保持在整理区间内"
    CONSOLIDATION_NEAR_BOUNDARY = "价格接近区间边界"
    CONSOLIDATION_BREACH_SINGLE = "价格单次越出区间边界"
    CONSOLIDATION_BREACH_SUSTAINED = "价格持续越出区间边界"
    
    # Uptrend
    UPTREND_ABOVE_SUPPORT = "价格保持在关键支撑上方"
    UPTREND_NEAR_SUPPORT = "价格接近关键支撑位"
    UPTREND_BREACH_SUPPORT = "价格跌破关键支撑位"
    UPTREND_MA200_MAINTAINED = "价格保持在MA200上方"
    UPTREND_MA200_NEAR = "价格接近MA200"
    UPTREND_MA200_BELOW = "价格跌破MA200"
    
    # Downtrend
    DOWNTREND_BELOW_RESISTANCE = "价格保持在关键压力下方"
    DOWNTREND_NEAR_RESISTANCE = "价格接近关键压力位"
    DOWNTREND_BREACH_RESISTANCE = "价格突破关键压力位"
    DOWNTREND_SUSTAINED_ABOVE = "价格持续站稳压力位上方"
    DOWNTREND_MA200_MAINTAINED = "价格保持在MA200下方"
    DOWNTREND_MA200_NEAR = "价格接近MA200"
    DOWNTREND_MA200_ABOVE = "价格突破MA200上方"
    
    # General
    STRUCTURE_INTACT = "结构前提保持完整"
    STRUCTURE_CHALLENGED = "结构前提受到挑战"
    STRUCTURE_INVALIDATED = "结构前提已被破坏"


class JudgmentVerifier:
    """Verify judgment structure status based on price movement"""
    
    def __init__(self):
        self.logger = get_logger()
    
    def verify(
        self,
        snapshot: JudgmentSnapshot,
        current_price: float,
        ma200_value: Optional[float] = None,
        price_history: Optional[List[float]] = None
    ) -> Dict[str, Any]:
        """
        Verify judgment structure status
        
        Args:
            snapshot: Original judgment snapshot
            current_price: Latest close price
            ma200_value: Latest MA200 value (optional)
            price_history: Recent price history for sustained breach check (optional)
            
        Returns:
            {
                "current_structure_status": "maintained|weakened|broken",
                "reasons": List[str],
                "current_price": float,
                "price_change_pct": float
            }
        """
        # Calculate price change
        snapshot_price = self._get_snapshot_price(snapshot)
        price_change_pct = ((current_price - snapshot_price) / snapshot_price * 100) if snapshot_price else 0.0
        
        # Extract support and resistance levels
        support_levels, resistance_levels = self._extract_levels(snapshot.key_levels_snapshot)
        
        # Verify based on structure type
        if snapshot.structure_type == StructureType.CONSOLIDATION:
            status, reasons = self._verify_consolidation(
                current_price, support_levels, resistance_levels, price_history
            )
        elif snapshot.structure_type == StructureType.UPTREND:
            status, reasons = self._verify_uptrend(
                current_price, support_levels, snapshot.ma200_position, ma200_value
            )
        elif snapshot.structure_type == StructureType.DOWNTREND:
            status, reasons = self._verify_downtrend(
                current_price, resistance_levels, snapshot.ma200_position, ma200_value, price_history
            )
        else:
            status = StructureStatus.MAINTAINED
            reasons = [ReasonTemplates.STRUCTURE_INTACT]
        
        return {
            "current_structure_status": status.value,
            "reasons": reasons[:3],  # Max 3 reasons
            "current_price": current_price,
            "price_change_pct": round(price_change_pct, 2)
        }
    
    def _get_snapshot_price(self, snapshot: JudgmentSnapshot) -> float:
        """Get reference price from snapshot (use middle of range)"""
        if not snapshot.key_levels_snapshot:
            return 0.0
        
        prices = [level.price for level in snapshot.key_levels_snapshot]
        return sum(prices) / len(prices)
    
    def _extract_levels(self, key_levels: List[PriceLevel]) -> Tuple[List[float], List[float]]:
        """
        Extract support and resistance levels from key_levels_snapshot
        
        Returns:
            (support_levels, resistance_levels)
        """
        support_levels = []
        resistance_levels = []
        
        for level in key_levels:
            label_lower = level.label.lower()
            if "支撑" in label_lower or "support" in label_lower:
                support_levels.append(level.price)
            elif "压力" in label_lower or "resistance" in label_lower:
                resistance_levels.append(level.price)
        
        return sorted(support_levels, reverse=True), sorted(resistance_levels)
    
    def _verify_consolidation(
        self,
        current_price: float,
        support_levels: List[float],
        resistance_levels: List[float],
        price_history: Optional[List[float]] = None
    ) -> Tuple[StructureStatus, List[str]]:
        """
        Verify consolidation structure
        
        Rules:
        - In range: maintained
        - Out of range: weakened
        - Sustained out (3+ days): broken
        """
        reasons = []
        
        # Get range boundaries
        lower_bound = support_levels[0] if support_levels else 0
        upper_bound = resistance_levels[0] if resistance_levels else float('inf')
        
        # Check if in range
        in_range = lower_bound <= current_price <= upper_bound
        
        if in_range:
            reasons.append(ReasonTemplates.CONSOLIDATION_IN_RANGE)
            reasons.append(ReasonTemplates.STRUCTURE_INTACT)
            return StructureStatus.MAINTAINED, reasons
        
        # Out of range - check if sustained
        if price_history and len(price_history) >= 3:
            # Check if last 3 days all out of range
            sustained_breach = all(
                p < lower_bound or p > upper_bound
                for p in price_history[-3:]
            )
            
            if sustained_breach:
                reasons.append(ReasonTemplates.CONSOLIDATION_BREACH_SUSTAINED)
                reasons.append(ReasonTemplates.STRUCTURE_INVALIDATED)
                return StructureStatus.BROKEN, reasons
        
        # Single breach
        reasons.append(ReasonTemplates.CONSOLIDATION_BREACH_SINGLE)
        reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
        return StructureStatus.WEAKENED, reasons
    
    def _verify_uptrend(
        self,
        current_price: float,
        support_levels: List[float],
        original_ma200_position: MA200Position,
        ma200_value: Optional[float] = None
    ) -> Tuple[StructureStatus, List[str]]:
        """
        Verify uptrend structure
        
        Rules:
        - Break key support or MA200 above→below: broken
        - MA200 above→near: weakened
        - Otherwise: maintained
        """
        reasons = []
        
        # Check MA200 first (more critical)
        if ma200_value and original_ma200_position == MA200Position.ABOVE:
            if current_price < ma200_value:
                reasons.append(ReasonTemplates.UPTREND_MA200_BELOW)
                reasons.append(ReasonTemplates.STRUCTURE_INVALIDATED)
                return StructureStatus.BROKEN, reasons
            elif current_price < ma200_value * 1.01:  # Within 1%
                reasons.append(ReasonTemplates.UPTREND_MA200_NEAR)
                reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
                return StructureStatus.WEAKENED, reasons
            else:
                reasons.append(ReasonTemplates.UPTREND_MA200_MAINTAINED)
        
        # Check key support
        if support_levels:
            key_support = support_levels[0]
            
            if current_price < key_support:
                reasons.append(ReasonTemplates.UPTREND_BREACH_SUPPORT)
                reasons.append(ReasonTemplates.STRUCTURE_INVALIDATED)
                return StructureStatus.BROKEN, reasons
            elif current_price < key_support * 1.02:  # Within 2%
                reasons.append(ReasonTemplates.UPTREND_NEAR_SUPPORT)
                reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
                return StructureStatus.WEAKENED, reasons
            else:
                reasons.append(ReasonTemplates.UPTREND_ABOVE_SUPPORT)
        
        reasons.append(ReasonTemplates.STRUCTURE_INTACT)
        return StructureStatus.MAINTAINED, reasons
    
    def _verify_downtrend(
        self,
        current_price: float,
        resistance_levels: List[float],
        original_ma200_position: MA200Position,
        ma200_value: Optional[float] = None,
        price_history: Optional[List[float]] = None
    ) -> Tuple[StructureStatus, List[str]]:
        """
        Verify downtrend structure
        
        Rules:
        - Break resistance and sustain: broken
        - MA200 below→near: weakened
        - Otherwise: maintained
        """
        reasons = []
        
        # Check key resistance
        if resistance_levels:
            key_resistance = resistance_levels[0]
            
            if current_price > key_resistance:
                # Check if sustained (3+ days)
                if price_history and len(price_history) >= 3:
                    sustained_above = all(p > key_resistance for p in price_history[-3:])
                    
                    if sustained_above:
                        reasons.append(ReasonTemplates.DOWNTREND_SUSTAINED_ABOVE)
                        reasons.append(ReasonTemplates.STRUCTURE_INVALIDATED)
                        return StructureStatus.BROKEN, reasons
                
                # Single breach
                reasons.append(ReasonTemplates.DOWNTREND_BREACH_RESISTANCE)
                reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
                return StructureStatus.WEAKENED, reasons
            elif current_price > key_resistance * 0.98:  # Within 2%
                reasons.append(ReasonTemplates.DOWNTREND_NEAR_RESISTANCE)
                reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
                return StructureStatus.WEAKENED, reasons
            else:
                reasons.append(ReasonTemplates.DOWNTREND_BELOW_RESISTANCE)
        
        # Check MA200 if available
        if ma200_value and original_ma200_position == MA200Position.BELOW:
            if current_price > ma200_value:
                reasons.append(ReasonTemplates.DOWNTREND_MA200_ABOVE)
                reasons.append(ReasonTemplates.STRUCTURE_INVALIDATED)
                return StructureStatus.BROKEN, reasons
            elif current_price > ma200_value * 0.99:  # Within 1%
                reasons.append(ReasonTemplates.DOWNTREND_MA200_NEAR)
                reasons.append(ReasonTemplates.STRUCTURE_CHALLENGED)
                return StructureStatus.WEAKENED, reasons
            else:
                reasons.append(ReasonTemplates.DOWNTREND_MA200_MAINTAINED)
        
        reasons.append(ReasonTemplates.STRUCTURE_INTACT)
        return StructureStatus.MAINTAINED, reasons
