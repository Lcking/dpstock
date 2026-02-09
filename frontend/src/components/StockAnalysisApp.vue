<template>
  <div class="app-container mobile-bottom-extend">
    <!-- 公告横幅 -->
    <AnnouncementBanner 
      v-if="announcement && showAnnouncementBanner" 
      :content="announcement" 
      :auto-close-time="5"
      @close="handleAnnouncementClose"
    />
    
    <n-layout class="main-layout">
      <n-layout-content class="main-content mobile-content-container">
        
        <!-- 市场时间显示 -->
        <MarketTimeDisplay :is-mobile="isMobile" />
        
        <!-- 核心价值闭环 -->
        <ValueLoop />
        
        <!-- 主要内容 -->
        <n-card class="analysis-container mobile-card mobile-card-spacing mobile-shadow">
          
          <n-grid cols="1 xl:24" :x-gap="16" :y-gap="16" responsive="screen">
            <!-- 左侧配置区域 -->
            <n-grid-item span="1 xl:8">
              <div class="config-section">
                <div class="search-config-container">
                  <n-form-item label="智能搜索与选择">
                    <n-input-group>
                      <n-select
                        v-model:value="marketType"
                        :options="marketOptions"
                        style="width: 120px"
                        @update:value="handleMarketTypeChange"
                      />
                      <n-select
                        v-model:value="selectedStockValues"
                        multiple
                        filterable
                        remote
                        placeholder="输入名称、拼音或代码\u2026"
                        :options="searchOptions"
                        :loading="isSearching"
                        :clearable="true"
                        :tag="true"
                        @search="handleSearch"
                        @update:value="handleUpdateValue"
                      />
                    </n-input-group>
                  </n-form-item>
                </div>
                
                <div class="action-buttons">
                  <n-button
                    type="primary"
                    :loading="isAnalyzing"
                    :disabled="selectedStockValues.length === 0"
                    @click="analyzeStocks"
                  >
                    {{ isAnalyzing ? '分析中\u2026' : '开始分析' }}
                  </n-button>
                  
                  <n-button
                    :disabled="analyzedStocks.length === 0"
                    @click="copyAnalysisResults"
                  >
                    复制结果
                  </n-button>
                </div>
              </div>
            </n-grid-item>
            
            <!-- 右侧结果区域 -->
            <n-grid-item span="1 xl:16">
              <div class="results-section">
                <div class="results-header">
                  <n-space align="center" justify="space-between">
                    <n-text>分析结果 ({{ analyzedStocks.length }})</n-text>
                    <n-space>
                      <n-select 
                        v-model:value="displayMode" 
                        size="small" 
                        style="width: 120px"
                        :options="[
                          { label: '卡片视图', value: 'card' },
                          { label: '表格视图', value: 'table' }
                        ]"
                      />
                      <n-button 
                        size="small" 
                        :disabled="analyzedStocks.length === 0"
                        @click="copyAnalysisResults"
                      >
                        复制结果
                      </n-button>
                      <n-dropdown 
                        trigger="click" 
                        :disabled="analyzedStocks.length === 0"
                        :options="exportOptions"
                        @select="handleExportSelect"
                      >
                        <n-button size="small" :disabled="analyzedStocks.length === 0">
                          导出
                          <template #icon>
                            <n-icon>
                              <DownloadIcon />
                            </n-icon>
                          </template>
                        </n-button>
                      </n-dropdown>
                    </n-space>
                  </n-space>
                </div>
                
                <template v-if="analyzedStocks.length === 0 && !isAnalyzing">
                  <AiScorePanel :loading="true" :compact="false" style="margin-bottom: 12px;" />
                  <n-empty description="尚未分析" size="large">
                    <template #icon>
                      <n-icon :component="DocumentTextIcon" />
                    </template>
                  </n-empty>
                </template>
                
                <template v-else-if="displayMode === 'card'">
                  <n-grid cols="1" :x-gap="8" :y-gap="8" responsive="screen">
                    <n-grid-item v-for="stock in analyzedStocks" :key="stock.code">
                      <StockCard :stock="stock" />
                    </n-grid-item>
                  </n-grid>
                </template>
                
                <template v-else>
                  <div class="table-container">
                    <n-data-table
                      :columns="stockTableColumns"
                      :data="analyzedStocks"
                      :pagination="{ pageSize: 10 }"
                      :row-key="(row: StockInfo) => row.code"
                      :bordered="false"
                      :single-line="false"
                      striped
                      :scroll-x="1200"
                    />
                  </div>
                </template>
              </div>
            </n-grid-item>
          </n-grid>
        </n-card>

      </n-layout-content>
    </n-layout>
    
    <!-- Quota Exceeded Modal -->
    <QuotaExceededModal 
      v-model:show="showQuotaExceededModal"
      :error-data="quotaExceededData"
      @open-invite="handleOpenInviteFromQuota"
    />
  </div>
