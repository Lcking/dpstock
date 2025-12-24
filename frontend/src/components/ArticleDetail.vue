<template>
  <div class="article-detail-container">
    <n-button class="back-button" quaternary @click="$router.push('/analysis')">
      <template #icon><n-icon><ArrowBack /></n-icon></template>
      返回专栏
    </n-button>

    <div v-if="loading" class="loading-state">
      <n-spin size="large" />
    </div>

    <div v-else-if="!article" class="error-state">
      <n-empty description="文章不存在" />
    </div>

    <article v-else class="article-body">
      <header class="article-header">
        <div class="article-meta">
          <n-tag :type="getMarketType(article.market_type)" size="small" round :bordered="false">
            {{ article.market_type }}
          </n-tag>
          <span class="publish-date">发布于: {{ article.publish_date }}</span>
        </div>
        <h1 class="article-title">{{ article.title }}</h1>
        <div class="stock-info-bar">
          <div class="stock-basic">
            <h2 class="stock-name">{{ article.stock_name }}</h2>
            <span class="stock-code">{{ article.stock_code }}</span>
          </div>
          <div class="score-badge" :class="getScoreClass(article.score)">
            <div class="score-label">AI 综合评分</div>
            <div class="score-value">{{ article.score }}</div>
          </div>
        </div>
      </header>
      
      <!-- 分享按钮 -->
      <ShareButtons :url="articleUrl" :title="article.title" />
      
      <n-divider />

      <!-- 行情走势回顾 -->
      <section class="chart-section">
        <h3 class="section-title">行情走势回顾</h3>
        <div ref="chartRef" class="kline-chart"></div>
        <div v-if="chartLoading" class="chart-loading">
          <n-spin size="small" />
          <span>加载行情数据...</span>
        </div>
      </section>

      <section class="analysis-content-section">
        <h3 class="section-title">AI 深度分析报告</h3>
        <div class="article-content" v-html="parsedContent"></div>
      </section>

      <footer class="article-footer">
        <n-divider />
        <p class="disclaimer">免责声明：本分析报告由 AI 自动生成，基于技术面和基本面历史数据，仅供参考，不构成任何投资建议。股市有风险，入市需谨慎。</p>
      </footer>

      <!-- JSON-LD Schema for SEO -->
      <component :is="'script'" type="application/ld+json" v-html="schemaData"></component>
    </article>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, nextTick } from 'vue';
import { useRoute } from 'vue-router';
import { NButton, NIcon, NTag, NSpin, NEmpty, NDivider } from 'naive-ui';
import { ArrowBackOutline as ArrowBack } from '@vicons/ionicons5';
import * as echarts from 'echarts';
import { apiService } from '@/services/api';
import { parseMarkdown, getCategoryName } from '@/utils';
import ShareButtons from './ShareButtons.vue';

const route = useRoute();
const article = ref<any>(null);
const loading = ref(true);

async function fetchArticle() {
  const id = Number(route.params.id);
  if (isNaN(id)) return;
  
  loading.value = true;
  try {
    const data = await apiService.getArticleDetail(id);
    article.value = data;
    
    // 更新 TKD 标签
    updateMetaTags();
  } catch (error) {
    console.error('获取文章详情失败:', error);
  } finally {
    loading.value = false;
    // 等待DOM更新后再初始化图表
    await nextTick();
    await nextTick(); // 双重nextTick确保v-if渲染完成
    initChart();
  }
}

// SEO: 更新 Meta 标签
function updateMetaTags() {
  if (!article.value) return;
  
  const categoryName = getCategoryName(article.value.market_type);
  const title = article.value.title;
  const description = `${article.value.stock_name}(${article.value.stock_code})当日行情深度分析，综合评分 ${article.value.score}。${article.value.content.substring(0, 150)}...`;
  const keywords = `${article.value.stock_name}, ${article.value.stock_code}, ${categoryName}分析, 智能辅助, 投资辅助, ${article.value.market_type}`;

  document.title = title;
  
  // 更新或创建 meta 标签
  const updateMeta = (name: string, content: string, attr: 'name' | 'property' = 'name') => {
    let el = document.querySelector(`meta[${attr}="${name}"]`);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, name);
      document.head.appendChild(el);
    }
    el.setAttribute('content', content);
  };

  updateMeta('description', description);
  updateMeta('keywords', keywords);
  updateMeta('og:title', title, 'property');
  updateMeta('og:description', description, 'property');
  updateMeta('og:type', 'article', 'property');
}

