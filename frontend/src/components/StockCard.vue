<template>
  <n-card class="stock-card mobile-card mobile-shadow mobile-stock-card" :bordered="false" :class="{ 'is-analyzing': isAnalyzing }">
    <div class="card-header mobile-card-header">
      <div class="header-main">
        <div class="header-left">
          <div class="stock-info">
            <div class="stock-code">{{ stock.code }}</div>
            <div class="stock-name" v-if="stock.name">{{ stock.name }}</div>
          </div>
          <div class="stock-price-info" v-if="stock.price !== undefined">
            <div class="stock-price">
              <span class="label">当前价格:</span>
              <span class="value">{{ stock.price.toFixed(2) }}</span>
            </div>
            <div class="stock-change" :class="{ 
              'up': calculatedChangePercent && calculatedChangePercent > 0,
              'down': calculatedChangePercent && calculatedChangePercent < 0
            }">
              <span class="label">涨跌幅:</span>
              <span class="value">{{ formatChangePercent(calculatedChangePercent) }}</span>
            </div>
          </div>
        </div>
        <div class="header-right">
            <n-button 
              size="small" 
              v-if="stock.analysisStatus === 'completed'"
              @click="copyStockAnalysis"
              class="header-action-button copy-button"
              type="primary"
              secondary
              round
            >
              <template #icon>
                <n-icon><CopyOutline /></n-icon>
              </template>
              复制
            </n-button>
            <n-button 
              size="small" 
              v-if="stock.analysisStatus === 'completed'"
              @click="generateShareImage"
              class="header-action-button share-button"
              type="info"
              secondary
              round
            >
              <template #icon>
                <n-icon><ShareSocialOutline /></n-icon>
              </template>
              分享
            </n-button>
            <n-button 
              size="small" 
              v-if="stock.analysisStatus === 'completed'"
              @click="saveJudgment"
              class="header-action-button save-button"
              type="success"
              secondary
              round
              :loading="savingJudgment"
            >
              <template #icon>
                <n-icon><BookmarkOutline /></n-icon>
              </template>
              保存判断
            </n-button>
        </div>
      </div>
      <div class="analysis-status" v-if="stock.analysisStatus !== 'completed'">
        <n-tag 
          :type="getStatusType" 
          size="small" 
          round
          :bordered="false"
        >
          <template #icon>
            <n-icon>
              <component :is="getStatusIcon" />
            </n-icon>
          </template>
          {{ getStatusText }}
        </n-tag>
      </div>
    </div>
    
    <AiScorePanel
      :ai-score="(stock.aiScore || stock.analysisV1?.ai_score) ?? null"
      :loading="stock.analysisStatus === 'waiting' || stock.analysisStatus === 'analyzing'"
      :compact="false"
      style="margin-top: 10px;"
    />
    
    <div class="analysis-date" v-if="stock.analysisDate">
      <n-tag type="info" size="small">
        <template #icon>
          <n-icon><CalendarOutline /></n-icon>
        </template>
        分析日期: {{ formatDate(stock.analysisDate) }}
      </n-tag>
    </div>
    
    <div class="technical-indicators" v-if="hasAnyTechnicalIndicator">
      <n-divider dashed style="margin: 12px 0 8px 0">技术指标</n-divider>
      
      <div class="indicators-grid">
        <div class="indicator-item" v-if="stock.rsi !== undefined">
          <div class="indicator-value" :class="getRsiClass(stock.rsi)">{{ stock.rsi.toFixed(2) }}</div>
          <div class="indicator-label">RSI</div>
        </div>
        
        <div class="indicator-item" v-if="stock.priceChange !== undefined">
          <div class="indicator-value" :class="{ 
            'up': stock.priceChange > 0,
            'down': stock.priceChange < 0
          }">{{ formatPriceChange(stock.priceChange) }}</div>
          <div class="indicator-label">涨跌额</div>
        </div>
        
        <div class="indicator-item" v-if="stock.maTrend">
          <div class="indicator-value" :class="getTrendClass(stock.maTrend)">
            {{ getChineseTrend(stock.maTrend) }}
          </div>
          <div class="indicator-label">均线趋势</div>
        </div>
        
        <div class="indicator-item" v-if="stock.macdSignal">
          <div class="indicator-value" :class="getSignalClass(stock.macdSignal)">
            {{ getChineseSignal(stock.macdSignal) }}
          </div>
          <div class="indicator-label">MACD信号</div>
        </div>
        
        <div class="indicator-item" v-if="stock.volumeStatus">
          <div class="indicator-value" :class="getVolumeStatusClass(stock.volumeStatus)">
            {{ getChineseVolumeStatus(stock.volumeStatus) }}
          </div>
          <div class="indicator-label">成交量</div>
        </div>
      </div>
    </div>
    
    <div class="card-content">
      <!-- K线图区域 -->
      <div class="chart-section" v-if="stock.analysisStatus === 'completed' || isAnalyzing">
        <n-divider dashed style="margin: 0 0 12px 0">行情走势 (静态回顾)</n-divider>
        <div ref="chartRef" class="kline-chart" :style="{ height: isMobile ? '250px' : '350px' }"></div>
        <div v-if="chartLoading" class="chart-loading">
          <n-spin size="small" />
          <span>加载行情数据\u2026</span>
        </div>
      </div>

      <n-divider dashed v-if="stock.analysisStatus === 'completed' || isAnalyzing || stock.analysisStatus === 'waiting'" style="margin: 12px 0">AI 深度分析</n-divider>

      <!-- 等待分析状态：显示骨架屏和进度提示 -->
      <template v-if="stock.analysisStatus === 'waiting'">
        <div class="analysis-waiting">
          <div class="waiting-progress">
            <div class="progress-step active">
              <span class="step-icon">✓</span>
              <span class="step-text">股票代码已确认</span>
            </div>
            <div class="progress-step pending">
              <n-spin size="small" />
              <span class="step-text">正在获取行情数据...</span>
            </div>
            <div class="progress-step pending">
              <span class="step-icon">○</span>
              <span class="step-text">计算技术指标</span>
            </div>
            <div class="progress-step pending">
              <span class="step-icon">○</span>
              <span class="step-text">AI深度分析</span>
            </div>
          </div>
          <div class="skeleton-content">
            <div class="skeleton-line long"></div>
            <div class="skeleton-line medium"></div>
            <div class="skeleton-line short"></div>
            <div class="skeleton-line long"></div>
            <div class="skeleton-line medium"></div>
          </div>
        </div>
      </template>

      <template v-else-if="stock.analysisStatus === 'error'">
        <div class="error-status">
          <n-icon :component="AlertCircleIcon" class="error-icon" />
          <span>{{ stock.error || '未知错误' }}</span>
        </div>
      </template>
      
      <template v-else-if="stock.analysisStatus === 'analyzing'">
        <div class="analysis-result analysis-streaming" 
             ref="analysisResultRef"
             v-html="parsedAnalysis">
        </div>
      </template>
      
      <template v-else-if="stock.analysisStatus === 'completed'">
        <!-- 优先显示 Analysis V1 格式 -->
        <AnalysisV1Display 
          v-if="stock.analysisV1"
          :data="stock.analysisV1"
          :stock-code="stock.code"
          :stock-name="stock.name || stock.code"
          @saved="handleJudgmentSaved"
        />
        <!-- 降级：显示普通文本分析 -->
        <div v-else class="analysis-result analysis-completed" v-html="parsedAnalysis"></div>
      </template>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed, watch, ref, nextTick, onMounted, onBeforeUnmount } from 'vue';
