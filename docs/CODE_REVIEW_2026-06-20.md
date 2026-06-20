# 代码诊断与任务规划 · 第二轮（交付 Cursor 执行）

> 生成日期：2026-06-20
> 前置：第一轮见 `docs/CODE_REVIEW_2026-06-19.md`，T1–T9 已基本落地。
> 本轮已核实上轮成果，并转向新维度：**成本/安全、激活留存、性能、内容引擎、可验证性**。
> 每个任务卡含「文件位置 / 证据 / 改动方案 / 验收标准」，可直接执行。

---

## 0. 上轮成果核实（已确认落地，勿重做）

| 上轮任务 | 状态 | 证据 |
|---|---|---|
| T1 文章页 meta 注入 | ✅ 已改为占位符方案 | `frontend/index.html` 现有 `<!--SSR:TITLE-->`/`<!--SSR:DESCRIPTION-->`/`<!--SSR:JSON_LD-->` 等锚点；`web_server.py` 调 `inject_article_page()` |
| T4 全 A 股 SSR + sitemap | ✅ 已用 sitemap_index 分片 | `sitemap_generator.py` 拆 core/stock 两张表；`search_snapshot_service` 按 mtime 缓存全市场清单 |
| T5 公开诊断准确率 / 信任 | ✅ | `feat(trust)`、`feat(me)` 提交，user center trust stats |
| T6 合规措辞 | ✅ 已去指向性 | `stock_scorer.get_recommendation()` 现返回「结构强/偏强/中性/偏弱/弱/极弱」 |
| T3 数据时间戳/来源 | ✅ | 新增 `services/data_provenance.py`、`services/instrument_name_resolver.py` |
| T9 组合健康度 | ✅ | `feat(watchlist)` 行业暴露 + 集中度 + 权重 health panel |
| ETF/LOF 识别 | ✅ 本次修复 | `fix(etf)` 4 连提交：名称解析回退 tushare、批量预载、从代码推断市场 |

做得很扎实。下面是新一轮的推进点。

---

## 任务优先级总览

| 优先级 | 任务 | 类型 | 预估 |
|---|---|---|---|
| **P0** | N1 `/api/analyze` 成本滥用加固 | 安全/成本 | 1 天 |
| P1 | N2 风险提醒邮件/推送（激活留存） | 增长/功能 | 1–2 天 |
| P1 | N3 ETF/LOF 修复加防回归测试 | 质量 | 0.5 天 |
| P1 | N4 测试套件可运行性 + CI 门禁 | 工程 | 1 天 |
| P2 | N5 前端首屏性能（移动端优先） | 性能 | 1–2 天 |
| P2 | N6 自动「诊断复盘」内容引擎（SEO/GEO 复利） | 增长 | 2–3 天 |
| P3 | N7 可观测性补全（错误告警 + 成本看板） | 运维 | 1 天 |
| P3 | N8 数据层与配置一致性收尾 | 技术债 | 0.5–1 天 |

---

## P0 — N1：`/api/analyze` 成本滥用加固（最重要的新发现）

**类型**：安全 / 成本（直接对应真金白银的 LLM 调用）

**文件**：`web_server.py`（`AnalyzeRequest` 约 137 行；`analyze()` 约 262–520 行）、`services/quota_service.py`。

**证据（已确认，三重缺口叠加）**：
1. **批量分析完全绕过额度**：
   ```python
   # Quota check for single stock analysis only (batch analysis not subject to quota)
   if len(stock_codes) == 1 and canonical_user_id:
       ... check_quota ...
   ```
   只要传 ≥2 个代码，`check_quota` 完全不执行。批量分支 `for code in stock_codes: ... scan_stocks(...)` 按代码逐个发起 LLM 调用。
2. **请求体无长度上限**：`class AnalyzeRequest: stock_codes: List[str]`，无 `Field(max_length=...)`、无 `conlist`。可一次提交任意长列表。
3. **该端点无任何限流**：全仓 `rate_limit` 仅出现在 `auth/admin_auth.py`（admin 登录）和 `anchor_service`（邮件验证码）。`/api/analyze` 无限流；`require_login` 在 `REQUIRE_LOGIN=False`（未设 `LOGIN_PASSWORD`）时是 pass-through，匿名可调。

