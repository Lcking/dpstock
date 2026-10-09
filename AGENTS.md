# AGENTS.md

## Cursor Cloud specific instructions

This is a single product: an AI-powered stock analysis web app ("Aguai / 股票分析系统").
It is a FastAPI monolith (`web_server.py`) plus a Vue 3 + Vite frontend. SQLite is embedded
(no DB server). Standard commands live in `README.md` (验证命令) and `frontend/package.json`.

### Services

| Service | How to run (from repo root) | Port | Notes |
| --- | --- | --- | --- |
| Backend API | `source .venv/bin/activate && python web_server.py` | 8888 | Loads `.env`, auto-runs migrations on startup. `UVICORN_RELOAD=true` enables autoreload. |
| Frontend (Vite dev) | `npm run dev --prefix frontend` | 5173 | Proxies `/api` → `127.0.0.1:8888`. Binds to `localhost` only (probe `http://localhost:5173`, not `127.0.0.1`). |

The update script already installs both dependency sets (`.venv` pip deps + `frontend/node_modules`).
A local `.env` (copied from `.env.example`) is created during setup and is gitignored.

### Non-obvious gotchas

- **Python version**: this VM runs Python 3.12 (CI uses 3.10). `Pillow==9.5.0` has no 3.12 wheel
  and is compiled from source; the build needs `libjpeg-dev`, `zlib1g-dev`, `python3.12-dev`
  (already installed in the VM snapshot — not in the update script).
- **`DB_PATH` mismatch**: `/api/health` defaults `DB_PATH` to the Docker path `/app/data/stocks.db`,
  while migrations default to the relative `data/stocks.db`. In dev, set `DB_PATH=/workspace/data/stocks.db`
  in `.env` (already done) so `/api/health` reports `db: ok` / `disk: ok` instead of failing.
- **LLM key required for AI text**: the core technical analysis (score, RSI, MACD, MA, recommendation)
  is computed locally from market data and works without secrets. The AI narrative layer needs a real
  OpenAI-compatible `API_KEY`/`API_URL`; with the placeholder it returns `API请求失败: Invalid URL ...`
  in the analyze stream — expected in dev, not a bug.
- **Test DB pollution**: tests are DB-isolated via `tests/conftest.py`, but a stale/partially-initialized
  `data/stocks.db` can make `tests/test_etf_article_names.py` fail with `no such table: ...`.
  If you hit that, delete `data/stocks.db*` (it auto-recreates) or run `python scripts/run_migrations.py`.
- **Network-dependent data**: market-data sources (akshare → szse.cn, tushare with a real token) may be
  unreachable; the app degrades gracefully and logs warnings. The risk-stock collector and per-stock
  kline data did work during setup.
- The empty `stock_analysis.db` at repo root is unused; the real DB is `data/stocks.db`.
- Streaming endpoints (`/api/analyze`): see `.cursor/rules/shell-and-deploy-pitfalls.mdc` for the
  required `curl --http1.1 -N --max-time 120` test flags and the `asyncio.shield` heartbeat pattern.
