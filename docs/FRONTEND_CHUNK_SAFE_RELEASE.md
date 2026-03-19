# 前端 Chunk 安全发布与回滚手册

适用范围：ECharts 异步化与前端分包调整发布。

## 1. 发布前门禁

在本地或 CI 必须通过：

```bash
cd frontend
npm run build:with-metrics
```

并检查：

- `frontend/build-metrics/latest.json` 已生成
- `warning_chunks` 记录有变化（用于对比优化前后）
- 无构建失败

同时运行关键契约测试：

```bash
cd /Users/ck/Desktop/Project/stock-scanner-baseline
python -m pytest tests/test_frontend_chunk_contract.py tests/test_frontend_seo_contract.py -q
```

## 2. 预发布验证（防白屏）

重点页面：

- `/`
- `/analysis`
- `/analysis/{id}`

验证动作：

1. 普通刷新 3 次
2. 强刷（清缓存）2 次
3. 观察浏览器控制台是否出现 `ChunkLoadError` 或 `Failed to fetch dynamically imported module`

## 3. 生产发布步骤（低风险）

```bash
cd /root/dpstock
git pull --ff-only origin main
docker compose -f docker-compose.prod.yml up -d --build app nginx
docker compose -f docker-compose.prod.yml ps
```

发布后立即检查：

```bash
curl -s http://127.0.0.1/health
curl -s https://aguai.net/api/need_login
curl -s "https://aguai.net/api/search_global?keyword=600519&market_type=A"
curl -s https://aguai.net/api/market-overview
docker compose -f docker-compose.prod.yml logs --tail=120 app
docker compose -f docker-compose.prod.yml logs --tail=120 nginx
```

## 4. 回滚步骤（出现白屏或路由异常时）

1. 回退到上一稳定提交：

```bash
cd /root/dpstock
git checkout <last-good-commit>
```

2. 重建并拉起服务：

```bash
docker compose -f docker-compose.prod.yml up -d --build app nginx
```

3. 重新执行健康检查（同上）。

## 5. 故障定位顺序

1. `nginx` 日志是否有静态资源 404
2. 浏览器控制台是否有 chunk 加载错误
3. 异步图表组件是否加载失败但页面主体仍可用
4. `runtimeRecovery` 是否触发自动刷新/提示
