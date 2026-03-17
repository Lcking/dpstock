# User System Phase 1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在保持“游客可先分析”的前提下，上线第一版统一用户体系，让 `watchlist`、判断日记、配额、邀请和用户中心形成可沉淀、可召回的闭环。

**Architecture:** 第一版不做重型登录系统，而是引入统一 `user_id` 作为用户主键，把现有 `anonymous id / aguai_uid / anchor` 统一收敛到身份映射层。前台继续开放分析与专栏，个人资产页通过 `我的` 入口承接，邮箱绑定作为注册完成节点，资产在绑定时自动归并。

**Tech Stack:** FastAPI、SQLite、Pydantic、Vue 3、TypeScript、Naive UI、现有 `anchor / invite / quota / journal / watchlist` 服务。

---

## 稳定性前提

系统已存在真实用户使用，因此 Phase 1 的所有实现必须遵循以下约束：
- 不破坏现有可用入口：`Aguai` Logo、分析专栏、判断日记、实盘策略平台必须先保持可用
- 新能力先叠加，不直接替换旧路径
- 旧身份、旧数据、旧链接优先兼容，不做一次性激进迁移
- 减少认知打扰：命名、位置、交互变化尽量渐进
- 任何可能影响现有用户资产的改动，都要先验证兼容路径，再推进收口
## Phase 1 范围边界

### 必须实现
- 统一用户主键与身份映射
- 顶部导航分阶段演进：
  - 当前阶段保持：`Aguai Logo（首页） / 分析专栏 / 判断日记 / 实盘策略平台`
  - 移除：`配查查`
  - 用户体系页完善后再引入：`我的`
- `我的` 下拉承接：`我的观察 / 判断日记 / 用户中心 / 额度与邀请`
- 邮箱绑定完成注册
- `watchlist`、判断日记、配额、邀请、提醒状态统一归到用户身份
- 资产动作触发绑定引导
- 用户中心工作台首页

### 暂不实现
- 手机号登录
- 微信登录
- 复杂会员体系
- 完整个人资料编辑页
- 旧数据全量回填脚本
- 专栏文章“用户私有化”改造

## 导航与页面口径

### 顶部导航顺序
按阶段定义：

当前线上阶段：
1. `Aguai` Logo（首页）
2. 分析专栏
3. 判断日记
4. 实盘策略平台（外部链接）

用户体系 Phase 1 完成后：
1. `Aguai` Logo（首页）
2. 专栏
3. 我的
4. 实盘策略平台（外部链接）

说明：
- `我的` 不提前上线
- `判断日记` 在当前阶段继续保持显性入口
- 后续收编进 `我的`

### `我的` 下拉固定项
- 我的观察
- 判断日记
- 用户中心
- 额度与邀请

### 页面职责
- `我的观察`：观察池，负责收藏、跟踪、批量分析，不承担复盘职责
- `判断日记`：判断与复盘池，负责结构前提、验证周期、复盘记录
- `用户中心`：工作台首页，负责状态汇总与引导下一步动作

## 实施顺序

### Task 1: 统一用户模型

**Files:**
- Create: `migrations/008_create_user_tables.sql`
- Create: `schemas/user.py`
- Create: `services/user_service.py`
- Test: `tests/test_user_identity_flow.py`

**Step 1: Write the failing test**

```python
def test_create_user_from_email_binding():
    service = UserService()
    user_id = service.get_or_create_user_by_identity(
        identity_type="email_anchor",
        identity_value="anchor_xxx"
    )
    user = service.get_user(user_id)
    assert user["user_id"] == user_id
    assert user["status"] == "active"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_user_identity_flow.py::test_create_user_from_email_binding -v`

Expected: FAIL，因为 `UserService` 或用户表尚不存在。

**Step 3: Write minimal implementation**

实现最小用户模型：
- `users`
- `user_identities`

推荐字段：
- `users.user_id`
- `users.primary_email`
- `users.email_verified`
- `users.display_name`
- `users.profile_completed`
- `users.is_public_analysis_enabled`
- `users.status`
- `users.created_at`
- `users.last_active_at`

