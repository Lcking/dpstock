"""
Relative Strength Enhancer
计算个股相对大盘/行业的超额收益
"""
from datetime import datetime, timedelta
from typing import Optional, List
from .base import BaseEnhancer
from ..schemas import ModuleResult, KeyMetric, ModuleDetails, TableData
from utils.logger import get_logger

logger = get_logger()


class RelativeStrengthEnhancer(BaseEnhancer):
    """
    相对强弱增强器
    
    计算 5/20/60 日超额收益 = 个股收益 - 基准收益
    标签阈值：≥+1.5% 强，≤-1.5% 弱，其余中性
    """
    
    MODULE_NAME = "relative_strength"
    
    # 基准指数
    BENCHMARKS = {
        '000300.SH': '沪深300',
        '000001.SH': '上证指数'
    }
    
    # 计算窗口
    WINDOWS = [5, 20, 60]
    
    # 阈值
    STRONG_THRESHOLD = 0.015  # +1.5%
    WEAK_THRESHOLD = -0.015   # -1.5%
    
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """计算相对强弱"""
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        hit, cached = self._get_cached(ts_code, asof.replace('-', ''))
        if hit and cached:
            return cached
        
        # 获取个股日线数据
        end_date = asof.replace('-', '')
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=90)).strftime('%Y%m%d')
        
        stock_df = self.client.get_daily(ts_code, start_date=start_date, end_date=end_date)
        
        if stock_df is None or len(stock_df) < 5:
            return ModuleResult.unavailable("无法获取个股行情数据")
        
        # 按日期排序（升序）
        stock_df = stock_df.sort_values('trade_date')
        
        # 获取基准指数数据（默认沪深300）
        bench_code = '000300.SH'
        bench_df = self.client.get_index_daily(bench_code, start_date=start_date, end_date=end_date)
        
        if bench_df is None or len(bench_df) < 5:
            # 降级：只计算个股收益，不做对比
            return self._make_degraded_result(ts_code, stock_df, asof)
        
        bench_df = bench_df.sort_values('trade_date')
        
        # 计算各窗口收益
        results = []
        key_metrics = []
        
        for window in self.WINDOWS:
            if len(stock_df) >= window and len(bench_df) >= window:
                # 个股收益
                stock_ret = (stock_df['close'].iloc[-1] / stock_df['close'].iloc[-window] - 1)
                # 基准收益
                bench_ret = (bench_df['close'].iloc[-1] / bench_df['close'].iloc[-window] - 1)
                # 超额收益
                excess = stock_ret - bench_ret
                
                results.append({
                    'window': window,
                    'stock_ret': round(stock_ret, 4),
                    'bench_ret': round(bench_ret, 4),
                    'excess': round(excess, 4)
                })
                
                # 生成关键指标
                label = self._get_strength_label(excess)
                key_metrics.append(KeyMetric(
                    key=f"excess_{window}d",
                    label=f"{window}日超额",
                    value=round(excess * 100, 2),
                    unit="pct"
                ))
        
        if not results:
            return ModuleResult.unavailable("数据不足以计算相对强弱")
        
        # 生成摘要（基于20日超额）
        excess_20d = next((r['excess'] for r in results if r['window'] == 20), results[0]['excess'])
        summary = self._generate_summary(excess_20d, self.BENCHMARKS[bench_code])
        
        result = ModuleResult(
            available=True,
            degraded=False,
            summary=summary,
            key_metrics=key_metrics,
            details=ModuleDetails(
                tables=[TableData(
                    name="window_returns",
                    columns=["window", "stock_ret", "bench_ret", "excess"],
                    rows=results
                )],
                notes=[
                    f"对照基准: {self.BENCHMARKS[bench_code]}",
                    "excess = 个股收益 - 基准收益",
                    f"数据区间: {start_date} ~ {end_date}"
                ]
            ),
            meta=self._make_meta(
                asof,
                cache_hit=False,
                window_days=self.WINDOWS,
                benchmarks=[bench_code],
                calculation="excess=stock_ret-bench_ret"
            )
        )
        
        # 写入缓存
        self._set_cache(ts_code, result, asof.replace('-', ''))
        
        return result
    
    def _get_strength_label(self, excess: float) -> str:
        """获取强弱标签"""
        if excess >= self.STRONG_THRESHOLD:
            return "强"
        elif excess <= self.WEAK_THRESHOLD:
            return "弱"
        else:
            return "中性"
    
    def _generate_summary(self, excess_20d: float, bench_name: str) -> str:
        """生成摘要文案"""
        pct = abs(excess_20d * 100)
        if excess_20d >= self.STRONG_THRESHOLD:
            return f"近20日相对{bench_name}跑赢{pct:.1f}%，属于强于市场走势。"
        elif excess_20d <= self.WEAK_THRESHOLD:
            return f"近20日相对{bench_name}跑输{pct:.1f}%，属于弱于市场走势。"
        else:
            return f"近20日相对{bench_name}表现持平（超额{excess_20d*100:+.1f}%），走势中性。"
    
    def _make_degraded_result(self, ts_code: str, stock_df, asof: str) -> ModuleResult:
        """生成降级结果（无基准对比）"""
        results = []
        for window in self.WINDOWS:
            if len(stock_df) >= window:
                stock_ret = (stock_df['close'].iloc[-1] / stock_df['close'].iloc[-window] - 1)
                results.append({
                    'window': window,
                    'stock_ret': round(stock_ret, 4),
                    'bench_ret': None,
                    'excess': None
                })
        
        return ModuleResult.degraded_result(
            reason="无法获取基准指数数据",
            summary="仅显示个股收益，无法计算相对强弱",
            key_metrics=[
                KeyMetric(key=f"stock_ret_{r['window']}d", label=f"{r['window']}日涨跌", value=round(r['stock_ret']*100, 2), unit="pct")
                for r in results
            ],
            details=ModuleDetails(
                tables=[TableData(name="window_returns", columns=["window", "stock_ret"], rows=results)],
                notes=["降级模式：仅个股数据可用"]
            ),
            meta=self._make_meta(asof, cache_hit=False)
        )
