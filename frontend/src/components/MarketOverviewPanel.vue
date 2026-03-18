<template>
  <div class="market-overview-card">
    <div class="panel-header">
      <div class="panel-heading">
        <h2>核心指数市场快照</h2>
        <p class="panel-note">帮助快速了解主要指数日线变化，适合作为概览参考。</p>
      </div>
      <span v-if="updatedLabel" class="updated-at">快照更新 {{ updatedLabel }}</span>
    </div>

    <n-grid cols="1 s:2 xl:4" :x-gap="16" :y-gap="16" responsive="screen">
      <n-grid-item v-for="item in items" :key="item.key">
        <div class="index-card" :class="statusClass(item)">
          <div class="index-header">
            <div>
              <p class="index-name">{{ item.name }}</p>
              <p class="index-symbol">{{ item.symbol }}</p>
            </div>
            <n-tag size="small" round :bordered="false">
              {{ marketLabel(item.market) }}
            </n-tag>
          </div>

          <template v-if="item.status === 'ok' && item.price !== null">
            <div class="index-main-row">
              <div>
                <div class="index-price">{{ formatPrice(item.price) }}</div>
                <div class="index-change" :class="changeClass(item.change_percent)">
                  {{ formatSigned(item.change) }}
                  <span>{{ formatPercent(item.change_percent) }}</span>
                </div>
              </div>
              <svg
                v-if="item.trend?.length"
                class="sparkline-svg"
                viewBox="0 0 96 32"
                preserveAspectRatio="none"
                aria-hidden="true"
              >
                <path
                  class="sparkline-path"
                  :class="changeClass(item.change_percent)"
                  :d="buildSparklinePath(item.trend)"
                />
              </svg>
            </div>
          </template>
          <template v-else>
            <div class="index-price unavailable">暂不可用</div>
            <div class="index-change neutral">稍后自动重试</div>
          </template>
        </div>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { NGrid, NGridItem, NTag } from 'naive-ui'
import { apiService } from '@/services/api'
import type { MarketOverviewItem } from '@/types'

const items = ref<MarketOverviewItem[]>([
  { key: 'shanghai', name: '上证指数', market: 'A', symbol: '000001.SH', price: null, change: null, change_percent: null, trend: [], status: 'unavailable' },
  { key: 'csi300', name: '沪深300', market: 'A', symbol: '000300.SH', price: null, change: null, change_percent: null, trend: [], status: 'unavailable' },
  { key: 'hangseng', name: '恒生指数', market: 'HK', symbol: '^HSI', price: null, change: null, change_percent: null, trend: [], status: 'unavailable' },
  { key: 'nasdaq', name: '纳斯达克', market: 'US', symbol: '^IXIC', price: null, change: null, change_percent: null, trend: [], status: 'unavailable' },
])
const updatedAt = ref<number | null>(null)
const MARKET_OVERVIEW_REFRESH_MS = 60000
let refreshTimer: number | null = null

const updatedLabel = computed(() => {
  if (!updatedAt.value) return ''
  return new Date(updatedAt.value * 1000).toLocaleTimeString('zh-CN', {
    hour: '2-digit',
    minute: '2-digit',
  })
})

const loadOverview = async () => {
  const data = await apiService.getMarketOverview()
  if (data.items?.length) {
    items.value = data.items
  }
  updatedAt.value = data.updated_at
}

const marketLabel = (market: string) => {
  const map: Record<string, string> = {
    A: 'A股',
    HK: '港股',
    US: '美股',
  }
  return map[market] || market
}

const statusClass = (item: MarketOverviewItem) => {
  if (item.status !== 'ok' || item.change_percent === null) return 'is-neutral'
  if (item.change_percent > 0) return 'is-up'
  if (item.change_percent < 0) return 'is-down'
  return 'is-neutral'
}

const changeClass = (value: number | null) => {
  if (value === null) return 'neutral'
  if (value > 0) return 'up'
  if (value < 0) return 'down'
  return 'neutral'
}