import { NCard, NDivider, NIcon, NTag, NButton, useMessage } from 'naive-ui';
import { 
  AlertCircleOutline as AlertCircleIcon,
  CalendarOutline,
  CopyOutline,
  HourglassOutline,
  ReloadOutline,
  ShareSocialOutline,
  BookmarkOutline
} from '@vicons/ionicons5';
import * as echarts from 'echarts';
import { apiService } from '@/services/api';
import { getCategoryName, parseMarkdown } from '@/utils';
import type { StockInfo } from '@/types';
import AnalysisV1Display from './AnalysisV1Display.vue';
import AiScorePanel from './AiScorePanel.vue';

const props = defineProps<{
  stock: StockInfo;
}>();

const isAnalyzing = computed(() => {
  return props.stock.analysisStatus === 'analyzing';
});

const isMobile = computed(() => {
  return window.innerWidth <= 768;
});

const lastAnalysisLength = ref(0);
const lastAnalysisText = ref('');

// 监听分析内容变化
watch(() => props.stock.analysis, (newVal) => {
  if (newVal && props.stock.analysisStatus === 'analyzing') {
    lastAnalysisLength.value = newVal.length;
    lastAnalysisText.value = newVal;
  }
}, { immediate: true });

// 分析内容的解析
const parsedAnalysis = computed(() => {
  if (props.stock.analysis) {
    let result = parseMarkdown(props.stock.analysis);
    
    // 为关键词添加样式类
    result = highlightKeywords(result);
    
    return result;
  }
  return '';
});

