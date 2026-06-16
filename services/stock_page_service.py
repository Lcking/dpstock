import html
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional


@dataclass(frozen=True)
class StockPageInfo:
    code: str
    name: str
    market: str


class StockPageService:
    """Generate crawlable stock landing pages for SEO/GEO entry traffic."""

    HOT_STOCKS: Dict[str, StockPageInfo] = {
        "600519": StockPageInfo(code="600519", name="贵州茅台", market="A"),
        "000001": StockPageInfo(code="000001", name="平安银行", market="A"),
        "300750": StockPageInfo(code="300750", name="宁德时代", market="A"),
        "601318": StockPageInfo(code="601318", name="中国平安", market="A"),
        "600036": StockPageInfo(code="600036", name="招商银行", market="A"),
    }

    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip("/")

    def get_stock(self, stock_code: str) -> Optional[StockPageInfo]:
        normalized = self.normalize_code(stock_code)
        return self.HOT_STOCKS.get(normalized)

    def list_hot_stocks(self) -> List[StockPageInfo]:
        return list(self.HOT_STOCKS.values())

    def render_stock_page(self, stock_code: str) -> Optional[str]:
        stock = self.get_stock(stock_code)
        if not stock:
            return None

        canonical_url = f"{self.base_url}/stock/{stock.code}"
        title = f"{stock.name}({stock.code}) AI诊股分析_结构趋势风险解读 - Agu AI"
        description = (
            f"{stock.name}({stock.code})AI诊股分析入口，使用 Agu AI 从结构、趋势、"
            "相对强弱和风险线索解读个股，仅供研究参考，不构成投资建议。"
        )
        updated_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
        realtime_url = f"/?code={stock.code}&market={stock.market}"

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
</head>
<body>
  <main>
    <nav aria-label="面包屑">
      <a href="/">Agu AI</a> / <span>{self._escape(stock.name)} AI诊股</span>
    </nav>
    <h1>{self._escape(stock.name)}({self._escape(stock.code)}) AI诊股分析</h1>
    <p>
      这是 {self._escape(stock.name)}({self._escape(stock.code)}) 的 Agu AI 个股诊股入口页，
      用于从结构、趋势、相对强弱和风险线索理解这只股票。
    </p>
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
      <h2>实时 AI 诊股</h2>
      <p>点击下方入口，可进入 Agu AI 前端工具，对 {self._escape(stock.name)} 发起实时分析。</p>
      <p><a href="{self._escape(realtime_url)}">实时 AI 诊断这只股票</a></p>
    </section>
    <section>
      <h2>数据更新时间</h2>
      <p>{self._escape(updated_at)}</p>
    </section>
    <section>
      <h2>风险提示</h2>
      <p>本页面内容仅供研究参考，不构成投资建议。市场有风险，投资决策需结合自身情况独立判断。</p>
    </section>
  </main>
</body>
</html>"""

    def normalize_code(self, stock_code: str) -> str:
        return str(stock_code or "").strip().upper().split(".")[0]

    def _escape(self, value: str) -> str:
        return html.escape(str(value), quote=True)

    def _json(self, value: Dict) -> str:
        return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
