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

    <div v-if="riskAlerts.length > 0" id="risk-alert-panel">
    <n-alert
      type="warning"
      :bordered="false"
      class="risk-alert-panel"
    >
      <template #header>
        自选风险提醒（{{ riskAlerts.length }}）
      </template>
      <div class="risk-alert-list">
        <div v-for="alert in riskAlerts" :key="alert.id" class="risk-alert-item">
          <div class="risk-alert-main">
            <a :href="`/stock/${alert.ts_code.slice(0, 6)}`" class="risk-alert-name">{{ alert.stock_name }}</a>
            <span class="risk-alert-code">{{ alert.ts_code }}</span>
          </div>
          <div class="risk-alert-tags">
            <n-tag
              v-for="tag in alert.tags"
              :key="`${alert.id}-${tag}`"
              size="small"
              :bordered="false"
              type="warning"
            >
              {{ tag }}
            </n-tag>
          </div>
          <div class="risk-alert-reason">{{ alert.reason }}</div>
        </div>
      </div>
      <div class="risk-alert-actions">
        <n-space>
          <n-button size="small" @click="goRiskStocks">查看风险股清单</n-button>
          <n-button size="small" type="primary" secondary @click="markRiskAlertsRead">标记已读</n-button>
        </n-space>
      </div>
    </n-alert>
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

    <n-alert
      v-if="needsSessionRestore && watchlistState.isTemporary"
      type="warning"
      :bordered="false"
      class="restore-session-alert"
    >
      <template #header>
        换设备了？
      </template>
      <div class="trial-alert-content">
        <span>你曾在其他设备绑定邮箱。在当前设备再次验证邮箱，即可恢复观察列表与判断记录。</span>
        <n-button type="primary" size="small" @click="showBindDialog = true">
          验证邮箱恢复
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

      <div v-if="healthOverview" class="health-overview-panel">
        <div class="health-overview-main">
          <div class="health-label">自选健康度</div>
          <div class="health-score">{{ healthOverview.health_score }}</div>
          <n-tag
            class="health-status-tag"
            :type="healthLabelType(healthOverview.label)"
            size="small"
            :bordered="false"
          >
            {{ healthOverview.label }}
          </n-tag>
          <p v-if="healthOverview.summary_line" class="health-summary-line">
            {{ healthOverview.summary_line }}
          </p>
        </div>
        <div class="health-metrics">
          <div class="health-metric">
            <span class="metric-value strong">{{ healthOverview.strong_count }}</span>
            <span class="metric-label">强势</span>
          </div>
          <div class="health-metric">
            <span class="metric-value weak">{{ healthOverview.weak_count }}</span>
            <span class="metric-label">弱势</span>
          </div>
          <div
            class="health-metric"
            :class="{ 'health-metric--highlight': healthOverview.high_risk_count > 0 }"
          >
            <span class="metric-value risk">{{ healthOverview.high_risk_count }}</span>
            <span class="metric-label">高风险</span>
          </div>
          <div class="health-metric">
            <span class="metric-value watch">{{ healthOverview.watch_count }}</span>
            <span class="metric-label">待观察</span>
          </div>
          <div class="health-metric">
            <span class="metric-value judgement">{{ healthOverview.active_judgment_count }}</span>
            <span class="metric-label">追踪中</span>
          </div>
        </div>
        <div
          v-if="healthOverview.top_industries.length > 0"
          class="health-exposure-panel"
        >
          <div class="health-exposure-header">
            <span class="health-exposure-title">行业暴露</span>
            <n-tag
              size="small"
              :type="concentrationTagType(healthOverview.concentration_level)"
              :bordered="false"
            >
              集中度 {{ healthOverview.concentration_level }}
            </n-tag>
            <span v-if="healthOverview.industry_count > 0" class="health-exposure-meta">
              覆盖 {{ healthOverview.industry_count }} 个行业
              <template v-if="healthOverview.uses_position_weights"> · 按持仓权重</template>
              <template v-else> · 按等权</template>
            </span>
          </div>
          <div class="health-exposure-list">
            <div
              v-for="item in healthOverview.top_industries"
              :key="item.industry"
              class="health-exposure-item"
            >
              <span class="exposure-industry">{{ item.industry }}</span>
              <span class="exposure-weight">{{ item.count }} 只 · {{ item.weight_pct }}%</span>
            </div>
          </div>
          <p v-if="healthOverview.concentration_note" class="health-exposure-note">
            {{ healthOverview.concentration_note }}
          </p>
          <p v-if="weightNote" class="health-exposure-note weight-note">
            {{ weightNote }}
          </p>
        </div>
        <div
          v-if="healthOverview.risk_list_hits?.length"
          class="health-risk-panel"
        >
          <div class="health-risk-header">
            <span class="health-risk-title">命中风险股清单</span>
            <span v-if="healthOverview.risk_list_trade_date" class="health-risk-meta">
              交易日 {{ healthOverview.risk_list_trade_date }}
            </span>
          </div>
          <div class="health-risk-list">
            <div
              v-for="hit in healthOverview.risk_list_hits"
              :key="hit.ts_code"
              class="health-risk-item"
            >
              <a :href="`/stock/${hit.ts_code.slice(0, 6)}`" class="health-risk-name">{{ hit.name }}</a>
              <span class="health-risk-code">{{ hit.ts_code }}</span>
              <n-space :size="4" class="health-risk-tags">
                <n-tag
                  v-for="tag in hit.tags"
                  :key="`${hit.ts_code}-${tag}`"
                  size="small"
                  type="warning"
                  :bordered="false"
                >
                  {{ tag }}
                </n-tag>
              </n-space>
            </div>
          </div>
          <n-button size="small" tertiary type="warning" @click="goRiskStocks">
            查看完整风险股清单
          </n-button>
          <n-button
            v-if="healthOverview.risk_list_hits.length >= 2"
            size="small"
            type="warning"
            secondary
            @click="compareRiskHits"
          >
            对比命中标的
          </n-button>
        </div>
      </div>

      <n-alert
        v-if="detailLoading"
        type="info"
        :bordered="false"
        class="detail-loading-alert"
      >
        正在加载完整指标，已展示缓存数据与骨架行…
      </n-alert>

      <n-data-table
        :columns="tableColumns"
        :data="tableData"
        :row-key="(row: WatchlistItemSummary) => row.ts_code"
        :checked-row-keys="selectedCodes"
        :loading="loading"
        :row-class-name="rowClassName"
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
import { ref, computed, h, onMounted, nextTick } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  NButton, NIcon, NText, NModal, NForm, NFormItem,
  NInput, NSpace, NAlert, NDataTable, NTag, NInputNumber, NSkeleton, useMessage, useDialog,
  type DataTableColumns, type DataTableRowKey
} from 'naive-ui'
import { AddCircleOutline } from '@vicons/ionicons5'
import WatchlistFilters from './WatchlistFilters.vue'
import EmptyState from '../common/EmptyState.vue'
import AnchorBindDialog from '../AnchorBindDialog.vue'
import { apiService } from '@/services/api'
import type { WatchlistSummary, Watchlist, WatchlistItemSummary, WatchlistRiskAlert } from '@/types/watchlist'
import { applyPageSeo } from '@/utils/seo'
import { syncAnchorSession } from '@/utils/anchorSession'
import { useNotificationStore } from '@/stores/notification'