</template>

<script setup lang="ts">

import HtmlRenderer from './HtmlRenderer';
import { h } from 'vue';
import { ref, onMounted, computed, onBeforeUnmount } from 'vue';
import { 
  NLayout, 
  NLayoutContent, 
  NCard, 
  NIcon, 
  NGrid, 
  NGridItem, 
  NFormItem, 
  NSelect, 
  NButton,
  NInputGroup,
  NEmpty,
  useMessage,
  NSpace,
  NText,
  NDataTable,
  NDropdown,
  type DataTableColumns
} from 'naive-ui';
import { useClipboard } from '@vueuse/core'
import { 
  DocumentTextOutline as DocumentTextIcon,
  DownloadOutline as DownloadIcon,
} from '@vicons/ionicons5';

import MarketTimeDisplay from './MarketTimeDisplay.vue';
import ValueLoop from './ValueLoop.vue';
import StockCard from './StockCard.vue';
import AiScorePanel from './AiScorePanel.vue';
import AnnouncementBanner from './AnnouncementBanner.vue';
import QuotaExceededModal from './QuotaExceededModal.vue';

import { apiService } from '@/services/api';
import type { StockInfo, StreamInitMessage, StreamAnalysisUpdate } from '@/types';
import { validateMultipleStockCodes, MarketType } from '@/utils/stockValidator';

// 使用Naive UI的组件API
const message = useMessage();
const { copy } = useClipboard();

// 公告配置
const announcement = ref('');
const showAnnouncementBanner = ref(true);

// 配额超限弹窗
const showQuotaExceededModal = ref(false);
const quotaExceededData = ref<any>(null);

// 股票分析配置
const marketType = ref('A');
const selectedStockValues = ref<string[]>([]); // 存储选中的代码
const searchOptions = ref<any[]>([]); // 搜索结果选项
const isSearching = ref(false);
const isAnalyzing = ref(false);
const analyzedStocks = ref<StockInfo[]>([]);

// 让控制台可以访问 analyzedStocks
(window as any).analyzedStocks = analyzedStocks;

const displayMode = ref<'card' | 'table'>('card');

// 移动端检测
const isMobile = computed(() => {
  return window.innerWidth <= 768;
});

// 监听窗口大小变化
function handleResize() {
  // 窗口大小变化时，isMobile计算属性会自动更新
  // 这里可以添加其他需要在窗口大小变化时执行的逻辑
}

// 显示系统公告
const showAnnouncement = (content: string) => {
  if (!content) return;
  
  // 使用AnnouncementBanner组件显示公告
  announcement.value = content;
  showAnnouncementBanner.value = true;
};

// 市场选项
const marketOptions = [
  { label: 'A股', value: 'A', showSearch: true },
  { label: '港股', value: 'HK', showSearch: true },
  { label: '美股', value: 'US', showSearch: true },
  { label: 'ETF', value: 'ETF', showSearch: true  },
  { label: 'LOF', value: 'LOF', showSearch: true  }
];


