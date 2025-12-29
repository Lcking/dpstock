"""
POC: Test DeepSeek API with Analysis V1 Schema
测试 DeepSeek API 是否能输出 Analysis V1 格式
"""
import sys
import os
# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import httpx
import asyncio
from dotenv import load_dotenv
from schemas.analysis_v1 import AnalysisV1Response
from pydantic import ValidationError
from utils.api_utils import APIUtils

# 加载环境变量
load_dotenv()

API_URL = os.getenv('API_URL')
API_KEY = os.getenv('API_KEY')
API_MODEL = os.getenv('API_MODEL', 'deepseek-reasoner')

# Analysis V1 示例 prompt（修复后的版本）
ANALYSIS_V1_PROMPT = """
你是一个专业的股票技术分析师。请对以下股票进行结构化分析，并严格按照 JSON schema 格式输出。

**重要规则：**
1. 只进行结构分析，不做走势预测
2. 不提供买卖建议、目标价
3. 判断区只提供结构前提的候选项，让用户自己判断
4. 必须严格使用指定的枚举值

**枚举值说明（必须严格遵守）：**
- structure_type: "uptrend" | "downtrend" | "consolidation"
- ma200_position: "above" | "below" | "near" | "no_data"
- phase: "early" | "middle" | "late" | "unclear"
- pattern_type: "head_shoulders" | "double_top_bottom" | "triangle" | "channel" | "wedge" | "flag" | "none"
- signal: "strengthening" | "weakening" | "extreme" | "neutral"
- risk_level: "high" | "medium" | "low"
- option_type: "structure_premise" | "execution_method" | "risk_check"

**股票信息：**
- 代码：000001
- 名称：平安银行
- 当前价格：12.50
- MA5: 12.30, MA20: 12.00, MA200: 11.50
- RSI: 55
- 成交量：放量

**请按以下 JSON 格式输出（必须是有效的 JSON）：**

```json
{
  "stock_code": "000001",
  "stock_name": "平安银行",
  "market_type": "A",
  "analysis_date": "2025-12-29T16:00:00",
  "structure_snapshot": {
    "structure_type": "uptrend",
    "ma200_position": "above",
    "phase": "middle",
    "key_levels": [
      {"price": 12.00, "label": "支撑位1"},
      {"price": 11.50, "label": "支撑位2(MA200)"},
      {"price": 12.80, "label": "压力位1"}
    ],
    "trend_description": "价格位于MA200上方，短中期均线呈多头排列"
  },
  "pattern_fitting": {
    "pattern_type": "channel",
    "pattern_description": "价格在上升通道中运行",
    "completion_rate": 65
  },
  "indicator_translate": {
    "indicators": [
      {
        "name": "RSI(14)",
        "value": "55",
        "signal": "strengthening",
        "interpretation": "RSI位于50-70区间，显示多头力量占优但未进入超买"
      },
      {
        "name": "成交量",
        "value": "1.2倍均量",
        "signal": "strengthening",
        "interpretation": "成交量温和放大，配合价格上涨"
      }
    ],
    "global_note": "技术指标整体偏多，但需关注是否能突破压力位"
  },
  "risk_of_misreading": {
    "risk_level": "medium",
    "risk_factors": [
      "价格接近前期高点，存在回调可能",
      "成交量未显著放大，突破力度待观察"
    ],
    "risk_flags": ["volume_divergence"],
    "caution_note": "需关注价格能否有效突破12.80压力位"
  },
  "judgment_zone": {
    "candidates": [
      {
        "option_id": "A",
        "option_type": "structure_premise",
        "description": "上升结构延续，价格保持在MA200上方运行"
      },
      {
        "option_id": "B",
        "option_type": "structure_premise",
        "description": "测试12.00支撑位，结构前提受到挑战"
      },
      {
        "option_id": "C",
        "option_type": "structure_premise",
        "description": "跌破MA200(11.50)，上升结构被破坏"
      }
    ],
    "risk_checks": [
      "关键支撑位(12.00)失守风险",
      "MA200位置关系改变风险",
      "成交量配合情况"
    ],
    "note": "以上为结构分析，非走势预测，系统不提供买卖建议"
  }
}
```

**关键要求：**
1. pattern_type 必须是: "channel", "triangle", "wedge", "flag", "none" 等之一
2. signal 必须是: "strengthening", "weakening", "extreme", "neutral" 之一
3. option_type 必须是: "structure_premise", "execution_method", "risk_check" 之一
4. risk_checks 必须是字符串数组，不是对象数组

**请直接输出 JSON，不要添加任何其他文字说明。**
"""

