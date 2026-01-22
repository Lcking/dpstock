"""
Capital Flow Enhancer
资金流向分析（Lite 版本）
"""
from datetime import datetime, timedelta
from .base import BaseEnhancer
from ..schemas import ModuleResult, KeyMetric, ModuleDetails, TableData
from utils.logger import get_logger

logger = get_logger()


class CapitalFlowEnhancer(BaseEnhancer):
    """
    资金流向增强器（Lite）
    
    输出: net_inflow_today, net_inflow_5d, flow_label
    
    flow_label 规则：
    - vol_ratio≥1.2 & flow>0 → 承接放量
    - vol_ratio≥1.2 & flow<0 → 分歧放量
    - vol_ratio<0.9 & flow<0 → 缩量阴跌/观望
    - vol_ratio<0.9 & flow>0 → 缩量潜伏（谨慎）
    - else → 中性
    """
    
    MODULE_NAME = "capital_flow"
    
    # 量比阈值
    VOL_RATIO_HIGH = 1.2
    VOL_RATIO_LOW = 0.9
    
    def enhance(self, ts_code: str, asof: str = None) -> ModuleResult:
        """获取资金流向信息"""
        if asof is None:
            asof = datetime.now().strftime('%Y-%m-%d')
        
        # 检查缓存
        hit, cached = self._get_cached(ts_code, asof.replace('-', ''))
        if hit and cached:
            return cached
        
        end_date = asof.replace('-', '')
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
        
        # 尝试获取资金流向数据
        flow_df = self.client.get_moneyflow(ts_code, start_date=start_date, end_date=end_date)
        
        if flow_df is None or len(flow_df) == 0:
            # 资金接口不可用，尝试从日线数据推算
            return self._fallback_from_daily(ts_code, start_date, end_date, asof)
        
        # 按日期排序
        flow_df = flow_df.sort_values('trade_date')
        
        # 计算净流入（单位：万元）
        if 'net_mf_amount' in flow_df.columns:
            net_today = flow_df['net_mf_amount'].iloc[-1] if len(flow_df) > 0 else 0
            net_5d = flow_df['net_mf_amount'].tail(5).sum() if len(flow_df) >= 5 else flow_df['net_mf_amount'].sum()
        else:
            # 尝试其他字段名
            net_today = 0
            net_5d = 0
        
        # 获取量比（需要从日线数据计算）
        vol_ratio = self._get_volume_ratio(ts_code, end_date)
        
        # 计算 flow_label
        flow_label = self._calculate_flow_label(vol_ratio, net_today)
        
        key_metrics = [
            KeyMetric(key="net_inflow_today", label="今日净流入", value=round(net_today/10000, 2), unit="亿"),
            KeyMetric(key="net_inflow_5d", label="5日净流入", value=round(net_5d/10000, 2), unit="亿"),
            KeyMetric(key="vol_ratio", label="量比", value=round(vol_ratio, 2) if vol_ratio else None, unit=None),
            KeyMetric(key="flow_label", label="资金语义", value=flow_label, unit=None)
        ]
        
        summary = self._generate_summary(flow_label, net_today, vol_ratio)
        
        result = ModuleResult(
            available=True,
            degraded=False,
            summary=summary,
            key_metrics=key_metrics,
            details=ModuleDetails(
                tables=[TableData(
                    name="flow_history",
                    columns=["date", "net_flow"],
                    rows=[{"date": row['trade_date'], "net_flow": row.get('net_mf_amount', 0)} 
                          for _, row in flow_df.tail(5).iterrows()]
                )],
                notes=[
                    "净流入 = 主力资金净买入额",
                    "量比 = 当日成交量 / 5日均量",
                    f"数据区间: {start_date} ~ {end_date}"
                ]
            ),
            meta=self._make_meta(asof, cache_hit=False)
        )
        
        self._set_cache(ts_code, result, asof.replace('-', ''))
        return result
    
    def _get_volume_ratio(self, ts_code: str, end_date: str) -> float:
        """计算量比"""
        start_date = (datetime.strptime(end_date, '%Y%m%d') - timedelta(days=10)).strftime('%Y%m%d')
        daily_df = self.client.get_daily(ts_code, start_date=start_date, end_date=end_date)
        
        if daily_df is None or len(daily_df) < 2:
            return 1.0
        
        daily_df = daily_df.sort_values('trade_date')
        today_vol = daily_df['vol'].iloc[-1]
        avg_vol = daily_df['vol'].iloc[-6:-1].mean() if len(daily_df) >= 6 else daily_df['vol'].mean()
        
        return today_vol / avg_vol if avg_vol > 0 else 1.0
    
    def _calculate_flow_label(self, vol_ratio: float, net_flow: float) -> str:
        """计算资金语义标签"""
        if vol_ratio is None:
            vol_ratio = 1.0
        
        if vol_ratio >= self.VOL_RATIO_HIGH:
            if net_flow > 0:
                return "承接放量"
            else:
                return "分歧放量"
        elif vol_ratio < self.VOL_RATIO_LOW:
            if net_flow < 0:
                return "缩量观望"
            else:
                return "缩量潜伏"
        else:
            return "中性"
    
    def _generate_summary(self, flow_label: str, net_today: float, vol_ratio: float) -> str:
        """生成摘要"""
        net_desc = "净流入" if net_today > 0 else "净流出"
        net_val = abs(net_today / 10000)
        
        if flow_label == "承接放量":
            return f"放量且{net_desc}{net_val:.2f}亿，更像承接放量，资金积极。"
        elif flow_label == "分歧放量":
            return f"放量但{net_desc}{net_val:.2f}亿，更像分歧放量，需提高警惕（非预测）。"
        elif flow_label == "缩量观望":
            return f"缩量且{net_desc}，市场观望情绪浓厚。"
        elif flow_label == "缩量潜伏":
            return f"缩量但有小幅净流入，可能有资金低调潜伏（谨慎解读）。"
        else:
            return f"资金流向中性，{net_desc}{net_val:.2f}亿。"
    
    def _fallback_from_daily(self, ts_code: str, start_date: str, end_date: str, asof: str) -> ModuleResult:
        """降级：从日线数据推算"""
        daily_df = self.client.get_daily(ts_code, start_date=start_date, end_date=end_date)
        
        if daily_df is None or len(daily_df) < 2:
            return ModuleResult.unavailable("资金流向和日线数据均不可用")
        
        daily_df = daily_df.sort_values('trade_date')
        vol_ratio = self._get_volume_ratio(ts_code, end_date)
        
        # 通过涨跌判断资金方向（简化推算）
        today_pct = daily_df['pct_chg'].iloc[-1] if 'pct_chg' in daily_df.columns else 0
        flow_direction = 1 if today_pct > 0 else -1
        
        flow_label = self._calculate_flow_label(vol_ratio, flow_direction)
        
        return ModuleResult.degraded_result(
            reason="资金流向接口不可用，使用日线数据推算",
            summary=f"量比{vol_ratio:.2f}，{flow_label}（基于涨跌推算，非精确资金数据）",
            key_metrics=[
                KeyMetric(key="vol_ratio", label="量比", value=round(vol_ratio, 2), unit=None),
                KeyMetric(key="flow_label", label="资金语义", value=flow_label, unit=None)
            ],
            meta=self._make_meta(asof, cache_hit=False)
        )
