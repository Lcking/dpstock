# Agu AI 产品增长与信任闭环优化路线图

> **For Claude:** REQUIRED SUB-SKILL: Use `test-driven-development` before implementation. Execute this plan task-by-task, update the progress log after each shipped task, and do not start implementation work until the current task has clear tests and acceptance criteria.

**Goal:** 把 Agu AI 从“前端 SPA 诊股工具”推进成“可被搜索发现、可解释、可验证、可留存”的股票分析系统。

**Architecture:** 先修复可发现性与基础索引链路，再补诊股结果的信任表达，最后扩展自选/组合与提醒。所有公开增长页优先采用服务端 HTML 首包输出；交互型能力继续由 Vue SPA 承载。

**Tech Stack:** FastAPI, Vue 3, Vite, Naive UI, SQLite, existing archive/journal/watchlist services, pytest contract tests, `npm run build`.

---

## 0. 当前诊断结论

这份路线图基于外部诊断反馈和当前代码/线上行为核对，先记录事实，避免后续跑偏。

### 已确认问题

1. `https://aguai.net/sitemap.xml` 当前线上返回 500。
2. `https://aguai.net/stock/600519` 返回的是 SPA 首页壳，不是真正的个股正文 HTML。
3. 前端路由里没有 `/stock/:code`，后端也没有独立的个股 HTML 落地页。
4. 当前 sitemap 只包含 `/`、`/analysis`、`/analysis/{id}`，没有个股长尾 URL。
5. 文章页已有部分 meta/JSON-LD 注入，但不是完整服务端正文渲染。
6. 站内已完成部分局部闭环：判断日记系统初判、复盘统计、邀请拉新漏斗和排查工具。但它们还没有统一服务于“诊股信任与留存”主线。

### 核心判断

“能抓取页面”不等于“会索引、有排名”。现在最缺的不是再加更多 meta，而是：

- 稳定可发现的 URL。
- 服务端首包唯一正文。
- 唯一 title/description/canonical。
- sitemap 正常。
- 站内内链。
- 内容不是重复首页壳。
- 风险提示、数据时间戳和解释层提升可信度。

---

## 1. 工作原则

1. **先记录，再执行。** 每个任务开工前必须在本文件明确状态、目标、验收标准。
2. **一次只做一个任务包。** 不同时改 SEO、结果页、判断日记和自选股，避免散打。
3. **TDD。** 新行为先写失败测试，再实现。
4. **频繁提交。** 每个任务包独立提交，方便线上验证和回滚。
5. **线上验证后再推进下一项。** 尤其是 SEO/GEO 任务，需要部署后用 `curl`、sitemap、搜索控制台或站点搜索验证。
6. **合规优先。** 不写“买入/卖出/强烈推荐/稳赚”等荐股措辞。

---

## 2. 优先级总览

| 优先级 | 主题 | 目标 | 为什么先做 |
| --- | --- | --- | --- |
| P0 | SEO 基础链路修复 | sitemap 正常、个股页不再返回首页壳 | 当前增长链路硬故障 |
| P0 | 个股静态 HTML 落地页 MVP | `/stock/{code}` 首包可抓取 | 长尾 SEO/GEO 的入口 |
| P1 | 诊股结果页信任重构 | 一句话结论 + 为什么这么判 + 数据时间 | 提升转化与信任 |
| P1 | 判断日记详情收口 | 不进复盘也能看到系统初判 | 延续已完成的判断闭环 |
| P1 | 自选股健康度总览 | 单股诊断走向组合管理 | 增强留存和差异化 |
| P2 | 风险触发提醒 | 从低频诊股到高频提醒 | 增加日活和回访 |
| P2 | GEO 问答块与内容规模化 | 让 AI 搜索更容易引用 | 长期增长 |

---

## 3. 执行任务拆分

### Task 1: 修复 sitemap 500

**Priority:** P0

**Goal:** `https://aguai.net/sitemap.xml` 稳定返回 200，并包含当前可访问公开页面。

**Files:**
- Modify: `services/sitemap_generator.py`
- Modify if needed: `web_server.py`
- Test: `tests/test_frontend_seo_contract.py`

