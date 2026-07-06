"""
Dynamic llms.txt generator for GEO surfaces.
"""
from __future__ import annotations

from datetime import datetime

from services.judgment_accuracy_service import JudgmentAccuracyService
from services.stock_page_service import StockPageService


class LlmsTxtService:
    def __init__(self, base_url: str = "https://aguai.net"):
        self.base_url = base_url.rstrip("/")
        self.stock_page_service = StockPageService(base_url=base_url)
        self.accuracy_service = JudgmentAccuracyService()

    def render(self) -> str:
        now = datetime.utcnow().strftime("%Y-%m-%d")
        stats = self.accuracy_service.get_public_accuracy_stats(window_days=90)
        support_rate = stats.get("support_rate")
        reviewed_count = stats.get("reviewed_count") or 0
        accuracy_line = (
            f"- 近 {stats['window_days']} 天已复盘判断 {reviewed_count} 条，"
            f"系统支持率 {support_rate}%（仅供参考，不构成投资建议）"
            if support_rate is not None and reviewed_count > 0
            else "- 历史验证统计样本积累中，请以实时诊断结果为准"
        )

        hot_links = "\n".join(
            f"- [{stock.name}({stock.code})]({self.base_url}/stock/{stock.code})"
            for stock in self.stock_page_service.list_hot_stocks()[:20]
        )

        return f"""# Agu AI 股票分析平台

## 网站简介
Agu AI 是一个基于人工智能的股票分析平台，为投资者提供 A 股、港股、美股的结构、趋势、相对强弱与风险线索研究视图。

## 主要功能
- 实时股票结构分析
- AI 深度研究解读
- 多维度评分系统（结构、相对强弱、资金、风险）
- 专业分析文章归档
- 判断日记与历史验证统计

## 核心页面
- 首页: {self.base_url}/
- 分析专栏: {self.base_url}/analysis
- 个股列表: {self.base_url}/stocks
- 风险股清单: {self.base_url}/risk-stocks
## 热门个股入口
{hot_links}

## 历史验证统计
{accuracy_line}

## 评分体系说明
- 综合评分用于描述当前结构强弱与证据完整度，不等同于买卖建议
- 结构标签示例：结构强 / 结构偏强 / 中性 / 结构偏弱 / 结构弱

## 数据来源
- A 股行情：akshare / tushare
- 港股行情：雅虎财经
- 美股行情：雅虎财经

## 分析频率
- 实时分析：按需触发
- 文章归档：按分析生成
- 行情快照：按交易日更新

## 联系方式
- 网站: {self.base_url}
- 邮箱: support@aguai.net

## 免责声明
本平台提供的分析仅供研究参考，不构成投资建议。股市有风险，投资需谨慎。

## 最后更新
{now}
"""