// 关键词高亮处理函数
function highlightKeywords(html: string): string {
  // 买入/卖出/持有信号
  html = html.replace(/(<strong>)(买入|卖出|持有)(<\/strong>)/g, '$1<span class="buy">$2</span>$3');
  
  // 上涨/增长相关词
  html = html.replace(/(<strong>)(上涨|看涨|增长|增加|上升)(<\/strong>)/g, '$1<span class="up">$2</span>$3');
  
  // 下跌/减少相关词
  html = html.replace(/(<strong>)(下跌|看跌|减少|降低|下降)(<\/strong>)/g, '$1<span class="down">$2</span>$3');
  
  // 技术指标相关词
  html = html.replace(/(<strong>)(RSI|MACD|MA|KDJ|均线|成交量|布林带|Bollinger|移动平均|相对强弱|背离)(<\/strong>)/g, 
                      '$1<span class="indicator">$2</span>$3');
  
  // 高亮重要的百分比数字 (如 +12.34%, -12.34%)
  html = html.replace(/([+-]?\d+\.?\d*\s*%)/g, '<span class="number">$1</span>');
  
  // 高亮重要的数值 (如带小数位的数字)
  html = html.replace(/(\s|>)(\d+\.\d+)(\s|<)/g, '$1<span class="number">$2</span>$3');
  
  return html;
}

// 获取涨跌幅
const calculatedChangePercent = computed(() => {
  if (props.stock.changePercent !== undefined) {
    return props.stock.changePercent;
  }
  return undefined;
});

const hasAnyTechnicalIndicator = computed(() => {
  return props.stock.rsi !== undefined || 
         props.stock.priceChange !== undefined || 
         props.stock.maTrend !== undefined || 
         props.stock.macdSignal !== undefined || 
         props.stock.volumeStatus !== undefined;
});

function formatChangePercent(percent: number | undefined): string {
  if (percent === undefined) return '--';
  
  const sign = percent > 0 ? '+' : '';
  return `${sign}${percent.toFixed(2)}%`;
}

function formatPriceChange(change: number | undefined | null): string {
  if (change === undefined || change === null) return '--';
  const sign = change > 0 ? '+' : '';
  return `${sign}${change.toFixed(2)}`;
}

function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return '--';
  try {
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) {
      return dateStr;
    }
    return date.toISOString().split('T')[0];
  } catch (e) {
    return dateStr;
  }
}

function getRsiClass(rsi: number): string {
  if (rsi >= 70) return 'rsi-overbought';
  if (rsi <= 30) return 'rsi-oversold';
  return '';
}

function getTrendClass(trend: string): string {
  if (trend === 'UP') return 'trend-up';
  if (trend === 'DOWN') return 'trend-down';
  return 'trend-neutral';
}

function getSignalClass(signal: string): string {
  if (signal === 'BUY') return 'signal-buy';
  if (signal === 'SELL') return 'signal-sell';
  return 'signal-neutral';
}

function getVolumeStatusClass(status: string): string {
  if (status === 'HIGH') return 'volume-high';
  if (status === 'LOW') return 'volume-low';
  return 'volume-normal';
}

function getChineseTrend(trend: string): string {
  const trendMap: Record<string, string> = {
    'UP': '上升',
    'DOWN': '下降',
    'NEUTRAL': '平稳'
  };
  
  return trendMap[trend] || trend;
}

function getChineseSignal(signal: string): string {
  const signalMap: Record<string, string> = {
    'BUY': '买入',
    'SELL': '卖出',
    'HOLD': '持有',
    'NEUTRAL': '中性'
  };
  
  return signalMap[signal] || signal;
}

function getChineseVolumeStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'HIGH': '放量',
    'LOW': '缩量',
    'NORMAL': '正常'
  };
  
  return statusMap[status] || status;
}

const message = useMessage();

