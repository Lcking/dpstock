# 仓库清理后恢复与排障手册

适用场景：完成“保守清理与归档”后，若出现页面异常、接口异常或环境不一致，可按本文快速定位与恢复。

## 1. 本次归档清单

| 原路径 | 归档后路径 |
| --- | --- |
| `debug_eastmoney.py` | `archive/debug/debug_eastmoney.py` |
| `debug_yfinance.py` | `archive/debug/debug_yfinance.py` |
| `scripts/debug_admin_data.py` | `archive/scripts/debug_admin_data.py` |
| `poc_analysis_v1_output.json` | `archive/artifacts/poc_analysis_v1_output.json` |
| `frontend/src/components/MyJudgments.vue.backup` | `archive/frontend/MyJudgments.vue.backup` |

说明：以上文件均为历史调试或备份性质，不参与当前核心运行链路。

## 2. 快速回滚（文件回迁）

若需要恢复某个归档文件到旧路径：

1. 将归档文件复制回原路径（保持文件名不变）。
2. 启动/重启相关服务。
3. 执行最小验证命令确认影响范围。

示例（恢复 `debug_admin_data.py`）：

```bash
cd /root/dpstock
cp archive/scripts/debug_admin_data.py scripts/debug_admin_data.py
```

## 3. 服务重启与最小验证

```bash
cd /root/dpstock
docker compose -f docker-compose.prod.yml up -d --build app nginx
docker compose -f docker-compose.prod.yml ps
curl -s http://127.0.0.1/health
curl -s https://aguai.net/api/need_login
curl -s "https://aguai.net/api/search_global?keyword=600519&market_type=A"
curl -s https://aguai.net/api/market-overview
```

预期：

- `app`/`nginx` 健康状态正常
- `health` 返回 `healthy`
- `need_login`、`search_global`、`market-overview` 均返回有效 JSON

## 4. 常见异常与定位顺序

### A. 前端页面异常（白屏/资源缺失）

1. `docker compose -f docker-compose.prod.yml logs --tail=120 nginx`
2. 检查是否有前端静态资源 404。
3. 若为缓存问题，强刷浏览器并重新验证。

### B. 后端接口异常

1. `docker compose -f docker-compose.prod.yml logs --tail=120 app`
2. 先检查迁移与启动日志是否完整。
3. 使用 `curl` 单独验证接口，避免前端因素干扰。

### C. 环境变量缺失

重点检查：

- `TUSHARE_TOKEN`
- `JUMDATA_APP_CODE`

命令：

```bash
cd /root/dpstock
grep -E "TUSHARE_TOKEN|JUMDATA_APP_CODE" .env
```

## 5. 清理后变更原则

- 核心业务目录（`routes/`, `services/`, `frontend/src/`）不做结构性移动。
- 对可能仍有价值的文件，优先“归档”而不是“删除”。
- 每次清理后都保留可执行恢复文档，并执行最小冒烟验证。
