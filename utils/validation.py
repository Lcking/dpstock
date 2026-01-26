"""
Stock Code Validation Utilities
Validates and normalizes stock codes for different markets
"""
import re
from typing import Optional, Tuple
from fastapi import HTTPException


# Valid stock code patterns
# A-share: 6xxxxx.SH, 0xxxxx.SZ, 3xxxxx.SZ, 9xxxxx.SH
# ETF/LOF: 5xxxxx.SH/SZ, 1xxxxx.SH/SZ
A_SHARE_PATTERN = re.compile(r'^[0369]\d{5}(\.(SH|SZ))?$', re.IGNORECASE)
ETF_LOF_PATTERN = re.compile(r'^[15]\d{5}(\.(SH|SZ))?$', re.IGNORECASE)
HK_PATTERN = re.compile(r'^\d{5}(\.HK)?$', re.IGNORECASE)
US_PATTERN = re.compile(r'^[A-Z]{1,5}$', re.IGNORECASE)


def validate_ts_code(code: str, allow_us: bool = True, allow_hk: bool = True) -> bool:
    """
    Validate if a stock code is valid format
    
    Args:
        code: Stock code to validate
        allow_us: Whether to allow US stock codes
        allow_hk: Whether to allow HK stock codes
        
    Returns:
        True if valid, False otherwise
    """
    if not code or len(code) < 1 or len(code) > 12:
        return False
    
    code = code.strip().upper()
    
    # Check A-share
    if A_SHARE_PATTERN.match(code):
        return True
    
    # Check ETF/LOF
    if ETF_LOF_PATTERN.match(code):
        return True
    
    # Check HK
    if allow_hk and HK_PATTERN.match(code):
        return True
    
    # Check US
    if allow_us and US_PATTERN.match(code):
        return True
    
    return False


def normalize_ts_code(code: str) -> str:
    """
    标准化股票代码为 Tushare 格式
    
    输入: '600519', '600519.SH', '000001', '000001.SZ'
    输出: '600519.SH', '000001.SZ'
    
    Raises:
        HTTPException 400 if code format is invalid
    """
    if not code:
        raise HTTPException(status_code=400, detail="股票代码不能为空")
    
    code = code.upper().strip()
    
    # Validate format first
    if not validate_ts_code(code):
        raise HTTPException(
            status_code=400, 
            detail=f"无效的股票代码格式: {code}。请输入正确的A股(如600519)、港股(如00700)或美股(如AAPL)代码"
        )
    
    # If already has suffix, return as-is
    if '.' in code:
        return code
    
    # Add suffix based on code prefix
    if code.startswith(('6', '9')):
        return f"{code}.SH"
    elif code.startswith(('0', '3', '2')):
        return f"{code}.SZ"
    elif code.startswith('5'):
        # ETF - could be SH or SZ, default to SH
        return f"{code}.SH"
    elif code.startswith('1'):
        # LOF - could be SH or SZ, default to SZ
        return f"{code}.SZ"
    else:
        # US/HK stocks - return as-is
        return code


def validate_ts_code_or_raise(code: str) -> str:
    """
    Validate and normalize ts_code, raise HTTPException if invalid
    
    This is a convenience function for API routes.
    """
    return normalize_ts_code(code)


def validate_ts_code_list(codes: list, max_count: int = 50) -> list:
    """
    Validate a list of ts_codes
    
    Args:
        codes: List of stock codes
        max_count: Maximum allowed count
        
    Returns:
        List of normalized codes
        
    Raises:
        HTTPException if any code is invalid or count exceeds limit
    """
    if not codes:
        raise HTTPException(status_code=400, detail="股票代码列表不能为空")
    
    if len(codes) > max_count:
        raise HTTPException(
            status_code=400, 
            detail=f"股票代码数量超过限制: {len(codes)} > {max_count}"
        )
    
    normalized = []
    invalid = []
    
    for code in codes:
        if validate_ts_code(code):
            normalized.append(normalize_ts_code(code))
        else:
            invalid.append(code)
    
    if invalid:
        raise HTTPException(
            status_code=400,
            detail=f"以下股票代码格式无效: {', '.join(invalid[:5])}"
        )
    
    return normalized
