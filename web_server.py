import os
from dotenv import load_dotenv
load_dotenv()  # Initialize environment variables BEFORE any other local imports

from fastapi import FastAPI, Request, Response, Depends, HTTPException, BackgroundTasks, Cookie
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Generator
from services.stock_analyzer_service import StockAnalyzerService
from services.us_stock_service_async import USStockServiceAsync
from services.fund_service_async import FundServiceAsync
import asyncio
import httpx
from services.anchor_service import AnchorService
from services.quota_service import QuotaService
from services.invite_service import InviteService
from services.verification_scheduler import start_verification_scheduler
from routes import captcha, auth, judgments, quota, invite, anchor, admin, enhancements, watchlists, compare, journal

from utils.logger import get_logger
import uvicorn
import json
import secrets
from datetime import datetime, timedelta
from jose import JWTError, jwt

# 获取日志器
logger = get_logger()

# JWT相关配置
SECRET_KEY = os.getenv("JWT_SECRET_KEY", secrets.token_hex(32))
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # Token过期时间一周

LOGIN_PASSWORD = os.getenv("LOGIN_PASSWORD", "")
print(LOGIN_PASSWORD)

# 是否需要登录
REQUIRE_LOGIN = bool(LOGIN_PASSWORD.strip())


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
app.include_router(admin.router)   # Admin overview
app.include_router(enhancements.router)  # Tushare data enhancements
app.include_router(watchlists.router)    # Watchlists module
app.include_router(compare.router)       # Compare bucketing
app.include_router(journal.router)       # Journal records

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

# 初始化异步服务
us_stock_service = USStockServiceAsync()
fund_service = FundServiceAsync()

# 定义请求和响应模型
class AnalyzeRequest(BaseModel):
    stock_codes: List[str]
    market_type: str = "A"

class LoginRequest(BaseModel):
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

# 自定义依赖项，在REQUIRE_LOGIN=False时不要求token
class OptionalOAuth2PasswordBearer(OAuth2PasswordBearer):
    async def __call__(self, request: Request) -> Optional[str]:
        if not REQUIRE_LOGIN:
            return None
        try:
            return await super().__call__(request)
        except HTTPException:
            if not REQUIRE_LOGIN:
                return None
            raise

# 使用自定义的依赖项
optional_oauth2_scheme = OptionalOAuth2PasswordBearer(tokenUrl="login")

# 创建访问令牌
def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 验证令牌
async def verify_token(token: Optional[str] = Depends(optional_oauth2_scheme)):
    # 如果未设置密码，则不需要验证
    if not REQUIRE_LOGIN:
        return "guest"
        
    # 如果没有token且不需要登录，返回guest
    if token is None and not REQUIRE_LOGIN:
        return "guest"
        
    credentials_exception = HTTPException(
        status_code=401,
        detail="无效的认证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # 如果需要登录但没有token，抛出异常
    if token is None:
        raise credentials_exception
        
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        return username
    except JWTError:
        raise credentials_exception

# 用户登录接口
@app.post("/api/login")
async def login(request: LoginRequest):
    """用户登录接口"""
    # 如果未设置密码，表示不需要登录
    if not REQUIRE_LOGIN:
        access_token = create_access_token(data={"sub": "guest"})
        return {"access_token": access_token, "token_type": "bearer"}
        
    if request.password != LOGIN_PASSWORD:
        logger.warning("登录失败：密码错误")
        raise HTTPException(status_code=401, detail="密码错误")
    
    # 创建访问令牌
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "user"}, expires_delta=access_token_expires
    )
    logger.info("用户登录成功")
    return {"access_token": access_token, "token_type": "bearer"}

# 检查用户认证状态
@app.get("/api/check_auth")
async def check_auth(username: str = Depends(verify_token)):
    """检查用户认证状态"""
    return {"authenticated": True, "username": username}

# 获取系统配置
@app.get("/api/config")
async def get_config():
    """返回系统配置信息"""
    return {
        'announcement': os.getenv('ANNOUNCEMENT_TEXT') or ''
    }
    