const formatPrice = (value: number) => {
  return new Intl.NumberFormat('zh-CN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value)
}

const formatSigned = (value: number | null) => {
  if (value === null) return '--'
  return `${value > 0 ? '+' : ''}${formatPrice(value)}`
}

const formatPercent = (value: number | null) => {
  if (value === null) return '--'
  return `${value > 0 ? '+' : ''}${value.toFixed(2)}%`
}

const buildSparklinePath = (points: number[]) => {
  if (!points.length) return ''
  if (points.length === 1) return 'M0,16 L96,16'

  const min = Math.min(...points)
  const max = Math.max(...points)
  const range = max - min || 1

  return points
    .map((point, index) => {
      const x = (index / (points.length - 1)) * 96
      const y = 28 - ((point - min) / range) * 24
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

onMounted(() => {
  loadOverview()
  refreshTimer = window.setInterval(loadOverview, MARKET_OVERVIEW_REFRESH_MS)
})

onBeforeUnmount(() => {
  if (refreshTimer !== null) {
    window.clearInterval(refreshTimer)
    refreshTimer = null
  }
})
</script>

<style scoped>
.market-overview-card {
  margin-bottom: 1.5rem;
  padding: 0.95rem 1.05rem;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(91, 103, 241, 0.10);
  box-shadow:
    0 14px 36px rgba(79, 93, 160, 0.10),
    0 2px 10px rgba(15, 23, 42, 0.04);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;
}

.panel-heading {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1rem;
  color: #1f2540;
}

.panel-note {
  margin: 0;
  font-size: 0.78rem;
  color: #64748b;
}

.updated-at {
  color: #94a3b8;
  font-size: 0.78rem;
  white-space: nowrap;
}

.index-card {
  min-height: 112px;
  padding: 12px 13px;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.15);
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.index-card.is-up {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.08) 0%, rgba(240, 253, 250, 0.96) 100%);
  border-color: rgba(16, 185, 129, 0.18);
}

.index-card.is-down {
  background: linear-gradient(135deg, rgba(239, 68, 68, 0.08) 0%, rgba(254, 242, 242, 0.96) 100%);
  border-color: rgba(239, 68, 68, 0.16);
}

.index-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
}

.index-name {
  margin: 0;
  font-size: 0.92rem;
  font-weight: 700;
  color: #1f2937;
}

.index-symbol {
  margin: 2px 0 0;
  color: #94a3b8;
  font-size: 0.75rem;
}

.index-main-row {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
  margin-top: 10px;
}

.index-price {
  font-size: 1.4rem;
  line-height: 1.1;
  font-weight: 800;
  color: #0f172a;
  font-variant-numeric: tabular-nums;
}

.index-price.unavailable {
  font-size: 1.2rem;
  color: #64748b;
}

.index-change {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 4px;
  font-size: 0.84rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.index-change.up {
  color: #059669;
}

.index-change.down {
  color: #dc2626;
}

.index-change.neutral {
  color: #64748b;
}

.sparkline-svg {
  width: 96px;
  height: 32px;
  flex: 0 0 96px;
  overflow: visible;
}

.sparkline-path {
  fill: none;
  stroke-width: 2.5;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.sparkline-path.up {
  stroke: #059669;
}

.sparkline-path.down {
  stroke: #dc2626;
}

.sparkline-path.neutral {
  stroke: #94a3b8;
}

@media (max-width: 768px) {
  .market-overview-card {
    padding: 0.9rem;
    border-radius: 16px;
    margin-bottom: 1rem;
  }

  .panel-header {
    flex-direction: column;
    align-items: flex-start;
    margin-bottom: 10px;
  }

  .index-card {
    min-height: 104px;
  }

  .index-price {
    font-size: 1.22rem;
  }

  .sparkline-svg {
    width: 82px;
    height: 28px;
    flex-basis: 82px;
  }
}
</style>
