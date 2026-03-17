<template>
  <div class="watchlist-page">
    <!-- 顶部操作栏 -->
    <div class="watchlist-header">
      <h1>自选股</h1>
      <div class="header-actions">
        <n-button type="primary" @click="showAddDialog = true">
          <template #icon>
            <n-icon><AddCircleOutline /></n-icon>
          </template>
          添加标的
        </n-button>
      </div>
    </div>

    <n-alert
      v-if="watchlistState.isTemporary && watchlistState.trialMessage"
      type="warning"
      :bordered="false"
      class="trial-alert"
    >
      <template #header>
        当前为游客观察列表
      </template>
      <div class="trial-alert-content">
        <span>{{ watchlistState.trialMessage }}</span>
        <n-button type="primary" secondary size="small" @click="showBindDialog = true">
          绑定邮箱
        </n-button>
      </div>
    </n-alert>

    <n-alert
      v-if="watchlistState.isTemporary"
      type="info"
      :bordered="false"
      class="bind-value-alert"
    >
      <div class="trial-alert-content">
        <span>绑定邮箱，保存你的观察资产。绑定后资产不会因换设备或清缓存而丢失。</span>
        <n-button tertiary type="primary" size="small" @click="showBindDialog = true">
          立即绑定
        </n-button>
      </div>
    </n-alert>

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
        <n-button
          v-if="watchlistState.isTemporary"
          tertiary
          type="warning"
          @click="showBindDialog = true"
        >
          绑定后长期保存
        </n-button>
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

    <AnchorBindDialog
      v-model:show="showBindDialog"
      @bind-success="handleBindSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { 
  NButton, NIcon, NText, NModal, NForm, NFormItem, 
  NInput, NSpace, NCard, NSkeleton, NAlert, useMessage 
} from 'naive-ui'
import { AddCircleOutline } from '@vicons/ionicons5'
import WatchlistFilters from './WatchlistFilters.vue'
import WatchlistItemCard from './WatchlistItemCard.vue'
import EmptyState from '../common/EmptyState.vue'
import AnchorBindDialog from '../AnchorBindDialog.vue'
import { apiService } from '@/services/api'
import type { WatchlistSummary, Watchlist } from '@/types/watchlist'
import { hasAnchorToken } from '@/utils/anchorToken'
import { applyPageSeo } from '@/utils/seo'

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
const showBindDialog = ref(false)
const WATCHLIST_ADD_COUNT_KEY = 'aguai_watchlist_add_count'
const watchlistState = ref({
  isTemporary: false,
  trialMessage: null as string | null
})

const applyWatchlistState = (source?: Partial<WatchlistSummary & Watchlist> | null) => {
  watchlistState.value = {
    isTemporary: Boolean(source?.is_temporary),
    trialMessage: source?.trial_message || null
  }
}

// 加载摘要数据
const loadSummary = async () => {
  loading.value = true
  try {
    summaryData.value = await apiService.getWatchlistSummary(watchlistId.value, {
      sort: currentSort.value,
      filters: currentFilters.value
    })
    applyWatchlistState(summaryData.value)
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
    const watchlists = await apiService.getWatchlists()
    
    if (watchlists.length === 0) {
      // 创建默认自选股
      const newList = await apiService.createWatchlist('默认自选')
      watchlistId.value = newList.id
      applyWatchlistState(newList)
    } else {
      watchlistId.value = watchlists[0].id
      applyWatchlistState(watchlists[0])
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
    const result = await apiService.addWatchlistSymbols(watchlistId.value, codes)
    message.success(`成功添加 ${result.added} 只`)
    checkAndTriggerBindAfterAdd(result.added)
    
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

const checkAndTriggerBindAfterAdd = (addedCount: number) => {
  if (!watchlistState.value.isTemporary || hasAnchorToken() || addedCount <= 0) return

  const count = parseInt(localStorage.getItem(WATCHLIST_ADD_COUNT_KEY) || '0', 10) + 1
  localStorage.setItem(WATCHLIST_ADD_COUNT_KEY, count.toString())

  if (count === 1) {
    message.info('绑定邮箱，保存你的观察资产。绑定后资产不会因换设备或清缓存而丢失。')
    setTimeout(() => {
      showBindDialog.value = true
    }, 600)
  }
}

// 移除标的
const handleRemove = async (code: string) => {
  try {
    await apiService.removeWatchlistSymbol(watchlistId.value, code)
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
  if (watchlistState.value.isTemporary) {
    message.info('当前观察为临时资产，绑定后可长期保存并跨设备同步')
  }
  router.push({
    path: '/compare',
    query: { codes: selectedCodes.value.join(',') }
  })
}

const handleBindSuccess = async () => {
  message.success('已绑定邮箱，你的观察列表现在会长期保存')
  await initWatchlist()
}

onMounted(() => {
  applyPageSeo({
    title: '我的观察 | Agu AI',
    description: '查看你的自选股观察列表与跟踪状态。',
    canonicalPath: '/watchlist',
    robots: 'noindex, nofollow',
  })
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

.watchlist-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.trial-alert {
  margin-bottom: 16px;
}

.bind-value-alert {
  margin-bottom: 16px;
}

.trial-alert-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
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
