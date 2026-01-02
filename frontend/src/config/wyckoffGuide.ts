/**
 * 威科夫二世判断引导配置
 * 
 * 这是一个纯解释层,不产生新结论,只在用户做判断时提供认知减速
 */

// Risk Flag 解释结构
export interface RiskFlagExplanation {
    title: string;
    explanation: string;
    reminder: string;
}

// 判断状态消息结构
export interface JudgmentStatusMessage {
    title: string;
    meaning: string;
    suggestion: string;
}

/**
 * risk_flag 中英文映射
 * 后端返回中文key,前端需要映射到英文key
 */
export const RISK_FLAG_CN_TO_EN: Record<string, string> = {
    // 常见的中文 risk_flag 映射
    "均线粘合": "pattern_as_signal",
    "缩量": "low_volume_ambiguity",
    "背离": "indicator_overinterpretation",
    "关键位": "key_level_overconfidence",
    "趋势延续": "trend_perpetuity_illusion",
    "消息面": "news_dependency",
    "确认偏误": "confirmation_bias",
    "前提失效": "premise_invalidation_denial"
};

/**
 * 威科夫二世误判解释字典
 * 
 * 每个 risk_flag key 对应一段教育性解释
 * 文案原则: 中性、克制、允许失败、无交易建议
 */
export const WyckoffMisreadingGuide: Record<string, RiskFlagExplanation> = {
    // 关键位过度自信
    key_level_overconfidence: {
        title: "关键位置的局限性",
        explanation: "支撑/压力位只是历史价格聚集区,不是未来行为的保证。价格可能在此反应,也可能直接穿越。把位置当作'必然反转点'是常见的过度解读。",
        reminder: "位置只是参考坐标,不是交易信号"
    },

    // 把形态当信号
    pattern_as_signal: {
        title: "形态不等于信号",
        explanation: "图表形态(如头肩顶、三角形)只是价格运动的几何描述,不包含方向预测能力。形态完成后,价格可能上涨、下跌或横盘,取决于当时的供需关系。",
        reminder: "形态是结构描述,不是行动指令"
    },

    // 低量模糊性
    low_volume_ambiguity: {
        title: "低成交量的多重解释",
        explanation: "低量可能意味着:观望、控盘、流动性枯竭或市场冷淡。单凭成交量无法判断后续方向,需要结合价格行为与市场阶段综合观察。",
        reminder: "低量是现象,不是方向指引"
    },

    // 确认偏误
    confirmation_bias: {
        title: "寻找证据的陷阱",
        explanation: "当你已有判断倾向时,容易只看到支持观点的信息,忽略矛盾信号。这会让你在错误判断中停留过久,错过调整时机。",
        reminder: "主动寻找反驳自己的证据"
    },

    // 前提失效否认
    premise_invalidation_denial: {
        title: "不愿承认判断前提已变",
        explanation: "当初做判断时的关键前提(如'量价配合'、'趋势延续')可能已被破坏,但人倾向于找理由维持原判断。及时承认前提失效,是保护资本的关键。",
        reminder: "前提破坏时,判断需要重新审视"
    },

    // 指标过度解读
    indicator_overinterpretation: {
        title: "技术指标的滞后性",
        explanation: "RSI、MACD等指标都是价格的数学变换,本质上是滞后的。它们可以描述'已发生的状态',但不能预测'即将发生的变化'。",
        reminder: "指标是后视镜,不是望远镜"
    },

    // 趋势永恒幻觉
    trend_perpetuity_illusion: {
        title: "趋势不会永远延续",
        explanation: "上涨或下跌趋势都会结束,但结束的时间和方式无法提前确定。'趋势是你的朋友'不意味着趋势永不改变,而是提醒你尊重当前状态。",
        reminder: "趋势会转变,只是时间未知"
    },

    // 消息面依赖
    news_dependency: {
        title: "消息的不确定性",
        explanation: "利好/利空消息的市场反应是不可预测的。同样的消息在不同阶段可能引发完全相反的价格行为,因为市场已经提前反应或选择性忽略。",
        reminder: "消息是催化剂,不是方向决定器"
    }
};