const router = useRouter()
const route = useRoute()
const message = useMessage()
const dialog = useDialog()
const notificationStore = useNotificationStore()

// State
const loading = ref(false)
const detailLoading = ref(false)
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
const riskAlerts = ref<WatchlistRiskAlert[]>([])
const needsSessionRestore = ref(false)

const applyWatchlistState = (source?: Partial<WatchlistSummary & Watchlist> | null) => {
  watchlistState.value = {
    isTemporary: Boolean(source?.is_temporary),
    trialMessage: source?.trial_message || null
  }
}

// ── 表格相关 ──

const tableData = computed(() => summaryData.value?.items ?? [])
const healthOverview = computed(() => summaryData.value?.health_overview ?? null)

const weightTotal = computed(() => {
  const items = summaryData.value?.items ?? []
  const weighted = items.filter((item) => item.weight_pct != null)
  if (weighted.length === 0) return null
  return weighted.reduce((sum, item) => sum + Number(item.weight_pct || 0), 0)
})

const weightNote = computed(() => {
  if (weightTotal.value == null) return ''
  const total = Math.round(weightTotal.value * 10) / 10
  if (total === 100) return '持仓权重合计 100%，集中度按权重计算。'
  if (total > 100) return `持仓权重合计 ${total}%（超过 100%，建议调整）。`
  return `持仓权重合计 ${total}%（未满 100%，未设权重的标的按等权补充理解）。`
})

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

