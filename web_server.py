import os
import mimetypes
from dotenv import load_dotenv
load_dotenv()  # Initialize environment variables BEFORE any other local imports

from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks, Cookie
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from services.stock_analyzer_service import StockAnalyzerService
from services.us_stock_service_async import USStockServiceAsync
from services.fund_service_async import FundServiceAsync
from services.search_snapshot_service import SearchSnapshotService
from services.market_overview_service import MarketOverviewService
import asyncio
import httpx
from services.quota_service import QuotaService
from services.invite_service import InviteService
from services.user_service import UserService
from services.verification_scheduler import start_verification_scheduler
from services.risk_stock_scheduler import RiskStockScheduler, start_risk_stock_scheduler
from services.analyze_slo_tracker import analyze_slo_tracker
from auth.dependencies import (
    require_login,
    create_user_token,
    UserContext,
    REQUIRE_LOGIN,
    LOGIN_PASSWORD,
)
from routes import admin, captcha, auth, judgments, quota, invite, anchor, enhancements, watchlists, compare, journal, user_center, risk_stocks

from utils.logger import get_logger
import uvicorn
import json
from datetime import datetime

logger = get_logger()
user_service = UserService()


app = FastAPI(
    title="Stock Scanner API",
    description="异步股票分析API",
    version="1.0.0"
)

# 用户注册接口,到Fastapi应用中 - 区别于上述密码用户体系    
app.include_router(captcha.router)
app.include_router(auth.router) 
app.include_router(judgments.router)
app.include_router(quota.router)
app.include_router(invite.router)
app.include_router(anchor.router)  # Anchor system for email binding
app.include_router(enhancements.router)  # Tushare data enhancements
app.include_router(watchlists.router)    # Watchlists module
app.include_router(compare.router)       # Compare bucketing
app.include_router(journal.router)       # Journal records
app.include_router(user_center.router)   # User center
app.include_router(risk_stocks.router)   # Risk stock list
app.include_router(risk_stocks.admin_router)  # Admin risk stock refresh
app.include_router(admin.router)         # Admin (JWT separate from users)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源，生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],    
    allow_headers=["*"],
)

# 添加验证错误处理器
from fastapi.exceptions import RequestValidationError
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error for {request.url}: {exc.errors()}")
    logger.error(f"Request body: {await request.body()}")
    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": str(await request.body())},
    )

@app.on_event("startup")
async def startup_event():
    """Execute startup tasks"""
    logger.info("Initializing background tasks...")
    
    # Auto-run migrations to ensure DB schema is up to date
    try:
        from scripts.run_migrations import run_migrations
        logger.info("[Startup] Running database migrations...")
        await asyncio.to_thread(run_migrations)
        logger.info("[Startup] Database migrations completed.")
    except Exception as e:
        logger.error(f"[Startup] Failed to run migrations: {e}")
        
    start_verification_scheduler()
    start_risk_stock_scheduler()

    asyncio.create_task(_refresh_search_snapshot_background())
    asyncio.create_task(_refresh_risk_stocks_background())


async def _refresh_risk_stocks_background():
    try:
        await asyncio.to_thread(RiskStockScheduler.refresh_if_missing)
    except Exception as e:
        logger.warning(f"[Startup] Failed to refresh risk stock list: {e}")


async def _refresh_search_snapshot_background():
    try:
        await asyncio.to_thread(search_snapshot_service.refresh_a_share_snapshot)
    except Exception as e:
        logger.warning(f"[Startup] Failed to refresh search snapshot: {e}")

# 初始化异步服务
us_stock_service = USStockServiceAsync()
fund_service = FundServiceAsync()
search_snapshot_service = SearchSnapshotService()
market_overview_service = MarketOverviewService()
SEARCH_TASK_TIMEOUT_SECONDS = 2.5

# 定义请求和响应模型
class AnalyzeRequest(BaseModel):
    stock_codes: List[str]
    market_type: str = "A"

