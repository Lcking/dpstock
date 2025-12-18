<template>
  <div class="analysis-list-container">
    <div class="page-header">
      <h1 class="page-title">分析专栏</h1>
      <p class="page-subtitle">沉淀每日 AI 深度分析，见证市场异动轨迹</p>
    </div>

    <div class="search-bar">
      <n-input
        v-model:value="searchQuery"
        placeholder="搜索股票代码、名称或文章标题..."
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
          <n-button @click="$router.push('/')">去分析几只股票</n-button>
        </template>
      </n-empty>
    </div>

    <div v-else class="articles-grid">
      <n-card 
        v-for="article in articles" 
        :key="article.id" 
        class="article-card"
        @click="$router.push(`/analysis/${article.id}`)"
      >
        <div class="article-meta">
          <n-tag :type="getMarketType(article.market_type)" size="small" round :bordered="false">
            {{ article.market_type }}
          </n-tag>
          <span class="publish-date">{{ article.publish_date }}</span>
        </div>
        <h2 class="article-title">{{ article.title }}</h2>
        <div class="article-preview">
          {{ article.content.substring(0, 100) }}...
        </div>
        <div class="article-footer">
          <div class="stock-info">
            <span class="stock-name">{{ article.stock_name }}</span>
            <span class="stock-code">{{ article.stock_code }}</span>
          </div>
          <div class="score-tag" :class="getScoreClass(article.score)">
            评分: {{ article.score }}
          </div>
        </div>
      </n-card>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { NCard, NTag, NEmpty, NButton, NSpin, NInput, NIcon } from 'naive-ui';
import { SearchOutline } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import { useDebounceFn } from '@vueuse/core';

const articles = ref<any[]>([]);
const loading = ref(true);
const searchQuery = ref('');

const handleSearch = useDebounceFn(() => {
  fetchArticles();
}, 500);

async function fetchArticles() {
  loading.value = true;
  try {
    const data = await apiService.getArticles(50, 0, searchQuery.value);
    articles.value = data;
  } catch (error) {
    console.error('获取文章列表失败:', error);
  } finally {
    loading.value = false;
  }
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

onMounted(() => {
  fetchArticles();
  document.title = '分析专栏 - Agu AI';
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

.article-card {
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.23, 1, 0.32, 1);
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
  gap: 8px;
}

.stock-name {
  font-weight: 600;
  color: #475569;
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
</style>
