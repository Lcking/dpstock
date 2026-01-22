"""
Enhancement Orchestrator
协调所有增强模块的执行
"""
from datetime import datetime
from typing import Dict, Optional
from .schemas import EnhancementsResponse, ModuleResult
from .enhancers import (
    RelativeStrengthEnhancer,
    IndustryPositionEnhancer,
    CapitalFlowEnhancer,
    EventsEnhancer
)
from utils.logger import get_logger

logger = get_logger()


class EnhancementOrchestrator:
    """
    增强协调器
    
    负责调用所有增强模块并汇总结果
    """
    
    def __init__(self):
        self.enhancers = {
            'relative_strength': RelativeStrengthEnhancer(),
            'industry_position': IndustryPositionEnhancer(),
            'capital_flow': CapitalFlowEnhancer(),
            'events': EventsEnhancer()
        }
    
    def enhance(self, ts_code: str, asof: str = None) -> EnhancementsResponse:
        """
        执行所有增强模块
        
        Args:
            ts_code: 股票代码 (e.g., '600519.SH')
            asof: 数据日期
            
        Returns:
            EnhancementsResponse: 完整增强结果
        """
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        logger.info(f"[Enhancement] Starting enhancement for {ts_code} as of {asof}")
        
        results: Dict[str, ModuleResult] = {}
        available_modules = []
        
        for module_name, enhancer in self.enhancers.items():
            try:
                result = enhancer.safe_enhance(ts_code, asof)
                results[module_name] = result
                
                if result.available:
                    available_modules.append(module_name)
                    logger.info(f"[Enhancement] {module_name}: available")
                else:
                    logger.info(f"[Enhancement] {module_name}: unavailable - {result.degrade_reason}")
                    
            except Exception as e:
                logger.error(f"[Enhancement] {module_name} failed: {str(e)}")
                results[module_name] = ModuleResult.unavailable(f"执行异常: {str(e)}")
        
        response = EnhancementsResponse(
            version="1.0.0",
            generated_at=datetime.now(),
            available_modules=available_modules,
            relative_strength=results.get('relative_strength'),
            industry_position=results.get('industry_position'),
            capital_flow=results.get('capital_flow'),
            events=results.get('events')
        )
        
        logger.info(f"[Enhancement] Completed for {ts_code}: {len(available_modules)} modules available")
        
        return response
    
    def get_module_results_dict(self, ts_code: str, asof: str = None) -> Dict[str, ModuleResult]:
        """
        获取模块结果字典（用于 JudgementBuilder）
        """
        response = self.enhance(ts_code, asof)
        
        return {
            'relative_strength': response.relative_strength,
            'industry_position': response.industry_position,
            'capital_flow': response.capital_flow,
            'events': response.events
        }


# Singleton instance
enhancement_orchestrator = EnhancementOrchestrator()
