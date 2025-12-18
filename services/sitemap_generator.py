from datetime import datetime
from typing import List, Dict
from services.archive_service import ArchiveService
from utils.logger import get_logger
import xml.etree.ElementTree as ET

logger = get_logger()

class SitemapGenerator:
    """
    生成sitemap.xml的服务
    自动包含所有文章链接
    """
    
    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip('/')
        self.archive_service = ArchiveService()
    
    async def generate_sitemap(self) -> str:
        """
        生成sitemap.xml内容
        
        Returns:
            XML格式的sitemap字符串
        """
        try:
            # 创建根元素
            urlset = ET.Element('urlset')
            urlset.set('xmlns', 'http://www.sitemaps.org/schemas/sitemap/0.9')
            urlset.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
            urlset.set('xsi:schemaLocation', 
                      'http://www.sitemaps.org/schemas/sitemap/0.9 '
                      'http://www.sitemaps.org/schemas/sitemap/0.9/sitemap.xsd')
            
            # 添加首页
            self._add_url(urlset, '/', priority='1.0', changefreq='daily')
            
            # 添加分析专栏页面
            self._add_url(urlset, '/analysis', priority='0.9', changefreq='daily')
            
            # 获取所有文章
            articles = await self.archive_service.get_articles(limit=1000, offset=0)
            
            # 添加每篇文章
            for article in articles:
                article_url = f"/analysis/{article['id']}"
                # 使用文章的发布日期或创建日期
                lastmod = article.get('publish_date') or article.get('created_at', '')
                if lastmod:
                    # 确保日期格式为 YYYY-MM-DD
                    if ' ' in lastmod:
                        lastmod = lastmod.split(' ')[0]
                
                self._add_url(
                    urlset, 
                    article_url, 
                    lastmod=lastmod,
                    priority='0.8', 
                    changefreq='weekly'
                )
            
            # 生成XML字符串
            tree = ET.ElementTree(urlset)
            ET.indent(tree, space='  ')  # 格式化输出
            
            # 转换为字符串
            xml_str = '<?xml version="1.0" encoding="UTF-8"?>\n'
            xml_str += ET.tostring(urlset, encoding='unicode')
            
            logger.info(f"生成sitemap成功,包含 {len(articles) + 2} 个URL")
            return xml_str
            
        except Exception as e:
            logger.error(f"生成sitemap失败: {str(e)}")
            raise
    
    def _add_url(self, parent: ET.Element, path: str, 
                 lastmod: str = None, priority: str = '0.5', 
                 changefreq: str = 'weekly'):
        """
        添加URL条目到sitemap
        
        Args:
            parent: 父元素
            path: URL路径
            lastmod: 最后修改日期 (YYYY-MM-DD)
            priority: 优先级 (0.0-1.0)
            changefreq: 更新频率
        """
        url = ET.SubElement(parent, 'url')
        
        # loc - 完整URL
        loc = ET.SubElement(url, 'loc')
        loc.text = f"{self.base_url}{path}"
        
        # lastmod - 最后修改时间
        if lastmod:
            lastmod_elem = ET.SubElement(url, 'lastmod')
            lastmod_elem.text = lastmod
        else:
            # 使用当前日期
            lastmod_elem = ET.SubElement(url, 'lastmod')
            lastmod_elem.text = datetime.now().strftime('%Y-%m-%d')
        
        # changefreq - 更新频率
        changefreq_elem = ET.SubElement(url, 'changefreq')
        changefreq_elem.text = changefreq
        
        # priority - 优先级
        priority_elem = ET.SubElement(url, 'priority')
        priority_elem.text = priority