async def test_analysis_v1_output():
    """测试 DeepSeek 是否能输出 Analysis V1 格式"""
    
    print("=" * 60)
    print("POC: 测试 DeepSeek API 输出 Analysis V1 格式")
    print("=" * 60)
    print()
    
    # 准备请求
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }
    
    request_data = {
        "model": API_MODEL,
        "messages": [{"role": "user", "content": ANALYSIS_V1_PROMPT}],
        "temperature": 0.3,  # 降低温度以获得更稳定的 JSON 输出
        "stream": False
    }
    
    print(f"📡 发送请求到: {API_URL}")
    print(f"📦 模型: {API_MODEL}")
    print()
    
    # 格式化 API URL
    api_url = APIUtils.format_api_url(API_URL)
    print(f"🔗 完整 API URL: {api_url}")
    print()
    
    try:
        async with httpx.AsyncClient(timeout=120) as client:  # 增加到 120 秒
            response = await client.post(api_url, json=request_data, headers=headers)
            
            if response.status_code != 200:
                print(f"❌ API 请求失败: {response.status_code}")
                print(response.text)
                return False
            
            result = response.json()
            
            # 提取 AI 返回的内容
            content = result.get('choices', [{}])[0].get('message', {}).get('content', '')
            
            print("📄 AI 返回的原始内容:")
            print("-" * 60)
            print(content[:500] + "..." if len(content) > 500 else content)
            print("-" * 60)
            print()
            
            # 尝试提取 JSON（可能被包裹在 markdown 代码块中）
            json_str = content
            
            # 移除可能的 markdown 代码块标记
            if "```json" in json_str:
                json_str = json_str.split("```json")[1].split("```")[0].strip()
            elif "```" in json_str:
                json_str = json_str.split("```")[1].split("```")[0].strip()
            
            print("🔍 提取的 JSON 字符串:")
            print("-" * 60)
            print(json_str[:500] + "..." if len(json_str) > 500 else json_str)
            print("-" * 60)
            print()
            
            # 解析 JSON
            try:
                parsed_json = json.loads(json_str)
                print("✅ JSON 解析成功")
                print()
                
                # 验证是否符合 Analysis V1 schema
                print("🔬 验证 Analysis V1 Schema...")
                try:
                    analysis_v1 = AnalysisV1Response(**parsed_json)
                    print("✅ Analysis V1 Schema 验证通过！")
                    print()
                    
                    # 显示关键信息
                    print("📊 关键信息:")
                    print(f"  - 股票代码: {analysis_v1.stock_code}")
                    print(f"  - 结构类型: {analysis_v1.structure_snapshot.structure_type}")
                    print(f"  - MA200位置: {analysis_v1.structure_snapshot.ma200_position}")
                    print(f"  - 阶段: {analysis_v1.structure_snapshot.phase}")
                    print(f"  - 候选项数量: {len(analysis_v1.judgment_zone.candidates)}")
                    print(f"  - 风险检查项数量: {len(analysis_v1.judgment_zone.risk_checks)}")
                    print()
                    
                    print("🎯 判断区候选项:")
                    for candidate in analysis_v1.judgment_zone.candidates:
                        print(f"  {candidate.option_id}. [{candidate.option_type.value}] {candidate.description}")
                    print()
                    
                    print("⚠️ 风险检查项:")
                    for risk in analysis_v1.judgment_zone.risk_checks:
                        print(f"  - {risk}")
                    print()
                    
                    # 保存示例输出
                    with open('poc_analysis_v1_output.json', 'w', encoding='utf-8') as f:
                        json.dump(parsed_json, f, ensure_ascii=False, indent=2)
                    print("💾 完整输出已保存到: poc_analysis_v1_output.json")
                    print()
                    
                    return True
                    
                except ValidationError as e:
                    print("❌ Analysis V1 Schema 验证失败:")
                    print(e)
                    print()
                    return False
                    
            except json.JSONDecodeError as e:
                print(f"❌ JSON 解析失败: {e}")
                print()
                return False
                
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_analysis_v1_output())
    
    print("=" * 60)
    if success:
        print("🎉 POC 成功！DeepSeek 可以输出 Analysis V1 格式")
        print("✅ 下一步：将此 prompt 集成到 ai_analyzer.py")
    else:
        print("⚠️ POC 失败，需要调整 prompt 或 schema")
    print("=" * 60)
