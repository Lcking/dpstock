<template>
  <div class="analysis-list-container">
    <div class="page-header">
      <h1 class="page-title">分析专栏</h1>
      <p class="page-subtitle">沉淀每日 AI 深度分析，见证市场异动轨迹</p>
      <a href="/stocks" class="stock-index-link">浏览热门个股 AI 诊股清单</a>
    </div>

    <div v-if="!searchQuery" class="weekly-recap-banner">
      <div class="weekly-recap-copy">
        <h2 class="weekly-recap-title">判断验证周报</h2>
        <p class="weekly-recap-desc">汇总近一周复盘结果与条件表现，辅助检验判断质量。</p>
      </div>
      <div class="weekly-recap-actions">
        <a href="/review/weekly" class="weekly-recap-link primary">查看周报</a>
        <router-link
          v-if="latestWeeklyArticle"
          :to="`/analysis/${latestWeeklyArticle.id}`"
          class="weekly-recap-link secondary"
        >
          最新归档
        </router-link>
      </div>
    </div>

    <div class="search-bar">
      <n-input
        v-model:value="searchQuery"
        aria-label="搜索分析文章"
        placeholder="搜索代码、名称或文章标题…"
        clearable
        @update:value="handleSearch"
      >
        <template #prefix>
          <n-icon><SearchOutline /></n-icon>
        </template>
      </n-input>
    </div>

    <div v-if="loading" class="loading-state">
      <n-spin size="large" />
      <p>正在拉取最新文章...</p>
    </div>

    <div v-else-if="articles.length === 0" class="empty-state">
      <n-empty description="暂无存档分析">
        <template #extra>
          <n-button @click="$router.push('/')">去分析</n-button>
        </template>
      </n-empty>
    </div>

    <div v-else class="articles-grid">
      <div
        v-for="article in articles"
        :key="article.id"
        class="article-card-link"
        :class="{ 'article-card-link--weekly': article.stock_code === 'WEEKLY_RECAP' }"
      >
        <n-card class="article-card" :class="{ 'article-card--weekly': article.stock_code === 'WEEKLY_RECAP' }">
          <div class="article-meta">
            <n-tag
              v-if="article.stock_code === 'WEEKLY_RECAP'"
              type="warning"
              size="small"
              round
              :bordered="false"
            >
              周报
            </n-tag>
            <n-tag v-else :type="getMarketType(article.market_type)" size="small" round :bordered="false">
              {{ article.market_type }}
            </n-tag>
            <span class="publish-date">{{ article.publish_date }}</span>
          </div>
          <router-link :to="`/analysis/${article.id}`" class="article-title-link">
            <h2 class="article-title">{{ article.title }}</h2>
          </router-link>
          <div class="article-preview">
            {{ getArticlePreview(article.content) }}
          </div>
          <div class="article-footer">
            <div class="stock-info">
              <a :href="`/stock/${article.stock_code}`" class="stock-page-link">查看个股页：{{ article.stock_name }}</a>
              <span class="stock-code">{{ article.stock_code }}</span>
            </div>
            <div class="score-tag" :class="getScoreClass(article.score)">
              评分: {{ article.score }}
            </div>
          </div>
        </n-card>
      </div>
    </div>
    
    <!-- 加载更多状态 -->
    <div v-if="loadingMore" class="loading-more">
      <n-spin size="small" />
      <span>加载更多…</span>
    </div>
    <div v-else-if="!hasMore && articles.length > 0" class="no-more">
      已加载全部内容
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { NCard, NTag, NEmpty, NButton, NSpin, NInput, NIcon } from 'naive-ui';
import { SearchOutline } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import { applyPageSeo, getArticlePreview } from '@/utils/seo';
import { useDebounceFn } from '@vueuse/core';

const articles = ref<any[]>([]);
const latestWeeklyArticle = ref<{ id: number; title: string } | null>(null);
const loading = ref(true);
const loadingMore = ref(false);
const searchQuery = ref('');
const offset = ref(0);
const hasMore = ref(true);
const LIMIT = 20;

function sortWeeklyRecapFirst(list: any[]) {
  return [...list].sort((a, b) => {
    const aWeekly = a.stock_code === 'WEEKLY_RECAP' ? 1 : 0;
    const bWeekly = b.stock_code === 'WEEKLY_RECAP' ? 1 : 0;
    return bWeekly - aWeekly;
  });
}

const handleSearch = useDebounceFn(() => {
  // 搜索时重置分页
  offset.value = 0;
  hasMore.value = true;
  fetchArticles(false);
}, 500);

async function fetchArticles(append = false) {
  if (append) {
    loadingMore.value = true;
  } else {
    loading.value = true;
    offset.value = 0;
  }
  
  try {
    const data = await apiService.getArticles(LIMIT, offset.value, searchQuery.value);
    const sorted = sortWeeklyRecapFirst(data);
    
    if (append) {
      articles.value.push(...sorted);
    } else {
      articles.value = sorted;
    }
    
    // 如果返回数量少于请求数量，说明没有更多了
    hasMore.value = data.length === LIMIT;
    offset.value += data.length;
  } catch (error) {
    console.error('获取文章列表失败:', error);
  } finally {
    loading.value = false;
    loadingMore.value = false;
  }
}