// 添加复制功能
async function copyStockAnalysis() {
  if (!props.stock.analysis) {
    message.warning('暂无分析结果可复制');
    return;
  }

  try {
    let result = `【${props.stock.code} ${props.stock.name || ''}】\n`;
    
    // 添加分析日期
    if (props.stock.analysisDate) {
      result += `分析日期: ${formatDate(props.stock.analysisDate)}\n`;
    }
    
    // 添加评分和推荐信息
    if (props.stock.score !== undefined) {
      result += `评分: ${props.stock.score}\n`;
    }
    
    if (props.stock.recommendation) {
      result += `推荐: ${props.stock.recommendation}\n`;
    }
    
    // 添加技术指标信息
    if (props.stock.rsi !== undefined) {
      result += `RSI: ${props.stock.rsi.toFixed(2)}\n`;
    }
    
    if (props.stock.priceChange !== undefined) {
      const sign = props.stock.priceChange > 0 ? '+' : '';
      result += `涨跌额: ${sign}${props.stock.priceChange.toFixed(2)}\n`;
    }
    
    if (props.stock.maTrend) {
      result += `均线趋势: ${getChineseTrend(props.stock.maTrend)}\n`;
    }
    
    if (props.stock.macdSignal) {
      result += `MACD信号: ${getChineseSignal(props.stock.macdSignal)}\n`;
    }
    
    if (props.stock.volumeStatus) {
      result += `成交量: ${getChineseVolumeStatus(props.stock.volumeStatus)}\n`;
    }
    
    // 添加分析结果
    result += `\n${props.stock.analysis}\n`;
    
    await navigator.clipboard.writeText(result);
    message.success('已复制分析结果到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
    console.error('复制分析结果时出错:', error);
  }
}

// 添加状态相关的计算属性
const getStatusType = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return 'default';
    case 'analyzing':
      return 'info';
    case 'error':
      return 'error';
    default:
      return 'default';
  }
});

const getStatusIcon = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return HourglassOutline;
    case 'analyzing':
      return ReloadOutline;
    case 'error':
      return AlertCircleIcon;
    default:
      return HourglassOutline;
  }
});

const getStatusText = computed(() => {
  switch (props.stock.analysisStatus) {
    case 'waiting':
      return '等待分析';
    case 'analyzing':
      return '正在分析';
    case 'error':
      return '分析出错';
    default:
      return '';
  }
});

// 添加滚动控制相关变量
const analysisResultRef = ref<HTMLElement | null>(null);
const userScrolling = ref(false);
const scrollPosition = ref(0);
const scrollThreshold = 30; // 底部阈值，小于这个值认为用户已滚动到底部

// 检测用户滚动行为
function handleScroll() {
  if (!analysisResultRef.value) return;
  
  const element = analysisResultRef.value;
  const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < scrollThreshold;
  
  // 记录当前滚动位置
  scrollPosition.value = element.scrollTop;
  
  // 判断用户是否正在主动滚动
  if (atBottom) {
    // 用户滚动到底部，标记为非主动滚动状态
    userScrolling.value = false;
  } else {
    // 用户未在底部，标记为主动滚动状态
    userScrolling.value = true;
  }
}

// 图表加载逻辑
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = ref<echarts.ECharts | null>(null);
const chartLoading = ref(false);