// SEO: 结构化数据 (JSON-LD)
const schemaData = computed(() => {
  if (!article.value) return '';
  const data = {
    "@context": "https://schema.org",
    "@type": "Article",
    "headline": article.value.title,
    "description": article.value.content.substring(0, 200),
    "author": {
      "@type": "Organization",
      "name": "Stock Scanner AI"
    },
    "publisher": {
      "@type": "Organization",
      "name": "Stock Scanner AI"
    },
    "datePublished": article.value.publish_date,
    "about": {
      "@type": "Thing",
      "name": article.value.stock_name,
      "alternateName": article.value.stock_code
    }
  };
  return JSON.stringify(data);
});

// 图表加载逻辑
const chartRef = ref<HTMLElement | null>(null);
const chartInstance = ref<echarts.ECharts | null>(null);
const chartLoading = ref(false);

// 文章完整 URL（用于分享）
const articleUrl = computed(() => {
  if (!article.value) return '';
  return `${window.location.origin}/article/${article.value.id}`;
});


async function initChart() {
  if (!chartRef.value || !article.value) {
    console.warn('initChart aborted: chartRef or article missing');
    return;
  }
  
  chartLoading.value = true;
  try {
    const stockCode = article.value.stock_code;
    const marketType = article.value.market_type;
    console.log('Loading K-line data for:', stockCode, marketType);
    
    const data = await apiService.getKlineData(stockCode, marketType);
    if (!data || data.error) {
      console.error('K-line data error:', data?.error);
      throw new Error(data?.error || 'No data');
    }
    
    console.log('K-line data received:', data.dates?.length, 'points');

    // 等待DOM完全渲染
    await nextTick();
    await new Promise(resolve => setTimeout(resolve, 100));

    if (!chartRef.value) {
      console.error('Chart container disappeared');
      return;
    }

    // 确保容器有尺寸
    const containerWidth = chartRef.value.offsetWidth;
    const containerHeight = chartRef.value.offsetHeight;
    console.log('Chart container size:', containerWidth, 'x', containerHeight);
    
    if (containerWidth === 0 || containerHeight === 0) {
      console.warn('Chart container has 0 size, setting explicit dimensions');
      chartRef.value.style.width = '100%';
      chartRef.value.style.height = '400px';
      await new Promise(resolve => setTimeout(resolve, 50));
    }

    if (chartInstance.value) {
      chartInstance.value.dispose();
    }

    chartInstance.value = echarts.init(chartRef.value);

    // 处理 MACD 数据格式适配
    const macdData = data.macd && data.macd.macd ? data.macd.macd : (data.macd || []);

    const option = {
      backgroundColor: 'transparent',
      animation: true,
      tooltip: {
        trigger: 'axis',
        axisPointer: { type: 'cross' }
      },
      grid: [
        { left: '8%', right: '3%', height: '55%', top: '5%' },
        { left: '8%', right: '3%', top: '65%', height: '15%' },
        { left: '8%', right: '3%', top: '85%', height: '10%' }
      ],
      xAxis: [
        { type: 'category', data: data.dates, boundaryGap: false, axisLine: { lineStyle: { color: '#94a3b8' } } },
        { type: 'category', gridIndex: 1, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } },
        { type: 'category', gridIndex: 2, data: data.dates, boundaryGap: false, axisTick: { show: false }, axisLabel: { show: false } }
      ],
      yAxis: [
        { scale: true, splitArea: { show: false }, splitLine: { lineStyle: { type: 'dashed', color: '#f1f5f9' } }, axisLabel: { fontSize: 10 } },
        { gridIndex: 1, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } },
        { gridIndex: 2, splitNumber: 3, axisLabel: { show: false }, axisTick: { show: false }, splitLine: { show: false } }
      ],
      series: [
        {
          name: 'K线',
          type: 'candlestick',
          data: data.values,
          itemStyle: { color: '#ef4444', color0: '#10b981', borderColor: '#ef4444', borderColor0: '#10b981' }
        },
        { name: 'MA5', type: 'line', data: data.ma5, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#f59e0b' } },
        { name: 'MA20', type: 'line', data: data.ma20, smooth: true, showSymbol: false, lineStyle: { width: 1.5, color: '#6366f1' } },
        { name: '成交量', type: 'bar', xAxisIndex: 1, yAxisIndex: 1, data: data.volumes, itemStyle: { color: (params: any) => data.values[params.dataIndex][1] > data.values[params.dataIndex][0] ? '#ef4444' : '#10b981' } },
        { name: 'MACD', type: 'line', xAxisIndex: 2, yAxisIndex: 2, data: macdData, smooth: true, showSymbol: false, lineStyle: { width: 1, color: '#ec4899' } }
      ]
    };

    chartInstance.value.setOption(option);
    console.log('Chart initialized successfully');
  } catch (err) {
    console.error('初始化图表失败:', err);
  } finally {
    chartLoading.value = false;
  }
}