- `user_identities.identity_type`
- `user_identities.identity_value`
- `user_identities.user_id`
- `user_identities.is_primary`
- `user_identities.verified_at`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_user_identity_flow.py::test_create_user_from_email_binding -v`

Expected: PASS

**Step 5: Commit**

```bash
git add migrations/008_create_user_tables.sql schemas/user.py services/user_service.py tests/test_user_identity_flow.py
git commit -m "feat: add unified user identity model"
```

### Task 2: 统一身份解析与绑定迁移

**Files:**
- Modify: `routes/anchor.py`
- Modify: `routes/journal.py`
- Modify: `routes/watchlists.py`
- Modify: `routes/quota.py`
- Modify: `routes/invite.py`
- Modify: `services/anchor_service.py`
- Modify: `services/user_service.py`
- Test: `tests/test_user_identity_flow.py`

**Step 1: Write the failing test**

```python
def test_bind_email_merges_anonymous_cookie_and_anchor_to_same_user():
    service = UserService()
    user_id = service.bind_email_identity(
        anonymous_id="anon_1",
        cookie_uid="cookie_1",
        anchor_id="anchor_1",
        email="test@example.com"
    )
    assert service.resolve_identity("anonymous", "anon_1") == user_id
    assert service.resolve_identity("cookie_uid", "cookie_1") == user_id
    assert service.resolve_identity("email_anchor", "anchor_1") == user_id
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_user_identity_flow.py::test_bind_email_merges_anonymous_cookie_and_anchor_to_same_user -v`

Expected: FAIL

**Step 3: Write minimal implementation**

实现：
- `UserService.resolve_request_user(...)`
- `UserService.bind_email_identity(...)`
- `UserService.merge_identities(...)`

并在以下入口接入统一解析：
- `routes/anchor.py`
- `routes/journal.py`
- `routes/watchlists.py`
- `routes/quota.py`
- `routes/invite.py`

要求：
- 先兼容旧身份
- 不破坏匿名使用
- 绑定时自动把匿名资产归并到 `user_id`

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_user_identity_flow.py -v`

Expected: 新增身份合并用例 PASS

**Step 5: Commit**

```bash
git add routes/anchor.py routes/journal.py routes/watchlists.py routes/quota.py routes/invite.py services/anchor_service.py services/user_service.py tests/test_user_identity_flow.py
git commit -m "feat: unify request identity resolution"
```

### Task 3: 把 `watchlist` 改成“游客可试用、绑定后长期保存”

**Files:**
- Modify: `routes/watchlists.py`
- Modify: `services/watchlist/service.py`
- Modify: `frontend/src/components/Watchlist/WatchlistList.vue`
- Modify: `frontend/src/components/StockAnalysisApp.vue`
- Modify: `frontend/src/services/api.ts`
- Test: `tests/test_watchlist_integration.py`

**Step 1: Write the failing test**

```python
def test_guest_watchlist_items_are_marked_temporary_until_bound():
    result = watchlist_service.create_watchlist(
        user_id="guest_user_1",
        data=WatchlistCreate(name="临时观察")
    )
    assert result.user_id == "guest_user_1"
```

以及前端交互预期：
- 游客可看到“加入观察”
- 游客可创建临时观察列表
- 进入 `watchlist` 时看到“绑定后长期保存”提示

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_watchlist_integration.py -v`

Expected: 现有行为与“临时观察 + 绑定提示”不一致

**Step 3: Write minimal implementation**

后端：
- 不阻止游客创建观察列表
- 在接口响应中增加 `is_temporary` 或等效状态

前端：
- 搜索与分析页保留“加入观察”
- `watchlist` 页面增加游客提示条
- 在批量分析/保存资产等关键动作上引导绑定

**Step 4: Run test to verify it passes**

Run:
- `pytest tests/test_watchlist_integration.py -v`
- `npm run build`

Expected: PASS / Build OK

**Step 5: Commit**

```bash
git add routes/watchlists.py services/watchlist/service.py frontend/src/components/Watchlist/WatchlistList.vue frontend/src/components/StockAnalysisApp.vue frontend/src/services/api.ts tests/test_watchlist_integration.py
git commit -m "feat: add guest watchlist trial flow"
```

### Task 4: 让判断日记成为“绑定后强资产”

**Files:**
- Modify: `routes/journal.py`
- Modify: `services/journal/service.py`
- Modify: `frontend/src/components/AnalysisV1Display.vue`
- Modify: `frontend/src/components/Journal/JournalList.vue`
- Test: `tests/test_verification_integration.py`

**Step 1: Write the failing test**

```python
def test_bound_user_sees_same_journal_records_after_identity_merge():
    migrated = journal_service.migrate_user_records("anon_1", "user_1")
    assert migrated >= 0