async function initChart() {
  if (!chartRef.value) return;
  
  chartLoading.value = true;
  try {
    const data = await apiService.getKlineData(props.stock.code, props.stock.marketType);
    if (data.error) throw new Error(data.error);

    if (!chartInstance.value) {
      chartInstance.value = echarts.init(chartRef.value);
    }

    const option = {
      animation: false,
      silent: true, // 禁用交互以提升性能
      grid: [
        { left: '8%', right: '3%', height: '50%', top: '5%' },
        { left: '8%', right: '3%', top: '60%', height: '15%' },
        { left: '8%', right: '3%', top: '78%', height: '18%' }
      ],
      xAxis: [
        { type: 'category', data: data.dates, boundaryGap: false, axisLine: { lineStyle: { color: '#ccc' } } },
        { type: 'category', gridIndex: 1, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 2, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } }
      ],
      yAxis: [
        { scale: true, splitArea: { show: true }, axisLabel: { fontSize: 10 } },
        { gridIndex: 1, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
        { gridIndex: 2, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
      ],
      series: [
        {
          name: 'KLine',
          type: 'candlestick',
          data: data.values,
          itemStyle: { color: '#ef4444', color0: '#10b981', borderColor: '#ef4444', borderColor0: '#10b981' }
        },
        { name: 'MA5', type: 'line', data: data.ma5, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#f59e0b' } },
        { name: 'MA20', type: 'line', data: data.ma20, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#6366f1' } },
        { name: 'Volume', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: data.volumes, itemStyle: { color: '#718096' } },
        { name: 'RSI', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: data.rsi, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#8b5cf6' } }
      ]
    };

    chartInstance.value.setOption(option);
  } catch (err) {
    console.error('初始化图标失败:', err);
  } finally {
    chartLoading.value = false;
  }
}

// 复制分享链接
async function generateShareImage() {
  try {
    // 构建更详细的分享内容
    const baseUrl = window.location.origin;
    const stockName = props.stock.name || props.stock.code;
    const score = props.stock.score || 'N/A';
    const recommendation = props.stock.recommendation || '待分析';
    
    // 提取分析摘要(前200字符)
    const analysisSummary = props.stock.analysis 
      ? props.stock.analysis.replace(/[#*]/g, '').substring(0, 200) + '\u2026'
      : '完整分析请访问平台';
    
    const categoryName = getCategoryName(props.stock.marketType);
    const shareText = `📊 AI${categoryName}分析报告
━━━━━━━━━━━━━━━
${categoryName}: ${stockName}
代码: ${props.stock.code}
综合评分: ${score}分
投资建议: ${recommendation}

📈 分析摘要:
${analysisSummary}

🔗 查看更多分析:
${baseUrl}/analysis

⚡ 由 Agu AI 智能生成`;
    
    await navigator.clipboard.writeText(shareText);
    message.success('分享内容已复制到剪贴板');
  } catch (error) {
    console.error('复制分享链接失败:', error);
    message.error('复制失败，请重试');
  }
}

// 保存判断状态
const savingJudgment = ref(false);

// 保存判断功能
async function saveJudgment() {
  if (!props.stock.analysis) {
    message.warning('暂无分析结果可保存');
    return;
  }

  savingJudgment.value = true;
  try {
    // 构造 Journal 系统需要的记录格式
    const recordRequest = {
      ts_code: props.stock.code,
      selected_candidate: 'A', // 默认设为候选A，后续可从分析中提取或让用户选择
      selected_premises: [
        `趋势: ${getChineseTrend(props.stock.maTrend || 'NEUTRAL')}`,
        `RSI: ${props.stock.rsi ? props.stock.rsi.toFixed(2) : 'N/A'}`
      ],
      selected_risk_checks: [],
      constraints: {
        price: props.stock.price || 0,
        analysis_date: props.stock.analysisDate || new Date().toISOString()
      },
      validation_period_days: 7 // 默认验证周期为7天
    };

    const response = await apiService.saveJudgment(recordRequest);
    
    if (response && (response.id || response.judgment_id)) {
      message.success('判断已保存！可在"判断日记"中查看');
    } else {
      message.error('保存失败，请重试');
    }
  } catch (error: any) {
    console.error('保存判断失败:', error);
    if (error.response?.status === 409) {
      message.error('判断重复，保存失败');
    } else if (error.response?.status === 422) {
      const details = error.response.data?.detail;
      const detailStr = Array.isArray(details) 
        ? details.map((d: any) => `${d.loc.join('.')}: ${d.msg}`).join('; ')
        : JSON.stringify(details);
      message.error(`数据格式错误: ${detailStr}`);
    } else {
      message.error('保存失败，请重试');
    }
  } finally {
    savingJudgment.value = false;
  }
}

// 处理判断保存成功事件
function handleJudgmentSaved(judgmentId: string) {
  console.log('Judgment saved:', judgmentId);
  // 可以在这里添加额外的处理逻辑
}

// 监听滚动事件
onMounted(() => {
  if (analysisResultRef.value) {
    // 初始滚动到底部
    analysisResultRef.value.scrollTop = analysisResultRef.value.scrollHeight;
    analysisResultRef.value.addEventListener('scroll', handleScroll);
  }
  
  // 如果分析已完成或正在分析，初始化图表
  if (props.stock.analysisStatus === 'completed' || props.stock.analysisStatus === 'analyzing') {
    initChart();
  }
});

// 清理事件监听
onBeforeUnmount(() => {
  if (analysisResultRef.value) {
    analysisResultRef.value.removeEventListener('scroll', handleScroll);
  }
});

// 改进流式更新监听，更保守地控制滚动行为
let isProcessingUpdate = false; // 防止重复处理更新
watch(() => props.stock.analysis, (newVal, oldVal) => {
  // 只在分析中且内容增加时处理
  if (newVal && oldVal && newVal.length > oldVal.length && 
      props.stock.analysisStatus === 'analyzing' && !isProcessingUpdate) {
    
    isProcessingUpdate = true; // 标记正在处理更新
    
    // 检查是否应该自动滚动
    let shouldAutoScroll = false;
    if (analysisResultRef.value) {
      const element = analysisResultRef.value;
      // 仅当滚动接近底部或用户尚未开始滚动时自动滚动
      const atBottom = element.scrollHeight - element.scrollTop - element.clientHeight < scrollThreshold;
      shouldAutoScroll = atBottom || !userScrolling.value;
    }
    
    // 使用nextTick确保DOM已更新
    nextTick(() => {
      if (analysisResultRef.value && shouldAutoScroll) {
        // 使用smoothScroll而非直接设置scrollTop，减少视觉跳动
        smoothScrollToBottom(analysisResultRef.value);
      }
      
      // 重置处理标记
      setTimeout(() => {
        isProcessingUpdate = false;
      }, 50); // 短暂延迟，防止过快连续处理
    });
  }
}, { immediate: false });

// 平滑滚动到底部的辅助函数
function smoothScrollToBottom(element: HTMLElement) {
  const targetPosition = element.scrollHeight;
  
  // 如果已经很接近底部，直接跳转避免不必要的动画
  const currentGap = targetPosition - element.scrollTop - element.clientHeight;
  if (currentGap < 100) {
    element.scrollTop = targetPosition;
    return;
  }
  
  // 否则使用平滑滚动
  element.scrollTo({
    top: targetPosition,
    behavior: 'smooth'
  });
}

// 监听状态变化，如果是开始分析，则触发图表加载
watch(() => props.stock.analysisStatus, (status) => {
  if (status === 'analyzing' && !chartInstance.value) {
    nextTick(() => initChart());
  }
});

// 处理窗口大小改变
window.addEventListener('resize', () => {
  chartInstance.value?.resize();
});
</script>

<style scoped>
/* Glassmorphism Card Style */
.stock-card {
  height: 100%;
  display: flex;
  flex-direction: column;
  transition: all 0.5s cubic-bezier(0.23, 1, 0.32, 1);
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.07);
  width: 100%;
  max-width: 100%;
  background: rgba(255, 255, 255, 0.75);
  backdrop-filter: blur(20px) saturate(180%);
  -webkit-backdrop-filter: blur(20px) saturate(180%);
  border: 1px solid rgba(255, 255, 255, 0.4);
  border-radius: 24px !important;
  overflow: hidden;
}

.stock-card:hover {
  transform: translateY(-6px) scale(1.01);
  box-shadow: 0 20px 40px rgba(31, 38, 135, 0.12);
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(255, 255, 255, 0.8);
}

.stock-card.is-analyzing {
  border: 2px solid transparent;
  background-image: linear-gradient(rgba(255, 255, 255, 0.8), rgba(255, 255, 255, 0.8)), 
                    linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  background-origin: border-box;
  background-clip: padding-box, border-box;
  animation: pulse-border 2s infinite;
}

@keyframes pulse-border {
  0% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0.4); }
  70% { box-shadow: 0 0 0 10px rgba(102, 126, 234, 0); }
  100% { box-shadow: 0 0 0 0 rgba(102, 126, 234, 0); }
}

/* Header Styling */
.card-header {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08) 0%, rgba(118, 75, 162, 0.08) 100%);
}

.header-main {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-left {
  display: flex;
  gap: 20px;
  align-items: center;
}

/* Stock Info Typography */
.stock-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 120px;
}

.stock-code {
  font-size: 1.75rem;
  font-weight: 800;
  background: linear-gradient(135deg, #1a202c 0%, #4a5568 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  line-height: 1.1;
  letter-spacing: -0.03em;
}

.stock-name {
  font-size: 1rem;
  color: #4a5568;
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 180px;
}

/* Price Info */
.stock-price-info {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding-left: 20px;
  border-left: 2px solid rgba(0, 0, 0, 0.06);
}

.stock-price, .stock-change {
  display: flex;
  align-items: center;
  gap: 10px;
}

.stock-price .label,
.stock-change .label {
  font-size: 0.75rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 600;
}

.stock-price .value {
  font-size: 1.25rem;
  font-weight: 800;
  color: #2d3748;
  font-variant-numeric: tabular-nums;
}

.stock-change .value {
  font-size: 1rem;
  font-weight: 700;
  padding: 4px 10px;
  border-radius: 8px;
  font-variant-numeric: tabular-nums;
}

.up .value {
  color: #dc2626;
  background-color: rgba(220, 38, 38, 0.1);
}

.down .value {
  color: #059669;
  background-color: rgba(5, 150, 105, 0.1);
}

/* Header Right Actions */
.header-right {
  display: flex;
  align-items: center;
}

.copy-button {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  font-weight: 600;
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.25);
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: none !important;
}

.copy-button:hover {
  transform: translateY(-2px) scale(1.05);
  box-shadow: 0 6px 16px rgba(102, 126, 234, 0.4);
  opacity: 0.95;
}

.copy-button:active {
  transform: translateY(0) scale(0.98);
}

/* Analysis Status Badge */
.analysis-status {
  display: flex;
  align-items: center;
  margin-top: 4px;
}

.analysis-status :deep(.n-tag) {
  border-radius: 12px;
  padding: 0 10px;
  font-weight: 500;
  border: none;
  background: rgba(255, 255, 255, 0.6);
  box-shadow: 0 2px 4px rgba(0,0,0,0.05);
}

.analysis-status :deep(.n-tag .n-icon) {
  margin-right: 4px;
}

.analysis-status :deep(.n-tag--info .n-icon) {
  animation: spin 2s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Dashboard Summary Section */
.stock-summary {
  display: grid;
  grid-template-columns: 1fr 1fr;
  margin: 0 20px 20px;
  padding: 16px;
  background: rgba(255, 255, 255, 0.45);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.6);
  box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
}

.summary-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
}

