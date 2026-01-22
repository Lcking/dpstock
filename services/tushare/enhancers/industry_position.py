"""
Industry Position Enhancer
获取行业分类和行业排名信息
"""
from datetime import datetime, timedelta
from .base import BaseEnhancer
from ..schemas import ModuleResult, KeyMetric, ModuleDetails, TableData
from utils.logger import get_logger

logger = get_logger()


class IndustryPositionEnhancer(BaseEnhancer):
    """
    行业位置增强器
    
    输出: industry_name, industry_ret_20d, industry_rank
    """
    
    MODULE_NAME = "industry_position"
    
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """获取行业位置信息"""
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        hit, cached = self._get_cached(ts_code, asof.replace('-', ''))
        if hit and cached:
            return cached
        
        # 获取股票基础信息（含行业）
        basic_df = self.client.get_stock_basic(ts_code)
        
        if basic_df is None or len(basic_df) == 0:
            return ModuleResult.unavailable("无法获取股票基础信息")
        
        industry = basic_df['industry'].iloc[0] if 'industry' in basic_df.columns else None
        stock_name = basic_df['name'].iloc[0] if 'name' in basic_df.columns else ts_code
        
        if not industry:
            return ModuleResult.degraded_result(
                reason="行业分类信息缺失",
                summary=f"{stock_name}：行业分类信息不可用",
                key_metrics=[]
            )
        
        # 尝试获取行业指数数据（这需要行业指数映射，简化处理）
        # 由于 Tushare 行业指数需要额外映射，这里先返回基础行业信息
        
        key_metrics = [
            KeyMetric(key="industry_name", label="所属行业", value=industry, unit=None)
        ]
        
        summary = f"{stock_name}所属行业：{industry}"
        
        result = ModuleResult(
            available=True,
            degraded=True,  # 暂时降级，完整版需要行业排名
            degrade_reason="行业排名数据需更高权限接口",
            summary=summary,
            key_metrics=key_metrics,
            details=ModuleDetails(
                tables=[],
                notes=[
                    f"股票: {stock_name} ({ts_code})",
                    f"行业: {industry}",
                    "完整行业排名需要申请更高权限接口"
                ]
            ),
            meta=self._make_meta(asof, cache_hit=False)
        )
        
        # 写入缓存
        self._set_cache(ts_code, result, asof.replace('-', ''))
        
        return result
