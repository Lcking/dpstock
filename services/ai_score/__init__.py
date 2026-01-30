"""
AI Score (Spec v1.0)

Provides:
- Pydantic models for ai_score output
- Calculator implementing the fixed rules in Spec v1.0
"""

from .models import AiScore  # noqa: F401
from .calculator import AiScoreCalculator  # noqa: F401

