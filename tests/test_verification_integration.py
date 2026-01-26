"""
Integration Tests for Verification Scheduler
Tests the end-to-end flow: create judgment -> trigger verification -> check status update
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import json
import uuid

from services.judgment_verifier import JudgmentVerifier
from services.judgment_service import JudgmentService
from schemas.analysis_v1 import (
    JudgmentSnapshot,
    StructureType,
    StructureStatus,
    MA200Position,
    Phase,
    PriceLevel
)


class TestVerificationIntegration(unittest.TestCase):
    """Integration tests for the verification pipeline"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.verifier = JudgmentVerifier()
        
    def test_verify_uptrend_maintained_flow(self):
        """
        Test full verification flow for uptrend that is maintained.
        Simulates: Judgment created -> Price stays above support -> Status = CONFIRMED
        """
        # Create snapshot (simulating what gets stored in DB)
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now() - timedelta(days=3),
            structure_premise={"type": "uptrend", "description": "上涨趋势"},
            selected_candidates=["trend_continuation"],
            key_levels_snapshot=[
                PriceLevel(price=1300.0, label="关键支撑"),
                PriceLevel(price=1400.0, label="压力位")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Simulate current price ABOVE support (structure maintained)
        current_price = 1380.0
        ma200_value = 1250.0  # Price well above MA200
        
        # Verify
        result = self.verifier.verify(
            snapshot=snapshot,
            current_price=current_price,
            ma200_value=ma200_value
        )
        
        # Assert
        self.assertEqual(result["current_structure_status"], "maintained")
        self.assertEqual(result["current_price"], 1380.0)
        self.assertIn("保持", result["reasons"][0])  # Should mention "maintained"
        
    def test_verify_uptrend_broken_flow(self):
        """
        Test full verification flow for uptrend that breaks.
        Simulates: Judgment created -> Price drops below support -> Status = BROKEN
        """
        snapshot = JudgmentSnapshot(
            stock_code="600519",
            snapshot_time=datetime.now() - timedelta(days=3),
            structure_premise={"type": "uptrend"},
            selected_candidates=["trend_continuation"],
            key_levels_snapshot=[
                PriceLevel(price=1300.0, label="关键支撑")
            ],
            structure_type=StructureType.UPTREND,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Simulate current price BELOW support (structure broken)
        current_price = 1280.0  # Below 1300 support
        
        result = self.verifier.verify(
            snapshot=snapshot,
            current_price=current_price
        )
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn("跌破", result["reasons"][0])  # Should mention "breach"
        
    def test_verify_consolidation_weakened_flow(self):
        """
        Test verification for consolidation that weakens (single breach).
        """
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now() - timedelta(days=2),
            structure_premise={"type": "consolidation"},
            selected_candidates=["range_bound"],
            key_levels_snapshot=[
                PriceLevel(price=10.0, label="支撑位"),
                PriceLevel(price=11.0, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Price slightly above resistance (single breach)
        current_price = 11.20
        
        result = self.verifier.verify(
            snapshot=snapshot,
            current_price=current_price
        )
        
        self.assertEqual(result["current_structure_status"], "weakened")
        
    def test_verify_consolidation_broken_sustained(self):
        """
        Test verification for consolidation that breaks (sustained breach).
        """
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now() - timedelta(days=5),
            structure_premise={"type": "consolidation"},
            selected_candidates=["range_bound"],
            key_levels_snapshot=[
                PriceLevel(price=10.0, label="支撑位"),
                PriceLevel(price=11.0, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Sustained breach: 3 days above resistance
        current_price = 11.50
        price_history = [11.30, 11.40, 11.50]  # All above 11.0
        
        result = self.verifier.verify(
            snapshot=snapshot,
            current_price=current_price,
            price_history=price_history
        )
        
        self.assertEqual(result["current_structure_status"], "broken")
        self.assertIn("持续", result["reasons"][0])  # "Sustained"

    def test_price_change_calculation_accuracy(self):
        """
        Test that price change percentage is calculated correctly.
        """
        snapshot = JudgmentSnapshot(
            stock_code="000001",
            snapshot_time=datetime.now(),
            structure_premise={"type": "consolidation"},
            selected_candidates=["A"],
            key_levels_snapshot=[
                PriceLevel(price=100.0, label="支撑位"),
                PriceLevel(price=110.0, label="压力位")
            ],
            structure_type=StructureType.CONSOLIDATION,
            ma200_position=MA200Position.ABOVE,
            phase=Phase.MIDDLE
        )
        
        # Snapshot price = avg(100, 110) = 105
        # Current = 115
        # Change = (115 - 105) / 105 * 100 = 9.52%
        result = self.verifier.verify(snapshot, current_price=115.0)
        
        self.assertAlmostEqual(result["price_change_pct"], 9.52, places=1)


class TestVerificationSchedulerTrigger(unittest.TestCase):
    """Test VerificationScheduler trigger functionality"""
    
    @patch('services.judgment_service.JudgmentService')
    @patch('services.verification_scheduler.DatabaseFactory')
    def test_trigger_now_executes_without_error(self, mock_db, mock_service):
        """Test that trigger_now() can be called without throwing errors"""
        from services.verification_scheduler import VerificationScheduler
        
        # Mock database to return empty list (no pending judgments)
        mock_db.fetchall.return_value = []
        
        # This should not raise any exceptions
        try:
            VerificationScheduler._run_verification_job()
            success = True
        except Exception as e:
            success = False
            print(f"Trigger failed: {e}")
            
        self.assertTrue(success)
        
    @patch('services.verification_scheduler.DatabaseFactory')
    def test_get_pending_owners_returns_list(self, mock_db):
        """Test _get_all_pending_owners returns proper structure"""
        from services.verification_scheduler import VerificationScheduler
        
        # Mock database response
        mock_db.fetchall.return_value = [
            {'owner_type': 'anonymous', 'owner_id': 'test-uuid-1'},
            {'owner_type': 'anchor', 'owner_id': 'test@example.com'}
        ]
        
        result = VerificationScheduler._get_all_pending_owners()
        
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0], ('anonymous', 'test-uuid-1'))
        self.assertEqual(result[1], ('anchor', 'test@example.com'))


def run_tests():
    """Run all tests"""
    unittest.main(argv=[''], verbosity=2, exit=False)


if __name__ == "__main__":
    run_tests()
