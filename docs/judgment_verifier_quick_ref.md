# Judgment Verifier v0.1 - Quick Reference

## 🎯 Core Function

```python
from services.judgment_verifier import JudgmentVerifier

verifier = JudgmentVerifier()
result = verifier.verify(
    snapshot,           # JudgmentSnapshot
    current_price,      # float (required)
    ma200_value,        # float (optional)
    price_history       # List[float] (optional, for sustained breach)
)
```

**Returns:**
```python
{
    "current_structure_status": "maintained|weakened|broken",
    "reasons": ["reason1", "reason2", "reason3"],  # Max 3
    "current_price": 12.75,
    "price_change_pct": 2.0
}
```

---

## 📊 Verification Rules

### Consolidation
| Status | Condition |
|--------|-----------|
| **maintained** | Price in range |
| **weakened** | Single breach |
| **broken** | 3+ days out of range |

### Uptrend
| Status | Condition |
|--------|-----------|
| **maintained** | Above support & MA200 |
| **weakened** | Near support/MA200 |
| **broken** | Below support OR MA200 |

### Downtrend
| Status | Condition |
|--------|-----------|
| **maintained** | Below resistance & MA200 |
| **weakened** | Near resistance |
| **broken** | 3+ days above resistance |

---

## 📝 Reason Templates (20 total)

**Structure Language Only** - No trading signals

### Consolidation (4)
- 价格保持在整理区间内
- 价格接近区间边界
- 价格单次越出区间边界
- 价格持续越出区间边界

### Uptrend (6)
- 价格保持在关键支撑上方
- 价格接近关键支撑位
- 价格跌破关键支撑位
- 价格保持在MA200上方
- 价格接近MA200
- 价格跌破MA200

### Downtrend (7)
- 价格保持在关键压力下方
- 价格接近关键压力位
- 价格突破关键压力位
- 价格持续站稳压力位上方
- 价格保持在MA200下方
- 价格接近MA200
- 价格突破MA200上方

### General (3)
- 结构前提保持完整
- 结构前提受到挑战
- 结构前提已被破坏

---

## 🧪 Tests

```bash
python3 -m pytest tests/test_judgment_verifier.py -v
```

**13 tests** - All passing ✅

---

## 📁 Files

- `services/judgment_verifier.py` - Verifier service
- `tests/test_judgment_verifier.py` - Unit tests
