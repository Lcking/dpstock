"""
Enhancement API Routes
Tushare 数据增强 API 端点
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime
from services.tushare.orchestrator import enhancement_orchestrator
from services.tushare.schemas import EnhancementsResponse
from services.judgement.builder import judgement_builder
from utils.logger import get_logger

logger = get_logger()

router = APIRouter()


@router.get("/api/enhancements/{ts_code}")
async def get_enhancements(
    ts_code: str,
    asof: Optional[str] = Query(None, description="数据日期 YYYY-MM-DD，默认为今天")
):
    """
    获取股票增强数据
    
    Args:
        ts_code: 股票代码 (e.g., '600519.SH', '000001.SZ')
        asof: 数据日期
    
    Returns:
        EnhancementsResponse: 增强数据
    """
    try:
        # 标准化股票代码格式
        ts_code = normalize_ts_code(ts_code)
        
        logger.info(f"[EnhancementAPI] Request for {ts_code}, asof={asof}")
        
        # 执行增强
        result = enhancement_orchestrator.enhance(ts_code, asof)
        
        return result.model_dump()
        
    except Exception as e:
        logger.error(f"[EnhancementAPI] Error for {ts_code}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/judgment-zone-v11/{ts_code}")
async def get_judgment_zone_v11(
    ts_code: str,
    asof: Optional[str] = Query(None, description="数据日期"),
    candidate_a: str = Query("若有效突破压力位且放量，结构转为上升", description="候选项A文案"),
    candidate_b: str = Query("若跌破支撑位且放量，结构转为下降", description="候选项B文案"),
    candidate_c: str = Query("继续在区间内震荡，等待方向明确", description="候选项C文案")
):
    """
    获取判断区 v1.1 增强数据
    
    根据原有候选项和增强数据生成完整的判断区 v1.1 结构
    """
    try:
        ts_code = normalize_ts_code(ts_code)
        
        logger.info(f"[JudgmentV11API] Request for {ts_code}")
        
        # 获取增强模块结果
        module_results = enhancement_orchestrator.get_module_results_dict(ts_code, asof)
        
        # 构建原有候选项
        original_candidates = [
            {"option_id": "A", "description": candidate_a},
            {"option_id": "B", "description": candidate_b},
            {"option_id": "C", "description": candidate_c}
        ]
        
        # 构建判断区 v1.1
        judgment_v11 = judgement_builder.build_judgment_zone_v11(original_candidates, module_results)
        
        return judgment_v11.model_dump()
        
    except Exception as e:
        logger.error(f"[JudgmentV11API] Error for {ts_code}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


def normalize_ts_code(code: str) -> str:
    """
    标准化股票代码为 Tushare 格式
    
    输入: '600519', '600519.SH', '000001', '000001.SZ'
    输出: '600519.SH', '000001.SZ'
    """
    code = code.upper().strip()
    
    # 如果已经有后缀，直接返回
    if '.' in code:
        return code
    
    # 根据代码前缀判断市场
    if code.startswith(('6', '9')):
        return f"{code}.SH"
    elif code.startswith(('0', '3', '2')):
        return f"{code}.SZ"
    else:
        # 默认上海
        return f"{code}.SH"
