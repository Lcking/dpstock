import html
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional

from services.archive_service import ArchiveService


@dataclass(frozen=True)
class StockPageInfo:
    code: str
    name: str
    market: str


class StockPageService:
    """Generate crawlable stock landing pages for SEO/GEO entry traffic."""

    HOT_STOCK_LIST: List[StockPageInfo] = [
        StockPageInfo(code="600519", name="贵州茅台", market="A"),
        StockPageInfo(code="000001", name="平安银行", market="A"),
        StockPageInfo(code="300750", name="宁德时代", market="A"),
        StockPageInfo(code="601318", name="中国平安", market="A"),
        StockPageInfo(code="600036", name="招商银行", market="A"),
        StockPageInfo(code="000858", name="五粮液", market="A"),
        StockPageInfo(code="002594", name="比亚迪", market="A"),
        StockPageInfo(code="601899", name="紫金矿业", market="A"),
        StockPageInfo(code="600900", name="长江电力", market="A"),
        StockPageInfo(code="000333", name="美的集团", market="A"),
        StockPageInfo(code="002475", name="立讯精密", market="A"),
        StockPageInfo(code="600276", name="恒瑞医药", market="A"),
        StockPageInfo(code="600030", name="中信证券", market="A"),
        StockPageInfo(code="601088", name="中国神华", market="A"),
        StockPageInfo(code="600887", name="伊利股份", market="A"),
        StockPageInfo(code="601398", name="工商银行", market="A"),
        StockPageInfo(code="601288", name="农业银行", market="A"),
        StockPageInfo(code="601988", name="中国银行", market="A"),
        StockPageInfo(code="601939", name="建设银行", market="A"),
        StockPageInfo(code="600941", name="中国移动", market="A"),
        StockPageInfo(code="601857", name="中国石油", market="A"),
        StockPageInfo(code="600028", name="中国石化", market="A"),
        StockPageInfo(code="601628", name="中国人寿", market="A"),
        StockPageInfo(code="601166", name="兴业银行", market="A"),
        StockPageInfo(code="600000", name="浦发银行", market="A"),
        StockPageInfo(code="601328", name="交通银行", market="A"),
        StockPageInfo(code="600309", name="万华化学", market="A"),
        StockPageInfo(code="002415", name="海康威视", market="A"),
        StockPageInfo(code="000651", name="格力电器", market="A"),
        StockPageInfo(code="300760", name="迈瑞医疗", market="A"),
        StockPageInfo(code="688981", name="中芯国际", market="A"),
        StockPageInfo(code="688041", name="海光信息", market="A"),
        StockPageInfo(code="688111", name="金山办公", market="A"),
        StockPageInfo(code="688012", name="中微公司", market="A"),
        StockPageInfo(code="688008", name="澜起科技", market="A"),
        StockPageInfo(code="688256", name="寒武纪", market="A"),
        StockPageInfo(code="600104", name="上汽集团", market="A"),
        StockPageInfo(code="000725", name="京东方A", market="A"),
        StockPageInfo(code="002352", name="顺丰控股", market="A"),
        StockPageInfo(code="002714", name="牧原股份", market="A"),
        StockPageInfo(code="600031", name="三一重工", market="A"),
        StockPageInfo(code="601012", name="隆基绿能", market="A"),
        StockPageInfo(code="600438", name="通威股份", market="A"),
        StockPageInfo(code="002027", name="分众传媒", market="A"),
        StockPageInfo(code="002230", name="科大讯飞", market="A"),
        StockPageInfo(code="300059", name="东方财富", market="A"),
        StockPageInfo(code="600050", name="中国联通", market="A"),
        StockPageInfo(code="601985", name="中国核电", market="A"),
        StockPageInfo(code="601668", name="中国建筑", market="A"),
        StockPageInfo(code="601669", name="中国电建", market="A"),
        StockPageInfo(code="601800", name="中国交建", market="A"),
        StockPageInfo(code="601390", name="中国中铁", market="A"),
        StockPageInfo(code="601186", name="中国铁建", market="A"),
        StockPageInfo(code="601919", name="中远海控", market="A"),
        StockPageInfo(code="600019", name="宝钢股份", market="A"),
        StockPageInfo(code="600585", name="海螺水泥", market="A"),
        StockPageInfo(code="601600", name="中国铝业", market="A"),
        StockPageInfo(code="600111", name="北方稀土", market="A"),
        StockPageInfo(code="600010", name="包钢股份", market="A"),
        StockPageInfo(code="601225", name="陕西煤业", market="A"),
        StockPageInfo(code="600188", name="兖矿能源", market="A"),
        StockPageInfo(code="000063", name="中兴通讯", market="A"),
        StockPageInfo(code="000100", name="TCL科技", market="A"),
        StockPageInfo(code="000792", name="盐湖股份", market="A"),
        StockPageInfo(code="000568", name="泸州老窖", market="A"),
        StockPageInfo(code="000596", name="古井贡酒", market="A"),
        StockPageInfo(code="002304", name="洋河股份", market="A"),
        StockPageInfo(code="600809", name="山西汾酒", market="A"),
        StockPageInfo(code="603288", name="海天味业", market="A"),
        StockPageInfo(code="603259", name="药明康德", market="A"),
        StockPageInfo(code="300015", name="爱尔眼科", market="A"),
        StockPageInfo(code="300124", name="汇川技术", market="A"),
        StockPageInfo(code="300274", name="阳光电源", market="A"),
        StockPageInfo(code="300014", name="亿纬锂能", market="A"),
        StockPageInfo(code="300122", name="智飞生物", market="A"),
        StockPageInfo(code="300408", name="三环集团", market="A"),
        StockPageInfo(code="300496", name="中科创达", market="A"),
        StockPageInfo(code="002241", name="歌尔股份", market="A"),
        StockPageInfo(code="002371", name="北方华创", market="A"),
        StockPageInfo(code="002460", name="赣锋锂业", market="A"),
        StockPageInfo(code="002466", name="天齐锂业", market="A"),
        StockPageInfo(code="002812", name="恩捷股份", market="A"),
        StockPageInfo(code="002129", name="TCL中环", market="A"),
        StockPageInfo(code="002142", name="宁波银行", market="A"),
        StockPageInfo(code="002271", name="东方雨虹", market="A"),
        StockPageInfo(code="002410", name="广联达", market="A"),
        StockPageInfo(code="002555", name="三七互娱", market="A"),
        StockPageInfo(code="002603", name="以岭药业", market="A"),
        StockPageInfo(code="002709", name="天赐材料", market="A"),
        StockPageInfo(code="002920", name="德赛西威", market="A"),
        StockPageInfo(code="600048", name="保利发展", market="A"),
        StockPageInfo(code="600089", name="特变电工", market="A"),
        StockPageInfo(code="600150", name="中国船舶", market="A"),
        StockPageInfo(code="600176", name="中国巨石", market="A"),
        StockPageInfo(code="600196", name="复星医药", market="A"),
        StockPageInfo(code="600406", name="国电南瑞", market="A"),
        StockPageInfo(code="600436", name="片仔癀", market="A"),
        StockPageInfo(code="600570", name="恒生电子", market="A"),
        StockPageInfo(code="600690", name="海尔智家", market="A"),
        StockPageInfo(code="600745", name="闻泰科技", market="A"),
        StockPageInfo(code="600760", name="中航沈飞", market="A"),
        StockPageInfo(code="600837", name="海通证券", market="A"),
        StockPageInfo(code="600958", name="东方证券", market="A"),
        StockPageInfo(code="601006", name="大秦铁路", market="A"),
        StockPageInfo(code="601066", name="中信建投", market="A"),
        StockPageInfo(code="601100", name="恒立液压", market="A"),
        StockPageInfo(code="601138", name="工业富联", market="A"),
        StockPageInfo(code="601211", name="国泰君安", market="A"),
        StockPageInfo(code="601229", name="上海银行", market="A"),
        StockPageInfo(code="601658", name="邮储银行", market="A"),
        StockPageInfo(code="601688", name="华泰证券", market="A"),
        StockPageInfo(code="601816", name="京沪高铁", market="A"),
        StockPageInfo(code="601888", name="中国中免", market="A"),
        StockPageInfo(code="603501", name="韦尔股份", market="A"),
        StockPageInfo(code="603799", name="华友钴业", market="A"),
        StockPageInfo(code="603986", name="兆易创新", market="A"),
        StockPageInfo(code="605499", name="东鹏饮料", market="A"),
        StockPageInfo(code="000002", name="万科A", market="A"),
        StockPageInfo(code="000338", name="潍柴动力", market="A"),
        StockPageInfo(code="000776", name="广发证券", market="A"),
        StockPageInfo(code="000977", name="浪潮信息", market="A"),
        StockPageInfo(code="000983", name="山西焦煤", market="A"),
        StockPageInfo(code="001979", name="招商蛇口", market="A"),
        StockPageInfo(code="002007", name="华兰生物", market="A"),
        StockPageInfo(code="002050", name="三花智控", market="A"),
        StockPageInfo(code="002179", name="中航光电", market="A"),
        StockPageInfo(code="002236", name="大华股份", market="A"),
    ]
    HOT_STOCKS: Dict[str, StockPageInfo] = {stock.code: stock for stock in HOT_STOCK_LIST}

    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip("/")
        self.archive_service = ArchiveService()

    def get_stock(self, stock_code: str) -> Optional[StockPageInfo]:
        normalized = self.normalize_code(stock_code)
        hot = self.HOT_STOCKS.get(normalized)
        if hot:
            return hot
        return self._resolve_from_snapshot(normalized)

    def list_a_share_stocks(self, ensure_full: bool = True) -> List[StockPageInfo]:
        try:
            from services.search_snapshot_service import SearchSnapshotService

            snapshot_service = SearchSnapshotService()
            if ensure_full:
                snapshot_service.ensure_a_share_snapshot()
            rows = snapshot_service._load_snapshot("A")
            if len(rows) < 100:
                rows = self._fetch_a_share_rows_live()
            stocks = []
            seen = set()
            for row in rows:
                code = self.normalize_code(row.get("symbol"))
                name = str(row.get("name") or "").strip()
                if not code or not name or code in seen:
                    continue
                seen.add(code)
                stocks.append(StockPageInfo(code=code, name=name, market="A"))
            stocks.sort(key=lambda item: item.code)
            return stocks
        except Exception:
            return self._list_a_share_stocks_from_provider()

    def _fetch_a_share_rows_live(self) -> List[Dict[str, str]]:
        return [
            {"symbol": row["code"], "name": row["name"]}
            for row in self._list_a_share_provider_rows()
        ]

    def _list_a_share_provider_rows(self) -> List[Dict[str, str]]:
        try:
            from services.stock_data_provider import StockDataProvider

            return StockDataProvider().get_a_share_list()
        except Exception:
            return []

    def _list_a_share_stocks_from_provider(self) -> List[StockPageInfo]:
        stocks = []
        seen = set()
        for row in self._list_a_share_provider_rows():
            code = self.normalize_code(row.get("code") or row.get("symbol"))
            name = str(row.get("name") or "").strip()
            if not code or not name or code in seen:
                continue
            seen.add(code)
            stocks.append(StockPageInfo(code=code, name=name, market="A"))
        stocks.sort(key=lambda item: item.code)
        return stocks

    def _resolve_from_snapshot(self, stock_code: str) -> Optional[StockPageInfo]:
        try:
            from services.search_snapshot_service import SearchSnapshotService

            snapshot_service = SearchSnapshotService()
            snapshot_service.ensure_a_share_snapshot()
            rows = snapshot_service._load_snapshot("A")
            for row in rows:
                symbol = self.normalize_code(row.get("symbol"))
                if symbol == stock_code:
                    name = str(row.get("name") or stock_code).strip()
                    if name:
                        return StockPageInfo(code=stock_code, name=name, market="A")
        except Exception:
            return None
        return None

    def list_hot_stocks(self) -> List[StockPageInfo]:
        return list(self.HOT_STOCKS.values())

    async def render_stock_page(self, stock_code: str) -> Optional[str]:
        stock = self.get_stock(stock_code)
        recent_articles = None
        if not stock:
            stock = await self._get_stock_from_archived_articles(stock_code)
            if not stock:
                return None

        canonical_url = f"{self.base_url}/stock/{stock.code}"
        title = f"{stock.name}({stock.code}) AI诊股分析_结构趋势风险解读 - Agu AI"
        description = (
            f"{stock.name}({stock.code})AI诊股分析入口，使用 Agu AI 从结构、趋势、"
            "相对强弱和风险线索解读个股，仅供研究参考，不构成投资建议。"
        )
        updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        from services.data_provenance import resolve_data_source
        from services.judgment_accuracy_service import JudgmentAccuracyService

        data_source = resolve_data_source(stock.market)
        data_provenance_label = f"页面更新 {updated_at} · 行情来源：{data_source}"
        accuracy_stats = JudgmentAccuracyService().get_public_accuracy_stats(window_days=90)
        accuracy_line = ""
        if (
            accuracy_stats.get("reviewed_count", 0) > 0
            and accuracy_stats.get("support_rate") is not None
        ):
            accuracy_line = (
                f"近 {accuracy_stats['window_days']} 天历史验证："
                f"已复盘 {accuracy_stats['reviewed_count']} 条，"
                f"系统支持率 {accuracy_stats['support_rate']}%（仅供参考）"
            )
        condition_line = ""
        leaderboard = accuracy_stats.get("condition_quality_leaderboard") or []
        top_condition = next(
            (item for item in leaderboard if int(item.get("reviewed_count") or 0) >= 3),
            None,
        )
        if top_condition and top_condition.get("support_rate") is not None:
            condition_line = (
                f"条件质量参考：{top_condition['label']} "
                f"支持率 {top_condition['support_rate']}%（仅供参考）"
            )
        realtime_url = f"/?code={stock.code}&market={stock.market}&focus=search"
        if recent_articles is None:
            recent_articles = await self._get_recent_articles(stock)

        faq_entries = self._build_faq_entries(stock, recent_articles, updated_at)
        faq_json_ld = self._build_faq_json_ld(faq_entries)

        json_ld = {
            "@context": "https://schema.org",
            "@type": "WebPage",
            "name": title,
            "description": description,
            "url": canonical_url,
            "about": {
                "@type": "Thing",
                "name": stock.name,
                "identifier": stock.code,
            },
            "publisher": {
                "@type": "Organization",
                "name": "Agu AI",
                "url": self.base_url,
            },
            "dateModified": updated_at,
        }

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self._escape(title)}</title>
  <meta name="description" content="{self._escape(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{self._escape(canonical_url)}">
  <meta property="og:title" content="{self._escape(title)}">
  <meta property="og:description" content="{self._escape(description)}">
  <meta property="og:url" content="{self._escape(canonical_url)}">
  <meta property="og:type" content="website">
  <script type="application/ld+json">{self._json(json_ld)}</script>
  <script type="application/ld+json">{self._json(faq_json_ld)}</script>
  <style>
    :root {{
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: #f6f8fc;
      color: #172033;
    }}
    body {{
      margin: 0;
      background: linear-gradient(135deg, #f7f9ff 0%, #eef5ff 48%, #f8fbf5 100%);
    }}
    a {{ color: #2f5bea; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    .page {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 18px 18px 56px;
    }}
    .nav-shell {{
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-bottom: 1px solid rgba(61, 91, 204, 0.10);
      background: rgba(255, 255, 255, 0.82);
    }}
    .nav-inner {{
      max-width: 1040px;
      margin: 0 auto;
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }}
    .brand {{
      font-weight: 800;
      color: #172033;
      letter-spacing: -0.02em;
    }}
    .nav-links {{
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }}
    .nav-links a {{
      color: #475467;
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 14px;
    }}
    .nav-links a:hover {{
      background: rgba(49, 87, 213, 0.08);
      color: #3157d5;
      text-decoration: none;
    }}
    .hero {{
      padding: 34px;
      border: 1px solid rgba(61, 91, 204, 0.12);
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.86);
      box-shadow: 0 18px 50px rgba(38, 64, 126, 0.10);
    }}
    .eyebrow {{
      color: #5d6b86;
      font-size: 14px;
      margin-bottom: 12px;
    }}
    h1 {{ margin: 0 0 14px; font-size: clamp(28px, 5vw, 44px); line-height: 1.15; }}
    h2 {{ margin: 0 0 14px; font-size: 22px; }}
    p {{ line-height: 1.75; }}
    .cta {{
      display: inline-flex;
      margin-top: 18px;
      padding: 12px 18px;
      border-radius: 999px;
      color: #fff;
      background: #3157d5;
      font-weight: 700;
    }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 16px;
      margin-top: 18px;
    }}
    section {{
      margin-top: 20px;
      padding: 24px;
      border: 1px solid rgba(61, 91, 204, 0.10);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.78);
    }}
    li {{ margin: 8px 0; line-height: 1.65; }}
    .article-list {{
      display: grid;
      gap: 12px;
      padding: 0;
      list-style: none;
    }}
    .article-card {{
      padding: 14px 16px;
      border-radius: 14px;
      background: #f8faff;
      border: 1px solid rgba(61, 91, 204, 0.10);
    }}
    .article-meta {{ color: #667085; font-size: 13px; margin-top: 6px; }}
    .disclaimer {{
      color: #6b7280;
      font-size: 14px;
    }}
    .faq-list {{
      display: grid;
      gap: 14px;
      margin: 0;
      padding: 0;
    }}
    .faq-item {{
      margin: 0;
      padding: 16px 18px;
      border-radius: 14px;
      background: #f8faff;
      border: 1px solid rgba(61, 91, 204, 0.10);
    }}
    .faq-question {{
      margin: 0 0 8px;
      font-size: 17px;
      line-height: 1.45;
    }}
    .faq-answer {{
      margin: 0;
      color: #344054;
    }}
  </style>
</head>
<body>
  <header class="nav-shell">
    <div class="nav-inner">
      <a class="brand" href="/">Agu AI</a>
      <nav class="nav-links" aria-label="主导航">
        <a href="/analysis">分析专栏</a>
        <a href="/stocks">个股列表</a>
        <a href="/risk-stocks">风险股清单</a>
        <a href="/watchlist">我的观察</a>
        <a href="/journal">判断日记</a>
        <a href="/about">关于我们</a>
      </nav>
    </div>
  </header>
  <main class="page">
    <nav aria-label="面包屑">
      <a href="/">Agu AI</a> / <span>{self._escape(stock.name)} AI诊股</span>
    </nav>
    <header class="hero">
      <div class="eyebrow">{self._escape(stock.market)}股 · {self._escape(stock.code)}</div>
      <h1>{self._escape(stock.name)}({self._escape(stock.code)}) AI诊股分析</h1>
      <p>
        这是 {self._escape(stock.name)}({self._escape(stock.code)}) 的 Agu AI 个股诊股入口页，
        用于从结构、趋势、相对强弱和风险线索理解这只股票。
      </p>
      <p class="disclaimer">{self._escape(data_provenance_label)}</p>
      {f'<p class="disclaimer">{self._escape(accuracy_line)}</p>' if accuracy_line else ''}
      {f'<p class="disclaimer">{self._escape(condition_line)}</p>' if condition_line else ''}
      <a class="cta" href="{self._escape(realtime_url)}">实时 AI 诊断这只股票</a>
    </header>
    <section>
      <h2>可以分析哪些维度？</h2>
      <ul>
        <li>结构状态：趋势结构、均线位置、近期高低点。</li>
        <li>趋势方向：短期、中期和长期趋势观察。</li>
        <li>相对强弱：个股相对市场的强弱变化。</li>
        <li>量价线索：成交量放大、缩量和异常波动。</li>
        <li>风险线索：关键位置失守、波动放大和过热风险。</li>
      </ul>
    </section>
    <section>
      <h2>最近 AI 诊断沉淀</h2>
      {self._render_recent_articles(recent_articles)}
    </section>
    {self._render_faq_section(faq_entries)}
    <section>
      <h2>实时 AI 诊股</h2>
      <p>点击下方入口，可进入 Agu AI 前端工具，对 {self._escape(stock.name)} 发起实时分析，并定位到“智能搜索与选择”区域。</p>
      <p><a class="cta" href="{self._escape(realtime_url)}">实时 AI 诊断这只股票</a></p>
    </section>
    <section>
      <h2>数据更新时间</h2>
      <p>{self._escape(updated_at)}</p>
    </section>
    <section>
      <h2>风险提示</h2>
      <p class="disclaimer">本页面内容仅供研究参考，不构成投资建议。市场有风险，投资决策需结合自身情况独立判断。</p>
    </section>
  </main>
</body>
</html>"""

    def render_stock_index_page(self, page: int = 1, per_page: int = 200) -> str:
        all_stocks = self.list_a_share_stocks()
        total = len(all_stocks)
        total_pages = max(1, (total + per_page - 1) // per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        page_stocks = all_stocks[start : start + per_page]

        title = "A股个股 AI 诊股清单 - Agu AI"
        description = (
            f"Agu AI A股个股 AI 诊股清单，覆盖 {total} 只 A 股的服务端落地页入口，"
            "便于搜索引擎和用户发现每只股票的 AI 诊股页面。"
        )
        canonical_url = f"{self.base_url}/stocks" if page == 1 else f"{self.base_url}/stocks?page={page}"
        stock_links = "\n".join(
            f'<li class="stock-index-item"><a class="stock-index-link" href="/stock/{self._escape(stock.code)}">'
            f'<span class="stock-index-name">{self._escape(stock.name)}</span>'
            f'<span class="stock-index-code">{self._escape(stock.code)}</span>'
            f'</a></li>'
            for stock in page_stocks
        )
        pagination_links = self._render_stock_index_pagination(page, total_pages)
        json_ld = {
            "@context": "https://schema.org",
            "@type": "CollectionPage",
            "name": title,
            "description": description,
            "url": canonical_url,
            "publisher": {
                "@type": "Organization",
                "name": "Agu AI",
                "url": self.base_url,
            },
        }

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{self._escape(title)}</title>
  <meta name="description" content="{self._escape(description)}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{self._escape(canonical_url)}">
  <meta property="og:title" content="{self._escape(title)}">
  <meta property="og:description" content="{self._escape(description)}">
  <meta property="og:url" content="{self._escape(canonical_url)}">
  <meta property="og:type" content="website">
  <script type="application/ld+json">{self._json(json_ld)}</script>
  <style>{self._shared_css()}</style>
</head>
<body>
  {self._render_nav()}
  <main class="page">
    <header class="hero">
      <div class="eyebrow">A股 · 全市场个股</div>
      <h1>A股个股 AI 诊股清单</h1>
      <p>这里聚合 Agu AI 当前开放的 A 股个股服务端落地页，共 {total} 只，方便搜索引擎和用户发现每只股票的 AI 诊股入口。</p>
      <p>也可查看 <a href="/risk-stocks">每日风险股清单</a>，聚焦 ST 股与三连板及以上高波动标的。</p>
      <a class="cta" href="/">返回首页实时诊股</a>
    </header>
    <section>
      <h2>个股列表</h2>
      <p class="section-hint">第 {page} / {total_pages} 页，本页展示 {len(page_stocks)} 只个股入口；所有链接均为服务端 HTML 页面，便于用户浏览和搜索引擎抓取。</p>
      <ul class="stock-index-grid">{stock_links}</ul>
      {pagination_links}
    </section>
    <section>
      <h2>风险提示</h2>
      <p class="disclaimer">本清单仅用于索引和研究入口，不构成投资建议。市场有风险，投资决策需结合自身情况独立判断。</p>
    </section>
  </main>
</body>
</html>"""

    def _render_stock_index_pagination(self, page: int, total_pages: int) -> str:
        if total_pages <= 1:
            return ""
        links = []
        if page > 1:
            prev_page = page - 1
            prev_href = "/stocks" if prev_page == 1 else f"/stocks?page={prev_page}"
            links.append(f'<a class="stock-index-page-link" href="{prev_href}">上一页</a>')
        links.append(f'<span class="stock-index-page-status">第 {page} / {total_pages} 页</span>')
        if page < total_pages:
            links.append(f'<a class="stock-index-page-link" href="/stocks?page={page + 1}">下一页</a>')
        return f'<nav class="stock-index-pagination" aria-label="分页">{" ".join(links)}</nav>'

    async def _get_recent_articles(self, stock: StockPageInfo) -> List[Dict[str, Any]]:
        try:
            articles = await self.archive_service.get_articles(limit=5, offset=0, keyword=stock.code)
            return [dict(article) for article in articles if article]
        except Exception:
            return []

    async def _get_stock_from_archived_articles(self, stock_code: str) -> Optional[StockPageInfo]:
        normalized = self.normalize_code(stock_code)
        try:
            articles = await self.archive_service.get_articles(limit=1, offset=0, keyword=normalized)
        except Exception:
            return None
        if not articles:
            return None
        article = dict(articles[0])
        article_code = self.normalize_code(article.get("stock_code") or normalized)
        if article_code != normalized:
            return None
        stock_name = str(article.get("stock_name") or "").strip()
        if not stock_name:
            return None
        market_type = str(article.get("market_type") or "A").strip() or "A"
        return StockPageInfo(code=normalized, name=stock_name, market=market_type)

    def _render_recent_articles(self, articles: List[Dict[str, Any]]) -> str:
        if not articles:
            return "<p>暂无沉淀分析，点击实时诊断可以生成第一份报告。</p>"

        items = []
        for article in articles[:5]:
            article_id = self._escape(article.get("id", ""))
            title = self._escape(article.get("title", "未命名分析"))
            publish_date = self._escape(article.get("publish_date") or article.get("created_at") or "")
            score = article.get("score")
            score_text = f"评分 {self._escape(score)}" if score is not None else "评分 —"
            items.append(
                f'<li class="article-card"><a href="/analysis/{article_id}">{title}</a>'
                f'<div class="article-meta">{publish_date} · {score_text}</div></li>'
            )
        return f'<ul class="article-list">{"".join(items)}</ul>'

    def _build_faq_entries(
        self,
        stock: StockPageInfo,
        recent_articles: List[Dict[str, Any]],
        updated_at: str,
    ) -> List[Dict[str, str]]:
        insights = self._parse_article_ai_insights(recent_articles[0] if recent_articles else None)
        latest_article = recent_articles[0] if recent_articles else None
        latest_date = ""
        if latest_article:
            latest_date = str(
                latest_article.get("publish_date") or latest_article.get("created_at") or ""
            ).strip()

        how_to_read = (
            f"查看 {stock.name}({stock.code}) 时，Agu AI 会从结构、趋势、相对强弱、量价和风险线索五个维度做研究型解读。"
            "你可以先阅读本页沉淀的 AI 诊断文章，或点击「实时 AI 诊断」获取最新观察。"
            "本内容仅供研究参考，不构成投资建议。"
        )

        if insights.get("one_liner"):
            focus_prefix = f"最近一次诊断（{latest_date}）" if latest_date else "最近一次诊断"
            overall_label = insights.get("overall_label")
            label_suffix = f"综合评级为「{overall_label}」。" if overall_label else ""
            diagnosis_focus = (
                f"{focus_prefix}，{stock.code} 的 AI 诊断重点关注：{insights['one_liner']} {label_suffix}"
                "你也可以在本页查看结构、趋势、相对强弱、量价和风险线索等维度拆解。"
            )
        elif latest_article:
            title = str(latest_article.get("title") or "").strip()
            score = latest_article.get("score")
            score_text = f"评分 {score}" if score is not None else "评分待补充"
            diagnosis_focus = (
                f"当前可参考最近一次 AI 诊断《{title}》（{latest_date or '日期待补充'}，{score_text}）。"
                f"Agu AI 会从结构、趋势、相对强弱、量价和风险线索理解 {stock.name}({stock.code})，"
                "并持续沉淀到分析专栏。"
            )
        else:
            diagnosis_focus = (
                f"当前 {stock.code} 暂无可引用的沉淀诊断，发起实时分析后，Agu AI 会优先关注："
                "趋势结构是否延续、相对市场强弱、量价配合、关键位置得失与波动风险。"
            )

        risk_points = insights.get("risk_evidence") or []
        if risk_points:
            risk_text = "；".join(str(point) for point in risk_points[:3])
            main_risk = (
                f"{stock.name}({stock.code}) 需要重点留意的风险线索包括：{risk_text}。"
                "以上来自最近一次 AI 诊断的风险维度拆解，仅供研究参考，不构成投资建议。"
            )
        else:
            main_risk = (
                f"研究 {stock.name}({stock.code}) 时，常见需观察的风险线索包括：关键位置失守、"
                "波动异常放大、量价背离、相对强弱走弱，以及事件扰动带来的不确定性。"
                "请结合自身判断独立决策，市场有风险。"
            )

        data_updated = f"本页服务端 HTML 更新时间为 {updated_at}。"
        if latest_date:
            data_updated += f" 最近一次 AI 诊断沉淀日期为 {latest_date}。"
        data_updated += " 实时诊股结果会随市场数据与模型分析即时更新。"

        return [
            {"question": f"{stock.name}股票怎么看？", "answer": how_to_read},
            {"question": f"{stock.code}当前 AI 诊断关注什么？", "answer": diagnosis_focus},
            {"question": "主要风险是什么？", "answer": main_risk},
            {"question": "数据更新时间是什么？", "answer": data_updated},
        ]

    def _build_faq_json_ld(self, faq_entries: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "@context": "https://schema.org",
            "@type": "FAQPage",
            "mainEntity": [
                {
                    "@type": "Question",
                    "name": entry["question"],
                    "acceptedAnswer": {
                        "@type": "Answer",
                        "text": entry["answer"],
                    },
                }
                for entry in faq_entries
            ],
        }

    def _render_faq_section(self, faq_entries: List[Dict[str, str]]) -> str:
        items = []
        for entry in faq_entries:
            items.append(
                f'<article class="faq-item">'
                f'<h3 class="faq-question">{self._escape(entry["question"])}</h3>'
                f'<p class="faq-answer">{self._escape(entry["answer"])}</p>'
                f"</article>"
            )
        return (
            '<section class="faq-section" aria-labelledby="stock-faq-heading">'
            '<h2 id="stock-faq-heading">常见问题</h2>'
            f'<div class="faq-list">{"".join(items)}</div>'
            "</section>"
        )

    def _parse_article_ai_insights(self, article: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not article:
            return {}

        raw = article.get("ai_score_json")
        if not raw:
            return {}

        try:
            data = json.loads(raw) if isinstance(raw, str) else raw
        except Exception:
            return {}

        if not isinstance(data, dict):
            return {}

        explain = data.get("explain") or {}
        risk_evidence: List[str] = []
        for dim in data.get("dimensions") or []:
            if isinstance(dim, dict) and dim.get("id") == "risk":
                evidence = dim.get("evidence") or []
                if isinstance(evidence, list):
                    risk_evidence = [str(item) for item in evidence if item]
                break

        overall = data.get("overall") or {}
        return {
            "one_liner": str(explain.get("one_liner") or "").strip(),
            "risk_evidence": risk_evidence,
            "overall_label": str(overall.get("label") or "").strip(),
        }

    def _render_nav(self) -> str:
        return """<header class="nav-shell">
    <div class="nav-inner">
      <a class="brand" href="/">Agu AI</a>
      <nav class="nav-links" aria-label="主导航">
        <a href="/analysis">分析专栏</a>
        <a href="/stocks">个股列表</a>
        <a href="/risk-stocks">风险股清单</a>
        <a href="/watchlist">我的观察</a>
        <a href="/journal">判断日记</a>
        <a href="/about">关于我们</a>
      </nav>
    </div>
  </header>"""

    def _shared_css(self) -> str:
        return """
    :root {
      color-scheme: light;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif;
      background: #f6f8fc;
      color: #172033;
    }
    body {
      margin: 0;
      background: linear-gradient(135deg, #f7f9ff 0%, #eef5ff 48%, #f8fbf5 100%);
    }
    a { color: #2f5bea; text-decoration: none; }
    a:hover { text-decoration: underline; }
    .page {
      max-width: 1040px;
      margin: 0 auto;
      padding: 18px 18px 56px;
    }
    .nav-shell {
      position: sticky;
      top: 0;
      z-index: 10;
      backdrop-filter: blur(18px);
      -webkit-backdrop-filter: blur(18px);
      border-bottom: 1px solid rgba(61, 91, 204, 0.10);
      background: rgba(255, 255, 255, 0.82);
    }
    .nav-inner {
      max-width: 1040px;
      margin: 0 auto;
      padding: 12px 18px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 16px;
    }
    .brand {
      font-weight: 800;
      color: #172033;
      letter-spacing: -0.02em;
    }
    .nav-links {
      display: flex;
      gap: 10px;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    .nav-links a {
      color: #475467;
      padding: 7px 10px;
      border-radius: 999px;
      font-size: 14px;
    }
    .nav-links a:hover {
      background: rgba(49, 87, 213, 0.08);
      color: #3157d5;
      text-decoration: none;
    }
    .hero {
      padding: 34px;
      border: 1px solid rgba(61, 91, 204, 0.12);
      border-radius: 24px;
      background: rgba(255, 255, 255, 0.86);
      box-shadow: 0 18px 50px rgba(38, 64, 126, 0.10);
    }
    .eyebrow {
      color: #5d6b86;
      font-size: 14px;
      margin-bottom: 12px;
    }
    h1 { margin: 0 0 14px; font-size: clamp(28px, 5vw, 44px); line-height: 1.15; }
    h2 { margin: 0 0 14px; font-size: 22px; }
    p { line-height: 1.75; }
    .cta {
      display: inline-flex;
      margin-top: 18px;
      padding: 12px 18px;
      border-radius: 999px;
      color: #fff;
      background: #3157d5;
      font-weight: 700;
    }
    section {
      margin-top: 20px;
      padding: 24px;
      border: 1px solid rgba(61, 91, 204, 0.10);
      border-radius: 20px;
      background: rgba(255, 255, 255, 0.78);
    }
    li { margin: 8px 0; line-height: 1.65; }
    .article-list {
      display: grid;
      gap: 12px;
      padding: 0;
      list-style: none;
    }
    .article-card {
      padding: 14px 16px;
      border-radius: 14px;
      background: #f8faff;
      border: 1px solid rgba(61, 91, 204, 0.10);
    }
    .article-meta { color: #667085; font-size: 13px; margin-top: 6px; }
    .section-hint {
      color: #667085;
      font-size: 14px;
      margin-top: -4px;
    }
    .stock-index-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(132px, 1fr));
      gap: 8px;
      padding: 0;
      margin: 14px 0 0;
      list-style: none;
    }
    .stock-index-item {
      margin: 0;
      line-height: 1.2;
    }
    .stock-index-link {
      display: flex;
      flex-direction: column;
      gap: 4px;
      min-height: 48px;
      padding: 9px 10px;
      border: 1px solid rgba(61, 91, 204, 0.10);
      border-radius: 12px;
      background: rgba(248, 250, 255, 0.86);
    }
    .stock-index-link:hover {
      background: rgba(49, 87, 213, 0.08);
      text-decoration: none;
    }
    .stock-index-name {
      color: #172033;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    .stock-index-code {
      color: #667085;
      font-size: 12px;
      font-variant-numeric: tabular-nums;
    }
    .stock-index-pagination {
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 14px;
      margin-top: 18px;
      flex-wrap: wrap;
    }
    .stock-index-page-link {
      display: inline-flex;
      align-items: center;
      padding: 8px 14px;
      border-radius: 999px;
      border: 1px solid rgba(61, 91, 204, 0.14);
      background: rgba(255, 255, 255, 0.9);
      font-weight: 600;
    }
    .stock-index-page-status {
      color: #667085;
      font-size: 14px;
    }
    .disclaimer {
      color: #6b7280;
      font-size: 14px;
    }
  """

    def normalize_code(self, stock_code: str) -> str:
        return str(stock_code or "").strip().upper().split(".")[0]

    def _escape(self, value: str) -> str:
        return html.escape(str(value), quote=True)

    def _json(self, value: Dict) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
