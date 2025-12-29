# Judgment API v0.1 - cURL Examples

## Prerequisites
- Server running on `http://localhost:8888`
- Database initialized with judgment tables

## 1. Create Judgment Snapshot

Save a user's judgment snapshot with anonymous identity.

```bash
curl -X POST "http://localhost:8888/api/v1/judgments" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{
    "snapshot": {
      "stock_code": "000001",
      "snapshot_time": "2025-12-29T10:00:00",
      "structure_premise": {
        "structure_type": "consolidation",
        "ma200_position": "above",
        "phase": "middle",
        "pattern_type": "triangle"
      },
      "selected_candidates": ["A", "C"],
      "key_levels_snapshot": [
        {"price": 12.50, "label": "近期支撑"},
        {"price": 13.00, "label": "近期压力"}
      ],
      "structure_type": "consolidation",
      "ma200_position": "above",
      "phase": "middle"
    }
  }'
```

**Response:**
```json
{
  "judgment_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "created_at": "2025-12-29T10:00:00"
}
```

**Notes:**
- `-c cookies.txt` saves the `aguai_uid` cookie
- If no cookie exists, server generates new anonymous user ID
- Returns judgment_id for future reference

---

## 2. Get My Judgments

Retrieve all judgments for the current user.

```bash
curl -X GET "http://localhost:8888/api/v1/me/judgments?limit=50" \
  -H "Content-Type: application/json" \
  -b cookies.txt
```

**Response:**
```json
{
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "total": 2,
  "judgments": [
    {
      "judgment_id": "550e8400-e29b-41d4-a716-446655440000",
      "stock_code": "000001",
      "snapshot_time": "2025-12-29T10:00:00",
      "structure_type": "consolidation",
      "ma200_position": "above",
      "phase": "middle",
      "selected_candidates": ["A", "C"],
      "created_at": "2025-12-29T10:00:00",
      "latest_check": {
        "current_price": 13.25,
        "price_change_pct": 6.0,
        "current_structure_status": "broken",
        "status_description": "有效突破13.00压力位且放量",
        "reasons": [
          "突破时成交量放大至2倍均量",
          "连续3日站稳13.00上方"
        ],
        "verification_time": "2025-12-30T10:00:00"
      }
    }
  ]
}
```

**Notes:**
- `-b cookies.txt` sends the `aguai_uid` cookie
- Returns judgments ordered by creation time (newest first)
- `latest_check` only present if verification exists
- `limit` parameter controls max results (default: 50)

---

## 3. Get Judgment Detail

Get full details of a specific judgment.

```bash
curl -X GET "http://localhost:8888/api/v1/judgments/550e8400-e29b-41d4-a716-446655440000" \
  -H "Content-Type: application/json"
```

**Response:**
```json
{
  "judgment_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "123e4567-e89b-12d3-a456-426614174000",
  "stock_code": "000001",
  "snapshot_time": "2025-12-29T10:00:00",
  "structure_premise": {
    "structure_type": "consolidation",
    "ma200_position": "above",
    "phase": "middle",
    "pattern_type": "triangle"
  },
  "selected_candidates": ["A", "C"],
  "key_levels_snapshot": [
    {"price": 12.50, "label": "近期支撑"},
    {"price": 13.00, "label": "近期压力"}
  ],
  "structure_type": "consolidation",
  "ma200_position": "above",
  "phase": "middle",
  "created_at": "2025-12-29T10:00:00",
  "latest_check": {
    "check_time": "2025-12-30T10:00:00",
    "current_price": 13.25,
    "price_change_pct": 6.0,
    "current_structure_status": "broken",
    "status_description": "有效突破13.00压力位且放量",
    "reasons": [
      "突破时成交量放大至2倍均量",
      "连续3日站稳13.00上方",
      "MACD金叉向上"
    ]
  }
}
```

**Notes:**
- No authentication required (public endpoint)
- Returns full judgment snapshot
- Includes latest verification check if exists
- Returns 404 if judgment_id not found

---

## Testing Workflow

### 1. Create a judgment
```bash
curl -X POST "http://localhost:8888/api/v1/judgments" \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d @- << 'EOF'
{
  "snapshot": {
    "stock_code": "000001",
    "snapshot_time": "2025-12-29T10:00:00",
    "structure_premise": {
      "structure_type": "consolidation",
      "ma200_position": "above",
      "phase": "middle"
    },
    "selected_candidates": ["A"],
    "key_levels_snapshot": [
      {"price": 12.50, "label": "支撑"},
      {"price": 13.00, "label": "压力"}
    ],
    "structure_type": "consolidation",
    "ma200_position": "above",
    "phase": "middle"
  }
}
EOF
```

### 2. List your judgments
```bash
curl -X GET "http://localhost:8888/api/v1/me/judgments" \
  -b cookies.txt | jq
```

### 3. Get specific judgment
```bash
# Replace with actual judgment_id from step 1
curl -X GET "http://localhost:8888/api/v1/judgments/YOUR_JUDGMENT_ID" | jq
```

---

## Cookie Management

### View saved cookie
```bash
cat cookies.txt
```

### Clear cookie (test new user)
```bash
rm cookies.txt
```

### Manual cookie test
```bash
curl -X GET "http://localhost:8888/api/v1/me/judgments" \
  -H "Cookie: aguai_uid=YOUR_USER_ID"
```

---

## Error Responses

### 404 - Judgment Not Found
```json
{
  "detail": "Judgment not found"
}
```

### 500 - Server Error
```json
{
  "detail": "Failed to create judgment: <error message>"
}
```