**合并影响**：单个匿名请求 → `{"stock_codes": [...N 个...]}` → N 次 LLM 调用，无额度、无限流、无批量上限。这是可被直接刷爆账单的成本漏洞。

**改动方案**：
- **批量上限**：`AnalyzeRequest.stock_codes` 改 `conlist(str, min_length=1, max_length=20)`（上限取业务合理值），超限 422。
- **批量也计额度**：`quota_service` 增加「按只数扣减」语义，批量请求按 `len(stock_codes)` 校验与扣减；移除「批量豁免」逻辑。
- **端点级限流**：引入 `slowapi`（或复用现有 `_rate_limit_ok` 思路）对 `/api/analyze` 按 IP + user_id 做窗口限流（如每分钟 N 次、每日上限）。
- **匿名收敛**：匿名身份的 analyze 额度应显著低于绑定用户，强化「绑定邮箱解锁更多额度」的转化钩子（与现有 anchor 体系联动）。

**验收标准**：
- 提交 21 个代码 → 422；提交 20 个 → 正常但**扣减 20 次额度**。
- 超过限流阈值 → 429。
- 新增 `tests/test_analyze_quota_and_limit.py`：覆盖批量扣额、批量上限、限流触发三个用例。

---

## P1 — N2：风险提醒的邮件/推送通道（激活与留存）

**类型**：增长（把一次性访问变成日活——这是最初诊断里仍未兑现的高频钩子）

**文件**：`services/watchlist_risk_alert_service.py`（现仅 `get_unread_count`/`list_alerts`/`mark_all_read`，**纯站内**）、`services/email_service.py`（现仅 `send_verification_code`）、`services/risk_stock_scheduler.py`。

**问题**：风险提醒已能生成并在站内展示，但**没有任何外呼通道**把休眠用户拉回来。诊股是低频行为，「我关注的票出现风险信号」才是高频触发点，目前这条链路断在最后一公里。

**改动方案**：
- `email_service` 增加 `send_risk_alert_digest(email, alerts)`：当用户自选股命中风险列表时，发当日/触发即时摘要邮件（已绑定邮箱用户）。
- 在 `sync_alerts_for_trade_date` 产生新 alert 后，触发摘要任务（去重、合并、频控，避免轰炸）。
- 邮件含「仅供参考、非投资建议」与一键退订；尊重用户通知偏好（新增 `notify_pref`）。
- 进阶：预留 Web Push / 公众号模板消息接口（中国场景公众号触达更有效）。

**验收标准**：绑定邮箱用户的自选股命中风险列表后收到摘要邮件；可退订；同一标的同日不重复发送。

---

## P1 — N3：ETF/LOF 修复补防回归测试

**类型**：质量（锁住本次刚修的 bug）

**文件**：`services/instrument_name_resolver.py`、`services/stock_data_provider.py`（`resolve_stock_code`）、`services/stock_page_service.py`（`normalize_code` 仅做 `.split(".")[0].upper()`）。

**问题**：ETF/LOF 修复跨 4 个提交、涉及名称解析与市场推断，但需确认有对应测试固化，否则后续重构易回退。

**改动方案 / 验收标准**：
- 新增 `tests/test_instrument_resolver.py`，覆盖：
  - ETF（如 `510300`/`159919`）、LOF（如 `161725`）、科创板（`688xxx`）、北交所（`8xxxxx`/`43xxxx`）的市场推断正确。
  - 名称解析失败时回退 tushare 的路径。
  - 占位名（如纯代码、"未知"）能被二次解析覆盖（对应 `fff78ee` re-resolve placeholder）。
- 断言 `/stock/{etf_code}` 与归档文章页显示真实基金名称而非占位符。

---

## P1 — N4：测试套件可运行性 + CI 门禁

**类型**：工程

**证据**：仓库 `.venv` 为本机（macOS）环境，CI/容器内无法直接用；`tests/` 有 38 个测试文件但缺一键可复现的运行入口；`.github/workflows` 存在但未确认跑测试。

**改动方案**：
- 提供干净的依赖安装与运行说明（`requirements.txt` + `pip install` + `pytest`），确保在全新容器内可一键跑通。
- GitHub Actions 增加 test job：PR 必须跑 `pytest`，关键路径（analyze、quota、judgment verify、seo injection、instrument resolver）作为门禁。
- 配合 N1/N3 的新测试纳入门禁。

