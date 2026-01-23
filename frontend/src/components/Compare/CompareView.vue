<template>
  <div class="compare-view">
    <!-- Header -->
    <div class="compare-header">
      <h2>标的比较</h2>
      <div class="header-controls">
        <n-space>
          <n-select
            v-model:value="window"
            :options="windowOptions"
            size="small"
            style="width: 120px"
            @update:value="loadCompare"
          />
          <n-select
            v-model:value="bench"
            :options="benchOptions"
            size="small"
            style="width: 150px"
            @update:value="loadCompare"
          />
          <n-button @click="$router.back()">返回</n-button>
        </n-space>
      </div>
    </div>

    <!-- Loading -->
    <div v-if="loading" class="loading-container">
      <n-spin size="large" />
    </div>

    <!-- Compare Results -->
    <div v-else-if="compareData" class="compare-content">
      <!-- Meta Info -->
      <div class="compare-meta">
        <n-text depth="3">
          比较 {{ compareData.meta.total_count }} 只标的，截至 {{ compareData.meta.asof }}
        </n-text>
      </div>

      <!-- 4-Bucket Kanban -->
      <div class="buckets-grid">
        <compare-bucket
          v-for="bucket in compareData.buckets"
          :key="bucket.id"
          :bucket="bucket"
          @item-click="handleItemClick"
        />
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state">
      <n-empty description="请从自选股页面选择标的进入比较" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NSpace, NSelect, NSpin, NText, NEmpty, useMessage } from 'naive-ui'
import CompareBucket from './CompareBucket.vue'
import type { CompareResponse } from '@/types/compare'

const route = useRoute()
const router = useRouter()
const message = useMessage()

// State
const loading = ref(false)
const compareData = ref<CompareResponse | null>(null)
const window = ref(20)
const bench = ref('000300.SH')

// Options
const windowOptions = [
  { label: '5日', value: 5 },
  { label: '20日', value: 20 },
  { label: '60日', value: 60 }
]

const benchOptions = [
  { label: '沪深300', value: '000300.SH' },
  { label: '上证指数', value: '000001.SH' },
  { label: '深证成指', value: '399001.SZ' }
]

// Load compare data
const loadCompare = async () => {
  const codesParam = route.query.codes as string
  if (!codesParam) {
    message.warning('未选择标的')
    return
  }

  const tsCodes = codesParam.split(',').filter(c => c.length > 0)
  if (tsCodes.length < 2) {
    message.warning('至少选择2只标的进行比较')
    return
  }

  loading.value = true
  try {
    const response = await fetch('/api/compare', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ts_codes: tsCodes,
        window: window.value,
        bench: bench.value,
        use_industry: true
      })
    })

    if (!response.ok) throw new Error('Failed to compare')

    compareData.value = await response.json()
  } catch (error) {
    console.error('Compare error:', error)
    message.error('比较失败')
  } finally {
    loading.value = false
  }
}

// Item click handler
const handleItemClick = (tsCode: string) => {
  router.push(`/analysis/${tsCode}`)
}

onMounted(() => {
  loadCompare()
})
</script>

<style scoped>
.compare-view {
  padding: 20px;
  max-width: 1600px;
  margin: 0 auto;
}

.compare-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.compare-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.compare-content {
  margin-top: 20px;
}

.compare-meta {
  margin-bottom: 16px;
  font-size: 14px;
}

.buckets-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
  gap: 20px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
