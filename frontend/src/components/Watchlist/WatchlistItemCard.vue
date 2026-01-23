<template>
  <div 
    class="watchlist-item-card" 
    :class="{ selected, clickable: true }"
    @click="$emit('click')"
  >
    <!-- 选择框 -->
    <div class="card-checkbox" @click.stop>
      <n-checkbox :checked="selected" @update:checked="$emit('select')" />
    </div>

    <!-- 股票基础信息 -->
    <div class="card-header">
      <div class="stock-info">
        <div class="stock-name">{{ item.name || item.ts_code }}</div>
        <div class="stock-code">{{ item.ts_code }}</div>
      </div>
      <div class="price-info">
        <div class="price">¥{{ item.price.toFixed(2) }}</div>
        <div v-if="item.change_pct !== null" class="change" :class="priceChangeClass">
          {{ formatPercent(item.change_pct) }}
        </div>
      </div>
    </div>

    <!-- 6个必须字段 -->
    <div class="card-body">
      <!-- 1. Trend -->
      <div class="info-row trend-row">
        <span class="label">趋势</span>
        <div class="trend-info">
          <n-tag :type="trendTagType" size="small">
            {{ trendLabel }}
          </n-tag>
          <span class="trend-strength">{{ item.trend.strength }}</span>
        </div>
      </div>

      <!-- 2. Relative Strength -->
      <div class="info-row">
        <span class="label">相对强弱</span>
        <n-tag 
          v-if="item.relative_strength.label_20d"
          :type="rsTagType"
          size="small"
        >
          {{ rsLabel }}
        </n-tag>
        <span v-else class="unavailable">-</span>
      </div>

      <!-- 3. Capital Flow -->
      <div class="info-row">
        <span class="label">资金</span>
        <n-tag :type="flowTagType" size="small">
          {{ item.capital_flow.label }}
        </n-tag>
      </div>

      <!-- 4. Risk -->
      <div class="info-row">
        <span class="label">风险</span>
        <n-tag :type="riskTagType" size="small">
          {{ riskLabel }}
        </n-tag>
      </div>

      <!-- 5. Events -->
      <div class="info-row">
        <span class="label">事件</span>
        <n-tag 
          v-if="item.events.flag !== 'none'"
          :type="eventTagType"
          size="small"
        >
          {{ eventLabel }}
        </n-tag>
        <span v-else class="event-none">无</span>
      </div>

      <!-- 6. Judgement -->
      <div class="info-row">
        <span class="label">判断</span>
        <div v-if="item.judgement.has_active" class="judgement-info">
          <n-tag type="info" size="small">
            {{ item.judgement.candidate }}
          </n-tag>
          <span v-if="item.judgement.days_left !== null" class="days-left">
            {{ item.judgement.days_left }}天
          </span>
        </div>
        <span v-else class="unavailable">-</span>
      </div>
    </div>

    <!-- 操作按钮 -->
    <div class="card-footer">
      <n-button text size="small" @click.stop="$emit('click')">
        查看分析
      </n-button>
      <n-button text size="small" type="error" @click.stop="handleRemove">
        移除
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NCheckbox, NTag, NButton, useDialog } from 'naive-ui'
import type { WatchlistItemSummary } from '@/types/watchlist'

interface Props {
  item: WatchlistItemSummary
  selected?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  selected: false
})

const emit = defineEmits<{
  (e: 'select'): void
  (e: 'remove'): void
  (e: 'click'): void
}>()

const dialog = useDialog()

// 价格变化样式
const priceChangeClass = computed(() => {
  if (!props.item.change_pct) return ''
  return props.item.change_pct > 0 ? 'positive' : 'negative'
})

// Trend
const trendLabel = computed(() => {
  const map = { up: '上涨', down: '下跌', sideways: '震荡' }
  return map[props.item.trend.direction]
})

const trendTagType = computed(() => {
  const map = { up: 'success', down: 'error', sideways: 'default' }
  return map[props.item.trend.direction] as 'success' | 'error' | 'default'
})

// Relative Strength
const rsLabel = computed(() => {
  const map = { strong: '强势', neutral: '中性', weak: '弱势' }
  return map[props.item.relative_strength.label_20d || 'neutral']
})

const rsTagType = computed(() => {
  const map = { strong: 'success', neutral: 'default', weak: 'warning' }
  return map[props.item.relative_strength.label_20d || 'neutral'] as 'success' | 'default' | 'warning'
})

// Capital Flow
const flowTagType = computed(() => {
  const label = props.item.capital_flow.label
  if (label === '承接放量') return 'success'
  if (label === '分歧放量' || label === '缩量阴跌') return 'error'
  if (label === '不可用') return 'default'
  return 'info'
})

// Risk
const riskLabel = computed(() => {
  const map = { low: '低', medium: '中', high: '高' }
  return map[props.item.risk.level]
})

const riskTagType = computed(() => {
  const map = { low: 'success', medium: 'warning', high: 'error' }
  return map[props.item.risk.level] as 'success' | 'warning' | 'error'
})

// Events
const eventLabel = computed(() => {
  const map = { minor: '次要', major: '重大', unavailable: '不可用' }
  return map[props.item.events.flag as 'minor' | 'major' | 'unavailable'] || '无'
})

const eventTagType = computed(() => {
  const map = { minor: 'warning', major: 'error', unavailable: 'default' }
  return map[props.item.events.flag as 'minor' | 'major' | 'unavailable'] as 'warning' | 'error' | 'default'
})

// 格式化百分比
const formatPercent = (value: number) => {
  const str = (value * 100).toFixed(2)
  return value >= 0 ? `+${str}%` : `${str}%`
}

// 移除确认
const handleRemove = () => {
  dialog.warning({
    title: '确认移除',
    content: `确定要从自选股中移除 ${props.item.name || props.item.ts_code} 吗？`,
    positiveText: '确定',
    negativeText: '取消',
    onPositiveClick: () => {
      emit('remove')
    }
  })
}
</script>

<style scoped>
.watchlist-item-card {
  position: relative;
  padding: 16px;
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  transition: all 0.2s;
  cursor: pointer;
}

.watchlist-item-card:hover {
  border-color: var(--n-color-target);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.watchlist-item-card.selected {
  border-color: var(--n-color-target);
  background: var(--n-color-hover);
}

.card-checkbox {
  position: absolute;
  top: 12px;
  right: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 16px;
  padding-right: 30px;
}

.stock-info {
  flex: 1;
}

.stock-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.stock-code {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.price-info {
  text-align: right;
}

.price {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.change {
  font-size: 12px;
  font-weight: 500;
}

.change.positive {
  color: #18a058;
}

.change.negative {
  color: #d03050;
}

.card-body {
  border-top: 1px solid var(--n-divider-color);
  padding-top: 12px;
  margin-bottom: 12px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 6px 0;
  font-size: 14px;
}

.info-row .label {
  color: var(--n-text-color-3);
  min-width: 60px;
}

.trend-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.trend-strength {
  font-size: 12px;
  font-weight: 600;
  color: var(--n-text-color-2);
}

.judgement-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.days-left {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.unavailable,
.event-none {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.card-footer {
  display: flex;
  gap: 12px;
  border-top: 1px solid var(--n-divider-color);
  padding-top: 12px;
}
</style>