class LoginRequest(BaseModel):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# 用户登录接口
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录接口 — issues a unified JWT"""
    if not REQUIRE_LOGIN:
        token = create_user_token(
            user_id="guest",
            identity_type="login",
            sub="guest",
        )
        return {"access_token": token, "token_type": "bearer"}

    if request.password != LOGIN_PASSWORD:
        logger.warning("登录失败：密码错误")
        raise HTTPException(status_code=401, detail="密码错误")

    token = create_user_token(
        user_id="login_user",
        identity_type="login",
        sub="user",
    )
    logger.info("用户登录成功")
    return {"access_token": token, "token_type": "bearer"}

# 检查用户认证状态
@app.get("/api/check_auth")
async def check_auth(user: UserContext = Depends(require_login)):
    """检查用户认证状态"""
    return {"authenticated": True, "username": user.user_id}

# 获取系统配置
@app.get("/api/config")
async def get_config():
    """返回系统配置信息（含导航外链，供 NavBar 使用）"""
    announcement = os.getenv("ANNOUNCEMENT_TEXT") or ""
    nav_links: List[Dict[str, Any]] = []
    try:
        from services.nav_links_service import NavLinksService

        nav_links = NavLinksService().list_public()
    except Exception as e:
        logger.warning(f"[Config] nav_links 读取失败: {e}")
    # 前端约定：text 对应 label
    nav_for_frontend = [
        {
            "text": row["label"],
            "href": row["href"],
            "target": row.get("target") or "_blank",
            "rel": row.get("rel") or "noopener",
        }
        for row in nav_links
    ]
    return {"announcement": announcement, "nav_links": nav_for_frontend}

# 健康检查（用于 Docker healthcheck + 外部 watchdog）
# 真实健康：覆盖"网站活着但子链路死了"这种月度复发故障
# 任一关键依赖失败 -> 503，Docker healthcheck 会标记 unhealthy，autoheal 自动重启容器
@app.get("/api/health")
async def health():
    import sqlite3
    import shutil

    checks: Dict[str, str] = {}
    overall_ok = True

    # 1) DB 可读：SQLite 锁累积/损坏会让分析归档静默失败
    db_path = os.getenv("DB_PATH", "/app/data/stocks.db")
    def _ping_db():
        conn = sqlite3.connect(db_path, timeout=2.0)
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    try:
        await asyncio.to_thread(_ping_db)
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"fail: {type(e).__name__}: {e}"
        overall_ok = False

    # 2) AI 关键配置存在：仅检测配置就位，不发起真实上游调用，避免把上游故障当成本服务故障
    if os.getenv("API_URL") and os.getenv("API_KEY"):
        checks["ai_config"] = "ok"
    else:
        checks["ai_config"] = "missing"
        overall_ok = False

    try:
        from auth.admin_auth import admin_login_configured

        checks["admin_login"] = "configured" if admin_login_configured() else "not_configured"
    except Exception:
        checks["admin_login"] = "unknown"

    # 3) 数据目录磁盘余量：日志/归档表写入路径阻塞是常见月度复发原因
    try:
        data_dir = os.path.dirname(db_path) or "/app/data"
        usage = shutil.disk_usage(data_dir)
        free_mb = usage.free // (1024 * 1024)
        if free_mb < 100:
            checks["disk"] = f"low: {free_mb}MB free"
            overall_ok = False
        else:
            checks["disk"] = f"ok: {free_mb}MB free"
    except Exception as e:
        checks["disk"] = f"fail: {type(e).__name__}: {e}"
        overall_ok = False

    body = {
        "ok": overall_ok,
        "ts": datetime.utcnow().isoformat() + "Z",
        "checks": checks,
    }
    if not overall_ok:
        return JSONResponse(status_code=503, content=body)
    return body


@app.get("/api/ops/analyze-slo")
async def analyze_slo(user: UserContext = Depends(require_login)):
    """Runtime SLO snapshot for /api/analyze."""
    return analyze_slo_tracker.snapshot()
    
# AI分析股票
@app.post("/api/analyze")
async def analyze(
    request: AnalyzeRequest,
    response: Response,
    user: UserContext = Depends(require_login),
    aguai_ref: Optional[str] = Cookie(None),
):
    slo_sample = analyze_slo_tracker.start()
    try:
        logger.info("开始处理分析请求")
        stock_codes = request.stock_codes
        market_type = request.market_type

        quota_service_instance = QuotaService()
        invite_service_instance = InviteService()
        canonical_user_id = user.user_id
        
        # Quota check for single stock analysis only (batch analysis not subject to quota)
        if len(stock_codes) == 1 and canonical_user_id:
            stock_code = stock_codes[0].strip()
            
            # Check quota before analysis
            allowed, reason, details = quota_service_instance.check_quota(
                user_id=canonical_user_id,
                stock_code=stock_code
            )
            
            if not allowed:
                logger.warning(f"Quota exceeded for user {canonical_user_id}, stock {stock_code}")
                raise HTTPException(
                    status_code=403,
                    detail={
                        "error": "quota_exceeded",
                        "message": details.get("message", "今日分析额度已用完"),
                        "remaining_quota": details.get("remaining_quota", 0),
                        "analyzed_stocks_today": details.get("analyzed_stocks_today", [])
                    }
                )
        
        # 后端再次去重，确保安全
        original_count = len(stock_codes)
        stock_codes = list(dict.fromkeys(stock_codes))  # 保持原有顺序的去重方法
        if len(stock_codes) < original_count:
            logger.info(f"后端去重: 从{original_count}个代码中移除了{original_count - len(stock_codes)}个重复项")
        
        logger.debug(f"接收到分析请求: stock_codes={stock_codes}, market_type={market_type}")
        
        # 创建分析器实例（使用服务端环境变量配置）
        analyzer = StockAnalyzerService()
        
        if not stock_codes:
            logger.warning("未提供股票代码")
            raise HTTPException(status_code=400, detail="请输入代码")
        
        # 定义流式生成器
        async def generate_stream():
            import asyncio
            import time
            try:
                if len(stock_codes) == 1:
                    # 单个股票分析流式处理
                    input_code = stock_codes[0].strip()
                    logger.info(f"开始单股流式分析: {input_code}")

                    # 先发送 init，避免前端在首包前无限等待
                    stock_code_json = json.dumps(input_code)
                    init_message = f'{{"stream_type": "single", "stock_code": {stock_code_json}}}\n'
                    analyze_slo_tracker.mark_first_chunk(slo_sample)
                    analyze_slo_tracker.add_chunk(slo_sample)
                    yield init_message

                    # 再解析代码；解析超时则回退原始代码
                    target_code = input_code
                    try:
                        resolved_code, resolved_name = await asyncio.wait_for(
                            asyncio.to_thread(analyzer.data_provider.resolve_stock_code, input_code, market_type),
                            timeout=8.0,
                        )
                        target_code = resolved_code if resolved_code else input_code
                        logger.info(f"解析结果: {input_code} -> {target_code} ({resolved_name})")
                    except asyncio.TimeoutError:
                        logger.warning(f"解析股票代码超时，使用原始代码继续: {input_code}")
                    except Exception as e:
                        logger.error(f"解析股票代码出错: {e}")
                    
                    logger.debug(f"开始处理股票 {target_code} 的流式响应")
                    chunk_count = 0
                    completed_seen = False

                    # 使用异步生成器，每 10 秒发心跳避免连接被中间网关 idle-close。
                    # 关键：用 shield 保护 __anext__()，不让 wait_for 的超时把它取消掉——
                    # 取消会让 async generator 直接 close（CancelledError 不被 except Exception 捕获），
                    # 之后再 __anext__() 立刻 StopAsyncIteration，AI 流被错杀（这就是之前的 bug）。
                    stream_iter = analyzer.analyze_stock(target_code, market_type, stream=True)
                    stream_idle_timeout_s = 180.0  # 真正的 idle 超时（无任何 chunk 多久才放弃）
                    heartbeat_interval_s = 10.0
                    last_chunk_at = time.monotonic()
                    pending_anext: Optional[asyncio.Task] = None

                    while True:
                        if pending_anext is None:
                            pending_anext = asyncio.ensure_future(stream_iter.__anext__())

                        try:
                            chunk = await asyncio.wait_for(
                                asyncio.shield(pending_anext),
                                timeout=heartbeat_interval_s,
                            )
                            pending_anext = None  # 已 resolve，下个循环新建
                        except StopAsyncIteration:
                            pending_anext = None
                            break
                        except asyncio.TimeoutError:
                            # 内层 __anext__() 还在跑（被 shield 保护），只是这轮没等到。
                            # 检查是否真的 idle 太久；否则发心跳继续等。
                            if time.monotonic() - last_chunk_at >= stream_idle_timeout_s:
                                logger.error(
                                    f"分析流超时（{int(stream_idle_timeout_s)}s无输出）: {target_code}"
                                )
                                pending_anext.cancel()
                                pending_anext = None
                                timeout_payload = json.dumps({
                                    "stock_code": target_code,
                                    "error": "分析超时，请稍后重试",
                                    "status": "timeout",
                                }, ensure_ascii=False)
                                if slo_sample.first_chunk_ms is None:
                                    analyze_slo_tracker.mark_first_chunk(slo_sample)
                                analyze_slo_tracker.add_chunk(slo_sample)
                                analyze_slo_tracker.finish(slo_sample, "timeout")
                                yield timeout_payload + '\n'
                                break

                            heartbeat_payload = json.dumps({
                                "stock_code": target_code,
                                "status": "analyzing",
                                "event": "heartbeat",
                            }, ensure_ascii=False)
                            if slo_sample.first_chunk_ms is None:
                                analyze_slo_tracker.mark_first_chunk(slo_sample)
                            analyze_slo_tracker.add_chunk(slo_sample)
                            yield heartbeat_payload + '\n'
                            continue

                        last_chunk_at = time.monotonic()
                        chunk_count += 1
                        if slo_sample.first_chunk_ms is None:
                            analyze_slo_tracker.mark_first_chunk(slo_sample)
                        analyze_slo_tracker.add_chunk(slo_sample)
                        try:
                            chunk_obj = json.loads(chunk)
                            if chunk_obj.get("status") == "completed":
                                completed_seen = True
                        except Exception:
                            pass
                        yield chunk + '\n'

                    if slo_sample.status == "running":
                        analyze_slo_tracker.finish(slo_sample, "completed")
                    if slo_sample.status == "completed":
                        logger.info(f"股票 {target_code} 流式分析完成，共发送 {chunk_count} 个块")
                    elif slo_sample.status == "timeout":
                        logger.warning(
                            f"股票 {target_code} 流式因超时结束，chunks={chunk_count}"
                        )
                    else:
                        logger.warning(
                            f"股票 {target_code} 流式未正常完成，status={slo_sample.status}, chunks={chunk_count}"
                        )

                    end_payload = json.dumps({
                        "stock_code": target_code,
                        "event": "stream_end",
                        "status": "completed" if completed_seen else slo_sample.status,
                    }, ensure_ascii=False)
                    analyze_slo_tracker.add_chunk(slo_sample)
                    yield end_payload + '\n'

                    # Record analysis consumption
                    if canonical_user_id:
                        quota_service_instance.record_analysis(
                            user_id=canonical_user_id,
                            stock_code=target_code
                        )
                        logger.info(f"Recorded analysis for user {canonical_user_id}, stock {target_code}")
                    
                        if aguai_ref:
                            reward_result = invite_service_instance.check_and_reward_inviter(
                                invitee_id=canonical_user_id,
                                referrer_id=aguai_ref
                            )
                            if reward_result:
                                logger.info(f"Invite reward granted: {reward_result}")

                else:
                    # 批量分析流式处理
                    logger.info(f"开始批量流式分析: {stock_codes}")

                    resolved_codes = []
                    for code in stock_codes:
                        try:
                            r_code, r_name = await asyncio.to_thread(analyzer.data_provider.resolve_stock_code, code.strip(), market_type)
                            resolved_codes.append(r_code if r_code else code.strip())
                        except Exception:
                            resolved_codes.append(code.strip())
                
                    stock_codes_json = json.dumps(resolved_codes)
                    init_message = f'{{"stream_type": "batch", "stock_codes": {stock_codes_json}}}\n'
                    analyze_slo_tracker.mark_first_chunk(slo_sample)
                    analyze_slo_tracker.add_chunk(slo_sample)
                    yield init_message

                    logger.debug(f"开始处理批量股票的流式响应")
                    chunk_count = 0

                    async for chunk in analyzer.scan_stocks(
                        resolved_codes, 
                        min_score=0, 
                        market_type=market_type,
                        stream=True
                    ):
                        chunk_count += 1
                        analyze_slo_tracker.add_chunk(slo_sample)
                        yield chunk + '\n'

                    logger.info(f"批量流式分析完成，共发送 {chunk_count} 个块")
                    analyze_slo_tracker.finish(slo_sample, "completed")
                    end_payload = json.dumps({
                        "stock_codes": resolved_codes,
                        "event": "stream_end",
                        "status": "completed",
                    }, ensure_ascii=False)
                    analyze_slo_tracker.add_chunk(slo_sample)
                    yield end_payload + '\n'
            except Exception as stream_exc:
                logger.error(f"分析流异常: {stream_exc}")
                if slo_sample.status == "running":
                    analyze_slo_tracker.finish(slo_sample, "error")
                error_payload = json.dumps({
                    "error": "分析流异常，请稍后重试",
                    "status": "error",
                }, ensure_ascii=False)
                yield error_payload + '\n'
        
        logger.info("成功创建流式响应生成器")
        return StreamingResponse(generate_stream(), media_type='application/json')
            
    except HTTPException:
        if slo_sample.status == "running":
            analyze_slo_tracker.finish(slo_sample, "error")
        # Re-raise HTTPException (like 403 quota exceeded) without catching
        raise
    except Exception as e:
        if slo_sample.status == "running":
            analyze_slo_tracker.finish(slo_sample, "error")
        error_msg = f"分析时出错: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        raise HTTPException(status_code=500, detail=error_msg)

# 搜索美股代码
@app.get("/api/search_us_stocks")
async def search_us_stocks(keyword: str = "", user: UserContext = Depends(require_login)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        return {"results": search_snapshot_service.search_us_stocks(keyword)}
        
    except Exception as e:
        logger.error(f"搜索美股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索 A 股代码
@app.get("/api/search_a_shares")
async def search_a_shares(keyword: str = "", user: UserContext = Depends(require_login)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")

        return {"results": search_snapshot_service.search_a_shares(keyword)}
        
    except Exception as e:
        logger.error(f"搜索 A 股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索港股代码
@app.get("/api/search_hk_shares")
async def search_hk_shares(keyword: str = "", user: UserContext = Depends(require_login)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        return {"results": search_snapshot_service.search_hk_shares(keyword)}
        
    except Exception as e:
        logger.error(f"搜索港股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 全局搜索接口 (A股, 港股, 美股, 基金)
@app.get("/api/search_global")
async def search_global(keyword: str = "", market_type: str = "ALL", user: UserContext = Depends(require_login)):
    try:
        if not keyword:
            return {"results": []}

        keyword = keyword.strip()
        flat_results = search_snapshot_service.search_global(keyword, market_type=market_type)
        tasks = []

        async def run_search_task(task_name: str, coro):
            try:
                return await asyncio.wait_for(coro, timeout=SEARCH_TASK_TIMEOUT_SECONDS)
            except asyncio.TimeoutError:
                logger.warning(f"[Search] {task_name} timed out for keyword={keyword}")
                return []
            except Exception as e:
                logger.warning(f"[Search] {task_name} failed for keyword={keyword}: {e}")
                return []
        
        # 4. 基金搜寻只在用户显式选择 ETF/LOF 时执行。
        # 避免 ALL 模式每次打字都去远程拉取基金列表，拖慢整个下拉搜索。
        if market_type in ["ETF", "LOF"]:
            async def search_f(m_type):
                funds = await fund_service.search_funds(keyword, m_type)
                return [{"label": f"{s['name']} ({s['symbol']})", "value": s['symbol'], "market": m_type, "name": s['name']} for s in funds[:5]]
            
            tasks.append(run_search_task(market_type, search_f(market_type)))

        # 并发执行所有搜索任务
        search_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 合并结果
        for sublist in search_results:
            if isinstance(sublist, list):
                flat_results.extend(sublist)
        
        return {"results": flat_results}
        
    except Exception as e:
        logger.error(f"全局搜索出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取美股详情
@app.get("/api/us_stock_detail/{symbol}")
async def get_us_stock_detail(symbol: str, user: UserContext = Depends(require_login)):
    try:
        if not symbol:
            raise HTTPException(status_code=400, detail="请提供股票代码")
        
        # 使用异步服务获取详情
        detail = await us_stock_service.get_us_stock_detail(symbol)
        return detail
        
    except Exception as e:
        logger.error(f"获取美股详情时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取基金详情
@app.get("/api/fund_detail/{symbol}")
async def get_fund_detail(symbol: str, market_type: str = "ETF", user: UserContext = Depends(require_login)):
    try:
        if not symbol:
            raise HTTPException(status_code=400, detail="请提供基金代码")
        
        # 使用异步服务获取详情
        detail = await fund_service.get_fund_detail(symbol, market_type)
        return detail
        
    except Exception as e:
        logger.error(f"获取基金详情时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取K线数据
@app.get("/api/kline/{code}")
async def get_kline(code: str, market_type: str = "A", days: int = 100, user: UserContext = Depends(require_login)):
    try:
        analyzer = StockAnalyzerService()
        data = await analyzer.get_kline_data(code, market_type, days)
        return data
    except Exception as e:
        logger.error(f"获取K线数据出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/market-overview")
async def get_market_overview(response: Response, user: UserContext = Depends(require_login)):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    try:
        return await asyncio.to_thread(market_overview_service.get_overview)
    except Exception as e:
        logger.error(f"获取首页指数概览失败: {str(e)}")
        return {"items": [], "updated_at": None}

# 获取文章列表 (分析专栏)
@app.get("/api/articles")
async def get_articles(limit: int = 20, offset: int = 0, q: str = None):
    try:
        analyzer = StockAnalyzerService()
        articles = await analyzer.archive_service.get_articles(limit, offset, q)
        return {"articles": articles}
    except Exception as e:
        logger.error(f"获取文章列表出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取单篇文章详情
@app.get("/api/articles/{article_id}")
async def get_article_detail(article_id: int):
    try:
        analyzer = StockAnalyzerService()
        article = await analyzer.archive_service.get_article_by_id(article_id)
        if not article:
            raise HTTPException(status_code=404, detail="文章不存在")
        return article
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取文章详情出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stock/{stock_code}")
async def stock_landing_page(stock_code: str):
    from services.stock_page_service import StockPageService

    html_content = await StockPageService(base_url="https://aguai.net").render_stock_page(stock_code)
    if not html_content:
        raise HTTPException(status_code=404, detail="股票页面不存在")
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=600",
        },
    )


@app.get("/stocks")
async def stock_index_page(page: int = 1):
    from services.stock_page_service import StockPageService

    html_content = StockPageService(base_url="https://aguai.net").render_stock_index_page(page=page)
    return Response(
        content=html_content,
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=600",
        },
    )


@app.get("/baidu_verify_codeva-m2d0KFsWXV.html")
async def baidu_site_verification():
    return Response(
        content="codeva-m2d0KFsWXV",
        media_type="text/html",
        headers={
            "Cache-Control": "public, max-age=86400",
        },
    )


# 检查是否需要登录
@app.get("/api/need_login")
async def need_login():
    """检查是否需要登录"""
    return {"require_login": REQUIRE_LOGIN}

# 设置静态文件
frontend_dist = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'frontend', 'dist')
if os.path.exists(frontend_dist):
    # 挂载静态文件目录
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, 'assets')), name="assets")
    
    # Catch-all 路由，用于支持 History 模式
    @app.get("/{path_name:path}")
    async def serve_spa(request: Request, path_name: str):
        # 处理SEO和AI优化文件
        if path_name == "sitemap.xml":
            try:
                from services.sitemap_generator import SitemapGenerator
                generator = SitemapGenerator(base_url="https://aguai.net")
                sitemap_content = await generator.generate_sitemap()
                return Response(content=sitemap_content, media_type="application/xml")
            except Exception as e:
                logger.error(f"生成sitemap失败: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        if path_name == "sitemap-core.xml":
            try:
                from services.sitemap_generator import SitemapGenerator
                generator = SitemapGenerator(base_url="https://aguai.net")
                sitemap_content = await generator.generate_core_sitemap()
                return Response(content=sitemap_content, media_type="application/xml")
            except Exception as e:
                logger.error(f"生成 core sitemap 失败: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))

        if path_name == "sitemap-stocks.xml":
            try:
                from services.sitemap_generator import SitemapGenerator
                generator = SitemapGenerator(base_url="https://aguai.net")
                sitemap_content = await generator.generate_stock_sitemap()
                return Response(content=sitemap_content, media_type="application/xml")
            except Exception as e:
                logger.error(f"生成 stock sitemap 失败: {str(e)}")
                raise HTTPException(status_code=500, detail=str(e))
        
        if path_name == "robots.txt":
            robots_content = """# Agu AI 股票分析平台 - Robots.txt
