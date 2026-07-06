from datetime import datetime
from typing import Any, List, Dict, Optional
import xml.etree.ElementTree as ET

from services.archive_service import ArchiveService
from services.stock_page_service import StockPageService
from utils.logger import get_logger

logger = get_logger()


class SitemapGenerator:
    """
    生成 sitemap.xml 的服务
    自动包含所有文章链接
    """

    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip("/")
        self.archive_service = ArchiveService()
        self.stock_page_service = StockPageService(base_url=base_url)

    async def generate_sitemap(self) -> str:
        """Return sitemap index that points to core and stock sitemaps."""
        try:
            stock_count = len(self.stock_page_service.list_a_share_stocks())
            if stock_count > 0:
                return self._render_sitemap_index(
                    [
                        f"{self.base_url}/sitemap-core.xml",
                        f"{self.base_url}/sitemap-stocks.xml",
                    ]
                )
            return await self.generate_core_sitemap()
        except Exception as e:
            logger.error(f"生成sitemap失败: {str(e)}")
            raise

    async def generate_core_sitemap(self) -> str:
        try:
            urlset = self._new_urlset()
            self._add_url(urlset, "/", priority="1.0", changefreq="daily")
            self._add_url(urlset, "/analysis", priority="0.9", changefreq="daily")
            self._add_url(urlset, "/stocks", priority="0.85", changefreq="weekly")
            self._add_url(urlset, "/risk-stocks", priority="0.8", changefreq="daily")

            hot_stocks = self.stock_page_service.list_hot_stocks()
            for stock in hot_stocks:
                self._add_url(
                    urlset,
                    f"/stock/{stock.code}",
                    priority="0.7",
                    changefreq="weekly",
                )

            articles = await self._get_articles_safely()
            archived_stock_paths = set()
            for article in articles:
                article_id = article.get("id") if hasattr(article, "get") else None
                if not article_id:
                    continue
                lastmod = article.get("publish_date") or article.get("created_at", "")
                if lastmod:
                    lastmod = str(lastmod)
                    if " " in lastmod:
                        lastmod = lastmod.split(" ")[0]
                self._add_url(
                    urlset,
                    f"/analysis/{article_id}",
                    lastmod=lastmod,
                    priority="0.8",
                    changefreq="weekly",
                )
                stock_code = str(article.get("stock_code") or "").strip()
                if stock_code:
                    archived_stock_paths.add(f"/stock/{stock_code}")

            for stock_path in sorted(archived_stock_paths):
                if stock_path in {f"/stock/{stock.code}" for stock in hot_stocks}:
                    continue
                self._add_url(
                    urlset,
                    stock_path,
                    priority="0.6",
                    changefreq="weekly",
                )

            logger.info(
                f"生成 core sitemap 成功, 包含 {len(articles) + len(hot_stocks) + len(archived_stock_paths) + 4} 个URL"
            )
            return self._render_urlset(urlset)
        except Exception as e:
            logger.error(f"生成 core sitemap 失败: {str(e)}")
            raise

    async def generate_stock_sitemap(self) -> str:
        try:
            urlset = self._new_urlset()
            stocks = self.stock_page_service.list_a_share_stocks()
            hot_codes = {stock.code for stock in self.stock_page_service.list_hot_stocks()}
            for stock in stocks:
                priority = "0.55" if stock.code not in hot_codes else "0.65"
                self._add_url(
                    urlset,
                    f"/stock/{stock.code}",
                    priority=priority,
                    changefreq="weekly",
                )
            logger.info(f"生成 stock sitemap 成功, 包含 {len(stocks)} 个个股 URL")
            return self._render_urlset(urlset)
        except Exception as e:
            logger.error(f"生成 stock sitemap 失败: {str(e)}")
            raise

    async def _get_articles_safely(self) -> List[Dict[str, Any]]:
        try:
            articles = await self.archive_service.get_articles(limit=1000, offset=0)
            return [dict(article) for article in articles if article]
        except Exception as e:
            logger.warning(f"获取文章列表失败，sitemap 降级为基础页面: {str(e)}")
            return []

    def _new_urlset(self) -> ET.Element:
        urlset = ET.Element("urlset")
        urlset.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        urlset.set("xmlns:xsi", "http://www.w3.org/2001/XMLSchema-instance")
        urlset.set(
            "xsi:schemaLocation",
            "http://www.sitemaps.org/schemas/sitemap/0.9 "
            "http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd",
        )
        return urlset

    def _render_urlset(self, urlset: ET.Element) -> str:
        if hasattr(ET, "indent"):
            ET.indent(ET.ElementTree(urlset), space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            urlset,
            encoding="unicode",
        )

    def _render_sitemap_index(self, sitemap_urls: List[str]) -> str:
        index = ET.Element("sitemapindex")
        index.set("xmlns", "http://www.sitemaps.org/schemas/sitemap/0.9")
        today = datetime.now().strftime("%Y-%m-%d")
        for sitemap_url in sitemap_urls:
            item = ET.SubElement(index, "sitemap")
            loc = ET.SubElement(item, "loc")
            loc.text = sitemap_url
            lastmod = ET.SubElement(item, "lastmod")
            lastmod.text = today
        if hasattr(ET, "indent"):
            ET.indent(ET.ElementTree(index), space="  ")
        return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(
            index,
            encoding="unicode",
        )

    def _add_url(
        self,
        parent: ET.Element,
        path: str,
        lastmod: Optional[str] = None,
        priority: str = "0.5",
        changefreq: str = "weekly",
    ):
        url = ET.SubElement(parent, "url")
        loc = ET.SubElement(url, "loc")
        loc.text = f"{self.base_url}{path}"
        lastmod_elem = ET.SubElement(url, "lastmod")
        lastmod_elem.text = lastmod or datetime.now().strftime("%Y-%m-%d")
        changefreq_elem = ET.SubElement(url, "changefreq")
        changefreq_elem.text = changefreq
        priority_elem = ET.SubElement(url, "priority")
        priority_elem.text = priority