// 表格列定义
const stockTableColumns = ref<DataTableColumns<StockInfo>>([
  {
    title: '代码',
    key: 'code',
    width: 100,
    fixed: 'left'
  },
  {
    title: '状态',
    key: 'analysisStatus',
    width: 100,
    render(row: StockInfo) {
      const statusMap = {
        'waiting': '等待分析',
        'analyzing': '分析中',
        'completed': '已完成',
        'error': '出错'
      };
      return statusMap[row.analysisStatus] || row.analysisStatus;
    }
  },
  {
    title: '价格',
    key: 'price',
    width: 100,
    render(row: StockInfo) {
      return row.price !== undefined ? row.price.toFixed(2) : '--';
    }
  },
  {
    title: '涨跌额',
    key: 'priceChange',
    width: 100,
    render(row: StockInfo) {
      if (row.priceChange === undefined) return '--';
      const sign = row.priceChange > 0 ? '+' : '';
      return `${sign}${row.priceChange.toFixed(2)}`;
    }
  },
  {
    title: '涨跌幅',
    key: 'changePercent',
    width: 100,
    render(row: StockInfo) {
      if (row.changePercent === undefined) {
        // 如果没有changePercent但有priceChange和price，尝试计算
        if (row.priceChange !== undefined && row.price !== undefined) {
          const basePrice = row.price - row.priceChange;
          if (basePrice !== 0) {
            const calculatedPercent = (row.priceChange / basePrice) * 100;
            const sign = calculatedPercent > 0 ? '+' : '';
            return `${sign}${calculatedPercent.toFixed(2)}%`;
          }
        }
        return '--';
      }
      const sign = row.changePercent > 0 ? '+' : '';
      return `${sign}${row.changePercent.toFixed(2)}%`;
    }
  },
  {
    title: 'RSI',
    key: 'rsi',
    width: 80,
    render(row: StockInfo) {
      return row.rsi !== undefined ? row.rsi.toFixed(2) : '--';
    }
  },
  {
    title: '均线趋势',
    key: 'maTrend',
    width: 100,
    render(row: StockInfo) {
      const trendMap: Record<string, string> = {
        'UP': '上升',
        'DOWN': '下降',
        'NEUTRAL': '平稳'
      };
      return row.maTrend ? trendMap[row.maTrend] || row.maTrend : '--';
    }
  },
  {
    title: 'MACD信号',
    key: 'macdSignal',
    width: 100,
    render(row: StockInfo) {
      const signalMap: Record<string, string> = {
        'BUY': '买入',
        'SELL': '卖出',
        'HOLD': '持有',
        'NEUTRAL': '中性'
      };
      return row.macdSignal ? signalMap[row.macdSignal] || row.macdSignal : '--';
    }
  },
  {
    title: '评分',
    key: 'score',
    width: 80,
    render(row: StockInfo) {
      return row.score !== undefined ? row.score : '--';
    }
  },
  {
    title: '推荐',
    key: 'recommendation',
    width: 100
  },
  {
    title: '分析日期',
    key: 'analysisDate',
    width: 120,
    render(row: StockInfo) {
      if (!row.analysisDate) return '--';
      try {
        const date = new Date(row.analysisDate);
        if (isNaN(date.getTime())) {
          return row.analysisDate;
        }
        return date.toISOString().split('T')[0];
      } catch (e) {
        return row.analysisDate;
      }
    }
  },
  {
    title: '分析结果',
    key: 'analysis',
    width: 300,
    className: 'analysis-cell',
    render(row: StockInfo) {
      return h(HtmlRenderer, { html: row.analysis });
    }
  }
]);

// 导出选项
const exportOptions = [
  {
    label: '导出为CSV',
    key: 'csv'
  },
  {
    label: '导出为Excel',
    key: 'excel'
  },
  {
    label: '导出为PDF',
    key: 'pdf'
  }
];

// 搜索防抖
let searchTimer: any = null;

