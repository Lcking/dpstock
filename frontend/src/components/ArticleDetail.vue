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
            <p class="stock-name">{{ article.stock_name }}</p>
            <span class="stock-code">{{ article.stock_code }}</span>
          </div>
          <AiScorePanel
            v-if="aiScoreForArticle"
            :ai-score="aiScoreForArticle"
            :compact="true"
            style="min-width: 240px;"
          />
          <div v-else class="score-badge" :class="getScoreClass(article.score)">
            <div class="score-label">AI 综合评分 (legacy)</div>
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
        <component
          v-if="article"
          :is="ArticleKlineChartAsync"
          :stock-code="article.stock_code"
          :market-type="article.market_type"
        />
        <div v-if="chartModuleError" class="chart-module-error">
          {{ chartModuleError }}
        </div>
      </section>

      <section class="analysis-content-section">
        <h3 class="section-title">AI 深度分析报告</h3>
        <!-- 优先显示 Analysis V1 格式 -->
        <AnalysisV1Display 
          v-if="analysisV1Data"
          :data="analysisV1Data"
          :stock-code="article.stock_code"
          :stock-name="article.stock_name"
          :hide-judgment-zone="true"
          @saved="handleJudgmentSaved"
        />
        <!-- 降级：显示普通文本分析 -->
        <div v-else class="article-content" v-html="parsedContent"></div>
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
import { ref, computed, onMounted, defineAsyncComponent, defineComponent, h } from 'vue';
import { useRoute } from 'vue-router';
import { NButton, NIcon, NTag, NEmpty, NDivider } from 'naive-ui';
import { ArrowBackOutline as ArrowBack } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import { parseMarkdown, getCategoryName } from '@/utils';
import { applyPageSeo, getArticlePreview, setCanonicalUrl } from '@/utils/seo';
import ShareButtons from './ShareButtons.vue';
import AnalysisV1Display from './AnalysisV1Display.vue';
import AiScorePanel from './AiScorePanel.vue';
import type { AiScore } from '@/types';

const route = useRoute();
const article = ref<any>(null);
const loading = ref(true);
const chartModuleError = ref('');

const ChartModuleLoading = defineComponent({
  name: 'ArticleChartModuleLoading',
  setup() {
    return () => h('div', { class: 'chart-module-loading' }, '图表模块加载中…');
  }
});

const ChartModuleError = defineComponent({
  name: 'ArticleChartModuleError',
  setup() {
    return () => h('div', { class: 'chart-module-error-placeholder' }, '图表模块加载失败，请稍后重试');
  }
});

const ArticleKlineChartAsync = defineAsyncComponent({
  loader: async () => {
    try {
      chartModuleError.value = '';
      return await import('@/components/charts/ArticleKlineChart.vue');
    } catch (error) {
      chartModuleError.value = '图表模块加载失败，正文内容不受影响';
      throw error;
    }
  },
  loadingComponent: ChartModuleLoading,
  errorComponent: ChartModuleError,
  delay: 120,
  timeout: 15000,
});

const aiScoreForArticle = computed<AiScore | null>(() => {
  // 1) Prefer stored ai_score_json (new articles)
  const raw = article.value?.ai_score_json;
  if (raw && typeof raw === 'string') {
    try {
      return JSON.parse(raw);
    } catch (e) {
      console.warn('Failed to parse ai_score_json:', e);
    }
  }
  // 2) Fallback: parse from AnalysisV1 content if embedded
  const v1 = analysisV1Data.value;
  if (v1 && (v1 as any).ai_score) {
    return (v1 as any).ai_score as AiScore;
  }
  return null;
});

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
  }
}

// SEO: 更新 Meta 标签
function updateMetaTags() {
  if (!article.value) return;
  
  const categoryName = getCategoryName(article.value.market_type);
  const title = article.value.title;
  const canonicalPath = `/analysis/${article.value.id}`;
  
  // 生成 description：优先从 Analysis V1 提取，否则使用原文本
  let description = '';
  if (analysisV1Data.value) {
    // 从 Analysis V1 提取有意义的描述
    const structureDesc = analysisV1Data.value.structure_snapshot?.trend_description || '';
    const s = aiScoreForArticle.value?.overall?.score ?? article.value.score;
    description = `${article.value.stock_name}(${article.value.stock_code})当日行情深度分析，综合评分 ${s}。${getArticlePreview(structureDesc, 120)}`;
  } else {
    const s = aiScoreForArticle.value?.overall?.score ?? article.value.score;
    description = `${article.value.stock_name}(${article.value.stock_code})当日行情深度分析，综合评分 ${s}。${getArticlePreview(article.value.content, 120)}`;
  }
  
  const keywords = `${article.value.stock_name}, ${article.value.stock_code}, ${categoryName}分析, 智能辅助, 投资辅助, ${article.value.market_type}`;
  applyPageSeo({
    title,
    description,
    canonicalPath,
    keywords,
    ogType: 'article',
  });
  setCanonicalUrl(canonicalPath);

  const updateMeta = (name: string, content: string, attr: 'name' | 'property' = 'name') => {
    let el = document.querySelector(`meta[${attr}="${name}"]`);
    if (!el) {
      el = document.createElement('meta');
      el.setAttribute(attr, name);
      document.head.appendChild(el);
    }
    el.setAttribute('content', content);
  };
  updateMeta('og:url', articleUrl.value, 'property');
  updateMeta('twitter:card', 'summary_large_image');
  updateMeta('twitter:title', title);
  updateMeta('twitter:description', description);
  updateMeta('twitter:image', 'https://aguai.net/favicon.ico');
}