**Steps:**

1. 写失败测试：`/sitemap.xml` 返回 200，content-type 是 XML，至少包含 `/`、`/analysis`。
2. 增加异常定位测试：当文章表为空或字段缺失时 sitemap 不能 500。
3. 修复 `SitemapGenerator.generate_sitemap()` 的异常路径。
4. 本地运行：
   - `python -m pytest tests/test_frontend_seo_contract.py::test_sitemap_and_robots_are_accessible_for_crawlers -q`
5. 构建不一定需要，除非动前端。
6. 部署后验证：
   - `curl -i https://aguai.net/sitemap.xml`

**Acceptance Criteria:**
- 线上 `/sitemap.xml` 返回 200。
- XML 中没有空 URL、非法日期、500 堆栈。
- robots.txt 仍指向 `https://aguai.net/sitemap.xml`。

**Commit message:** `fix(seo): make sitemap generation resilient`

---

### Task 2: 个股 SEO 落地页 MVP

**Priority:** P0

**Goal:** `/stock/{code}` 返回服务端 HTML 正文，不依赖前端 JS 渲染。

**Files:**
- Create: `services/stock_page_service.py`
- Modify: `web_server.py`
- Test: `tests/test_stock_seo_pages.py`

**Initial Scope:**
- 先支持 A 股热门股票 MVP。
- 最低要求支持 `600519`、`000001`、`300750` 等固定热门列表。
- 不做全市场动态生成，不做 SSR 框架迁移。

**Page Content Requirements:**
- `<title>`：`贵州茅台(600519) AI诊股分析_结构趋势风险解读 - Agu AI`
- `<meta name="description">`
- `<h1>`：`贵州茅台(600519) AI诊股分析`
- 正文包含：
  - 股票名称和代码。
  - 平台能力说明。
  - AI 诊股包含哪些维度：结构、趋势、相对强弱、风险线索。
  - 数据更新时间。
  - 风险提示。
  - “去实时分析”链接，指向 `/?code=600519&market=A` 或类似入口。
- JSON-LD：
  - `WebPage`
  - `FinancialProduct` 或更保守的 `Thing`
  - `Organization`

**Steps:**

1. 写失败测试：
   - `GET /stock/600519` 返回 200。
   - 响应文本包含 `600519`、`贵州茅台`、`AI诊股`、`风险提示`。
   - 响应不应只是 SPA 首页壳。
2. 实现 `StockPageService`：
   - 固定热门股票字典。
   - HTML escape。
   - 生成完整 HTML。
3. 在 `web_server.py` catch-all 之前或 catch-all 内优先处理 `stock/{code}`。
4. 运行测试：
   - `python -m pytest tests/test_stock_seo_pages.py -q`
5. 部署后验证：
   - `curl -sS https://aguai.net/stock/600519 | rg "贵州茅台|600519|风险提示"`

**Acceptance Criteria:**
- `web_fetch` 能看到个股正文。
- 搜索引擎不再把 `/stock/600519` 当首页重复页。
- 页面措辞不构成投资建议。

**Commit message:** `feat(seo): add stock landing page html`

---

### Task 3: sitemap 加入个股落地页

**Priority:** P0

**Goal:** sitemap 输出热门个股 URL，搜索引擎能稳定发现。

**Files:**
- Modify: `services/sitemap_generator.py`
- Reuse/Create: `services/stock_page_service.py`
- Test: `tests/test_stock_seo_pages.py`

**Steps:**

1. 写失败测试：
   - `/sitemap.xml` 包含 `https://aguai.net/stock/600519`。
2. `StockPageService` 暴露热门股票列表。
3. `SitemapGenerator` 加入 `/stock/{code}`。
4. 控制数量：第一版 20-100 个，不全量生成。
5. 运行：
   - `python -m pytest tests/test_frontend_seo_contract.py tests/test_stock_seo_pages.py -q`

**Acceptance Criteria:**
- sitemap 中包含个股 URL。
- sitemap 仍返回 200。
- 每个 URL 都是真实可访问页面。