async function handleSearch(keyword: string) {
  if (!keyword.trim()) {
    searchOptions.value = [];
    return;
  }
  
  isSearching.value = true;
  if (searchTimer) clearTimeout(searchTimer);
  
  searchTimer = setTimeout(async () => {
    try {
      // 调用全局搜索 API，同时带上当前选中的市场作为“首选市场”
      const results = await apiService.searchGlobal(keyword, marketType.value);
      searchOptions.value = results;
    } catch (error) {
      console.error('搜索出错:', error);
    } finally {
      isSearching.value = false;
    }
  }, 300);
}

function handleUpdateValue() {
  // 处理选中值的逻辑，如果需要可以在这里做额外处理
}

// 处理市场类型变更
function handleMarketTypeChange() {
  analyzedStocks.value = [];
  // 切换市场时，如果搜索框有正在进行的操作，可以清空
  searchOptions.value = [];
  selectedStockValues.value = []; // 清空已选项
}

// 处理流式响应的数据
function processStreamData(text: string) {
  try {
    // 尝试解析为JSON
    const data = JSON.parse(text);
    
    // 判断是初始消息还是更新消息
    if (data.stream_type === 'single' || data.stream_type === 'batch') {
      // 初始消息
      handleStreamInit(data as StreamInitMessage);
    } else if (data.stock_code) {
      // 更新消息
      handleStreamUpdate(data as StreamAnalysisUpdate);
    } else if (data.scan_completed) {
      // 扫描完成消息
      message.success(`分析完成，共扫描 ${data.total_scanned} 个，符合条件 ${data.total_matched} 个`);
      
      // 将所有分析中的股票状态更新为已完成
      analyzedStocks.value = analyzedStocks.value.map(stock => {
        if (stock.analysisStatus === 'analyzing') {
          return { 
            ...stock, 
            analysisStatus: 'completed' as const 
          };
        }
        return stock;
      });
      
      isAnalyzing.value = false;
    }
  } catch (e) {
    console.error('解析流数据出错:', e);
  }
}

// 处理流式初始化消息
function handleStreamInit(data: StreamInitMessage) {
  if (data.stream_type === 'single' && data.stock_code) {
    // 单个股票分析
    analyzedStocks.value = [{
      code: data.stock_code,
      name: '',
      marketType: marketType.value,
      analysisStatus: 'waiting'
    }];
  } else if (data.stream_type === 'batch' && data.stock_codes) {
    // 批量分析
    analyzedStocks.value = data.stock_codes.map(code => ({
      code,
      name: '',
      marketType: marketType.value,
      analysisStatus: 'waiting'
    }));
  }
}


// 处理流式更新消息（支持AI分析片段拼接）
function handleStreamUpdate(data: StreamAnalysisUpdate) {
  console.log("流片段:", JSON.stringify(data, null, 2));
  const stockIndex = analyzedStocks.value.findIndex((s: StockInfo) => s.code === data.stock_code);

  if (stockIndex >= 0) {
    const stock = { ...analyzedStocks.value[stockIndex] };

    // ✅ 确保数值字段有默认值
    stock.price = data.price ?? stock.price ?? undefined;
    stock.priceChange = data.price_change ?? stock.priceChange ?? undefined;
    stock.changePercent = data.change_percent ?? stock.changePercent ?? undefined;
    stock.marketValue = data.market_value ?? stock.marketValue ?? undefined;
    stock.score = data.score ?? stock.score ?? undefined;
    stock.rsi = data.rsi ?? stock.rsi ?? undefined;

    // ✅ 更新分析状态
    if (data.status) {
      stock.analysisStatus = data.status;
    }

    // ✅ 若收到完整分析文本，直接更新
    if (data.analysis !== undefined) {
      stock.analysis = data.analysis;
    }

    // ✅ 若收到 Analysis V1 数据，直接更新
    if (data.analysis_v1 !== undefined) {
      stock.analysisV1 = data.analysis_v1;
    }

    // ✅ 若收到 ai_score（Spec v1.0），写入并同步到 analysis_v1.ai_score（若存在）
    if ((data as any).ai_score !== undefined) {
      stock.aiScore = (data as any).ai_score;
      if (stock.analysisV1 && typeof stock.analysisV1 === 'object') {
        (stock.analysisV1 as any).ai_score = (data as any).ai_score;
      }
    }

    // ✅ 若收到增量片段，则拼接
    if (data.ai_analysis_chunk !== undefined) {
      stock.analysis = (stock.analysis || '') + data.ai_analysis_chunk;
      stock.analysisStatus = 'analyzing';
    }

    // ✅ 错误处理
    if (data.error !== undefined) {
      stock.error = data.error;
      stock.analysisStatus = 'error';
    }

    // ✅ 其余字段更新
    if (data.name !== undefined) {
      stock.name = data.name;
    }

    if (data.recommendation !== undefined) {
      stock.recommendation = data.recommendation;
    }

    if (data.ma_trend !== undefined) {
      stock.maTrend = data.ma_trend;
    }

    if (data.macd_signal !== undefined) {
      stock.macdSignal = data.macd_signal;
    }

    if (data.volume_status !== undefined) {
      stock.volumeStatus = data.volume_status;
    }

    if (data.analysis_date !== undefined) {
      stock.analysisDate = data.analysis_date;
    }

    // ✅ Vue响应式更新
    analyzedStocks.value[stockIndex] = stock;
  }
}