function healthLabelType(label: string): 'success' | 'warning' | 'error' | 'info' {
  if (label === '偏强') return 'success'
  if (label === '偏弱') return 'warning'
  if (label === '风险偏高') return 'error'
  return 'info'
}

function concentrationTagType(level: string): 'success' | 'warning' | 'error' | 'info' {
  if (level === '分散') return 'success'
  if (level === '中等') return 'warning'
  if (level === '偏高') return 'error'
  return 'info'
}

function flowTagType(label: string) {
  if (label === '承接放量') return 'success'
  if (label === '分歧放量' || label === '缩量阴跌') return 'error'
  if (label === '不可用') return 'default'
  return 'info'
}

function rowClassName(row: WatchlistItemSummary) {
  if (row.on_risk_list) return 'watchlist-row-risk-hit'
  if (row.is_skeleton) return 'watchlist-row-skeleton'
  return ''
}

function renderMetricCell(row: WatchlistItemSummary, content: () => ReturnType<typeof h>) {
  if (row.is_skeleton) {
    return h(NSkeleton, { text: true, width: '72%' })
  }
  return content()
}

const savingWeightCode = ref<string | null>(null)
const weightDrafts = ref<Record<string, number | null>>({})

function getWeightDraft(row: WatchlistItemSummary): number | null {
  if (row.ts_code in weightDrafts.value) {
    return weightDrafts.value[row.ts_code]
  }
  return row.weight_pct ?? null
}

