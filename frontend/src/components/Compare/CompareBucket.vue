<template>
  <div class="compare-bucket" :class="`bucket-${bucket.id}`">
    <!-- Bucket Header -->
    <div class="bucket-header">
      <div class="bucket-title">
        <n-tag :type="bucketTagType" :bordered="false" size="medium">
          {{ bucket.title }}
        </n-tag>
        <span class="item-count">{{ bucket.items.length }}</span>
      </div>
      <div class="bucket-reason">
        <n-text depth="3" size="small">{{ bucket.reason }}</n-text>
      </div>
    </div>

    <!-- Bucket Items -->
    <div class="bucket-items">
      <div
        v-for="item in bucket.items"
        :key="item.ts_code"
        class="bucket-item"
        @click="$emit('item-click', item.ts_code)"
      >
        <!-- Stock Basic Info -->
        <div class="item-header">
          <div class="stock-info">
            <span class="stock-name">{{ item.name || item.ts_code }}</span>
            <span class="stock-code">{{ item.ts_code }}</span>
          </div>
          <div class="price-change" :class="priceChangeClass(item.change_pct)">
            {{ formatPercent(item.change_pct) }}
          </div>
        </div>

        <!-- Key Signals -->
        <div class="item-signals">
          <n-space size="small">
            <!-- Trend -->
            <n-tag :type="getTrendType(item.trend.direction)" size="tiny">
              {{ getTrendLabel(item.trend.direction) }}
            </n-tag>
            
            <!-- RS -->
            <n-tag 
              v-if="item.relative_strength.label_20d"
              :type="getRSType(item.relative_strength.label_20d)"
              size="tiny"
            >
              {{ getRSLabel(item.relative_strength.label_20d) }}
            </n-tag>
            
            <!-- Flow -->
            <n-tag :type="getFlowType(item.capital_flow.label)" size="tiny">
              {{ item.capital_flow.label }}
            </n-tag>
          </n-space>
        </div>

        <!-- Structure Score (if available) -->
        <div class="item-footer">
          <n-text depth="3" size="tiny">
            强度: {{ item.trend.strength }}
          </n-text>
        </div>
      </div>

      <!-- Empty State -->
      <div v-if="bucket.items.length === 0" class="bucket-empty">
        <n-text depth="3" size="small">暂无标的</n-text>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag, NText, NSpace } from 'naive-ui'
import type { CompareBucket } from '@/types/compare'

interface Props {
  bucket: CompareBucket
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'item-click', tsCode: string): void
}>()

// Bucket tag type
const bucketTagType = computed(() => {
  const typeMap = {
    best: 'success',
    conflict: 'warning', 
    weak: 'default',
    event: 'error'
  }
  return typeMap[props.bucket.id] as 'success' | 'warning' | 'default' | 'error'
})

// Trend
const getTrendLabel = (direction: string) => {
  const map = { up: '上涨', down: '下跌', sideways: '震荡' }
  return map[direction as 'up' | 'down' | 'sideways'] || direction
}

const getTrendType = (direction: string) => {
  const map = { up: 'success', down: 'error', sideways: 'default' }
  return map[direction as 'up' | 'down' | 'sideways'] as 'success' | 'error' | 'default'
}

// RS
const getRSLabel = (label: string) => {
  const map = { strong: '强', neutral: '中', weak: '弱' }
  return map[label as 'strong' | 'neutral' | 'weak'] || label
}

const getRSType = (label: string) => {
  const map = { strong: 'success', neutral: 'info', weak: 'warning' }
  return map[label as 'strong' | 'neutral' | 'weak'] as 'success' | 'info' | 'warning'
}

// Flow
const getFlowType = (label: string) => {
  if (label === '承接放量') return 'success'
  if (label === '分歧放量' || label === '缩量阴跌') return 'error'
  return 'info'
}

// Price change
const priceChangeClass = (changePct: number | null) => {
  if (!changePct) return ''
  return changePct > 0 ? 'positive' : 'negative'
}

const formatPercent = (value: number | null) => {
  if (value === null) return '-'
  const str = (value * 100).toFixed(2)
  return value >= 0 ? `+${str}%` : `${str}%`
}
</script>

<style scoped>
.compare-bucket {
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  overflow: hidden;
}

.bucket-best {
  border-top: 3px solid #18a058;
}

.bucket-conflict {
  border-top: 3px solid #f0a020;
}

.bucket-weak {
  border-top: 3px solid #909399;
}

.bucket-event {
  border-top: 3px solid #d03050;
}

.bucket-header {
  padding: 16px;
  border-bottom: 1px solid var(--n-divider-color);
}

.bucket-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.item-count {
  font-size: 14px;
  font-weight: 600;
  color: var(--n-text-color-2);
}

.bucket-reason {
  font-size: 13px;
}

.bucket-items {
  padding: 12px;
  max-height: 600px;
  overflow-y: auto;
}

.bucket-item {
  padding: 12px;
  margin-bottom: 8px;
  background: var(--n-color-hover);
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.bucket-item:last-child {
  margin-bottom: 0;
}

.bucket-item:hover {
  background: var(--n-color-pressed);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 8px;
}

.stock-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.stock-name {
  font-size: 14px;
  font-weight: 600;
}

.stock-code {
  font-size: 12px;
  color: var(--n-text-color-3);
}

.price-change {
  font-size: 14px;
  font-weight: 600;
}

.price-change.positive {
  color: #18a058;
}

.price-change.negative {
  color: #d03050;
}

.item-signals {
  margin-bottom: 8px;
}

.item-footer {
  font-size: 12px;
}

.bucket-empty {
  display: flex;
  justify-content: center;
  padding: 40px 20px;
  color: var(--n-text-color-3);
}
</style>
