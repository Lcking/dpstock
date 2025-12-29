# Analysis V1 Response Schema

## 概述

Analysis V1 采用**固定五段式结构**，用于前后端联调的标准化响应格式。

## 核心设计原则

1. **固定五段式结构** - 每个分析响应必须包含以下五个部分
2. **无买卖建议** - 系统不提供任何买卖建议、概率或预测结论
3. **结构验证** - 支持用户判断快照和后续验证
4. **字段精简** - 严格控制字段数量，避免过度设计

## 五段式结构

### 1. Structure Snapshot（结构快照）
- **目的**: 描述当前价格结构和关键价格位
- **字段**:
  - `structure_type`: 结构类型（上升/下降/盘整/反转）
  - `key_levels`: 关键价格位列表（最多6个）
  - `trend_description`: 趋势描述（≤200字）

### 2. Pattern Fitting（形态拟合）
- **目的**: 识别技术形态
- **字段**:
  - `pattern_type`: 形态类型（头肩/双顶底/三角形/通道等）
  - `pattern_description`: 形态描述（≤200字）
  - `completion_rate`: 形态完成度（0-100%，可选）

### 3. Indicator Translate（指标翻译）
- **目的**: 将技术指标转化为可读解释
- **字段**:
  - `indicators`: 指标列表（最多5个）
    - `name`: 指标名称
    - `value`: 指标值（格式化字符串）
    - `signal`: 信号方向（看涨/看跌/中性）
    - `interpretation`: 指标解读（≤150字）

### 4. Risk of Misreading（误读风险）
- **目的**: 提示可能的误读风险
- **字段**:
  - `risk_level`: 风险等级（高/中/低）
  - `risk_factors`: 风险因素列表（最多4个）
  - `caution_note`: 注意事项（≤200字）

### 5. Judgment Zone（判断候选区）
- **目的**: 提供可能走势的候选项，供用户自行判断
- **字段**:
  - `options`: 判断候选项（2-4个）
    - `option_id`: 选项ID（A/B/C/D）
    - `description`: 判断描述（≤150字）
  - `note`: 免责说明

## 扩展功能

### Judgment Snapshot（判断快照）
用于保存用户选择的结构前提：
- `stock_code`: 股票代码
- `selected_option_id`: 用户选择的选项ID
- `selected_structure`: 用户判断的结构类型
- `snapshot_time`: 快照时间
- `key_price`: 快照时的关键价格

### Judgment Overview（判断概览）
用于展示结构验证结果：
- `original_judgment`: 原始判断快照
- `current_structure_status`: 当前结构状态（保持/削弱/破坏）
- `current_price`: 当前价格
- `price_change_pct`: 价格变化百分比
- `verification_time`: 验证时间
- `status_description`: 状态描述

## Enum 定义

### StructureType（结构类型）
```python
uptrend         # 上升趋势
downtrend       # 下降趋势
consolidation   # 盘整
reversal        # 反转
```

### PatternType（形态类型）
```python
head_shoulders      # 头肩顶/底
double_top_bottom   # 双顶/底
triangle            # 三角形
channel             # 通道
wedge               # 楔形
flag                # 旗形
none                # 无明显形态
```

### IndicatorSignal（指标信号）
```python
bullish   # 看涨
bearish   # 看跌
neutral   # 中性
```

### RiskLevel（风险等级）
```python
high      # 高风险
medium    # 中风险
low       # 低风险
```

### StructureStatus（结构状态）
```python
maintained   # 结构保持
weakened     # 结构被削弱
broken       # 结构被破坏
```

## 使用示例

### 导入模型
```python
from schemas.analysis_v1 import (
    AnalysisV1Response,
    StructureType,
    PatternType,
    IndicatorSignal,
    RiskLevel
)
```

### 创建响应
```python
from datetime import datetime

response = AnalysisV1Response(
    stock_code="600519",
    stock_name="贵州茅台",
    market_type="A",
    analysis_date=datetime.now(),
    structure_snapshot={
        "structure_type": StructureType.UPTREND,
        "key_levels": [
            {"price": 1650.0, "label": "支撑位1"},
            {"price": 1720.0, "label": "压力位1"}
        ],
        "trend_description": "中期上升趋势"
    },
    # ... 其他字段
)
```

### FastAPI 路由示例
```python
@app.post("/api/v1/analysis", response_model=AnalysisV1Response)
async def analyze_v1(stock_code: str, market_type: str = "A"):
    # 分析逻辑
    return response
```

## 完整示例

参见 `analysis_v1_example.json` 文件获取完整的 JSON 示例。

## 字段约束总结

| 字段 | 最大长度/数量 | 说明 |
|------|--------------|------|
| `trend_description` | 200字符 | 趋势描述 |
| `pattern_description` | 200字符 | 形态描述 |
| `key_levels` | 6个 | 关键价格位 |
| `indicators` | 5个 | 指标列表 |
| `interpretation` | 150字符 | 指标解读 |
| `risk_factors` | 4个 | 风险因素 |
| `caution_note` | 200字符 | 注意事项 |
| `options` | 2-4个 | 判断候选项 |
| `option description` | 150字符 | 选项描述 |

## 注意事项

1. **严格遵守五段式结构** - 所有响应必须包含完整的五个部分
2. **不提供建议** - `judgment_zone` 仅提供候选项，不做推荐
3. **字段精简** - 避免添加不必要的字段
4. **类型安全** - 使用 Pydantic 确保类型验证
5. **OpenAPI 兼容** - 自动生成 API 文档