// 分析股票
async function analyzeStocks() {
  if (selectedStockValues.value.length === 0) {
    message.warning('请选择要分析的项目');
    return;
  }
  
  // 去除重复
  const uniqueCodes = Array.from(new Set(selectedStockValues.value));
  
  isAnalyzing.value = true;
  analyzedStocks.value = [];
  
  // 在前端验证代码
  const marketTypeEnum = marketType.value as keyof typeof MarketType;
  const invalidCodes = validateMultipleStockCodes(
    uniqueCodes, 
    MarketType[marketTypeEnum]
  );
  
  // 如果有无效代码，显示错误信息并返回
  if (invalidCodes.length > 0) {
    const errorMessages = invalidCodes.map(item => item.errorMessage).join('\n');
    message.error(`代码验证失败:${errorMessages}`);
    return;
  }
  
  isAnalyzing.value = true;
  analyzedStocks.value = [];
  
  try {
    // 构建请求参数
    const requestData = {
      stock_codes: uniqueCodes,
      market_type: marketType.value
    } as any;
    
    // 添加这一行，确保走流式分析分支
    requestData.stream = true;
    
    // 获取身份验证令牌
    const token = localStorage.getItem('token');
    
    // 构建请求头
    const headers: Record<string, string> = {
      'Content-Type': 'application/json'
    };
    
    // 如果有令牌，添加到请求头
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    
    // 发送分析请求
    const response = await fetch('/api/analyze', {
      method: 'POST',
      headers,
      body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
      if (response.status === 401) {
        message.error('未授权访问，请登录后再试');
        // 可以在这里触发登录流程
        return;
      }
      if (response.status === 403) {
        // 配额超限错误
        try {
          const errorData = await response.json();
          quotaExceededData.value = errorData.detail || errorData;
          showQuotaExceededModal.value = true;
          isAnalyzing.value = false;
          return;
        } catch (e) {
          message.error('今日分析额度已用完');
          isAnalyzing.value = false;
          return;
        }
      }
      if (response.status === 404) {
        throw new Error('服务器接口未找到，请检查服务是否正常运行');
      }
      throw new Error(`服务器响应错误: ${response.status}`);
    }
    
    // 处理流式响应
    const reader = response.body?.getReader();
    if (!reader) {
      throw new Error('无法读取响应流');
    }
    
    const decoder = new TextDecoder();
    let buffer = '';
    
    while (true) {
      const { done, value } = await reader.read();
      
      if (done) {
        break;
      }
      
      // 解码并处理数据
      const text = decoder.decode(value, { stream: true });
      buffer += text;
      
      // 按行处理数据
      const lines = buffer.split('\n');
      buffer = lines.pop() || ''; // 最后一行可能不完整，保留到下一次
      
      for (const line of lines) {
        if (line.trim()) {
          try {
            processStreamData(line);
          } catch (e: Error | unknown) {
            console.error('处理数据流时出错:', e);
            message.error(`处理数据时出错: ${e instanceof Error ? e.message : '未知错误'}`);
          }
        }
      }
    }
    
    // 处理最后可能剩余的数据
    if (buffer.trim()) {
      try {
        processStreamData(buffer);
      } catch (e: Error | unknown) {
        console.error('处理最后的数据块时出错:', e);
        message.error(`处理数据时出错: ${e instanceof Error ? e.message : '未知错误'}`);
      }
    }
    
    message.success('分析完成');
  } catch (error: any) {
    let errorMessage = '分析出错: ';
    if (error.message.includes('404')) {
      errorMessage += '服务器接口未找到，请确保后端服务正常运行';
    } else {
      errorMessage += error.message || '未知错误';
    }
    message.error(errorMessage);
    console.error('分析时出错:', error);
    
    // 清空分析状态
    analyzedStocks.value = [];
  } finally {
    isAnalyzing.value = false;
  }
}

// 复制分析结果
async function copyAnalysisResults() {
  if (analyzedStocks.value.length === 0) {
    message.warning('没有可复制的分析结果');
    return;
  }
  
  try {
    // 格式化分析结果
    const formattedResults = analyzedStocks.value
      .filter((stock: StockInfo) => stock.analysisStatus === 'completed')
      .map((stock: StockInfo) => {
        let result = `【${stock.code} ${stock.name || ''}】\n`;
        
        // 添加分析日期
        if (stock.analysisDate) {
          try {
            const date = new Date(stock.analysisDate);
            if (!isNaN(date.getTime())) {
              result += `分析日期: ${date.toISOString().split('T')[0]}\n`;
            } else {
              result += `分析日期: ${stock.analysisDate}\n`;
            }
          } catch (e) {
            result += `分析日期: ${stock.analysisDate}\n`;
          }
        }
        
        // 添加评分和推荐信息
        if (stock.score !== undefined) {
          result += `评分: ${stock.score}\n`;
        }
        
        if (stock.recommendation) {
          result += `推荐: ${stock.recommendation}\n`;
        }
        
        // 添加技术指标信息
        if (stock.rsi !== undefined) {
          result += `RSI: ${stock.rsi.toFixed(2)}\n`;
        }
        
        if (stock.priceChange !== undefined) {
          const sign = stock.priceChange > 0 ? '+' : '';
          result += `涨跌额: ${sign}${stock.priceChange.toFixed(2)}\n`;
        }
        
        if (stock.maTrend) {
          const trendMap: Record<string, string> = {
            'UP': '上升',
            'DOWN': '下降',
            'NEUTRAL': '平稳'
          };
          const trend = trendMap[stock.maTrend] || stock.maTrend;
          result += `均线趋势: ${trend}\n`;
        }
        
        if (stock.macdSignal) {
          const signalMap: Record<string, string> = {
            'BUY': '买入',
            'SELL': '卖出',
            'HOLD': '持有',
            'NEUTRAL': '中性'
          };
          const signal = signalMap[stock.macdSignal] || stock.macdSignal;
          result += `MACD信号: ${signal}\n`;
        }
        
        if (stock.volumeStatus) {
          const statusMap: Record<string, string> = {
            'HIGH': '放量',
            'LOW': '缩量',
            'NORMAL': '正常'
          };
          const status = statusMap[stock.volumeStatus] || stock.volumeStatus;
          result += `成交量: ${status}\n`;
        }
        
        // 添加分析结果
        result += `\n${stock.analysis || '无分析结果'}\n`;
        
        return result;
      })
      .join('\n');
    
    if (!formattedResults) {
      message.warning('没有已完成的分析结果可复制');
      return;
    }
    
    // 复制到剪贴板
    await copy(formattedResults);
    message.success('已复制分析结果到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
    console.error('复制分析结果时出错:', error);
  }
}

// 处理导出选择
function handleExportSelect(key: string) {
  switch (key) {
    case 'csv':
      exportToCSV();
      break;
    case 'excel':
      message.info('Excel导出功能即将推出');
      break;
    case 'pdf':
      message.info('PDF导出功能即将推出');
      break;
  }
}

// 导出为CSV
function exportToCSV() {
  if (analyzedStocks.value.length === 0) {
    message.warning('没有可导出的分析结果');
    return;
  }
  
  try {
    // 创建CSV内容
    const headers = ['代码', '名称', '价格', '涨跌幅', 'RSI', '均线趋势', 'MACD信号', '成交量状态', '评分', '推荐', '分析日期'];
    let csvContent = headers.join(',') + '\n';
    
    // 添加数据行
    analyzedStocks.value.forEach(stock => {
      const row = [
        `"${stock.code}"`,
        `"${stock.name || ''}"`,
        stock.price !== undefined ? stock.price.toFixed(2) : '',
        stock.changePercent !== undefined ? `${stock.changePercent > 0 ? '+' : ''}${stock.changePercent.toFixed(2)}%` : '',
        stock.rsi !== undefined ? stock.rsi.toFixed(2) : '',
        stock.maTrend ? getChineseTrend(stock.maTrend) : '',
        stock.macdSignal ? getChineseSignal(stock.macdSignal) : '',
        stock.volumeStatus ? getChineseVolumeStatus(stock.volumeStatus) : '',
        stock.score !== undefined ? stock.score : '',
        `"${stock.recommendation || ''}"`,
        stock.analysisDate || ''
      ];
      
      csvContent += row.join(',') + '\n';
    });
    
    // 创建Blob对象
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    
    // 创建下载链接
    const link = document.createElement('a');
    link.setAttribute('href', url);
    link.setAttribute('download', `分析结果_${new Date().toISOString().split('T')[0]}.csv`);
    link.style.visibility = 'hidden';
    
    // 添加到文档并触发点击
    document.body.appendChild(link);
    link.click();
    
    // 清理
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
    
    message.success('已导出CSV文件');
  } catch (error) {
    message.error('导出失败');
    console.error('导出CSV时出错:', error);
  }
}

// 辅助函数：获取中文趋势描述
function getChineseTrend(trend: string): string {
  const trendMap: Record<string, string> = {
    'UP': '上升',
    'DOWN': '下降',
    'NEUTRAL': '平稳'
  };
  return trendMap[trend] || trend;
}

// 辅助函数：获取中文信号描述
function getChineseSignal(signal: string): string {
  const signalMap: Record<string, string> = {
    'BUY': '买入',
    'SELL': '卖出',
    'HOLD': '持有',
    'NEUTRAL': '中性'
  };
  return signalMap[signal] || signal;
}

// 辅助函数：获取中文成交量状态描述
function getChineseVolumeStatus(status: string): string {
  const statusMap: Record<string, string> = {
    'HIGH': '放量',
    'LOW': '缩量',
    'NORMAL': '正常'
  };
  return statusMap[status] || status;
}

// 页面加载时获取公告
onMounted(async () => {
  try {
    // 添加窗口大小变化监听
    window.addEventListener('resize', handleResize);
    
    // 从 API 获取公告信息
    const config = await apiService.getConfig();
    
    if (config.announcement) {
      announcement.value = config.announcement;
      // 使用通知显示公告
      showAnnouncement(config.announcement);
    }
  } catch (error) {
    console.error('获取配置时出错:', error);
  }
});

// 组件销毁前移除事件监听
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize);
});