**Commit message:** `feat(seo): include stock pages in sitemap`

---

### Task 4: 站内内链入口

**Priority:** P0

**Goal:** 首页/分析结果/文章页能自然链接到个股 SEO 页，避免孤岛页。

**Files:**
- Modify: `frontend/src/components/StockAnalysisApp.vue`
- Modify: `frontend/src/components/ArticleDetail.vue`
- Modify: `frontend/src/components/AnalysisList.vue`
- Test: `tests/test_frontend_seo_contract.py`

**Steps:**

1. 写前端契约测试：
   - 文章详情中存在 `/stock/${article.stock_code}` 链接。
   - 分析列表卡片中存在个股页入口。
2. 在文章详情股票信息处增加“查看个股 AI 诊股页”。
3. 在首页底部或市场快照附近增加热门个股入口，第一版可以很克制。

**Acceptance Criteria:**
- 个股落地页不是孤岛。
- 不影响现有 SPA 使用。

**Commit message:** `feat(seo): link stock landing pages`

---

### Task 5: 诊股结果页顶部一句话结论

**Priority:** P1

**Goal:** 用户一眼知道结论，但不触碰荐股合规边界。

**Files:**
- Modify: `frontend/src/components/AnalysisV1Display.vue`
- Modify if needed: `schemas/analysis_v1.py`
- Test: `tests/test_journal_frontend_contract.py` or new `tests/test_analysis_frontend_contract.py`

**Desired Output Example:**

`中期结构偏强，短期波动加大，重点观察 MA20 与量能变化。`

**Steps:**

1. 写契约测试：结果页存在“一句话结论”区域。
2. 从现有 Analysis V1 字段组合摘要，不改 AI 输出协议为第一选择。
3. 保证不出现“买入/卖出/推荐”等词。

**Acceptance Criteria:**
- 小白能先看一句话。
- 专业用户仍能看原详细内容。

**Commit message:** `feat(analysis): add plain-language summary`

---

### Task 6: 诊股结果“为什么这么判”

**Priority:** P1

**Goal:** 从“AI 给分”升级为“AI 帮我读盘”。

**Files:**
- Modify: `frontend/src/components/AnalysisV1Display.vue`
- Modify: `frontend/src/components/AiScorePanel.vue`
- Modify: `frontend/src/components/EnhancementCards.vue`
- Test: `tests/test_analysis_frontend_contract.py`

**Content Blocks:**
- 结构依据。
- 趋势依据。
- 相对强弱依据。
- 量能/风险依据。
- 数据缺失提示。

**Acceptance Criteria:**
- 每个核心判断都有可展开证据。
- 用户能区分“结论”和“依据”。

**Commit message:** `feat(analysis): explain score evidence`

---

### Task 7: 判断详情页显示系统初判

**Priority:** P1

**Goal:** due 记录不进复盘弹窗，也能看到机器初判。

**Files:**
- Modify: `frontend/src/components/Journal/JournalDetailDialog.vue`
- Test: `tests/test_journal_frontend_contract.py`

**Steps:**

1. 写契约测试：
   - `JournalDetailDialog.vue` 使用 `evaluation_preview`。
   - 显示 `系统初判`、`actual_path`、`summary`。
2. 实现详情页展示。
3. 保持 reviewed 记录显示最终 `review.system_evaluation`。

**Acceptance Criteria:**
- 用户查看详情时即可理解系统判断。
- 复盘弹窗仍用于提交人工总结。

**Commit message:** `feat(journal): show evaluation in detail`

---

### Task 8: 复盘学习总结字段

**Priority:** P1

**Goal:** 让复盘从“提交备注”变成“沉淀交易学习”。

**Files:**
- Modify: `services/journal/service.py`
- Modify: `frontend/src/components/Journal/JournalReviewDialog.vue`
- Modify: `frontend/src/types/journal.ts`
- Test: `tests/test_journal_condition_evaluator.py`

**Field Proposal:**

```json
{
  "notes": "复盘备注",
  "lesson": "这次学到了什么"
}
```

**Acceptance Criteria:**
- 提交复盘时可填写学习总结。
- 老记录兼容。
- 后续统计可扩展。