const parsedContent = computed(() => {
  if (article.value?.content) {
    return parseMarkdown(article.value.content);
  }
  return '';
});

function getMarketType(type: string) {
  const map: any = { 'A': 'success', 'HK': 'info', 'US': 'warning', 'Fund': 'error' };
  return map[type] || 'default';
}

function getScoreClass(score: number) {
  if (score >= 80) return 'high';
  if (score >= 60) return 'medium';
  return 'low';
}

onMounted(fetchArticle);
</script>

<style scoped>
.article-detail-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
  background: white;
}

.back-button {
  margin-bottom: 24px;
}

.article-header {
  margin-bottom: 32px;
}

.article-meta {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 16px;
}

.publish-date {
  color: #64748b;
  font-size: 0.95rem;
  font-weight: 500;
}

.article-title {
  font-size: 2.5rem;
  font-weight: 800;
  line-height: 1.25;
  color: #1e293b;
  margin-bottom: 24px;
  letter-spacing: -0.02em;
}

.stock-info-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f8fafc;
  padding: 20px 24px;
  border-radius: 16px;
  border: 1px solid #f1f5f9;
}

.stock-basic {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-name {
  font-size: 1.5rem;
  font-weight: 700;
  color: #334155;
  margin: 0;
}

.stock-code {
  color: #64748b;
  font-family: 'JetBrains Mono', monospace;
  font-size: 1.1rem;
}

.score-badge {
  text-align: center;
  padding: 8px 16px;
  border-radius: 12px;
  min-width: 100px;
}

.score-label {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
  margin-bottom: 2px;
}

.score-value {
  font-size: 1.75rem;
  font-weight: 800;
}

.score-badge.high { color: #059669; background: rgba(5, 150, 105, 0.1); }
.score-badge.medium { color: #d97706; background: rgba(217, 119, 6, 0.1); }
.score-badge.low { color: #dc2626; background: rgba(220, 38, 38, 0.1); }

.section-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1e293b;
  margin: 40px 0 20px 0;
  padding-left: 12px;
  border-left: 4px solid #6366f1;
}

.chart-section {
  margin: 32px 0;
  height: 450px;
  position: relative;
}

.kline-chart {
  width: 100%;
  height: 400px;
  min-height: 400px;
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.chart-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: #64748b;
}

.article-content {
  font-size: 1.15rem;
  line-height: 1.8;
  color: #334155;
}

.article-content :deep(h2) {
  color: #0f172a;
  margin-top: 2.5rem;
  margin-bottom: 1.25rem;
  font-size: 1.75rem;
  font-weight: 800;
}

.article-content :deep(p) {
  margin-bottom: 1.5rem;
}

.article-footer {
  margin-top: 80px;
}

.disclaimer {
  font-size: 0.9rem;
  color: #94a3b8;
  text-align: center;
  line-height: 1.6;
  max-width: 600px;
  margin: 0 auto;
}

.loading-state {
  display: flex;
  justify-content: center;
  padding: 100px 0;
}
</style>