.summary-item:first-child::after {
  content: '';
  position: absolute;
  right: 0;
  top: 15%;
  height: 70%;
  width: 1px;
  background: rgba(0, 0, 0, 0.08);
}

.summary-value {
  font-size: 1.75rem;
  font-weight: 850;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.summary-label {
  font-size: 0.8rem;
  color: #718096;
  margin-top: 6px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

/* Analysis Date Badge */
.analysis-date {
  margin: 0 20px 10px;
  display: flex;
  justify-content: flex-end;
}

.analysis-date .n-tag {
  background: rgba(237, 242, 247, 0.8);
  color: #4a5568;
  border: none;
  font-weight: 600;
}

/* Technical Indicators Grid */
.technical-indicators {
  margin: 0 20px;
}

.indicators-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 14px;
  margin-top: 14px;
}

.indicator-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 12px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 16px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
  box-shadow: 0 2px 6px rgba(0,0,0,0.02);
}

.indicator-item:hover {
  transform: translateY(-3px);
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 8px 16px rgba(31, 38, 135, 0.08);
  border-color: rgba(255, 255, 255, 0.9);
}

.indicator-value {
  font-size: 0.95rem;
  font-weight: 700;
  margin-bottom: 2px;
}

.indicator-label {
  font-size: 0.7rem;
  color: #9ca3af;
  font-weight: 500;
}