**验收标准**：全新环境 `pip install -r requirements.txt && pytest` 全绿；PR 未过测试无法合并。

---

## P2 — N5：前端首屏性能（移动端优先）

**类型**：性能（70%+ 流量在手机，首屏 JS 体积直接影响跳出率）

**证据**：`frontend/dist/assets/` 未压缩体积：`vendor-naive-ui` 625K + `vendor-echarts` 506K，两者合计 ~1.1MB（gzip 后约 350–400KB）仍偏重；echarts 在很多页面（如 SSR 落地页转化来的首屏）并非首屏必需。

**改动方案**：
- **echarts 按需/懒加载**：仅在需要 K 线/图表的视图动态 `import()`，移出主 vendor chunk。
- naive-ui 按需引入（`unplugin`），去掉未用组件。
- 校验 SSR 个股页（已是纯 HTML）不要被 SPA 重新拉满 bundle 才可交互——落地页用户应能在不下载全量 JS 时读到结论。
- 接入构建体积预算（`build-metrics/` 已存在，设阈值告警）。

**验收标准**：移动端首屏 JS（gzip）下降明显；Lighthouse 移动端性能分提升；echarts 不在初始 chunk。

---

## P2 — N6：自动「诊断复盘」内容引擎（SEO/GEO 复利）

**类型**：增长（把已验证的判断数据变成可被搜索/AI 引擎收录的新鲜内容）

**文件**：复用 `services/judgment_verifier.py`（已有命中/失败结论）、`services/archive_service.py`（文章归档）、`services/stock_page_service.py`。

**思路**：判断验证闭环已在产出「当时判断 vs 真实走势」的结构化结果。把它定期聚合成**自动生成的复盘文章/榜单**：
- 例：「本周 AI 诊断复盘：命中率、典型命中/打脸案例」「近 30 天结构偏强且后续验证为真的个股」。
- 这些页面天然新鲜、独家、可被抓取，且正好是 GEO 弹药（DeepSeek/豆包/Kimi 被问「AI 诊股准不准」时可引用）。
- 用现有 SSR 管线产出，纳入 sitemap。
- **合规**：以「历史验证统计、仅供参考」呈现，不预测未来收益、不点名荐股。

**验收标准**：定时任务每周生成 ≥1 篇复盘页，进 sitemap 且为真 SSR 正文；数据全部来自真实 verifier 结果。

---

## P3 — N7：可观测性补全

**类型**：运维

**现状**：已有 `analyze_slo_tracker`（首包/分块/完成度），是好底子。

**补强**：
- LLM 调用的**成本/调用次数看板**（按天、按匿名/绑定用户），与 N1 的滥用防护互为印证。
- 关键后台任务（migrations、snapshot refresh、risk scheduler、verification scheduler）失败时有**告警出口**（当前多为 `logger.warning` 吞掉，无外呼）。
- `/api/health` 暴露依赖项（DB、数据源、调度器）健康度。

**验收标准**：有一处可查 analyze 调用量与失败率；后台任务连续失败可触发告警。

---

## P3 — N8：数据层与配置一致性收尾

**类型**：技术债

**点位**：
- 确认上轮 T8（测试库写入生产 `data/` 目录、根目录 0 字节垃圾文件）已清理；若未，按 tmp_path 隔离 + 删除 `CANCELED/ERROR/vue-tsc/frontend@0.0.0`。
- `frontend/dist` 是否仍被 git 跟踪并漂移（上轮发现 `dist/index.html` 未提交改动）——建议产物移出版本库由 CI 构建。
- sqlite 在多 worker/高并发下的写竞争：确认 `DB_ENABLE_WAL` 生效、设置 `busy_timeout`，评估判断/额度等高写表的并发安全。

**验收标准**：`git status` 干净；跑测试不污染 `data/`；高并发写入无 `database is locked` 报错。

---

## 执行顺序建议

1. **N1**（成本漏洞，止血优先）→ 2. **N3 + N4**（把刚修的和核心路径用测试+CI 锁死）→ 3. **N2**（激活留存，最高 ROI 的增长动作）→ 4. **N5 + N6**（性能与内容复利并行）→ 5. **N7 / N8**（运维与技术债收尾）。
