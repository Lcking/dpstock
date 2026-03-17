<template>
  <div class="market-overview-card">
    <div class="panel-header">
      <div>
        <h2>核心指数概览</h2>
        <p>用更直接的市场温度，替代开休市提示。</p>
      </div>
      <span v-if="updatedLabel" class="updated-at">更新于 {{ updatedLabel }}</span>
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
            <div class="index-price">{{ formatPrice(item.price) }}</div>
            <div class="index-change" :class="changeClass(item.change_percent)">
              {{ formatSigned(item.change) }}
              <span>{{ formatPercent(item.change_percent) }}</span>
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
  { key: 'shanghai', name: '上证指数', market: 'A', symbol: '000001.SS', price: null, change: null, change_percent: null, status: 'unavailable' },
  { key: 'csi300', name: '沪深300', market: 'A', symbol: '000300.SS', price: null, change: null, change_percent: null, status: 'unavailable' },
  { key: 'hangseng', name: '恒生指数', market: 'HK', symbol: '^HSI', price: null, change: null, change_percent: null, status: 'unavailable' },
  { key: 'nasdaq', name: '纳斯达克', market: 'US', symbol: '^IXIC', price: null, change: null, change_percent: null, status: 'unavailable' },
])
const updatedAt = ref<number | null>(null)
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

onMounted(() => {
  loadOverview()
  refreshTimer = window.setInterval(loadOverview, 300000)
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
  padding: 1.25rem;
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
  margin-bottom: 16px;
}

.panel-header h2 {
  margin: 0 0 6px;
  font-size: 1.15rem;
  color: #1f2540;
}

.panel-header p {
  margin: 0;
  color: #667085;
  font-size: 0.92rem;
}

.updated-at {
  color: #94a3b8;
  font-size: 0.82rem;
  white-space: nowrap;
}

.index-card {
  min-height: 156px;
  padding: 16px;
  border-radius: 18px;
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
  font-weight: 700;
  color: #1f2937;
}

.index-symbol {
  margin: 4px 0 0;
  color: #94a3b8;
  font-size: 0.82rem;
}

.index-price {
  margin-top: 18px;
  font-size: 1.9rem;
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
  gap: 8px;
  font-size: 0.98rem;
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

@media (max-width: 768px) {
  .market-overview-card {
    padding: 1rem;
    border-radius: 16px;
    margin-bottom: 1rem;
  }

  .panel-header {
    flex-direction: column;
    margin-bottom: 14px;
  }

  .index-card {
    min-height: 132px;
  }

  .index-price {
    font-size: 1.55rem;
  }
}
</style>