/* Score Colors */
.score-high { color: #10b981; }
.score-medium-high { color: #34d399; }
.score-medium { color: #f59e0b; }
.score-medium-low { color: #fbbf24; }
.score-low { color: #ef4444; }

/* Status Colors */
.rsi-overbought { color: #ef4444; }
.rsi-oversold { color: #10b981; }
.trend-up { color: #ef4444; }
.trend-down { color: #10b981; }
.trend-neutral { color: #f59e0b; }
.signal-buy { color: #ef4444; }
.signal-sell { color: #10b981; }
.signal-neutral { color: #f59e0b; }
.volume-high { color: #ef4444; }
.volume-low { color: #10b981; }
.volume-normal { color: #f59e0b; }
.recommendation { color: #667eea; }

/* Main Content Area */
.card-content {
  flex: 1;
  padding: 0 16px 16px;
  display: flex;
  flex-direction: column;
}

.error-status {
  padding: 16px;
  border-radius: 12px;
  background: rgba(239, 68, 68, 0.1);
  color: #ef4444;
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

/* Analysis Result Text */
.analysis-result {
  font-size: 0.95rem;
  line-height: 1.7;
  color: #374151;
  padding: 16px;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.4);
  border: 1px solid rgba(255, 255, 255, 0.5);
  max-height: 400px;
  overflow-y: auto;
  
  /* Scrollbar */
  scrollbar-width: thin;
  scrollbar-color: rgba(102, 126, 234, 0.3) transparent;
}

.analysis-result::-webkit-scrollbar {
  width: 6px;
}

.analysis-result::-webkit-scrollbar-thumb {
  background-color: rgba(102, 126, 234, 0.3);
  border-radius: 3px;
}

/* Streaming Animation */
.analysis-streaming {
  position: relative;
  border-left: 3px solid #667eea;
  background: linear-gradient(to right, rgba(102, 126, 234, 0.05), transparent);
}

.analysis-streaming::after {
  content: '';
  display: inline-block;
  width: 8px;
  height: 16px;
  background-color: #667eea;
  animation: blink 1s step-end infinite;
  vertical-align: middle;
  margin-left: 4px;
}

.analysis-completed {
  border-left: 3px solid #10b981;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

/* Formatting for Analysis Text */
.analysis-result :deep(h1), 
.analysis-result :deep(h2), 
.analysis-result :deep(h3) {
  color: #4b5563;
  margin: 1.5rem 0 0.8rem;
  font-weight: 700;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  padding-bottom: 4px;
}

.analysis-result :deep(h1) { font-size: 1.3rem; color: #667eea; }
.analysis-result :deep(h2) { font-size: 1.15rem; color: #764ba2; }
.analysis-result :deep(h3) { font-size: 1.05rem; }

.analysis-result :deep(p) { margin: 0.8rem 0; }

.analysis-result :deep(strong) {
  font-weight: 600;
  color: #1f2937;
}

/* Highlight Classes */
.analysis-result :deep(.buy) {
  color: #dc2626;
  background: rgba(220, 38, 38, 0.1);
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 600;
}

.analysis-result :deep(.up) { color: #dc2626; font-weight: 600; }
.analysis-result :deep(.down) { color: #059669; font-weight: 600; }
.analysis-result :deep(.indicator) {
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 600;
}

.analysis-result :deep(.number) {
  font-family: 'SF Mono', 'Roboto Mono', monospace;
  color: #ec4899;
}

/* List Styling */
.analysis-result :deep(ul) {
  padding-left: 1.2rem;
  list-style-type: disc;
}

.analysis-result :deep(li) {
  margin-bottom: 0.4rem;
  color: #4b5563;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .card-header {
    padding: 12px;
  }
  
  .stock-code {
    font-size: 1.25rem;
  }
  
  .stock-price-info {
    padding-left: 12px;
  }
  
  .stock-price .value {
    font-size: 1rem;
  }
  
  .indicators-grid {
    grid-template-columns: repeat(2, 1fr);
  }
  
  .card-content {
    padding: 0 12px 12px;
  }
  
  .analysis-result {
    padding: 12px;
    font-size: 0.9rem;
  }
}

@media (max-width: 480px) {
  .header-main {
    flex-wrap: wrap;
  }
  
  .header-right {
    margin-left: auto;
  }
  
  .indicators-grid {
    grid-template-columns: 1fr 1fr;
    gap: 8px;
  }
}

/* Action Buttons */
.header-action-button {
  transition: all 0.3s ease;
  font-weight: 600;
}

.copy-button {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white !important;
  border: none !important;
}

.share-button {
  margin-left: 8px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%) !important;
  color: white !important;
  border: none !important;
}

.share-button:hover {
  filter: brightness(1.1);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

/* Chart Styles */
.chart-section {
  position: relative;
  margin: 12px 0;
  border: 1px solid rgba(0, 0, 0, 0.05);
  border-radius: 12px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.3);
}

.kline-chart {
  width: 100%;
}

.chart-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(2px);
  gap: 8px;
  border-radius: 12px;
  z-index: 5;
}

.chart-loading span {
  font-size: 0.75rem;
  color: #64748b;
}

/* New Content Divider */
.analysis-result {
  margin-top: 8px;
}

/* Waiting State - Skeleton & Progress */
.analysis-waiting {
  padding: 16px 0;
}

.waiting-progress {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 20px;
  padding: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border-radius: 12px;
  border: 1px solid rgba(102, 126, 234, 0.15);
}

.progress-step {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
}

.progress-step.active .step-icon {
  color: #10b981;
  font-weight: bold;
}

.progress-step.active .step-text {
  color: #10b981;
  font-weight: 600;
}

.progress-step.pending .step-icon {
  color: #94a3b8;
}

.progress-step.pending .step-text {
  color: #64748b;
}

.step-icon {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.step-text {
  font-size: 0.875rem;
}

/* Skeleton Loader */
.skeleton-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 12px;
}

.skeleton-line {
  height: 16px;
  border-radius: 8px;
  background: linear-gradient(
    90deg,
    rgba(102, 126, 234, 0.1) 0%,
    rgba(102, 126, 234, 0.2) 50%,
    rgba(102, 126, 234, 0.1) 100%
  );
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
}

.skeleton-line.long {
  width: 100%;
}

.skeleton-line.medium {
  width: 75%;
}

.skeleton-line.short {
  width: 50%;
}

@keyframes skeleton-shimmer {
  0% {
    background-position: 200% 0;
  }
  100% {
    background-position: -200% 0;
  }
}

/* Mobile Optimization for Waiting State */
@media (max-width: 768px) {
  .waiting-progress {
    padding: 12px;
    gap: 8px;
  }

  .progress-step {
    gap: 8px;
  }

  .step-text {
    font-size: 0.8rem;
  }
}
</style>
