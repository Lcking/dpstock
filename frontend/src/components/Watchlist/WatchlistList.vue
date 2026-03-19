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

    <!-- 表格内容 -->
    <div v-if="loading || (summaryData && summaryData.items.length > 0)" class="watchlist-content">
      <div v-if="summaryData" class="watchlist-stats">
        <n-text depth="3">
          共 {{ summaryData.total_count }} 只，筛选后 {{ summaryData.filtered_count }} 只
        </n-text>
      </div>

      <n-data-table
        :columns="tableColumns"
        :data="tableData"
        :row-key="(row: WatchlistItemSummary) => row.ts_code"
        :checked-row-keys="selectedCodes"
        :loading="loading"
        :bordered="false"
        :single-line="false"
        :scroll-x="740"
        size="small"
        striped
        @update:checked-row-keys="handleCheckedRowKeysChange"
        @update:sorter="handleTableSorterChange"
      />

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
import { ref, computed, h, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import {
  NButton, NIcon, NText, NModal, NForm, NFormItem,
  NInput, NSpace, NAlert, NDataTable, NTag, useMessage, useDialog,
  type DataTableColumns, type DataTableRowKey
} from 'naive-ui'
import { AddCircleOutline } from '@vicons/ionicons5'
import WatchlistFilters from './WatchlistFilters.vue'
import EmptyState from '../common/EmptyState.vue'
import AnchorBindDialog from '../AnchorBindDialog.vue'
import { apiService } from '@/services/api'
import type { WatchlistSummary, Watchlist, WatchlistItemSummary } from '@/types/watchlist'
import { hasAnchorToken } from '@/utils/anchorToken'
import { applyPageSeo } from '@/utils/seo'

const router = useRouter()
const message = useMessage()
const dialog = useDialog()

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

// ── 表格相关 ──

const tableData = computed(() => summaryData.value?.items ?? [])

const formatPercent = (value: number | null) => {
  if (value === null || value === undefined) return '--'
  const str = (value * 100).toFixed(2)
  return value >= 0 ? `+${str}%` : `${str}%`
}

const trendMap: Record<string, string> = { up: '上涨', down: '下跌', sideways: '震荡' }
const trendTypeMap: Record<string, 'success' | 'error' | 'default'> = { up: 'success', down: 'error', sideways: 'default' }
const rsMap: Record<string, string> = { strong: '强势', neutral: '中性', weak: '弱势' }
const rsTypeMap: Record<string, 'success' | 'default' | 'warning'> = { strong: 'success', neutral: 'default', weak: 'warning' }
const riskMap: Record<string, string> = { low: '低', medium: '中', high: '高' }
const riskTypeMap: Record<string, 'success' | 'warning' | 'error'> = { low: 'success', medium: 'warning', high: 'error' }

function flowTagType(label: string) {
  if (label === '承接放量') return 'success'
  if (label === '分歧放量' || label === '缩量阴跌') return 'error'
  if (label === '不可用') return 'default'
  return 'info'
}

const tableColumns = computed<DataTableColumns<WatchlistItemSummary>>(() => [
  { type: 'selection', fixed: 'left', width: 40 },
  {
    title: '股票',
    key: 'name',
    width: 130,
    fixed: 'left',
    align: 'center',
    render(row) {
      return h('div', { class: 'cell-stock', onClick: () => navigateToAnalysis(row.ts_code), style: 'cursor:pointer' }, [
        h('span', { class: 'cell-stock-name' }, row.name || row.ts_code),
        h('span', { class: 'cell-stock-code' }, row.ts_code),
      ])
    },
  },
  {
    title: '价格',
    key: 'price',
    width: 90,
    align: 'center',
    sorter: (a, b) => a.price - b.price,
    render(row) {
      if (!row.price) return h('span', { class: 'cell-na' }, '--')
      return h('span', { class: 'cell-price' }, `¥${row.price.toFixed(2)}`)
    },
  },
  {
    title: '涨跌幅',
    key: 'change_pct',
    width: 90,
    align: 'center',
    sorter: (a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0),
    render(row) {
      if (row.change_pct === null || row.change_pct === undefined) return h('span', { class: 'cell-na' }, '--')
      const cls = row.change_pct > 0 ? 'cell-up' : row.change_pct < 0 ? 'cell-down' : ''
      return h('span', { class: `cell-change ${cls}` }, formatPercent(row.change_pct))
    },
  },
  {
    title: '趋势',
    key: 'trend',
    width: 100,
    align: 'center',
    render(row) {
      return h('div', { class: 'cell-trend' }, [
        h(NTag, { type: trendTypeMap[row.trend.direction], size: 'small', bordered: false }, () => trendMap[row.trend.direction]),
        h('span', { class: 'cell-trend-num' }, String(row.trend.strength)),
      ])
    },
  },
  {
    title: '相对强弱',
    key: 'relative_strength',
    width: 90,
    align: 'center',
    render(row) {
      const label = row.relative_strength.label_20d
      if (!label) return h('span', { class: 'cell-na' }, '-')
      return h(NTag, { type: rsTypeMap[label], size: 'small', bordered: false }, () => rsMap[label])
    },
  },
  {
    title: '资金',
    key: 'capital_flow',
    width: 100,
    align: 'center',
    render(row) {
      if (!row.capital_flow.available) return h('span', { class: 'cell-na' }, '--')
      return h(NTag, { type: flowTagType(row.capital_flow.label) as any, size: 'small', bordered: false }, () => row.capital_flow.label)
    },
  },
  {
    title: '风险',
    key: 'risk',
    width: 70,
    align: 'center',
    render(row) {
      return h(NTag, { type: riskTypeMap[row.risk.level], size: 'small', bordered: false }, () => riskMap[row.risk.level])
    },
  },
  {
    title: '判断',
    key: 'judgement',
    width: 100,
    align: 'center',
    render(row) {
      if (!row.judgement.has_active) return h('span', { class: 'cell-na' }, '-')
      const children = [
        h(NTag, { type: 'info', size: 'small', bordered: false }, () => row.judgement.candidate),
      ]
      if (row.judgement.days_left !== null) {
        children.push(h('span', { class: 'cell-days' }, `${row.judgement.days_left}天`))
      }
      return h('div', { class: 'cell-judgement' }, children)
    },
  },
  {
    title: '',
    key: 'actions',
    width: 120,
    align: 'center',
    fixed: 'right',
    render(row) {
      return h('div', { class: 'cell-actions' }, [
        h(NButton, { text: true, size: 'small', type: 'info', onClick: () => navigateToAnalysis(row.ts_code) }, () => '分析'),
        h(NButton, { text: true, size: 'small', type: 'error', onClick: () => confirmRemove(row) }, () => '移除'),
      ])
    },
  },
])

const handleCheckedRowKeysChange = (keys: DataTableRowKey[]) => {
  selectedCodes.value = keys as string[]
}

const handleTableSorterChange = () => {
  // NDataTable handles client-side sort internally; no extra action needed
}

const confirmRemove = (row: WatchlistItemSummary) => {
  dialog.warning({
    title: '确认移除',
    content: `确定要从自选股中移除 ${row.name || row.ts_code} 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: () => handleRemove(row.ts_code),
  })
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

// 跳转首页并自动触发该股票的分析
const navigateToAnalysis = (tsCode: string) => {
  const pureCode = tsCode.replace(/\.(SH|SZ|BJ)$/i, '')
  router.push({ path: '/', query: { code: pureCode, market: 'A' } })
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

.watchlist-content {
  margin-top: 20px;
}

.watchlist-stats {
  margin-bottom: 12px;
  font-size: 14px;
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

/* ── 表格单元格样式 ── */
:deep(.cell-stock) {
  display: flex;
  flex-direction: column;
  gap: 2px;
  line-height: 1.3;
}

:deep(.cell-stock-name) {
  font-weight: 600;
  font-size: 13px;
  color: var(--n-text-color);
}

:deep(.cell-stock-code) {
  font-size: 11px;
  color: var(--n-text-color-3);
  font-family: 'JetBrains Mono', monospace;
}

:deep(.cell-price) {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

:deep(.cell-change) {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

:deep(.cell-up) {
  color: #d03050;
}

:deep(.cell-down) {
  color: #18a058;
}

:deep(.cell-trend) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

:deep(.cell-trend-num) {
  font-size: 11px;
  font-weight: 600;
  color: var(--n-text-color-2);
}

:deep(.cell-judgement) {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

:deep(.cell-days) {
  font-size: 11px;
  color: var(--n-text-color-3);
}

:deep(.cell-na) {
  font-size: 12px;
  color: var(--n-text-color-3);
}

:deep(.cell-actions) {
  display: inline-flex;
  gap: 10px;
}

@media (max-width: 768px) {
  .watchlist-page {
    padding: 12px;
  }

  .watchlist-header h1 {
    font-size: 20px;
  }
}
</style>