// 处理公告关闭事件
function handleAnnouncementClose() {
  showAnnouncementBanner.value = false;
}

// 从配额超限弹窗打开邀请对话框
function handleOpenInviteFromQuota() {
  // 这个功能需要在NavBar中实现邀请对话框
  // 目前只是关闭配额超限弹窗
  showQuotaExceededModal.value = false;
  message.info('请在导航栏点击"邀请"按钮生成邀请链接');
}

//analyzedStocks 控制台调试代码
(window as any).analyzedStocks = analyzedStocks.value;

</script>

<style scoped>
/* Main Layout - Transparent to show body gradient */
.app-container {
  min-height: 100vh;
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
  padding-bottom: 40px;
  box-sizing: border-box;
}

.main-layout {
  background: transparent !important; /* Allow body gradient to show */
  width: 100%;
  max-width: 100vw;
  overflow-x: hidden;
}

.main-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem 2rem;
  width: 100%;
  box-sizing: border-box;
  background: transparent !important;
}

/* Glassmorphism Analysis Card */
.analysis-container {
  margin-bottom: 1.5rem;
  border-radius: 24px !important;
  overflow: hidden;
  transition: box-shadow 0.4s cubic-bezier(0.4, 0, 0.2, 1);
  background: rgba(255, 255, 255, 0.75) !important;
  box-shadow: 0 4px 24px rgba(102, 126, 234, 0.08);
}

