<template>
  <div class="watchlist-filters">
    <div class="filter-section">
      <span class="section-label">排序</span>
      <n-select
        :value="sort"
        :options="sortOptions"
        size="small"
        style="width: 180px"
        @update:value="handleSortChange"
      />
    </div>

    <div class="filter-section">
      <span class="section-label">筛选</span>
      <n-space>
        <n-tag
          v-for="filter in filterOptions"
          :key="filter.value"
          :type="isActive(filter.value) ? 'info' : 'default'"
          :bordered="false"
          checkable
          :checked="isActive(filter.value)"
          @update:checked="(checked) => toggleFilter(filter.value, checked)"
          size="small"
        >
          {{ filter.label }}
        </n-tag>
      </n-space>
    </div>

    <div v-if="activeFilters.length > 0" class="active-filters">
      <n-text depth="3" size="small">
        已应用 {{ activeFilters.length }} 个筛选条件
      </n-text>
      <n-button text size="tiny" @click="clearFilters">
        清除全部
      </n-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NSelect, NSpace, NTag, NText, NButton } from 'naive-ui'

interface Props {
  sort: string
  filters: string[]
}

const props = withDefaults(defineProps<Props>(), {
  sort: 'SCORE_DESC',
  filters: () => []
})

const emit = defineEmits<{
  (e: 'update:sort', value: string): void
  (e: 'update:filters', value: string[]): void
}>()

// 排序选项
const sortOptions = [
  { label: '综合评分', value: 'SCORE_DESC' },
  { label: '相对强弱', value: 'RS_20D_DESC' },
  { label: '趋势强度', value: 'TREND_STRENGTH_DESC' },
  { label: '风险优先', value: 'RISK_ASC' },
  { label: '即将到期', value: 'JUDGEMENT_DUE_SOON' }
]

// 筛选选项
const filterOptions = [
  { label: '结构占优', value: 'STRUCTURE_ADVANTAGE' },
  { label: '无事件扰动', value: 'NO_EVENT' },
  { label: '有活跃判断', value: 'HAS_JUDGEMENT' },
  { label: '低风险', value: 'LOW_RISK' },
  { label: '强于大盘', value: 'STRONG_RS' }
]

const activeFilters = ref<string[]>(props.filters)

// 判断筛选是否激活
const isActive = (value: string) => {
  return activeFilters.value.includes(value)
}

// 切换筛选
const toggleFilter = (value: string, checked: boolean) => {
  if (checked) {
    if (!activeFilters.value.includes(value)) {
      activeFilters.value.push(value)
    }
  } else {
    const index = activeFilters.value.indexOf(value)
    if (index > -1) {
      activeFilters.value.splice(index, 1)
    }
  }
  emit('update:filters', activeFilters.value)
}

// 清除所有筛选
const clearFilters = () => {
  activeFilters.value = []
  emit('update:filters', [])
}

// 排序变化
const handleSortChange = (value: string) => {
  emit('update:sort', value)
}
</script>

<style scoped>
.watchlist-filters {
  padding: 16px;
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  margin-bottom: 16px;
}

.filter-section {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.filter-section:last-child {
  margin-bottom: 0;
}

.section-label {
  font-size: 14px;
  font-weight: 500;
  color: var(--n-text-color-2);
  min-width: 50px;
}

.active-filters {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--n-divider-color);
}
</style>