function handleScroll() {
  if (loadingMore.value || !hasMore.value) return;
  
  const { scrollTop, scrollHeight, clientHeight } = document.documentElement;
  // 距离底部 200px 时开始加载
  if (scrollTop + clientHeight >= scrollHeight - 200) {
    fetchArticles(true);
  }
}

function getMarketType(type: string) {
  const map: any = { 'A': 'success', 'HK': 'info', 'US': 'warning', 'ETF': 'info', 'LOF': 'info', 'Fund': 'error' };
  return map[type] || 'default';
}

function getScoreClass(score: number) {
  if (score >= 80) return 'high';
  if (score >= 60) return 'medium';
  return 'low';
}

onMounted(() => {
  fetchArticles(false);
  apiService.getLatestWeeklyRecapArticle().then((article) => {
    latestWeeklyArticle.value = article;
  });
  applyPageSeo({
    title: '分析专栏 | Agu AI',
    description: '查看每日 AI 股票分析专栏，快速浏览重点标的、市场异动与结构化研判。',
    canonicalPath: '/analysis',
    keywords: '分析专栏,股票分析文章,Agu AI,市场异动,结构化研判',
  });
  window.addEventListener('scroll', handleScroll);
});

onBeforeUnmount(() => {
  window.removeEventListener('scroll', handleScroll);
});
</script>

<style scoped>
.analysis-list-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-header {
  text-align: center;
  margin-bottom: 40px;
}

.page-title {
  font-size: 2.5rem;
  font-weight: 800;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  margin-bottom: 8px;
}

.page-subtitle {
  color: #64748b;
  font-size: 1.1rem;
}

.stock-index-link {
  display: inline-flex;
  margin-top: 14px;
  padding: 9px 14px;
  border-radius: 999px;
  background: rgba(85, 96, 214, 0.10);
  color: #5560d6;
  font-weight: 700;
  text-decoration: none;
}

.weekly-recap-banner {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 28px;
  padding: 20px 22px;
  border-radius: 18px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12) 0%, rgba(118, 75, 162, 0.10) 100%);
  border: 1px solid rgba(102, 126, 234, 0.18);
}

.weekly-recap-title {
  margin: 0 0 6px;
  font-size: 1.25rem;
  color: #334155;
}

.weekly-recap-desc {
  margin: 0;
  color: #64748b;
  font-size: 0.95rem;
}

.weekly-recap-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.weekly-recap-link {
  display: inline-flex;
  align-items: center;
  padding: 9px 14px;
  border-radius: 999px;
  text-decoration: none;
  font-weight: 600;
  font-size: 0.92rem;
}

.weekly-recap-link.primary {
  background: #667eea;
  color: #fff;
}

.weekly-recap-link.secondary {
  background: #fff;
  color: #667eea;
  border: 1px solid rgba(102, 126, 234, 0.35);
}

.article-card--weekly {
  border: 1px solid rgba(245, 158, 11, 0.35);
  background: linear-gradient(180deg, #fffdf8 0%, #ffffff 100%);
}

.article-card-link--weekly .article-title {
  color: #b45309;
}

.stock-index-link:hover {
  background: rgba(85, 96, 214, 0.16);
}

.search-bar {
  max-width: 600px;
  margin: 0 auto 40px;
}

.search-bar :deep(.n-input) {
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

.articles-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 24px;
}

.article-card-link {
  display: block;
  color: inherit;
  text-decoration: none;
}

.article-title-link {
  color: inherit;
  text-decoration: none;
}

.article-card {
  cursor: pointer;
  transition: transform 0.3s cubic-bezier(0.23, 1, 0.32, 1), box-shadow 0.3s cubic-bezier(0.23, 1, 0.32, 1), background 0.3s cubic-bezier(0.23, 1, 0.32, 1);
  border-radius: 16px !important;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.3);
}

.article-card:hover {
  transform: translateY(-8px);
  box-shadow: 0 12px 24px rgba(31, 38, 135, 0.1);
  background: rgba(255, 255, 255, 0.9);
}

.article-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.publish-date {
  font-size: 0.8rem;
  color: #94a3b8;
}

.article-title {
  font-size: 1.2rem;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 12px;
  color: #1e293b;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-preview {
  font-size: 0.9rem;
  color: #64748b;
  line-height: 1.6;
  margin-bottom: 20px;
  min-height: 4.5em;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.article-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.stock-page-link {
  font-weight: 600;
  color: #5560d6;
  text-decoration: none;
}

.stock-page-link:hover {
  text-decoration: underline;
}

.stock-code {
  color: #94a3b8;
  font-family: monospace;
}

.score-tag {
  font-weight: 700;
  padding: 4px 8px;
  border-radius: 6px;
  font-size: 0.85rem;
}

.score-tag.high { color: #059669; background: rgba(5, 150, 105, 0.1); }
.score-tag.medium { color: #d97706; background: rgba(217, 119, 6, 0.1); }
.score-tag.low { color: #dc2626; background: rgba(220, 38, 38, 0.1); }

.loading-state, .empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 100px 0;
}

.loading-more {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 32px 0;
  color: #64748b;
  font-size: 14px;
}

.no-more {
  text-align: center;
  padding: 32px 0;
  color: #94a3b8;
  font-size: 14px;
}
</style>
