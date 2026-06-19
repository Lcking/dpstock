# 代码诊断与任务规划（交付 Cursor 执行）

> 生成日期：2026-06-19
> 范围：基于实际代码审查（非 SPA 盲猜）。后端约 63.7K 行 Python（FastAPI）+ Vue3 前端。
> 阅读对象：Cursor / 执行工程师。每个任务卡含「文件位置 / 证据 / 改动方案 / 验收标准」，可直接执行，无需重新排查。

---

## 0. 现状结论（已落地的部分，勿重复造轮子）

以下能力已确认实现且质量可用，本次**不需要重做**，仅在相关任务里复用：

- `/stock/{code}` 个股页**真·服务端渲染**：canonical、OG、`WebPage` + `FAQPage` JSON-LD、可见正文 H1。实现于 `services/stock_page_service.py`。
- `sitemap.xml` / `robots.txt` / `llms.txt` 已生成（`web_server.py` catch-all + `services/sitemap_generator.py`）。
- 判断验证闭环已实现：`services/judgment_verifier.py`（上涨 / 下跌 / 盘整三类验证）+ `services/judgment_service.py`，并有 condition quality 排行榜（commit `daa050a`）。
- 自选股命中风险列表的提醒：`services/watchlist_risk_alert_service.py`。

---

## 任务优先级总览

| 优先级 | 任务 | 类型 | 预估 |
|---|---|---|---|
| P0 | T1 文章页 meta/OG 注入失效 | Bug | 0.5 天 |
| P1 | T2 文章页正文 SSR 化 | SEO/功能 | 1–2 天 |
| P1 | T3 诊断数据时间戳 + 数据源标注 | 可信度 | 0.5 天 |
| P1 | T6 合规措辞收口（去"推荐/买卖"） | 合规 | 0.5–1 天 |
| P2 | T4 SSR 个股页覆盖扩到全 A 股 | 增长 | 2–3 天 |
| P2 | T5 公开"AI 诊断准确率"（信任 + GEO） | 增长/功能 | 1–2 天 |
| P3 | T7 llms.txt 动态化 | SEO/GEO | 0.5 天 |
| P3 | T8 工程卫生：测试 DB 隔离 + 垃圾文件清理 | 技术债 | 0.5 天 |
| P3 | T9 自选组合健康度评分 | 功能 | 2–3 天 |

---

## P0 — T1：修复文章页 meta / OG 注入静默失效

**类型**：Bug（正在持续浪费抓取预算，止血优先）

**文件**：`web_server.py`，`serve_spa()` 内 `if path_name.startswith("analysis/")` 分支（约 870–950 行）。

**证据（已复现）**：注入逻辑用字符串替换：
```python
html_content.replace('content="免费的A股、港股、美股、ETF智能AI分析平台系统"', ...)
html_content.replace('content="Stock Scanner -免费股市AI分析工具"', ...)
html_content.replace('content="基于AI的股票量化分析平台，支持A股、港股、美股批量分析。"', ...)
```
逐条比对 `frontend/dist/index.html`：这三个目标字符串**全部不存在**（现文案已改为 "Agu AI 提供 A 股、港股、美股与 ETF 的智能股票分析…"）。
- `<title>` 替换目标 `免费AI在线股票分析平台系统 - 智能诊股助手_软件` → 仍存在，注入成功。
- 因此**只有 title 和 JSON-LD 生效**；meta description、og:title、og:description、twitter:* 全部静默回退到通用站点文案。

**影响**：sitemap 中 priority 0.8 的全部文章页，搜索结果摘要与社交分享卡片完全雷同，长尾点击率受损。

**改动方案（推荐：占位符注入，杜绝再次失效）**：
1. 在 `frontend/index.html` 的 head 中为可注入字段加占位符注释，例如：
   - title 行、description、og:title、og:description、og:url、twitter:title、twitter:description 各留一个稳定锚点（如 `<!--SSR:DESC-->`）或统一用一个 `<!--SSR_HEAD-->` 占位块，由后端整体替换。
2. `serve_spa()` 改为对占位符做替换，不再依赖具体中文文案串。
3. 同步处理 `og:url` / `canonical`：当前文章页未改写 canonical，应指向 `/analysis/{id}`。

**验收标准**：
- `curl -s https://<host>/analysis/<已知文章ID>` 返回的 HTML 中，`<meta name="description">`、`og:title`、`og:description`、`canonical` 均为该文章专属内容，且与首页不同。
- 新增防回归测试 `tests/test_seo_injection.py`：构造一篇文章，断言注入后的 HTML 包含文章专属 description 且不含通用站点文案；并断言占位符已被全部替换（HTML 中不再残留 `<!--SSR`）。

