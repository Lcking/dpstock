<template>
  <div class="risk-stock-page">
    <div class="page-header">
      <div>
        <h1>风险股清单</h1>
        <p>交易时段每 15 分钟滚动更新：ST 股、连续涨停/跌停、5%/9% 涨幅池、创业板大波动与 ST 征兆。涨幅池达标进入、回落自动移除。</p>
      </div>
      <div class="header-actions">
        <n-tag type="warning" size="small" :bordered="false">
          {{ data?.trade_date || '暂无日期' }}
        </n-tag>
        <n-space>
          <n-button
            size="small"
            secondary
            :disabled="!canExport"
            :loading="exportingFormat === 'csv'"
            @click="exportRiskStocks('csv')"
          >
            导出 CSV
          </n-button>
          <n-button
            size="small"
            type="primary"
            secondary
            :disabled="!canExport"
            :loading="exportingFormat === 'xlsx'"
            @click="exportRiskStocks('xlsx')"
          >
            导出 Excel
          </n-button>
        </n-space>
      </div>
    </div>

    <n-alert type="warning" :bordered="false" class="risk-note">
      风险股清单仅用于风险识别与研究观察，不构成投资建议。高风险标签不代表方向判断。
    </n-alert>

    <div class="filters">
      <n-button
        v-for="option in tagOptions"
        :key="option.value"
        size="small"
        :type="selectedTag === option.value ? 'primary' : 'default'"
        secondary
        @click="selectTag(option.value)"
      >
        {{ option.label }}
      </n-button>
    </div>

    <div v-if="loading" class="loading-state">
      <n-spin size="large" />
      <span>正在加载风险股清单...</span>
    </div>

    <n-empty v-else-if="items.length === 0" class="empty-state">
      <template #default>
        <div class="empty-copy">
          <p class="empty-title">暂无风险股数据</p>
          <p class="empty-desc">{{ emptyMessage }}</p>
        </div>
      </template>
      <template #extra>
        <n-space>
          <n-button type="primary" secondary @click="loadRiskStocks">重新加载</n-button>
          <n-button @click="goStocks">浏览个股列表</n-button>
        </n-space>
      </template>
    </n-empty>

    <n-data-table
      v-else
      :columns="columns"
      :data="items"
      :row-key="(row: RiskStockItem) => row.ts_code"
      :bordered="false"
      :single-line="false"
      size="small"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, h, onMounted, ref } from 'vue'
import { NAlert, NButton, NDataTable, NEmpty, NSpace, NSpin, NTag, useMessage, type DataTableColumns } from 'naive-ui'
import { apiService } from '@/services/api'
import { applyPageSeo } from '@/utils/seo'
import type { RiskStockItem, RiskStockListResponse } from '@/types/riskStock'

const loading = ref(false)
const exportingFormat = ref<'csv' | 'xlsx' | ''>('')
const data = ref<RiskStockListResponse | null>(null)
const selectedTag = ref('')
const message = useMessage()

const tagOptions = [
  { label: '全部', value: '' },
  { label: 'ST股', value: 'ST股' },
  { label: 'ST征兆', value: 'ST征兆' },
  { label: '连续涨停', value: '连续涨停' },
  { label: '连续跌停', value: '连续跌停' },
  { label: '三连板', value: '三连板' },
  { label: '高度板', value: '高度板' },
  { label: '5%涨幅池', value: '5%涨幅池' },
  { label: '9%涨幅池', value: '9%涨幅池' },
  { label: '创业板大波动', value: '创业板大波动' },
]

const items = computed(() => data.value?.items || [])
const canExport = computed(() => !loading.value && items.value.length > 0)

const emptyMessage = computed(() => {
  if (data.value?.message) return data.value.message
  if (data.value?.data_status === 'pending') {
    return '清单尚未生成，系统会在每个交易日收盘后自动刷新。你也可以稍后回来查看。'
  }
  return '当前筛选条件下暂无符合条件的标的，可切换标签或稍后再试。'
})

function goStocks() {
  window.location.href = '/stocks'
}

