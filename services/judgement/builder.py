"""
Judgement Builder
根据 enhancements 生成判断区增强内容
"""
from typing import Dict, Any, List, Optional
from datetime import datetime
from services.tushare.schemas import (
    EvidenceDomain, EnhancedPremise, RiskCheckItem, 
    JudgmentCandidate, JudgmentZoneV11, ModuleResult
)
from utils.logger import get_logger

logger = get_logger()


class JudgementBuilder:
    """
    判断区构建器 v1.1
    
    根据 enhancements 数据生成：
    - enhanced_premises: 增强前提（附加到 A/B/C 候选项）
    - risk_checks: 包含新增 #5~#7 的风险检查项
    - recommended_risk_checks: 推荐的检查项
    """
    
    # 原有风险检查项 (#1~#4)
    BASE_RISK_CHECKS = [
        RiskCheckItem(
            id="VOL_RATIO",
            domain=EvidenceDomain.PRICE,
            text="观察突破时成交量是否显著放大（量比≥1.2）",
            available=True
        ),
        RiskCheckItem(
            id="RSI_THRESH",
            domain=EvidenceDomain.PRICE,
            text="观察RSI是否进入超买/超卖区域（>70或<30）",
            available=True
        ),
        RiskCheckItem(
            id="MA_CROSS",
            domain=EvidenceDomain.PRICE,
            text="观察短期均线与长期均线的交叉情况",
            available=True
        ),
        RiskCheckItem(
            id="KEY_LEVEL",
            domain=EvidenceDomain.PRICE,
            text="观察价格是否站稳/跌破关键支撑/压力位",
            available=True
        )
    ]
    
    # 新增风险检查项 (#5~#7)
    ENHANCED_RISK_CHECKS = [
        RiskCheckItem(
            id="RS_EXCESS",
            domain=EvidenceDomain.RELATIVE,
            text="观察相对沪深300/行业指数的超额收益是否改善（20日超额回到>-1.5%）",
            available=True  # 将根据模块可用性动态设置
        ),
        RiskCheckItem(
            id="FLOW_REVERSAL",
            domain=EvidenceDomain.FLOW,
            text="观察近3日/5日资金净流入是否由负转正或持续为正（区分承接/分歧）",
            available=True
        ),
        RiskCheckItem(
            id="EVENT_WATCH",
            domain=EvidenceDomain.EVENT,
            text="观察验证期内是否出现新公告/停复牌/分红除权等事件，若出现需重新评估",
            available=True
        )
    ]
    
    def build_enhanced_premises(
        self, 
        candidate_id: str, 
        candidate_text: str,
        enhancements: Dict[str, ModuleResult]
    ) -> List[EnhancedPremise]:
        """
        为候选项生成增强前提
        
        Args:
            candidate_id: 候选项ID ('A', 'B', 'C')
            candidate_text: 候选项原文案
            enhancements: 增强模块结果字典
        """
        premises = []
        
        # 相对强弱前提
        rs_module = enhancements.get('relative_strength')
        if rs_module and rs_module.available:
            # 根据候选项类型生成不同前提
            if '突破' in candidate_text or '上升' in candidate_text or '反弹' in candidate_text:
                premises.append(EnhancedPremise(
                    id=f"{candidate_id}_REL_RS_IMPROVE",
                    domain=EvidenceDomain.RELATIVE,
                    text="相对沪深300的20日超额需改善至>-1.5%或继续改善，否则反弹/突破判断可信度下降。",
                    binding={"module": "relative_strength", "metric": "excess_20d"},
                    available=True
                ))
            elif '跌破' in candidate_text or '下降' in candidate_text:
                premises.append(EnhancedPremise(
                    id=f"{candidate_id}_REL_RS_WEAK",
                    domain=EvidenceDomain.RELATIVE,
                    text="若相对大盘已持续走弱（超额<-3%），下行结构更易被确认。",
                    binding={"module": "relative_strength", "metric": "excess_20d"},
                    available=True
                ))
        
        # 资金流向前提
        flow_module = enhancements.get('capital_flow')
        if flow_module and flow_module.available:
            premises.append(EnhancedPremise(
                id=f"{candidate_id}_FLOW_CONFIRM",
                domain=EvidenceDomain.FLOW,
                text="若出现承接放量（放量且净流入）更支持企稳；若为分歧放量（放量但净流出）需降低置信度。",
                binding={"module": "capital_flow", "metric": "flow_label"},
                available=True
            ))
        
        # 事件前提
        events_module = enhancements.get('events')
        if events_module and events_module.available:
            # 检查是否有事件
            has_events = False
            for metric in events_module.key_metrics:
                if metric.key == 'event_count_30d' and metric.value > 0:
                    has_events = True
                    break
            
            if has_events:
                premises.append(EnhancedPremise(
                    id=f"{candidate_id}_EVENT_ADJUST",
                    domain=EvidenceDomain.EVENT,
                    text="若近30日存在除权除息/重大公告扰动，验证周期建议≥7天并以复权口径观察关键位。",
                    binding={"module": "events", "metric": "has_corporate_action"},
                    available=True
                ))
        
        return premises
    
    def build_risk_checks(self, enhancements: Dict[str, ModuleResult]) -> List[RiskCheckItem]:
        """
        构建完整风险检查项列表（包含新增 #5~#7）
        """
        risk_checks = list(self.BASE_RISK_CHECKS)
        
        # 添加增强检查项，根据模块可用性设置 available
        for check in self.ENHANCED_RISK_CHECKS:
            new_check = RiskCheckItem(
                id=check.id,
                domain=check.domain,
                text=check.text,
                available=self._is_domain_available(check.domain, enhancements)
            )
            risk_checks.append(new_check)
        
        return risk_checks
    
    def _is_domain_available(self, domain: EvidenceDomain, enhancements: Dict[str, ModuleResult]) -> bool:
        """检查证据域对应的模块是否可用"""
        domain_module_map = {
            EvidenceDomain.RELATIVE: 'relative_strength',
            EvidenceDomain.FLOW: 'capital_flow',
            EvidenceDomain.EVENT: 'events'
        }
        
        module_name = domain_module_map.get(domain)
        if not module_name:
            return True  # PRICE 域始终可用
        
        module = enhancements.get(module_name)
        return module is not None and module.available
    
    def build_recommended_checks(self, enhancements: Dict[str, ModuleResult]) -> List[str]:
        """
        生成推荐的检查项列表
        """
        recommended = ["VOL_RATIO", "KEY_LEVEL"]  # 基础推荐
        
        # 相对强弱可用 → 推荐 #5
        rs_module = enhancements.get('relative_strength')
        if rs_module and rs_module.available:
            recommended.append("RS_EXCESS")
        
        # 资金流向可用 → 推荐 #6
        flow_module = enhancements.get('capital_flow')
        if flow_module and flow_module.available:
            recommended.append("FLOW_REVERSAL")
        
        # 有事件 → 推荐 #7
        events_module = enhancements.get('events')
        if events_module and events_module.available:
            for metric in events_module.key_metrics:
                if metric.key == 'event_count_30d' and metric.value > 0:
                    recommended.append("EVENT_WATCH")
                    break
        
        return recommended
    
    def build_judgment_zone_v11(
        self,
        original_candidates: List[Dict[str, Any]],
        enhancements: Dict[str, ModuleResult]
    ) -> JudgmentZoneV11:
        """
        构建判断区 v1.1
        
        Args:
            original_candidates: 原有候选项列表 [{"option_id": "A", "description": "..."}]
            enhancements: 增强模块结果
        """
        # 构建带增强前提的候选项
        candidates = []
        for orig in original_candidates:
            candidate_id = orig.get('option_id', 'A')
            candidate_text = orig.get('description', '')
            
            enhanced_premises = self.build_enhanced_premises(
                candidate_id, candidate_text, enhancements
            )
            
            candidates.append(JudgmentCandidate(
                id=candidate_id,
                text=candidate_text,
                enhanced_premises=enhanced_premises
            ))
        
        # 构建风险检查项
        risk_checks = self.build_risk_checks(enhancements)
        
        # 构建推荐检查项
        recommended = self.build_recommended_checks(enhancements)
        
        return JudgmentZoneV11(
            version="1.1.0",
            candidates=candidates,
            risk_checks=risk_checks,
            recommended_risk_checks=recommended,
            validation_period_options=[1, 3, 7, 30],
            defaults={
                "selected_candidate": None,
                "selected_premises": [],
                "selected_risk_checks": ["VOL_RATIO", "RSI_THRESH", "KEY_LEVEL"],
                "validation_period": 7
            }
        )


# Singleton instance
judgement_builder = JudgementBuilder()