```

并新增预期：
- 游客保存判断时允许创建临时资产
- 绑定后这些资产进入统一用户名下
- 日记列表支持按统一 `user_id` 展示

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_verification_integration.py -v`

Expected: FAIL 或用例缺失

**Step 3: Write minimal implementation**

后端：
- 判断日记统一按 `user_id` 查询
- 保持旧数据兼容归并

前端：
- 保存判断后提示“绑定后可长期追踪与复盘”
- 日记页强化“待复盘”感知

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_verification_integration.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add routes/journal.py services/journal/service.py frontend/src/components/AnalysisV1Display.vue frontend/src/components/Journal/JournalList.vue tests/test_verification_integration.py
git commit -m "feat: align journal assets with unified users"
```

### Task 5: 搭建用户中心 MVP 工作台

**Files:**
- Create: `frontend/src/components/UserCenter/UserCenterPage.vue`
- Create: `frontend/src/components/UserCenter/UserOverviewCards.vue`
- Modify: `frontend/src/router/index.ts`
- Modify: `frontend/src/components/NavBar.vue`
- Modify: `frontend/src/services/api.ts`
- Create: `routes/user_center.py`
- Modify: `web_server.py`
- Test: `frontend` build validation

**Step 1: Write the failing test**

前端最小验收标准：
- 存在 `/me` 或等效路由
- 导航顺序为：首页、分析、专栏、我的
- `我的` 下拉可进入：
  - 我的观察
  - 判断日记
  - 用户中心
  - 额度与邀请

**Step 2: Run test to verify it fails**

Run: `npm run build`

Expected: 当前没有用户中心页面与导航结构

**Step 3: Write minimal implementation**

用户中心首页只放：
- 绑定状态
- 当前额度
- 我的观察数量
- 待复盘数量
- 最近判断
- 邀请入口

注意：
- 当前导航先不强上 `我的`
- 名称用 `我的`
- 不用“会员主页”
- 移动端必须支持点击展开，不依赖 hover
- 保留 `实盘策略平台` 外部按钮
- 移除 `配查查`

**Step 4: Run test to verify it passes**

Run: `npm run build`

Expected: Build OK

**Step 5: Commit**

```bash
git add frontend/src/components/UserCenter/UserCenterPage.vue frontend/src/components/UserCenter/UserOverviewCards.vue frontend/src/router/index.ts frontend/src/components/NavBar.vue frontend/src/services/api.ts routes/user_center.py web_server.py
git commit -m "feat: add user center workbench"
```

### Task 6: 整合额度与邀请为统一用户资产

**Files:**
- Modify: `services/quota_service.py`
- Modify: `services/invite_service.py`
- Modify: `routes/quota.py`
- Modify: `routes/invite.py`
- Modify: `frontend/src/components/QuotaStatus.vue`
- Modify: `frontend/src/components/InviteDialog.vue`
- Test: `tests/test_user_identity_flow.py`

**Step 1: Write the failing test**

```python
def test_quota_and_invite_are_resolved_by_user_id():
    status = quota_service.get_quota_status("user_1")
    assert "remaining_quota" in status
