<template>
  <div class="watchlist-page">
    <!-- 顶部操作栏 -->
    <div class="watchlist-header">
      <h2>自选股</h2>
      <div class="header-actions">
        <n-button type="primary" @click="showAddDialog = true">
          <template #icon>
            <n-icon><AddCircleOutline /></n-icon>
          </template>
          添加标的
        </n-button>
      </div>
    </div>

    <!-- 筛选与排序 -->
    <watchlist-filters
      :sort="currentSort"
      :filters="currentFilters"
      @update:sort="handleSortChange"
      @update:filters="handleFiltersChange"
    />

    <!-- 加载状态：骨架屏 -->
    <div v-if="loading" class="watchlist-grid">
      <n-card v-for="i in 6" :key="i" class="watchlist-skeleton">
        <template #header>
          <n-skeleton text style="width: 40%" />
        </template>
        <template #header-extra>
          <n-skeleton text style="width: 60px" />
        </template>
        <n-space vertical>
          <n-skeleton text :repeat="2" />
          <n-skeleton text style="width: 60%" />
        </n-space>
      </n-card>
    </div>

    <!-- 列表内容 -->
    <div v-else-if="summaryData && summaryData.items.length > 0" class="watchlist-content">
      <div class="watchlist-stats">
        <n-text depth="3">
          共 {{ summaryData.total_count }} 只，筛选后 {{ summaryData.filtered_count }} 只
        </n-text>
      </div>

      <div class="watchlist-grid">
        <watchlist-item-card
          v-for="item in summaryData.items"
          :key="item.ts_code"
          :item="item"
          :selected="selectedCodes.includes(item.ts_code)"
          @select="toggleSelect(item.ts_code)"
          @remove="handleRemove(item.ts_code)"
          @click="navigateToAnalysis(item.ts_code)"
        />
      </div>

      <!-- 批量操作 -->
      <div v-if="selectedCodes.length > 0" class="batch-actions">
        <n-text>已选择 {{ selectedCodes.length }} 只</n-text>
        <n-button type="info" @click="navigateToCompare">
          进入比较
        </n-button>
      </div>
    </div>

    <!-- 空状态 -->
    <div v-else class="empty-state-container">
      <empty-state
        type="watchlist"
        title="还没有添加自选股"
        description="添加关注的股票，随时追踪趋势评分和结构变化"
      >
        <n-button type="primary" @click="showAddDialog = true">添加标的</n-button>
      </empty-state>
    </div>

    <!-- 添加标的对话框 -->
    <n-modal v-model:show="showAddDialog" preset="dialog" title="添加标的">
      <n-form>
        <n-form-item label="股票代码">
          <n-input
            v-model:value="newCodes"
            type="textarea"
            placeholder="输入股票代码，多个用逗号或换行分隔&#10;例如：600519.SH, 000001.SZ"
            :rows="5"
          />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space>
          <n-button @click="showAddDialog = false">取消</n-button>
          <n-button type="primary" @click="handleAdd" :loading="adding">
            添加
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  NButton, NIcon, NText, NModal, NForm, NFormItem, 
  NInput, NSpace, NCard, NSkeleton, useMessage 
} from 'naive-ui'
import { AddCircleOutline } from '@vicons/ionicons5'
import WatchlistFilters from './WatchlistFilters.vue'
import WatchlistItemCard from './WatchlistItemCard.vue'
import EmptyState from '../common/EmptyState.vue'
import type { WatchlistSummary } from '@/types/watchlist'

const router = useRouter()
const message = useMessage()

// State
const loading = ref(false)
const adding = ref(false)
const watchlistId = ref('default') // 默认自选股ID
const summaryData = ref<WatchlistSummary | null>(null)
const currentSort = ref('SCORE_DESC')
const currentFilters = ref<string[]>([])
const selectedCodes = ref<string[]>([])
const showAddDialog = ref(false)
const newCodes = ref('')

// 加载摘要数据
const loadSummary = async () => {
  loading.value = true
  try {
    const response = await fetch(
      `/api/watchlists/${watchlistId.value}/summary?` +
      `sort=${currentSort.value}&` +
      `filters=${currentFilters.value.join(',')}`
    )
    
    if (!response.ok) throw new Error('Failed to load summary')
    
    summaryData.value = await response.json()
  } catch (error) {
    console.error('Load summary error:', error)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

// 初始化：创建或获取默认自选股
const initWatchlist = async () => {
  loading.value = true // Ensure loading state covers initialization
  try {
    // 获取用户的自选股列表
    const response = await fetch('/api/watchlists')
    if (!response.ok) throw new Error('Failed to get watchlists')
    
    const watchlists = await response.json()
    
    if (watchlists.length === 0) {
      // 创建默认自选股
      const createResp = await fetch('/api/watchlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: '默认自选' })
      })
      if (!createResp.ok) throw new Error('Failed to create watchlist')
      
      const newList = await createResp.json()
      watchlistId.value = newList.id
    } else {
      watchlistId.value = watchlists[0].id
    }
    
    await loadSummary()
  } catch (error) {
    console.error('Init watchlist error:', error)
    message.error('初始化失败')
    loading.value = false
  }
}

// 排序变化
const handleSortChange = (sort: string) => {
  currentSort.value = sort
  loadSummary()
}

// 筛选变化
const handleFiltersChange = (filters: string[]) => {
  currentFilters.value = filters
  loadSummary()
}

// 选择/取消选择
const toggleSelect = (code: string) => {
  const index = selectedCodes.value.indexOf(code)
  if (index > -1) {
    selectedCodes.value.splice(index, 1)
  } else {
    selectedCodes.value.push(code)
  }
}

// 添加标的
const handleAdd = async () => {
  const codes = newCodes.value
    .split(/[,\n]/)
    .map(c => c.trim())
    .filter(c => c.length > 0)
  
  if (codes.length === 0) {
    message.warning('请输入股票代码')
    return
  }
  
  adding.value = true
  try {
    const response = await fetch(`/api/watchlists/${watchlistId.value}/symbols`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ts_codes: codes })
    })
    
    if (!response.ok) throw new Error('Failed to add symbols')
    
    const result = await response.json()
    message.success(`成功添加 ${result.added} 只`)
    
    showAddDialog.value = false
    newCodes.value = ''
    await loadSummary()
  } catch (error) {
    console.error('Add error:', error)
    message.error('添加失败')
  } finally {
    adding.value = false
  }
}

// 移除标的
const handleRemove = async (code: string) => {
  try {
    const response = await fetch(
      `/api/watchlists/${watchlistId.value}/symbols/${code}`,
      { method: 'DELETE' }
    )
    
    if (!response.ok) throw new Error('Failed to remove')
    
    message.success('已移除')
    await loadSummary()
  } catch (error) {
    console.error('Remove error:', error)
    message.error('移除失败')
  }
}

// 进入分析页
const navigateToAnalysis = (code: string) => {
  router.push(`/analysis/${code}`)
}

// 进入比较页
const navigateToCompare = () => {
  router.push({
    path: '/compare',
    query: { codes: selectedCodes.value.join(',') }
  })
}

onMounted(() => {
  initWatchlist()
})
</script>

<style scoped>
.watchlist-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.watchlist-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.watchlist-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.watchlist-content {
  margin-top: 20px;
}

.watchlist-stats {
  margin-bottom: 16px;
  font-size: 14px;
}

.watchlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.batch-actions {
  position: fixed;
  bottom: 30px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 24px;
  background: var(--n-color);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