async function handleWeightUpdate(row: WatchlistItemSummary, value: number | null) {
  if (!watchlistId.value) return
  if (row.weight_pct === value || (row.weight_pct == null && value == null)) {
    return
  }
  savingWeightCode.value = row.ts_code
  try {
    await apiService.updateWatchlistSymbolWeight(watchlistId.value, row.ts_code, value)
    delete weightDrafts.value[row.ts_code]
    await loadSummary()
  } catch (error) {
    console.error('Update weight error:', error)
    message.error('权重保存失败')
  } finally {
    savingWeightCode.value = null
  }
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
      const displayName = row.name && row.name !== row.ts_code ? row.name : ''
      const codeOnly = row.ts_code.replace(/\.(SH|SZ|BJ)$/i, '')
      const children = [
        h('span', { class: 'cell-stock-name' }, displayName || codeOnly),
        h('span', { class: 'cell-stock-code' }, displayName ? codeOnly : ''),
      ]
      if (row.on_risk_list) {
        children.push(
          h(NTag, { type: 'warning', size: 'small', bordered: false, class: 'cell-risk-tag' }, () => '风险清单')
        )
      }
      return h('div', { class: 'cell-stock', onClick: () => navigateToAnalysis(row.ts_code), style: 'cursor:pointer' }, children)
    },
  },
  {
    title: '权重%',
    key: 'weight_pct',
    width: 96,
    align: 'center',
    render(row) {
      return h(NInputNumber, {
        size: 'small',
        min: 0,
        max: 100,
        step: 1,
        placeholder: '均分',
        value: getWeightDraft(row),
        loading: savingWeightCode.value === row.ts_code,
        showButton: false,
        style: 'width: 72px',
        onUpdateValue: (value: number | null) => {
          weightDrafts.value[row.ts_code] = value
        },
        onBlur: () => handleWeightUpdate(row, getWeightDraft(row)),
      })
    },
  },
  {
    title: '价格',
    key: 'price',
    width: 90,
    align: 'center',
    sorter: (a, b) => a.price - b.price,
    render(row) {
      return renderMetricCell(row, () => {
        if (!row.price) return h('span', { class: 'cell-na' }, '--')
        return h('span', { class: 'cell-price' }, `¥${row.price.toFixed(2)}`)
      })
    },
  },
  {
    title: '涨跌幅',
    key: 'change_pct',
    width: 90,
    align: 'center',
    sorter: (a, b) => (a.change_pct ?? 0) - (b.change_pct ?? 0),
    render(row) {
      return renderMetricCell(row, () => {
        if (row.change_pct === null || row.change_pct === undefined) return h('span', { class: 'cell-na' }, '--')
        const cls = row.change_pct > 0 ? 'cell-up' : row.change_pct < 0 ? 'cell-down' : ''
        return h('span', { class: `cell-change ${cls}` }, formatPercent(row.change_pct))
      })
    },
  },
  {
    title: '趋势',
    key: 'trend',
    width: 100,
    align: 'center',
    render(row) {
      return renderMetricCell(row, () => h('div', { class: 'cell-trend' }, [
        h(NTag, { type: trendTypeMap[row.trend.direction], size: 'small', bordered: false }, () => trendMap[row.trend.direction]),
        h('span', { class: 'cell-trend-num' }, String(row.trend.strength)),
      ]))
    },
  },
  {
    title: '相对强弱',
    key: 'relative_strength',
    width: 90,
    align: 'center',
    render(row) {
      return renderMetricCell(row, () => {
        const label = row.relative_strength.label_20d
        if (!label) return h('span', { class: 'cell-na' }, '-')
        return h(NTag, { type: rsTypeMap[label], size: 'small', bordered: false }, () => rsMap[label])
      })
    },
  },
  {
    title: '资金',
    key: 'capital_flow',
    width: 100,
    align: 'center',
    render(row) {
      return renderMetricCell(row, () => {
        if (!row.capital_flow.available) return h('span', { class: 'cell-na' }, '--')
        return h(NTag, { type: flowTagType(row.capital_flow.label) as any, size: 'small', bordered: false }, () => row.capital_flow.label)
      })
    },
  },
  {
    title: '风险',
    key: 'risk',
    width: 90,
    align: 'center',
    render(row) {
      return renderMetricCell(row, () => {
        const children = [
          h(NTag, { type: riskTypeMap[row.risk.level], size: 'small', bordered: false }, () => riskMap[row.risk.level]),
        ]
        if (row.events.flag === 'major') {
          children.push(
            h(NTag, { type: 'warning', size: 'small', bordered: false }, () => '事件'),
          )
        }
        if (row.on_risk_list && row.risk_list_tags?.length) {
          children.push(
            h(NTag, { type: 'warning', size: 'small', bordered: false }, () => row.risk_list_tags![0]),
          )
        }
        return h('div', { class: 'cell-risk' }, children)
      })
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

// 加载摘要数据：fast 首屏 + full 完整指标
const loadSummary = async () => {
  loading.value = true
  detailLoading.value = false
  try {
    summaryData.value = await apiService.getWatchlistSummary(watchlistId.value, {
      sort: currentSort.value,
      filters: currentFilters.value,
      phase: 'fast',
    })
    applyWatchlistState(summaryData.value)
  } catch (error) {
    console.error('Load summary error:', error)
    message.error('加载失败')
    return
  } finally {
    loading.value = false
  }

  detailLoading.value = true
  try {
    const fullData = await apiService.getWatchlistSummary(watchlistId.value, {
      sort: currentSort.value,
      filters: currentFilters.value,
      phase: 'full',
    })
    summaryData.value = fullData
    applyWatchlistState(fullData)
  } catch (error) {
    console.error('Load full summary error:', error)
    message.warning('完整指标加载失败，当前显示缓存/骨架数据')
  } finally {
    detailLoading.value = false
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
  if (!watchlistState.value.isTemporary || addedCount <= 0) return

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

function compareRiskHits() {
  const hits = healthOverview.value?.risk_list_hits ?? []
  if (hits.length < 2) {
    message.warning('至少需要 2 只命中标的才能对比')
    return
  }
  const codes = hits.map((hit) => hit.ts_code)
  selectedCodes.value = codes
  router.push({
    path: '/compare',
    query: { codes: codes.join(',') }
  })
}

async function scrollToRiskPanel() {
  await nextTick()
  document.getElementById('risk-alert-panel')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const handleBindSuccess = async () => {
  needsSessionRestore.value = false
  message.success('已绑定邮箱，你的观察列表现在会长期保存')
  await initWatchlist()
}

async function loadRiskAlerts() {
  try {
    const response = await apiService.getWatchlistRiskAlerts({ unread_only: true, limit: 10 })
    riskAlerts.value = response.items
  } catch (error) {
    console.error('Load risk alerts error:', error)
  }
}

function goRiskStocks() {
  window.location.href = '/risk-stocks'
}

async function markRiskAlertsRead() {
  try {
    await apiService.markWatchlistRiskAlertsRead()
    riskAlerts.value = []
    await notificationStore.checkReviews()
    message.success('风险提醒已标记为已读')
  } catch (error) {
    console.error('Mark risk alerts read failed:', error)
    message.error('标记已读失败')
  }
}

onMounted(async () => {
  applyPageSeo({
    title: '我的观察 | Agu AI',
    description: '查看你的自选股观察列表与跟踪状态。',
    canonicalPath: '/watchlist',
    robots: 'noindex, nofollow',
  })
  needsSessionRestore.value = (await syncAnchorSession()) === 'restore'
  await initWatchlist()
  await loadRiskAlerts()
  if (route.query.focus === 'risk') {
    await scrollToRiskPanel()
  }
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

.risk-alert-panel {
  margin-bottom: 16px;
}

.risk-alert-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.risk-alert-item {
  padding: 10px 0;
  border-bottom: 1px solid rgba(148, 163, 184, 0.2);
}

.risk-alert-item:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.risk-alert-main {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}

.risk-alert-name {
  color: #5560d6;
  font-weight: 700;
  text-decoration: none;
}

.risk-alert-code {
  color: var(--n-text-color-3);
  font-size: 12px;
  font-family: monospace;
}

.risk-alert-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: 6px;
}

.risk-alert-reason {
  color: var(--n-text-color-3);
  font-size: 13px;
  line-height: 1.5;
}

.risk-alert-actions {
  margin-top: 12px;
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

.health-overview-panel {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
  padding: 14px 16px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(91, 103, 241, 0.12);
  box-shadow: 0 8px 22px rgba(79, 93, 160, 0.08);
}

.health-overview-main {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  min-width: 120px;
}

.health-label {
  color: var(--n-text-color-3);
  font-size: 13px;
}

.health-score {
  font-size: 32px;
  line-height: 1;
  font-weight: 800;
  color: var(--n-text-color);
}

.health-status-tag {
  margin-top: 2px;
}

.health-summary-line {
  margin: 4px 0 0;
  font-size: 13px;
  line-height: 1.6;
  color: var(--n-text-color-3);
  max-width: 280px;
}

.health-metrics {
  display: grid;
  grid-template-columns: repeat(5, minmax(64px, 1fr));
  gap: 10px;
  flex: 1;
}

.health-metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 8px;
  border-radius: 10px;
  background: var(--n-color);
}

.health-metric--highlight {
  background: rgba(208, 48, 80, 0.08);
  border: 1px solid rgba(208, 48, 80, 0.22);
}

.health-exposure-panel {
  flex-basis: 100%;
  width: 100%;
  margin-top: 0;
  padding-top: 12px;
  border-top: 1px solid rgba(91, 103, 241, 0.1);
}

.health-exposure-header {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}

.health-exposure-title {
  font-size: 13px;
  font-weight: 700;
  color: var(--n-text-color);
}

.health-exposure-meta {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.health-exposure-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.health-exposure-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  border-radius: 999px;
  background: rgba(99, 102, 241, 0.08);
  border: 1px solid rgba(99, 102, 241, 0.12);
}

.exposure-industry {
  font-size: 13px;
  font-weight: 600;
}

.exposure-weight {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.health-exposure-note {
  margin: 8px 0 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--n-text-color-3);
}

.health-risk-panel {
  flex-basis: 100%;
  width: 100%;
  padding-top: 12px;
  border-top: 1px solid rgba(245, 158, 11, 0.2);
}

.health-risk-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.health-risk-title {
  font-size: 13px;
  font-weight: 700;
  color: #b45309;
}

.health-risk-meta {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.health-risk-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 10px;
}

.health-risk-item {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}

.health-risk-name {
  color: #b45309;
  font-weight: 700;
  text-decoration: none;
}

.health-risk-code {
  font-size: 12px;
  color: var(--n-text-color-3);
  font-family: monospace;
}

.detail-loading-alert {
  margin-bottom: 12px;
}

:deep(.watchlist-row-risk-hit td) {
  background: rgba(245, 158, 11, 0.08) !important;
}

:deep(.watchlist-row-skeleton td) {
  opacity: 0.92;
}

.cell-risk-tag {
  margin-top: 4px;
}

.weight-note {
  color: #b45309;
}

.metric-value {
  font-size: 18px;
  font-weight: 800;
}

.metric-value.strong { color: #18a058; }
.metric-value.weak { color: #d97706; }
.metric-value.risk { color: #d03050; }
.metric-value.watch { color: #5560d6; }
.metric-value.judgement { color: #2080f0; }

.metric-label {
  font-size: 12px;
  color: var(--n-text-color-3);
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

:deep(.cell-risk) {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
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

  .health-overview-panel {
    flex-direction: column;
  }

  .health-metrics {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
