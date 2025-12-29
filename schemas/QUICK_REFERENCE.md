# Analysis V1 Schema - 快速参考

## 🚀 快速开始

### 导入
```python
from schemas import AnalysisV1Response, StructureType, PatternType
```

### 创建响应
```python
response = AnalysisV1Response(
    stock_code="600519",
    stock_name="贵州茅台",
    market_type="A",
    analysis_date=datetime.now(),
    structure_snapshot={...},
    pattern_fitting={...},
    indicator_translate={...},
    risk_of_misreading={...},
    judgment_zone={...}
)
```

---

## 📋 五段式结构速查

| 段落 | 英文名 | 核心字段 | 限制 |
|------|--------|----------|------|
| 1 | Structure Snapshot | structure_type, key_levels | ≤6个价格位 |
| 2 | Pattern Fitting | pattern_type, pattern_description | ≤200字符 |
| 3 | Indicator Translate | indicators | ≤5个指标 |
| 4 | Risk of Misreading | risk_level, risk_factors | ≤4个风险 |
| 5 | Judgment Zone | options, note | 2-4个选项 |

---

## 🏷️ Enum 速查表

### StructureType
```python
uptrend | downtrend | consolidation | reversal
```

### PatternType
```python
head_shoulders | double_top_bottom | triangle | channel | wedge | flag | none
```

### IndicatorSignal
```python
bullish | bearish | neutral
```

### RiskLevel
```python
high | medium | low
```

### StructureStatus
```python
maintained | weakened | broken
```

---

## 📏 字段长度限制

| 字段 | 最大值 |
|------|--------|
| trend_description | 200字符 |
| pattern_description | 200字符 |
| interpretation | 150字符 |
| caution_note | 200字符 |
| option description | 150字符 |
| note | 100字符 |

---

## 📊 数组限制

| 字段 | 最小 | 最大 |
|------|------|------|
| key_levels | - | 6 |
| indicators | - | 5 |
| risk_factors | - | 4 |
| options | 2 | 4 |

---

## 💡 示例数据

### 最小示例
```json
{
  "stock_code": "600519",
  "stock_name": "贵州茅台",
  "market_type": "A",
  "analysis_date": "2025-12-29T10:30:00",
  "structure_snapshot": {
    "structure_type": "uptrend",
    "key_levels": [
      {"price": 1650.0, "label": "支撑位1"}
    ],
    "trend_description": "上升趋势"
  },
  "pattern_fitting": {
    "pattern_type": "none",
    "pattern_description": "无明显形态"
  },
  "indicator_translate": {
    "indicators": [
      {
        "name": "RSI",
        "value": "60",
        "signal": "bullish",
        "interpretation": "多头占优"
      }
    ]
  },
  "risk_of_misreading": {
    "risk_level": "low",
    "risk_factors": ["无明显风险"],
    "caution_note": "保持观察"
  },
  "judgment_zone": {
    "options": [
      {"option_id": "A", "description": "继续上行"},
      {"option_id": "B", "description": "震荡整理"}
    ],
    "note": "系统不提供买卖建议"
  }
}
```

---

## 🔗 相关文件

- **Schema定义**: `schemas/analysis_v1.py`
- **完整文档**: `schemas/README.md`
- **架构图**: `schemas/ARCHITECTURE.md`
- **完整示例**: `schemas/analysis_v1_example.json`
- **OpenAPI**: `schemas/analysis_v1_openapi.json`
- **测试脚本**: `schemas/test_schema.py`

---

## ✅ 验证命令

```bash
# 运行测试
python3 -m schemas.test_schema

# 验证导入
python3 -c "from schemas import AnalysisV1Response; print('OK')"
```

---

## ⚠️ 核心原则

1. ✅ 必须包含完整五段式结构
2. ❌ 不提供任何买卖建议
3. 📊 严格遵守字段数量和长度限制
4. 🔒 使用 Pydantic 类型验证
5. 📝 所有字段必须有明确含义