.analysis-container:hover {
  box-shadow: 0 8px 40px rgba(102, 126, 234, 0.12);
}

/* Config Section */
.config-section {
  padding: 0.5rem;
  background: rgba(255, 255, 255, 0.3);
  border-radius: 12px;
  height: 100%;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.action-buttons .n-button {
  flex: 1;
}

/* Results Section */
.results-section {
  padding: 0.5rem;
  min-height: 400px;
  display: flex;
  flex-direction: column;
}

.results-header {
  margin-bottom: 1.25rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

/* Analysis HTML Content */
.analysis-html {
  font-size: 0.95rem;
  line-height: 1.6;
  white-space: pre-wrap;
  word-break: break-word;
  max-height: 300px;
  overflow-y: auto;
  color: #374151;
}

/* Highlighted Terms in Analysis */
.analysis-html :deep(strong) { color: #2563eb; font-weight: 600; }
.analysis-html :deep(.buy) { color: #dc2626; font-weight: 700; background: rgba(220, 38, 38, 0.1); padding: 0 4px; border-radius: 4px; }
.analysis-html :deep(.sell) { color: #059669; font-weight: 700; background: rgba(5, 150, 105, 0.1); padding: 0 4px; border-radius: 4px; }
.analysis-html :deep(.up) { color: #dc2626; }
.analysis-html :deep(.down) { color: #059669; }

/* Table Styles Override */
.table-container {
  width: 100%;
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.4);
}

:deep(.n-data-table) {
  background: transparent !important;
}

:deep(.n-data-table-th) {
  background: rgba(255, 255, 255, 0.5) !important;
  font-weight: 600 !important;
  color: #4b5563 !important;
}

:deep(.n-data-table-td) {
  background: transparent !important;
}

/* Scroll Indicator for Mobile Tables */
.table-container::after {
  content: '← 滑动查看更多 →';
  position: absolute;
  bottom: 12px;
  right: 50%;
  transform: translateX(50%);
  color: rgba(107, 114, 128, 0.6);
  font-size: 12px;
  pointer-events: none;
  background: rgba(255, 255, 255, 0.8);
  padding: 2px 8px;
  border-radius: 10px;
  opacity: 0;
  transition: opacity 0.3s;
  pointer-events: none;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .main-content {
    padding: 1rem 0.75rem;
  }
  
  .analysis-container {
    border-radius: 16px !important;
  }
  
  .analysis-container :deep(.n-card__content) {
    padding: 1rem !important;
  }
  
  .action-buttons {
    flex-direction: column;
  }
  
  /* Show table scroll hint on mobile */
  .table-container::after {
    opacity: 1;
    animation: fadeHint 3s 2 forwards;
  }
  
  .results-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.75rem;
  }
  
  .results-header :deep(.n-space) {
    width: 100%;
    justify-content: space-between;
  }
}

@keyframes fadeHint {
  0%, 10% { opacity: 0; }
  20%, 80% { opacity: 1; }
  90%, 100% { opacity: 0; }
}

/* Animations */
@media (prefers-reduced-motion: no-preference) {
  .analysis-container {
    animation: slideUp 0.6s cubic-bezier(0.16, 1, 0.3, 1);
  }
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