# AI分析股票
@app.post("/api/analyze")
async def analyze(
    request: AnalyzeRequest, 
    response: Response,
    username: str = Depends(verify_token),
    aguai_uid: Optional[str] = Cookie(None),
    aguai_ref: Optional[str] = Cookie(None)
):
    try:
        logger.info("开始处理分析请求")
        stock_codes = request.stock_codes
        market_type = request.market_type
        
        # Initialize quota service
        quota_service_instance = QuotaService()
        invite_service_instance = InviteService()
        
        # Quota check for single stock analysis only (batch analysis not subject to quota)
        if len(stock_codes) == 1 and aguai_uid:
            stock_code = stock_codes[0].strip()
            
            # Check quota before analysis
            allowed, reason, details = quota_service_instance.check_quota(
                user_id=aguai_uid,
                stock_code=stock_code
            )
            
            if not allowed:
                logger.warning(f"Quota exceeded for user {aguai_uid}, stock {stock_code}")
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
            
            if len(stock_codes) == 1:
                # 单个股票分析流式处理
                input_code = stock_codes[0].strip()
                logger.info(f"开始单股流式分析: {input_code}")
                
                # 在发送init消息前解析代码
                try:
                    resolved_code, resolved_name = await asyncio.to_thread(analyzer.data_provider.resolve_stock_code, input_code, market_type)
                    target_code = resolved_code if resolved_code else input_code
                    logger.info(f"解析结果: {input_code} -> {target_code} ({resolved_name})")
                except Exception as e:
                    logger.error(f"解析股票代码出错: {e}")
                    target_code = input_code

                stock_code_json = json.dumps(target_code)
                init_message = f'{{"stream_type": "single", "stock_code": {stock_code_json}}}\n'
                yield init_message
                
                logger.debug(f"开始处理股票 {target_code} 的流式响应")
                chunk_count = 0
                
                # 使用异步生成器
                async for chunk in analyzer.analyze_stock(target_code, market_type, stream=True):
                    chunk_count += 1
                    yield chunk + '\n'
                
                logger.info(f"股票 {target_code} 流式分析完成，共发送 {chunk_count} 个块")
                
                # Record analysis consumption (only for single stock with aguai_uid)
                if aguai_uid:
                    quota_service_instance.record_analysis(
                        user_id=aguai_uid,
                        stock_code=target_code
                    )
                    logger.info(f"Recorded analysis for user {aguai_uid}, stock {target_code}")
                    
                    # Check and reward inviter if applicable
                    if aguai_ref:
                        reward_result = invite_service_instance.check_and_reward_inviter(
                            invitee_id=aguai_uid,
                            referrer_id=aguai_ref
                        )
                        if reward_result:
                            logger.info(f"Invite reward granted: {reward_result}")

            else:
                # 批量分析流式处理
                logger.info(f"开始批量流式分析: {stock_codes}")
                
                # 解析所有代码
                resolved_codes = []
                for code in stock_codes:
                    try:
                        r_code, r_name = await asyncio.to_thread(analyzer.data_provider.resolve_stock_code, code.strip(), market_type)
                        resolved_codes.append(r_code if r_code else code.strip())
                    except:
                        resolved_codes.append(code.strip())
                
                stock_codes_json = json.dumps(resolved_codes)
                init_message = f'{{"stream_type": "batch", "stock_codes": {stock_codes_json}}}\n'
                yield init_message
                
                logger.debug(f"开始处理批量股票的流式响应")
                chunk_count = 0
                
                # 使用异步生成器
                async for chunk in analyzer.scan_stocks(
                    resolved_codes, 
                    min_score=0, 
                    market_type=market_type,
                    stream=True
                ):
                    chunk_count += 1
                    yield chunk + '\n'
                
                logger.info(f"批量流式分析完成，共发送 {chunk_count} 个块")
        
        logger.info("成功创建流式响应生成器")
        return StreamingResponse(generate_stream(), media_type='application/json')
            
    except HTTPException:
        # Re-raise HTTPException (like 403 quota exceeded) without catching
        raise
    except Exception as e:
        error_msg = f"分析时出错: {str(e)}"
        logger.error(error_msg)
        logger.exception(e)
        raise HTTPException(status_code=500, detail=error_msg)