---

## P1 — T2：文章页正文 SSR 化

**类型**：SEO / 功能

**文件**：`web_server.py` `serve_spa()` 的 `analysis/` 分支；可复用 `services/archive_service.py`、`services/stock_page_service.py` 的渲染风格。

**问题**：`/stock/{code}` 已是真 SSR（正文进首屏），但 `/analysis/{id}` 仍返回 SPA 空壳，正文靠 JS 渲染。会跑 JS 的 Google 尚可，但 GPTBot / 豆包 / Kimi 抓取与百度常拿不到正文。文章是站内内容量最大的长尾池，浪费可惜。

**改动方案**：
- 为 `/analysis/{id}` 增加 `<noscript>` 或首屏静态正文块：服务端取文章核心字段（结论段、综合评分、结构/趋势描述、关键价位、免责声明），渲染成可被抓取的语义化 HTML 注入首屏，SPA 加载后再接管。
- 可直接复用 `stock_page_service` 的 CSS 与结构骨架，保持视觉一致。
- 注意正文长度与 `articleBody` JSON-LD 一致性（当前 JSON-LD 已截 `content[:500]`）。

**验收标准**：
- 关闭 JS（或 `curl`）访问文章页，能看到文章标题 + 结论 + 评分 + 关键数据 + 免责声明的纯 HTML。
- Lighthouse / 手动检查：首屏 HTML 中包含文章正文关键词。

---

## P1 — T3：诊断结果标注数据时间戳与数据源

**类型**：可信度

**文件**：`services/ai_analyzer.py`（生成分析处）、`services/stock_analyzer_service.py`（组装返回处）、`services/stock_page_service.py`（SSR 页顶部）。

**问题**：当前诊断输出**无任何数据时间戳 / 数据源标注**（已 grep 确认 `ai_analyzer.py` 无 `timestamp / 数据时间 / as_of`）。金融场景"数据截至何时"比结论本身更影响可信度。

**改动方案**：
- 在分析结果数据结构中增加 `data_as_of`（行情数据最后交易时间）与 `data_source`（A 股 / 港股 / 美股各自来源）。
- 前端诊断结果页顶部、SSR 个股页结论区显示：`数据截至 YYYY-MM-DD HH:mm · 来源：xxx`。

**验收标准**：诊断结果页与 `/stock/{code}` 页面均显示数据时间与来源；接口响应包含 `data_as_of` 字段。

---

## P1 — T6：合规措辞收口（移除"推荐 / 买入 / 卖出"指向性表述）

**类型**：合规（国内证券投资咨询资质红线）

**文件**：
- `services/stock_scorer.py` `get_recommendation()`（约 106–127 行）：当前返回 `强烈推荐 / 推荐 / 谨慎推荐 / 观望 / 不推荐 / 强烈不推荐`。
- `services/ai_analyzer.py` `_extract_recommendation()`（约 749–768 行）：产出 `买入 / 卖出 / 持有`（疑似旧逻辑，仍可能进数据/页面）。

**问题**：对**点名个股**使用"推荐 / 不推荐 / 买入 / 卖出"贴近"荐股"红线，无投顾资质时风险高于中性的"结构偏强 / 偏弱"。

**改动方案**：
- 将 `get_recommendation()` 的标签改为**非指向性**描述，如：`结构强 / 结构偏强 / 中性 / 结构偏弱 / 结构弱`，或纯风险等级。保留 score 数值不变，仅改文案层。
- 审计 `_extract_recommendation()` 是否仍被消费（已确认主流程走 `scorer.get_recommendation`）；若无用则删除，若有用同样去指向化。
- 全站搜索并替换前端展示中的"建议买入/卖出/推荐"类文案；保留并强化"仅供参考、不构成投资建议"。

**验收标准**：
- grep 全仓 `买入|卖出|推荐` 在**面向用户输出路径**上无指向性荐股表述（测试代码、内部注释不限）。
- 每个诊断结果与 SSR 页均含显式免责声明。

---

## P2 — T4：SSR 个股页覆盖扩展到全 A 股

**类型**：增长（长尾 SEO 最大杠杆）

**文件**：`services/stock_page_service.py`（`HOT_STOCK_LIST` 硬编码 128 只 + `get_stock` 仅查热门表）；`services/sitemap_generator.py`（仅列热门 + 归档文章）。

**问题**：长尾落地页只兑现了 128 只热门股 + 有归档文章的股票。全 A 股（5000+）的长尾入口未建立。

