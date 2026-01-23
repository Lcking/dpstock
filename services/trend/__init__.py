"""
Trend Service Module
"""
from .calculator import TrendCalculator, trend_calculator
from .schemas import TrendInput, TrendResult

__all__ = [
    "TrendCalculator",
    "trend_calculator",
    "TrendInput",
    "TrendResult"
]