const columns: DataTableColumns<RiskStockItem> = [
  {
    title: '股票',
    key: 'name',
    render: (row) => h('div', { class: 'stock-cell' }, [
      h('a', { href: `/stock/${row.ts_code.slice(0, 6)}`, class: 'stock-name-link' }, row.name),
      h('span', { class: 'stock-code' }, row.ts_code),
    ])
  },
  {
    title: '风险标签',
    key: 'tags',
    render: (row) => h('div', { class: 'tag-list' }, row.tags.map(tag =>
      h(NTag, { type: tagType(tag), size: 'small', bordered: false }, () => tag)
    ))
  },
  {
    title: '连板/连跌',
    key: 'limit_up_days',
    width: 100,
    render: (row) => {
      if (row.limit_up_days) return `涨停 ${row.limit_up_days} 天`
      if (row.limit_down_days) return `跌停 ${row.limit_down_days} 天`
      return '-'
    }
  },
  {
    title: '当日涨跌',
    key: 'pct_chg',
    width: 90,
    render: (row) => {
      if (row.pct_chg === null || row.pct_chg === undefined) return '-'
      const value = Number(row.pct_chg)
      const cls = value > 0 ? 'pct-up' : value < 0 ? 'pct-down' : ''
      return h('span', { class: cls }, `${value > 0 ? '+' : ''}${value.toFixed(2)}%`)
    }
  },
  {
    title: '风险等级',
    key: 'risk_level',
    width: 90,
    render: (row) => h(NTag, { type: riskLevelType(row.risk_level), size: 'small', bordered: false }, () => levelLabel(row.risk_level))
  },
  {
    title: '原因',
    key: 'reason',
    ellipsis: { tooltip: true },
  },
  {
    title: '操作',
    key: 'actions',
    width: 120,
    render: (row) => h('a', { href: `/?code=${row.ts_code.slice(0, 6)}&market=A&focus=search`, class: 'action-link' }, '实时诊股')
  }
]

function tagType(tag: string): 'error' | 'warning' | 'info' {
  if (tag === 'ST征兆') return 'warning'
  if (tag.includes('ST') || tag.includes('跌停')) return 'error'
  if (tag.includes('连板') || tag.includes('高度') || tag.includes('涨停') || tag.includes('大波动')) return 'warning'
  return 'info'
}

function riskLevelType(level: string): 'error' | 'warning' | 'success' {
  if (level === 'high') return 'error'
  if (level === 'medium') return 'warning'
  return 'success'
}

function levelLabel(level: string) {
  if (level === 'high') return '高风险'
  if (level === 'medium') return '中风险'
  return '低风险'
}

async function loadRiskStocks() {
  loading.value = true
  try {
    data.value = await apiService.getRiskStocks({ tag: selectedTag.value || undefined })
  } finally {
    loading.value = false
  }
}

function selectTag(tag: string) {
  selectedTag.value = tag
  loadRiskStocks()
}

async function exportRiskStocks(format: 'csv' | 'xlsx') {
  if (!canExport.value) {
    message.warning('当前没有可导出的风险股数据')
    return
  }

  exportingFormat.value = format
  try {
    await apiService.downloadRiskStocks(format, {
      trade_date: data.value?.trade_date || undefined,
      tag: selectedTag.value || undefined,
    })
    message.success(format === 'csv' ? 'CSV 导出成功' : 'Excel 导出成功')
  } catch (error) {
    console.error('导出风险股清单失败:', error)
    message.error('导出失败，请稍后重试')
  } finally {
    exportingFormat.value = ''
  }
}

onMounted(() => {
  applyPageSeo({
    title: '风险股清单 | Agu AI',
    description: '盘中滚动更新的风险股清单：ST股、ST征兆、连续涨停/跌停、5%/9%涨幅池、创业板大波动。',
    canonicalPath: '/risk-stocks',
    keywords: '风险股清单,ST股,ST征兆,连续涨停,连续跌停,涨幅池,创业板大波动,A股风险提示',
  })
  loadRiskStocks()
})
</script>

<style scoped>
.risk-stock-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 40px 20px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;
  margin-bottom: 18px;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 10px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.page-header p {
  margin: 0;
  color: var(--n-text-color-3);
}

.risk-note,
.filters {
  margin-bottom: 16px;
}

.filters {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.loading-state {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
  color: var(--n-text-color-3);
}

.empty-state {
  padding: 80px 0;
}

.empty-copy {
  text-align: center;
}

.empty-title {
  margin: 0 0 8px;
  font-size: 16px;
  font-weight: 700;
  color: var(--n-text-color);
}

.empty-desc {
  margin: 0;
  max-width: 420px;
  color: var(--n-text-color-3);
  line-height: 1.6;
}

.stock-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-name-link,
.action-link {
  color: #5560d6;
  font-weight: 700;
  text-decoration: none;
}

.stock-name-link:hover,
.action-link:hover {
  text-decoration: underline;
}

.stock-code {
  color: var(--n-text-color-3);
  font-size: 12px;
  font-family: monospace;
}

.tag-list {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.pct-up {
  color: #d03050;
  font-weight: 600;
}

.pct-down {
  color: #18a058;
  font-weight: 600;
}
</style>