# 搜索美股代码
@app.get("/api/search_us_stocks")
async def search_us_stocks(keyword: str = "", username: str = Depends(verify_token)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        # 直接使用异步服务的异步方法
        results = await us_stock_service.search_us_stocks(keyword)
        # 为前端统一格式，将 symbol 映射为 symbol
        return {"results": results}
        
    except Exception as e:
        logger.error(f"搜索美股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索 A 股代码
@app.get("/api/search_a_shares")
async def search_a_shares(keyword: str = "", username: str = Depends(verify_token)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        analyzer = StockAnalyzerService()
        stock_list = await asyncio.to_thread(analyzer.data_provider.get_a_share_list)
        
        # 模糊匹配搜索
        keyword_lower = keyword.lower()
        results = []
        for stock in stock_list:
            if (keyword_lower in stock['code'].lower() or 
                keyword_lower in stock['name'].lower() or 
                keyword_lower in stock['pinyin'].lower()):
                results.append({
                    'symbol': stock['code'],
                    'name': stock['name'],
                    'market': 'A'
                })
                if len(results) >= 10:
                    break
                    
        return {"results": results}
        
    except Exception as e:
        logger.error(f"搜索 A 股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 搜索港股代码
@app.get("/api/search_hk_shares")
async def search_hk_shares(keyword: str = "", username: str = Depends(verify_token)):
    try:
        if not keyword:
            raise HTTPException(status_code=400, detail="请输入搜索关键词")
        
        analyzer = StockAnalyzerService()
        stock_list = await asyncio.to_thread(analyzer.data_provider.get_hk_share_list)
        
        # 模糊匹配搜索
        keyword_lower = keyword.lower()
        results = []
        for stock in stock_list:
            if (keyword_lower in stock['code'].lower() or 
                keyword_lower in stock['name'].lower() or 
                keyword_lower in stock['pinyin'].lower()):
                results.append({
                    'symbol': stock['code'],
                    'name': stock['name'],
                    'market': 'HK'
                })
                if len(results) >= 10:
                    break
                    
        return {"results": results}
        
    except Exception as e:
        logger.error(f"搜索港股代码时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 全局搜索接口 (A股, 港股, 美股, 基金)
@app.get("/api/search_global")
async def search_global(keyword: str = "", market_type: str = "ALL", username: str = Depends(verify_token)):
    try:
        if not keyword:
            return {"results": []}
        
        keyword_lower = keyword.lower()
        tasks = []
        
        # 1. A 股搜寻 (如果 market_type 为 ALL 或 A)
        if market_type in ["ALL", "A"]:
            async def search_a():
                analyzer = StockAnalyzerService()
                stock_list = await asyncio.to_thread(analyzer.data_provider.get_a_share_list)
                res = []
                for s in stock_list:
                    if keyword_lower in s['code'].lower() or keyword_lower in s['name'].lower() or keyword_lower in s['pinyin'].lower():
                        res.append({"label": f"{s['name']} ({s['code']})", "value": s['code'], "market": "A", "name": s['name']})
                        if len(res) >= 5: break
                return res
            tasks.append(search_a())

        # 2. 港股搜寻 (如果 market_type 为 ALL 或 HK)
        if market_type in ["ALL", "HK"]:
            async def search_hk():
                analyzer = StockAnalyzerService()
                stock_list = await asyncio.to_thread(analyzer.data_provider.get_hk_share_list)
                res = []
                for s in stock_list:
                    if keyword_lower in s['code'].lower() or keyword_lower in s['name'].lower() or keyword_lower in s['pinyin'].lower():
                        res.append({"label": f"{s['name']} ({s['code']})", "value": s['code'], "market": "HK", "name": s['name']})
                        if len(res) >= 5: break
                return res
            tasks.append(search_hk())

        # 3. 美股搜寻 (如果 market_type 为 ALL 或 US)
        if market_type in ["ALL", "US"]:
            async def search_us():
                us_stocks = await us_stock_service.search_us_stocks(keyword)
                return [{"label": f"{s['name']} ({s['symbol']})", "value": s['symbol'], "market": "US", "name": s['name']} for s in us_stocks[:5]]
            tasks.append(search_us())

        # 4. 基金搜寻 (如果 market_type 为 ALL, ETF 或 LOF)
        if market_type in ["ALL", "ETF", "LOF"]:
            async def search_f(m_type):
                funds = await fund_service.search_funds(keyword, m_type)
                return [{"label": f"{s['name']} ({s['symbol']})", "value": s['symbol'], "market": m_type, "name": s['name']} for s in funds[:5]]
            
            if market_type == "ALL":
                tasks.append(search_f("ETF"))
                tasks.append(search_f("LOF"))
            else:
                tasks.append(search_f(market_type))

        # 并发执行所有搜索任务
        search_results = await asyncio.gather(*tasks)
        
        # 合并结果
        flat_results = [item for sublist in search_results for item in sublist]
        
        return {"results": flat_results}
        
    except Exception as e:
        logger.error(f"全局搜索出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 获取美股详情
@app.get("/api/us_stock_detail/{symbol}")
async def get_us_stock_detail(symbol: str, username: str = Depends(verify_token)):
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
async def get_fund_detail(symbol: str, market_type: str = "ETF", username: str = Depends(verify_token)):
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
async def get_kline(code: str, market_type: str = "A", days: int = 100, username: str = Depends(verify_token)):
    try:
        analyzer = StockAnalyzerService()
        data = await analyzer.get_kline_data(code, market_type, days)
        return data
    except Exception as e:
        logger.error(f"获取K线数据出错: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

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
            llms_content = """# Agu AI 股票分析平台

## 网站简介
Agu AI 是一个基于人工智能的股票分析平台,为投资者提供A股、港股、美股的智能分析服务。

## 主要功能
- 实时股票技术分析
- AI深度投资建议
- 多维度评分系统(均线、RSI、MACD、成交量、波动率)
- 专业分析文章归档

## 技术指标
- 移动平均线(MA5, MA20, MA60)
- 相对强弱指标(RSI)
- MACD指标
- 成交量分析
- 波动率评估

## 评分体系
- 均线系统: 30分
- RSI指标: 20分
- MACD指标: 20分
- 成交量: 20分
- 波动率: 10分
总分: 100分

## 推荐等级
- 80分以上: 强烈推荐
- 60-79分: 推荐
- 40-59分: 观望
- 40分以下: 不推荐

## 数据来源
- A股数据: 新浪财经API
- 港股数据: 雅虎财经API
- 美股数据: 雅虎财经API

## 分析频率
- 实时分析: 按需
- 文章更新: 每日
- 数据更新: 实时

## 联系方式
- 网站: https://aguai.net
- 邮箱: support@aguai.net

## 免责声明
本平台提供的分析仅供参考,不构成投资建议。股市有风险,投资需谨慎。

## 最后更新
2025-12-18
"""
            return Response(content=llms_content, media_type="text/plain")
        
        # 如果是 API 请求，让 FastAPI 的 API 路由处理（通常 API 路由会先匹配）
        if path_name.startswith("api/"):
            raise HTTPException(status_code=404)
        
        # 检查是否是静态文件请求 (简单判断)
        file_path = os.path.join(frontend_dist, path_name)
        if os.path.isfile(file_path):
            return Response(content=open(file_path, "rb").read(), media_type="application/octet-stream")
            
        # 否则读取 index.html 并进行 SEO 注入
        index_path = os.path.join(frontend_dist, "index.html")
        if not os.path.exists(index_path):
            return Response(content="Frontend not built", status_code=404)
            
        with open(index_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        # SEO 动态注入逻辑
        if path_name.startswith("analysis/"):
            try:
                # 尝试从路径中提取文章 ID
                parts = path_name.split("/")
                article_id = parts[1] if len(parts) > 1 else ""
                
                if article_id and article_id.isdigit():
                    from services.archive_service import ArchiveService
                    import json
                    archive_service = ArchiveService()
                    article = await archive_service.get_article_by_id(int(article_id))
                    
                    if article:
                        title = f"{article['title']} - Agu AI"
                        
                        # 尝试从 Analysis V1 JSON 提取描述
                        desc = ""
                        try:
                            content_str = article['content']
                            # 移除可能的 markdown 代码块标记
                            if '```json' in content_str:
                                content_str = content_str.split('```json')[1].split('```')[0].strip()
                            elif '```' in content_str:
                                content_str = content_str.split('```')[1].split('```')[0].strip()
                            
                            content_json = json.loads(content_str)
                            # 如果是 Analysis V1 格式，从 trend_description 提取
                            if 'structure_snapshot' in content_json and 'trend_description' in content_json['structure_snapshot']:
                                trend_desc = content_json['structure_snapshot']['trend_description']
                                desc = f"{article['stock_name']}({article['stock_code']})当日行情深度分析，综合评分 {article['score']}。{trend_desc[:150]}..."
                            else:
                                # 降级：使用简短描述
                                desc = f"{article['stock_name']}({article['stock_code']})当日行情深度分析，综合评分 {article['score']}。"
                        except (json.JSONDecodeError, KeyError, IndexError):
                            # 如果不是 JSON 或解析失败，使用原文本
                            desc = f"{article['stock_name']}({article['stock_code']})当日行情深度分析，综合评分 {article['score']}。{article['content'][:150]}..."
                        
                        # 注入标题
                        html_content = html_content.replace("<title>免费AI在线股票分析平台系统 - 智能诊股助手_软件</title>", f"<title>{title}</title>")
                        
                        # 注入描述和关键词 (OG 标签也更新)
                        html_content = html_content.replace('content="免费的A股、港股、美股、ETF智能AI分析平台系统"', f'content="{desc}"')
                        html_content = html_content.replace('content="Stock Scanner -免费股市AI分析工具"', f'content="{title}"')
                        html_content = html_content.replace('content="基于AI的股票量化分析平台，支持A股、港股、美股批量分析。"', f'content="{desc}"')
                        
                        # 构建 JSON-LD 结构化数据
                        json_ld = {
                            "@context": "https://schema.org",
                            "@type": "Article",
                            "headline": article['title'],
                            "description": desc,
                            "datePublished": article.get('publish_date', article.get('created_at', '')),
                            "author": {
                                "@type": "Organization",
                                "name": "Agu AI",
                                "url": "https://aguai.net"
                            },
                            "publisher": {
                                "@type": "Organization",
                                "name": "Agu AI 股票分析平台",
                                "logo": {
                                    "@type": "ImageObject",
                                    "url": "https://aguai.net/favicon.ico"
                                }
                            },
                            "about": {
                                "@type": "FinancialProduct",
                                "name": article['stock_name'],
                                "identifier": article['stock_code'],
                                "category": f"{article['market_type']}股"
                            },
                            "keywords": f"{article['stock_name']}, {article['stock_code']}, 股票分析, AI分析, {article['market_type']}股",
                            "articleBody": article['content'][:500]
                        }
                        
                        # 注入 JSON-LD 到 head 标签中
                        json_ld_script = f'\n<script type="application/ld+json">\n{json.dumps(json_ld, ensure_ascii=False, indent=2)}\n</script>\n</head>'
                        html_content = html_content.replace('</head>', json_ld_script)
                        
            except Exception as e:
                logger.error(f"SEO Injection Error: {str(e)}")
        
        return Response(content=html_content, media_type="text/html")

    logger.info(f"前端构建目录挂载成功: {frontend_dist}")
else:
    logger.warning("前端构建目录不存在，仅API功能可用")


if __name__ == '__main__':
    uvicorn.run("web_server:app", host="0.0.0.0", port=8888, reload=True)