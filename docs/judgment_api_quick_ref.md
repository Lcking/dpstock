# Judgment API v0.1 - Quick Reference

## 🎯 3 API Endpoints

### 1. POST /api/v1/judgments
**Save judgment snapshot**
```bash
curl -X POST http://localhost:8888/api/v1/judgments \
  -H "Content-Type: application/json" \
  -c cookies.txt \
  -d '{"snapshot": {...}}'
```
Returns: `{judgment_id, user_id, created_at}`

### 2. GET /api/v1/me/judgments?limit=50
**Get my judgments**
```bash
curl -X GET http://localhost:8888/api/v1/me/judgments \
  -b cookies.txt
```
Returns: `{user_id, total, judgments: [...]}`

### 3. GET /api/v1/judgments/{judgment_id}
**Get judgment detail**
```bash
curl -X GET http://localhost:8888/api/v1/judgments/{id}
```
Returns: `{judgment_id, snapshot, latest_check}`

---

## 📊 Database Tables

### judgments
- judgment_id (UUID)
- user_id (from cookie)
- stock_code, structure_type, ma200_position, phase
- structure_premise (JSON)
- selected_candidates (JSON)
- key_levels_snapshot (JSON)

### judgment_checks
- judgment_id (FK)
- current_price, price_change_pct
- current_structure_status
- status_description, reasons (JSON)

---

## 🍪 Anonymous Identity

**Cookie:** `aguai_uid`
- Auto-generated UUID
- 1-year expiration
- HttpOnly, SameSite=lax

**Usage:**
- `-c cookies.txt` to save cookie
- `-b cookies.txt` to send cookie

---

## 📁 Files

**Created:**
- `migrations/001_create_judgments_tables.sql`
- `services/judgment_service.py`
- `routes/judgments.py`
- `docs/judgment_api_examples.md`

**Modified:**
- `web_server.py` (+2 lines)

---

## ✅ Status

- ✅ Database migrated
- ✅ Imports verified
- ✅ Router registered
- ✅ Ready to test

**Start server:**
```bash
python3 web_server.py
```

**Full examples:**
See `docs/judgment_api_examples.md`