**改动方案**：
- 用全市场股票清单（可来自现有 tushare 服务 `services/tushare/`）作为 `get_stock` 的兜底数据源，使任意合法 A 股代码都能渲染 SSR 页（无文章时展示"暂无沉淀分析 + 实时诊断入口"，已有空态文案可复用）。
- sitemap 分片：A 股数量大，需按 `sitemap_index` 拆分（每文件 ≤ 5 万 URL / ≤ 50MB），并对无内容页适当降低 priority 或延后收录，避免低质页拖累整站权重。
- 注意：**先完成 T1（meta 修复）再放量**，否则等于放大浪费抓取预算。

**验收标准**：
- 任意主板/创业板/科创板合法代码访问 `/stock/{code}` 返回 200 且含该股名称/代码的 SSR 正文。
- sitemap 通过 index 形式覆盖全量且文件体积合规。

**依赖**：建议在 T1 之后执行。

---

## P2 — T5：公开"AI 诊断准确率"（信任资产 + GEO 弹药）

**类型**：增长 / 功能

**文件**：复用 `services/judgment_verifier.py` + `services/judgment_service.py`（已有验证结果与排行榜）；新增聚合统计接口 + 前端展示 + SSR 页/llms.txt 引用。

**思路**：判断验证闭环已在跑，但数据藏在内部。把"历史诊断命中率"做成**公开可见**的信任资产：
- 聚合维度：整体命中率、按条件质量（已有 condition quality 排行）、按市场（A/港/美）、近 30/90 天。
- 展示位：首页信任区、`/stock/{code}` 个股页结论区、`llms.txt`（见 T7）。
- 这是同时服务信任钩子、独家 SEO 内容、GEO 被引用（"aguai 诊断准确率多少" → 有可引数据）的三合一动作。
- **注意合规**：以"历史验证统计、仅供参考"措辞呈现，不暗示未来收益。

**验收标准**：新增 `/api/judgment/accuracy-stats` 类接口；首页与个股页展示聚合准确率；数据来源于真实 verifier 结果而非写死。

---

## P3 — T7：llms.txt 动态化

**类型**：SEO / GEO

**文件**：`web_server.py` catch-all 中 `llms.txt` 分支（当前为硬编码字符串，写死"最后更新 2025-12-18"，数据源写新浪/雅虎）。

**改动方案**：改为动态生成——动态时间戳、真实数据源、热门个股入口列表、并引用 T5 的准确率数据。

**验收标准**：`curl /llms.txt` 的更新时间为当前日期；包含真实数据源与个股入口。

---

## P3 — T8：工程卫生

**类型**：技术债

**证据**：
- `data/` 目录堆积 **188 个 `test_*.db-shm/wal`** 残留——测试把临时库写进了**生产数据目录**（与 `stocks.db` 同级）。
- 根目录 0 字节垃圾文件：`CANCELED`、`ERROR`、`vue-tsc`、`frontend@0.0.0`（疑似 shell 重定向误建）。均未被 git 跟踪。
- `frontend/dist` 被 git 跟踪且已漂移（`git status` 显示 `dist/index.html` 未提交改动）——构建产物入库易出事故。

**改动方案**：
- 测试库改用 `tempfile.mkdtemp()` / pytest `tmp_path`，杜绝写入 `data/`；并加 fixture teardown 清理。
- 删除根目录垃圾文件；`.gitignore` 补充对应模式。
- 评估将 `frontend/dist` 移出 git 跟踪（改由 CI 构建产出），或至少固化提交流程。

**验收标准**：跑完整测试套件后 `data/` 不新增 `test_*.db*`；`git status` 干净；垃圾文件已删。

---

## P3 — T9：自选组合健康度评分

**类型**：功能（差异化空白）

**文件**：复用 `services/watchlist/`、`services/watchlist_risk_alert_service.py`、`services/stock_scorer.py`。

**思路**：自选股 + 单股评分 + 风险提醒基建都已具备，差一步合成**组合维度**：对用户整个自选篮子给"健康度评分"（结构强弱分布、命中风险列表数量、集中度/行业暴露提示），输出"谁该关注、谁有风险信号"。同类工具多止步单股，组合维度是明确空白。

**验收标准**：自选页新增组合健康度卡片；含篮子整体评分 + 风险标的高亮 + 一句话结论。

---

## 执行顺序建议

1. **T1**（止血，半天）→ 2. **T6**（合规，低成本高风险规避）→ 3. **T3**（可信度）→ 4. **T2**（文章页 SSR）→ 5. **T4**（全 A 股放量，必须在 T1 之后）→ 6. **T5 + T7**（信任/GEO 组合拳）→ 7. **T8 / T9**（技术债与新功能，可并行排期）。
