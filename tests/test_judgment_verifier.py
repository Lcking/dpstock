"""
Unit Tests for Judgment Verifier
Tests structure status calculation for consolidation, uptrend, and downtrend
"""
import unittest
from datetime import datetime
from services.judgment_verifier import JudgmentVerifier, ReasonTemplates
from schemas.analysis_v1 import (
    JudgmentSnapshot,
    StructureType,
    StructureStatus,
    MA200Position,
    Phase,
    PriceLevel
)


class TestJudgmentVerifier(unittest.TestCase):
    """Test cases for JudgmentVerifier"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.verifier = JudgmentVerifier()
    
    # ========== Consolidation Tests ==========
    
    def test_consolidation_maintained_in_range(self):
        """Test consolidation maintained when price in range"""
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=12.50, label="支撑位"),
                PriceLevel(price=13.00, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        result = self.verifier.verify(snapshot, current_price=12.75)
        
        self.assertEqual(result["current_structure_status"], "maintained")
        self.assertIn(ReasonTemplates.CONSOLIDATION_IN_RANGE, result["reasons"])
        self.assertEqual(result["current_price"], 12.75)
    
    def test_consolidation_weakened_single_breach(self):
        """Test consolidation weakened on single breach"""
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=12.50, label="支撑位"),
                PriceLevel(price=13.00, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Price above resistance (single breach)
        result = self.verifier.verify(snapshot, current_price=13.20)
        
        self.assertEqual(result["current_structure_status"], "weakened")
        self.assertIn(ReasonTemplates.CONSOLIDATION_BREACH_SINGLE, result["reasons"])
    
    def test_consolidation_broken_sustained_breach(self):
        """Test consolidation broken on sustained breach (3+ days)"""
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=12.50, label="支撑位"),
                PriceLevel(price=13.00, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # 3 days above resistance
        price_history = [13.10, 13.15, 13.20]
        result = self.verifier.verify(
            snapshot, 
            current_price=13.20, 
            price_history=price_history
        )
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn(ReasonTemplates.CONSOLIDATION_BREACH_SUSTAINED, result["reasons"])
    
    # ========== Uptrend Tests ==========
    
    def test_uptrend_maintained_above_support(self):
        """Test uptrend maintained when above support"""
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now(),
            structure_premise={"type": "uptrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=1650.0, label="关键支撑"),
                PriceLevel(price=1720.0, label="压力位")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        result = self.verifier.verify(
            snapshot, 
            current_price=1700.0,
            ma200_value=1600.0
        )
        
        self.assertEqual(result["current_structure_status"], "maintained")
        self.assertIn(ReasonTemplates.UPTREND_ABOVE_SUPPORT, result["reasons"])
        self.assertIn(ReasonTemplates.UPTREND_MA200_MAINTAINED, result["reasons"])
    
    def test_uptrend_weakened_near_support(self):
        """Test uptrend weakened when near support"""
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now(),
            structure_premise={"type": "uptrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=1650.0, label="关键支撑")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Price within 2% of support
        result = self.verifier.verify(snapshot, current_price=1655.0)
        
        self.assertEqual(result["current_structure_status"], "weakened")
        self.assertIn(ReasonTemplates.UPTREND_NEAR_SUPPORT, result["reasons"])
    
    def test_uptrend_broken_breach_support(self):
        """Test uptrend broken when breaching support"""
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now(),
            structure_premise={"type": "uptrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=1650.0, label="关键支撑")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Price below support
        result = self.verifier.verify(snapshot, current_price=1640.0)
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn(ReasonTemplates.UPTREND_BREACH_SUPPORT, result["reasons"])
    
    def test_uptrend_broken_ma200_cross(self):
        """Test uptrend broken when crossing below MA200"""
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now(),
            structure_premise={"type": "uptrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=1650.0, label="关键支撑")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Price clearly below MA200 (not just near)
        result = self.verifier.verify(
            snapshot, 
            current_price=1680.0,
            ma200_value=1720.0  # MA200 clearly above current price
        )
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn(ReasonTemplates.UPTREND_MA200_BELOW, result["reasons"])
    
    # ========== Downtrend Tests ==========
    
    def test_downtrend_maintained_below_resistance(self):
        """Test downtrend maintained when below resistance"""
        snapshot = JudgmentSnapshot(
            stock_code="000002",
            snapshot_time=datetime.now(),
            structure_premise={"type": "downtrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=10.00, label="关键压力")
            ],
            structure_type=StructureType.DOWNTREND,
            ma200_position=MA200Position.BELOW,
            phase=Phase.MIDDLE
        )
        
        result = self.verifier.verify(
            snapshot, 
            current_price=9.50,
            ma200_value=10.50
        )
        
        self.assertEqual(result["current_structure_status"], "maintained")
        self.assertIn(ReasonTemplates.DOWNTREND_BELOW_RESISTANCE, result["reasons"])
    
    def test_downtrend_weakened_near_resistance(self):
        """Test downtrend weakened when near resistance"""
        snapshot = JudgmentSnapshot(
            stock_code="000002",
            snapshot_time=datetime.now(),
            structure_premise={"type": "downtrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=10.00, label="关键压力")
            ],
            structure_type=StructureType.DOWNTREND,
            ma200_position=MA200Position.BELOW,
            phase=Phase.MIDDLE
        )
        
        # Price within 2% of resistance
        result = self.verifier.verify(snapshot, current_price=9.85)
        
        self.assertEqual(result["current_structure_status"], "weakened")
        self.assertIn(ReasonTemplates.DOWNTREND_NEAR_RESISTANCE, result["reasons"])
    
    def test_downtrend_weakened_single_breach(self):
        """Test downtrend weakened on single breach"""
        snapshot = JudgmentSnapshot(
            stock_code="000002",
            snapshot_time=datetime.now(),
            structure_premise={"type": "downtrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=10.00, label="关键压力")
            ],
            structure_type=StructureType.DOWNTREND,
            ma200_position=MA200Position.BELOW,
            phase=Phase.MIDDLE
        )
        
        # Single day above resistance
        result = self.verifier.verify(snapshot, current_price=10.20)
        
        self.assertEqual(result["current_structure_status"], "weakened")
        self.assertIn(ReasonTemplates.DOWNTREND_BREACH_RESISTANCE, result["reasons"])
    
    def test_downtrend_broken_sustained_breach(self):
        """Test downtrend broken on sustained breach (3+ days)"""
        snapshot = JudgmentSnapshot(
            stock_code="000002",
            snapshot_time=datetime.now(),
            structure_premise={"type": "downtrend"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=10.00, label="关键压力")
            ],
            structure_type=StructureType.DOWNTREND,
            ma200_position=MA200Position.BELOW,
            phase=Phase.MIDDLE
        )
        
        # 3 days above resistance
        price_history = [10.10, 10.15, 10.20]
        result = self.verifier.verify(
            snapshot, 
            current_price=10.20,
            price_history=price_history
        )
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn(ReasonTemplates.DOWNTREND_SUSTAINED_ABOVE, result["reasons"])
    
    # ========== Price Change Tests ==========
    
    def test_price_change_calculation(self):
        """Test price change percentage calculation"""
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=10.00, label="支撑位"),
                PriceLevel(price=12.00, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Snapshot price = (10 + 12) / 2 = 11
        # Current = 12.1
        # Change = (12.1 - 11) / 11 * 100 = 10%
        result = self.verifier.verify(snapshot, current_price=12.1)
        
        self.assertEqual(result["current_price"], 12.1)
        self.assertAlmostEqual(result["price_change_pct"], 10.0, places=1)
    
    def test_reasons_max_three(self):
        """Test that reasons are limited to max 3"""
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=12.50, label="支撑位"),
                PriceLevel(price=13.00, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        result = self.verifier.verify(snapshot, current_price=12.75)
        
        self.assertLessEqual(len(result["reasons"]), 3)


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