# 允许所有搜索引擎和AI爬虫抓取

User-agent: *
Allow: /
Allow: /analysis
Allow: /analysis/*

# 特别允许AI爬虫
User-agent: GPTBot
Allow: /

User-agent: ChatGPT-User
Allow: /

User-agent: Google-Extended
Allow: /

User-agent: anthropic-ai
Allow: /

User-agent: Claude-Web
Allow: /

User-agent: Bytespider
Allow: /

User-agent: Baiduspider
Allow: /

# Sitemap位置
Sitemap: https://aguai.net/sitemap.xml

# 爬取延迟(毫秒)
Crawl-delay: 1
"""
            return Response(content=robots_content, media_type="text/plain")
        
        if path_name == "llms.txt":
            from services.llms_txt_service import LlmsTxtService

            llms_content = LlmsTxtService(base_url="https://aguai.net").render()
            return Response(content=llms_content, media_type="text/plain")
        
        # 如果是 API 请求，让 FastAPI 的 API 路由处理（通常 API 路由会先匹配）
        if path_name.startswith("api/"):
            raise HTTPException(status_code=404)
        
        # 检查是否是静态文件请求 (简单判断)
        file_path = os.path.join(frontend_dist, path_name)
        if os.path.isfile(file_path):
            media_type = mimetypes.guess_type(file_path)[0] or "application/octet-stream"
            headers = {}
            if path_name.startswith("assets/"):
                headers["Cache-Control"] = "public, max-age=2592000, immutable"
            elif path_name == "index.html":
                headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                headers["Pragma"] = "no-cache"
                headers["Expires"] = "0"
            return Response(content=open(file_path, "rb").read(), media_type=media_type, headers=headers)
            
        # 否则读取 index.html 并进行 SEO 注入
        index_path = os.path.join(frontend_dist, "index.html")
        if not os.path.exists(index_path):
            return Response(content="Frontend not built", status_code=404)
            
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # SEO 动态注入逻辑
        if path_name.startswith("analysis/"):
            try:
                parts = path_name.split("/")
                article_id = parts[1] if len(parts) > 1 else ""

                if article_id and article_id.isdigit():
                    from services.archive_service import ArchiveService
                    from services.article_seo_service import ArticleSeoService

                    archive_service = ArchiveService()
                    article = await archive_service.get_article_by_id(int(article_id))

                    if article:
                        html_content = ArticleSeoService(
                            base_url="https://aguai.net"
                        ).inject_article_page(html_content, article)
            except Exception as e:
                logger.error(f"SEO Injection Error: {str(e)}")
        
        return Response(
            content=html_content,
            media_type="text/html",
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )

    logger.debug(f"前端构建目录挂载成功: {frontend_dist}")
else:
    logger.warning("前端构建目录不存在，仅API功能可用")


if __name__ == '__main__':
    reload_enabled = os.getenv("UVICORN_RELOAD", "false").lower() == "true"
    uvicorn.run("web_server:app", host="0.0.0.0", port=8888, reload=reload_enabled)