// SEO: 结构化数据 (JSON-LD)
const schemaData = computed(() => {
  if (!article.value) return '';
  const data = {
    "@context": "https://schema.org",
    "@graph": [
      {
        "@type": "Article",
        "headline": article.value.title,
        "description": getArticlePreview(article.value.content, 180),
        "author": {
          "@type": "Organization",
          "name": "Agu AI"
        },
        "publisher": {
          "@type": "Organization",
          "name": "Agu AI"
        },
        "datePublished": article.value.publish_date,
        "mainEntityOfPage": articleUrl.value,
        "about": {
          "@type": "Thing",
          "name": article.value.stock_name,
          "alternateName": article.value.stock_code
        }
      },
      {
        "@type": "BreadcrumbList",
        "itemListElement": [
          {
            "@type": "ListItem",
            "position": 1,
            "name": "分析专栏",
            "item": "https://aguai.net/analysis"
          },
          {
            "@type": "ListItem",
            "position": 2,
            "name": article.value.title,
            "item": articleUrl.value
          }
        ]
      }
    ]
  };
  return JSON.stringify(data);
});

// 文章完整 URL（用于分享）
const articleUrl = computed(() => {
  if (!article.value) return '';
  return `${window.location.origin}/analysis/${article.value.id}`;
});

// 尝试解析 Analysis V1 JSON
function repairJson(text: string): any | null {
  try {
    return JSON.parse(text)
  } catch {
    // pass
  }
  let fixed = text.replace(/,\s*([}\]])/g, '$1')
  const lines = fixed.split('\n')
  const repaired = lines.map(line => {
    const stripped = line.trim()
    const m = stripped.match(/^"([^"]+)"\s*:\s*(.+)$/)
    if (m) {
      let val = m[2].trimEnd()
      const hasComma = val.endsWith(',')
      if (hasComma) val = val.slice(0, -1)
      if (val && !val.startsWith('"') && !val.startsWith('{') && !val.startsWith('[')
          && !/^-?\d/.test(val) && !['true', 'false', 'null'].includes(val)) {
        const escaped = val.replace(/\\/g, '\\\\').replace(/"/g, '\\"')
        const indent = line.substring(0, line.length - line.trimStart().length)
        return `${indent}"${m[1]}": "${escaped}"${hasComma ? ',' : ''}`
      }
    }
    return line
  })
  try {
    return JSON.parse(repaired.join('\n'))
  } catch {
    return null
  }
}

const analysisV1Data = computed(() => {
  if (!article.value?.content) return null;
  
  try {
    let jsonStr = article.value.content;
    
    if (jsonStr.includes('```json')) {
      jsonStr = jsonStr.split('```json')[1].split('```')[0].trim();
    } else if (jsonStr.includes('```')) {
      jsonStr = jsonStr.split('```')[1].split('```')[0].trim();
    }
    
    const parsed = repairJson(jsonStr);
    
    if (parsed) {
      const requiredFields = ['structure_snapshot', 'pattern_fitting', 'indicator_translate', 
                             'risk_of_misreading', 'judgment_zone'];
      if (requiredFields.every(field => field in parsed)) {
        return parsed;
      }
    }
  } catch (e) {
    console.warn('Failed to parse Analysis V1 JSON:', e);
  }
  
  return null;
});

const parsedContent = computed(() => {
  // 如果是 Analysis V1 格式，不需要解析为 markdown
  if (analysisV1Data.value) return '';
  
  if (article.value?.content) {
    return parseMarkdown(article.value.content);
  }
  return '';
});

// 处理判断保存成功事件
function handleJudgmentSaved(judgmentId: string) {
  console.log('Judgment saved from archive:', judgmentId);
}

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
  min-height: 450px;
  position: relative;
}

.chart-module-loading {
  width: 100%;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px dashed rgba(100, 116, 139, 0.4);
  color: #64748b;
  font-size: 0.92rem;
  background: rgba(248, 250, 252, 0.72);
}

.chart-module-error-placeholder {
  width: 100%;
  min-height: 400px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid rgba(248, 113, 113, 0.35);
  color: #b91c1c;
  font-size: 0.92rem;
  background: rgba(254, 242, 242, 0.78);
}

.chart-module-error {
  margin-top: 10px;
  display: inline-flex;
  align-items: center;
  color: #b91c1c;
  font-size: 0.82rem;
  background: rgba(254, 242, 242, 0.78);
  border: 1px solid rgba(252, 165, 165, 0.5);
  border-radius: 999px;
  padding: 4px 10px;
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