**Commit message:** `feat(journal): capture review lesson`

---

### Task 9: 自选股健康度总览

**Priority:** P1

**Goal:** 从单股诊断走向组合/自选诊断。

**Files:**
- Modify: `services/watchlist/service.py`
- Modify: `routes/watchlists.py`
- Modify: `frontend/src/components/Watchlist/WatchlistList.vue`
- Test: watchlist integration tests or new contract tests.

**Acceptance Criteria:**
- 自选列表显示整体健康度。
- 显示强势、弱势、风险、待观察数量。
- 不直接建议买卖。

**Commit message:** `feat(watchlist): add health overview`

---

### Task 10: 风险触发提醒 MVP

**Priority:** P2

**Goal:** 把低频诊股转化为高频风险提醒。

**Files:**
- Modify: `services/watchlist/service.py`
- Modify: `services/verification_scheduler.py`
- Modify: `frontend/src/stores/notification.ts`
- Modify: `frontend/src/components/NavBar.vue`

**Acceptance Criteria:**
- 自选股出现关键风险信号时生成站内提醒。
- 第一版只做站内，不做邮件/微信。

**Commit message:** `feat(watchlist): notify risk triggers`

---

### Task 11: GEO 问答块

**Priority:** P2

**Goal:** 让 AI 搜索更容易引用 Agu AI 的页面。

**Files:**
- Modify: `services/stock_page_service.py`
- Test: `tests/test_stock_seo_pages.py`

**Required FAQ:**
- `{stock_name}股票怎么看？`
- `{stock_code}当前 AI 诊断关注什么？`
- `主要风险是什么？`
- `数据更新时间是什么？`

**Acceptance Criteria:**
- HTML 中有 FAQ 结构。
- JSON-LD 可选加入 `FAQPage`。

**Commit message:** `feat(seo): add stock page faq blocks`

---

## 4. 不做事项

这些不是否定价值，而是为了避免当前阶段跑偏。

1. 暂不做全站 SSR/Next/Nuxt 迁移。
2. 暂不做全市场数千个个股页。
3. 暂不做买卖建议型文案。
4. 暂不做邮件/微信推送。
5. 暂不做复杂运营后台大屏。
6. 暂不新增重型数据依赖，优先复用现有 `ArchiveService`、数据 provider 和热门股票静态表。

---

## 5. 进度记录

每完成一个任务，更新这里。

| 日期 | 任务 | 状态 | 提交 | 线上验证 |
| --- | --- | --- | --- | --- |
| 2026-06-16 | 路线图创建 | done | pending | n/a |
| 2026-06-16 | Task 1: sitemap 500 修复 | local_done | pending | pending |
| 2026-06-16 | Task 2: 个股 SEO HTML MVP | local_done | pending | pending |
| 2026-06-16 | Task 2 补丁: 样式/历史文章/CTA定位 | local_done | pending | pending |
| 2026-06-16 | Task 2 补丁: 热门池扩展至 127 个/主站导航 | local_done | pending | pending |
|  | Task 3: sitemap 加入个股 URL | pending |  |  |
|  | Task 4: 站内内链入口 | pending |  |  |
|  | Task 5: 诊股一句话结论 | pending |  |  |
|  | Task 6: 为什么这么判 | pending |  |  |
|  | Task 7: 判断详情显示系统初判 | pending |  |  |
|  | Task 8: 复盘学习总结 | pending |  |  |
|  | Task 9: 自选股健康度总览 | pending |  |  |
|  | Task 10: 风险触发提醒 | pending |  |  |
|  | Task 11: GEO 问答块 | pending |  |  |

---

## 6. 推荐下一步

从 P0 开始，严格按顺序推进：

1. Task 1：修复 sitemap 500。
2. Task 2：个股 SEO HTML MVP。
3. Task 3：sitemap 加入个股 URL。
4. Task 4：站内内链入口。

这四个任务形成一个完整的 SEO 基础闭环：

`可访问 → 可抓正文 → 可发现 → 有内链`

完成后，再进入 P1 的信任和留存体验。
