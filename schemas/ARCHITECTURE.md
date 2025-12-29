# Analysis V1 Schema 架构图

## 整体结构

```
AnalysisV1Response
├── stock_code (string)
├── stock_name (string)
├── market_type (string)
├── analysis_date (datetime)
│
├── 1️⃣ structure_snapshot
│   ├── structure_type (enum: uptrend/downtrend/consolidation/reversal)
│   ├── key_levels (array, max 6)
│   │   └── {price, label}
│   └── trend_description (string, max 200)
│
├── 2️⃣ pattern_fitting
│   ├── pattern_type (enum: head_shoulders/double_top_bottom/triangle/channel/wedge/flag/none)
│   ├── pattern_description (string, max 200)
│   └── completion_rate (int, 0-100, optional)
│
├── 3️⃣ indicator_translate
│   └── indicators (array, max 5)
│       └── {name, value, signal, interpretation}
│           └── signal (enum: bullish/bearish/neutral)
│
├── 4️⃣ risk_of_misreading
│   ├── risk_level (enum: high/medium/low)
│   ├── risk_factors (array, max 4)
│   └── caution_note (string, max 200)
│
└── 5️⃣ judgment_zone
    ├── options (array, 2-4 items)
    │   └── {option_id, description}
    └── note (string, max 100)
```

## 扩展模型

### JudgmentSnapshot（用户判断快照）
```
JudgmentSnapshot
├── stock_code (string)
├── selected_option_id (string)
├── selected_structure (StructureType)
├── snapshot_time (datetime)
└── key_price (float)
```

### JudgmentOverview（判断验证概览）
```
JudgmentOverview
├── stock_code (string)
├── original_judgment (JudgmentSnapshot)
├── current_structure_status (enum: maintained/weakened/broken)
├── current_price (float)
├── price_change_pct (float)
├── verification_time (datetime)
└── status_description (string, max 200)
```

## 数据流程

```
用户请求
    ↓
分析引擎
    ↓
生成五段式分析
    ├── 结构快照
    ├── 形态拟合
    ├── 指标翻译
    ├── 误读风险
    └── 判断候选区
    ↓
返回 AnalysisV1Response
    ↓
前端展示
    ↓
用户选择判断选项
    ↓
保存 JudgmentSnapshot
    ↓
后续验证
    ↓
生成 JudgmentOverview
```

## 字段约束总览

| 部分 | 字段 | 类型 | 约束 |
|------|------|------|------|
| **基础信息** | stock_code | string | 必填 |
| | stock_name | string | 必填 |
| | market_type | string | 必填 |
| | analysis_date | datetime | 必填 |
| **Section 1** | structure_type | enum | 4个选项 |
| | key_levels | array | ≤6个 |
| | trend_description | string | ≤200字符 |
| **Section 2** | pattern_type | enum | 7个选项 |
| | pattern_description | string | ≤200字符 |
| | completion_rate | int | 0-100，可选 |
| **Section 3** | indicators | array | ≤5个 |
| | interpretation | string | ≤150字符 |
| **Section 4** | risk_level | enum | 3个选项 |
| | risk_factors | array | ≤4个 |
| | caution_note | string | ≤200字符 |
| **Section 5** | options | array | 2-4个 |
| | option description | string | ≤150字符 |
| | note | string | ≤100字符 |