```

加一个邀请关系断言：
- 同一用户多身份进入时，邀请记录不重复裂变

**Step 2: Run test to verify it fails**

Run: `pytest tests/test_user_identity_flow.py -v`

Expected: FAIL

**Step 3: Write minimal implementation**

要求：
- 配额最终按 `user_id` 解析
- 邀请关系最终按 `user_id` 解析
- 保留现有 `aguai_uid` 兼容逻辑，但收口到统一用户

**Step 4: Run test to verify it passes**

Run: `pytest tests/test_user_identity_flow.py -v`

Expected: PASS

**Step 5: Commit**

```bash
git add services/quota_service.py services/invite_service.py routes/quota.py routes/invite.py frontend/src/components/QuotaStatus.vue frontend/src/components/InviteDialog.vue tests/test_user_identity_flow.py
git commit -m "feat: align quota and invite with unified users"
```

### Task 7: 增加绑定引导与召回入口

**Files:**
- Modify: `frontend/src/components/StockAnalysisApp.vue`
- Modify: `frontend/src/components/StockCard.vue`
- Modify: `frontend/src/components/AnalysisV1Display.vue`
- Modify: `frontend/src/components/Watchlist/WatchlistList.vue`
- Modify: `frontend/src/components/NavBar.vue`
- Test: `frontend` build validation

**Step 1: Write the failing test**

最小产品验收标准：
- 第一次加入观察时出现绑定价值提示
- 第一次保存判断时出现绑定价值提示
- 免费额度用尽时引导进入绑定/邀请

**Step 2: Run test to verify it fails**

Run: `npm run build`

Expected: 当前无统一文案和转化路径

**Step 3: Write minimal implementation**

统一文案：
- 绑定邮箱，保存你的观察资产
- 绑定后可持续追踪复盘
- 绑定后资产不会因换设备或清缓存而丢失
- 绑定后可解锁邀请奖励与更多额度

**Step 4: Run test to verify it passes**

Run: `npm run build`

Expected: Build OK

**Step 5: Commit**

```bash
git add frontend/src/components/StockAnalysisApp.vue frontend/src/components/StockCard.vue frontend/src/components/AnalysisV1Display.vue frontend/src/components/Watchlist/WatchlistList.vue frontend/src/components/NavBar.vue
git commit -m "feat: add progressive binding prompts"
```

### Task 8: 最终验证与文档收尾

**Files:**
- Modify: `docs/plans/2026-03-09-user-system-information-architecture-design.md`
- Modify: `README.md`
- Test: `tests/test_user_identity_flow.py`
- Test: `tests/test_watchlist_integration.py`
- Test: `tests/test_verification_integration.py`

**Step 1: Run backend verification**

Run:
- `pytest tests/test_user_identity_flow.py -v`
- `pytest tests/test_watchlist_integration.py -v`
- `pytest tests/test_verification_integration.py -v`
- `python -m compileall routes services web_server.py`

Expected: PASS / compile OK

**Step 2: Run frontend verification**

Run:
- `npm run build`

Expected: Build OK

**Step 3: Smoke-check product paths**

手动验证：
- 游客进入首页可直接分析
- 游客可加入观察，但会看到“绑定后长期保存”提示
- 绑定邮箱后资产仍在
- `我的` 下拉路径可进入观察、日记、用户中心、额度与邀请
- 判断日记与 `watchlist` 不互相替代

**Step 4: Commit**

```bash
git add docs/plans/2026-03-09-user-system-information-architecture-design.md docs/plans/2026-03-09-user-system-phase-1-implementation-plan.md README.md
git commit -m "docs: finalize phase 1 user system rollout plan"
```

## 推荐执行顺序总结
建议严格按以下顺序推进：

1. 统一用户模型
2. 统一身份解析与迁移
3. `watchlist` 游客试用 + 绑定后沉淀
4. 判断日记并入统一用户资产
5. 搭建用户中心工作台
6. 整合额度与邀请
7. 加入绑定引导与召回入口
8. 做完整验证与文档收尾

## 风险提醒
- 不要在 Phase 1 同时引入手机号、微信、小程序账户
- 不要把专栏文章强行绑定到个人资产
- 不要把 `watchlist` 和判断日记合并成一个页面
- 不要先做复杂资料页，再做资产沉淀
- 不要过早把尚未完善的“我的”入口推到线上导航

## 成功标准
- 游客仍能顺畅分析
- 用户在形成资产时被自然引导绑定
- 绑定后 `watchlist`、判断日记、配额、邀请统一沉淀到 `user_id`
- 用户中心成为“资产工作台”，而不是空资料页
- 市场 -> 分析 -> 观察 -> 判断 -> 复盘 形成稳定闭环
