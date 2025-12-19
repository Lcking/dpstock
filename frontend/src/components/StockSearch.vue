<template>
  <div class="stock-search-container">
    <n-input
      v-model:value="searchKeyword"
      placeholder="输入代码或名称搜索"
      @input="handleSearchInput"
      @blur="handleBlur"
      @focus="handleFocus"
      ref="searchInputRef"
    >
      <template #prefix>
        <n-icon :component="SearchIcon" />
      </template>
    </n-input>
    
    <div class="search-results mobile-search-results" v-show="showResults">
      <div v-if="loading" class="loading-results">
        <n-spin size="small" />
        <span>搜索中...</span>
      </div>
      
      <div v-else-if="results.length === 0 && searchKeyword" class="no-results">
        未找到相关数据
      </div>
      
      <template v-else>
        <n-scrollbar style="max-height: 300px;">
          <div
            v-for="item in results"
            :key="item.symbol"
            class="search-result-item mobile-search-result-item"
            @mousedown.prevent="selectStock(item)"
          >
            <div class="result-symbol-name">
              <span class="result-symbol">{{ item.symbol }}</span>
              <span class="result-name mobile-result-name">{{ item.name }}</span>
            </div>
            <div class="result-meta">
              <span class="result-market">{{ item.market }}</span>
              <span v-if="item.market_value" class="result-market-value">
                市值: {{ formatMarketValue(item.market_value) }}
              </span>
            </div>
          </div>
        </n-scrollbar>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { NInput, NIcon, NSpin, NScrollbar } from 'naive-ui';
import { Search as SearchIcon } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import { debounce, formatMarketValue as formatMarketValueFn } from '@/utils';
import type { SearchResult } from '@/types';

const props = defineProps<{
  marketType: string;
}>();

const emit = defineEmits<{
  (e: 'select', symbol: string): void;
}>();

const searchKeyword = ref('');
const results = ref<SearchResult[]>([]);
const loading = ref(false);
const showResults = ref(false);
const searchInputRef = ref<any>(null);
const isSelecting = ref(false); // 新增：防止blur和click竞争条件

// 创建防抖搜索函数
const debouncedSearch = debounce(async (keyword: string) => {
  if (!keyword) {
    results.value = [];
    loading.value = false;
    return;
  }

  loading.value = true;
  
  try {
    if (props.marketType === 'US') {
      // 美股搜索
      const searchResults = await apiService.searchUsStocks(keyword);
      // 限制只显示前10个结果
      results.value = searchResults.slice(0, 10);
    } else if (props.marketType === 'A') {
      // A 股搜索
      const searchResults = await apiService.searchAShares(keyword);
      results.value = searchResults.slice(0, 10);
    } else if (props.marketType === 'HK') {
      // 港股搜索
      const searchResults = await apiService.searchHKShares(keyword);
      results.value = searchResults.slice(0, 10);
    } else {
      // 基金搜索
      const searchResults = await apiService.searchFunds(keyword, props.marketType);
      // 限制只显示前10个结果
      results.value = searchResults.slice(0, 10);
    }
  } catch (error) {
    console.error('搜索数据时出错:', error);
    results.value = [];
  } finally {
    loading.value = false;
  }
}, 300);

function handleSearchInput() {
  showResults.value = true;
  debouncedSearch(searchKeyword.value);
}

function selectStock(item: SearchResult) {
  isSelecting.value = true; // 标记正在选择，防止blur误关闭
  // 处理symbol，确保不包含序号
  // 假设symbol格式可能是"1. AAPL"这样的格式，我们只需要"AAPL"部分
  const cleanSymbol = item.symbol.replace(/^\d+\.\s*/, '');
  emit('select', cleanSymbol);
  searchKeyword.value = '';
  showResults.value = false;
  
  // 延迟重置标志
  setTimeout(() => {
    isSelecting.value = false;
  }, 100);
}

function handleBlur() {
  // 延迟隐藏，并检查是否正在选择
  setTimeout(() => {
    if (!isSelecting.value) {
      showResults.value = false;
    }
  }, 250); // 增加到250ms，给选择操作更多时间
}

function handleFocus() {
  if (searchKeyword.value) {
    showResults.value = true;
  }
}

function formatMarketValue(value: number): string {
  return formatMarketValueFn(value);
}

// 点击外部时隐藏搜索结果
function handleClickOutside(event: MouseEvent) {
  if (
    searchInputRef.value &&
    !searchInputRef.value.$el.contains(event.target as Node)
  ) {
    showResults.value = false;
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleClickOutside);
});
</script>

<style scoped>
.stock-search-container {
  position: relative;
  width: 100%;
}

.search-results {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  z-index: 100;
  margin-top: 0.5rem;
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 12px;
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
  border: 1px solid rgba(255, 255, 255, 0.5);
  overflow: hidden;
  animation: slideDown 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  transform-origin: top center;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.loading-results,
.no-results {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  padding: 1.5rem;
  color: #6b7280;
  font-size: 0.9rem;
  font-weight: 500;
}

.search-result-item {
  padding: 0.85rem 1.25rem;
  cursor: pointer;
  transition: all 0.2s ease;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border-bottom: 1px solid rgba(0, 0, 0, 0.03);
}

.search-result-item:last-child {
  border-bottom: none;
}

.search-result-item:hover {
  background-color: rgba(102, 126, 234, 0.1);
  padding-left: 1.5rem;
}

.result-symbol-name {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.result-symbol {
  font-weight: 700;
  color: #1f2937;
  font-family: inherit;
}

.result-name {
  font-size: 0.8rem;
  color: #6b7280;
}

.result-meta {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 2px;
}

.result-market {
  font-size: 0.7rem;
  color: #9ca3af;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.05);
  padding: 2px 6px;
  border-radius: 4px;
}

.result-market-value {
  font-size: 0.75rem;
  color: #6b7280;
  font-feature-settings: "tnum";
  font-variant-numeric: tabular-nums;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .search-results {
    border-radius: 16px;
  }

  .search-result-item {
    padding: 1rem;
  }
  
  /* 确保输入框在移动端正确显示 */
  :deep(.n-input) {
    width: 100% !important;
  }
}

@media (max-width: 480px) {
  .result-symbol-name, .result-meta {
    font-size: 0.9rem;
  }
  
  .result-market, .result-market-value {
    font-size: 0.8rem;
  }
  
  .loading-results, .no-results {
    padding: 1rem;
    font-size: 0.85rem;
  }
}
</style>
