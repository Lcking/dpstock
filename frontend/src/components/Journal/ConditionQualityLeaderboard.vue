<template>
  <div v-if="items.length > 0" class="condition-leaderboard" :class="{ compact }">
    <div class="leaderboard-title">{{ title }}</div>
    <div v-if="hint" class="leaderboard-hint">{{ hint }}</div>
    <div class="leaderboard-table">
      <div class="leaderboard-head">
        <span>条件类型</span>
        <span>样本</span>
        <span>支持率</span>
        <span>结果分布</span>
      </div>
      <div v-for="item in visibleItems" :key="item.key" class="leaderboard-row">
        <span class="leaderboard-label">{{ item.label }}</span>
        <span>{{ item.reviewed_count }}</span>
        <span class="leaderboard-rate">{{ formatSupportRate(item.support_rate) }}</span>
        <span class="leaderboard-breakdown">
          支持 {{ item.supported_count }} / 证伪 {{ item.falsified_count }} / 不确定 {{ item.uncertain_count }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { JournalConditionQualityItem } from '@/types/journal'
import { formatSupportRate } from '@/utils/trustStats'

const props = withDefaults(
  defineProps<{
    items: JournalConditionQualityItem[]
    title?: string
    hint?: string
    compact?: boolean
    maxItems?: number
  }>(),
  {
    title: '条件质量榜单',
    hint: '',
    compact: false,
    maxItems: 5,
  },
)

const visibleItems = computed(() => props.items.slice(0, props.maxItems))
</script>

<style scoped>
.condition-leaderboard {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--n-border-color);
}

.condition-leaderboard.compact {
  margin-top: 12px;
  padding-top: 12px;
}

.leaderboard-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 6px;
}

.leaderboard-hint {
  font-size: 13px;
  color: var(--n-text-color-3);
  margin-bottom: 12px;
  line-height: 1.5;
}

.leaderboard-table {
  display: grid;
  gap: 8px;
}

.leaderboard-head,
.leaderboard-row {
  display: grid;
  grid-template-columns: 1.2fr 0.6fr 0.8fr 2fr;
  gap: 12px;
  align-items: center;
  font-size: 13px;
}

.leaderboard-head {
  color: var(--n-text-color-3);
  font-weight: 600;
}

.leaderboard-label {
  font-weight: 600;
}

.leaderboard-rate {
  font-weight: 600;
}

.leaderboard-breakdown {
  color: var(--n-text-color-3);
}

@media (max-width: 768px) {
  .leaderboard-head,
  .leaderboard-row {
    grid-template-columns: 1fr;
    gap: 4px;
    padding: 10px 0;
    border-bottom: 1px solid var(--n-border-color);
  }

  .leaderboard-head {
    display: none;
  }
}
</style>