/**
 * 判断状态解释消息
 * 
 * 用于 MyJudgments 中解释判断验证状态
 */
export const JudgmentStatusMessages: Record<string, JudgmentStatusMessage> = {
    maintained: {
        title: "判断前提目前维持",
        meaning: "您当初记录的结构前提尚未被明显破坏。但这不代表判断'正确',只是前提'尚未失效'。市场随时可能改变。",
        suggestion: "定期重新审视判断前提是否仍然成立。不要因为前提维持而产生过度自信。"
    },

    weakened: {
        title: "判断前提出现削弱迹象",
        meaning: "部分关键前提的支撑证据减弱,但尚未完全破坏。这是重新评估的信号,不是恐慌的理由。",
        suggestion: "重新检查当初的判断逻辑是否仍然有效。考虑是否需要调整判断或接受前提失效。削弱不等于错误,是市场动态的正常表现。"
    },

    broken: {
        title: "判断前提已被破坏",
        meaning: "您当初依据的关键结构前提已不再成立。这是正常的,判断本就是用来被验证和淘汰的。前提破坏不代表您'判断错误',而是市场演化的结果。",
        suggestion: "回顾当初的判断逻辑,哪些前提过于脆弱?是否存在确认偏误?下次做判断时,如何设置更稳健的前提?承认判断失效,比坚持错误判断更有价值。"
    }
};

/**
 * 获取 risk_flag 的解释
 * 支持中文key(通过映射)和英文key
 * 使用关键词匹配以适应生产环境的完整句子
 * 如果 key 不存在,返回通用提醒
 */
export function getRiskFlagExplanation(flagKey: string): RiskFlagExplanation {
    // 先尝试精确匹配
    const englishKey = RISK_FLAG_CN_TO_EN[flagKey] || flagKey;

    if (WyckoffMisreadingGuide[englishKey]) {
        return WyckoffMisreadingGuide[englishKey];
    }

    // 如果精确匹配失败,尝试关键词匹配
    const lowerFlagKey = flagKey.toLowerCase();

    // 关键词映射规则
    if (lowerFlagKey.includes('均线') || lowerFlagKey.includes('粘合') || lowerFlagKey.includes('ma')) {
        return WyckoffMisreadingGuide['pattern_as_signal'];
    }
    if (lowerFlagKey.includes('缩量') || lowerFlagKey.includes('成交量') || lowerFlagKey.includes('volume')) {
        return WyckoffMisreadingGuide['low_volume_ambiguity'];
    }
    if (lowerFlagKey.includes('背离') || lowerFlagKey.includes('rsi') || lowerFlagKey.includes('macd')) {
        return WyckoffMisreadingGuide['indicator_overinterpretation'];
    }
    if (lowerFlagKey.includes('关键位') || lowerFlagKey.includes('支撑') || lowerFlagKey.includes('压力')) {
        return WyckoffMisreadingGuide['key_level_overconfidence'];
    }
    if (lowerFlagKey.includes('趋势') || lowerFlagKey.includes('trend')) {
        return WyckoffMisreadingGuide['trend_perpetuity_illusion'];
    }
    if (lowerFlagKey.includes('消息') || lowerFlagKey.includes('news')) {
        return WyckoffMisreadingGuide['news_dependency'];
    }

    // 如果都不匹配,返回通用提醒
    return {
        title: "认知风险提醒",
        explanation: "当前分析识别到潜在的认知偏误风险。在做判断前,请确保您理解判断前提可能失效是正常的。",
        reminder: "保持开放心态,允许判断被证伪"
    };
}

/**
 * 获取判断状态的解释消息
 */
export function getJudgmentStatusMessage(status: string): JudgmentStatusMessage {
    return JudgmentStatusMessages[status] || {
        title: "判断状态未知",
        meaning: "无法确定当前判断状态。",
        suggestion: "请检查判断记录是否完整。"
    };
}
