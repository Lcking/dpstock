<template>
  <div class="weekly-recap-page">
    <div class="page-header">
      <n-button quaternary class="back-btn" @click="router.push('/me')">
        <template #icon><n-icon><ArrowBack /></n-icon></template>
        返回我的
      </n-button>
      <div>
        <h1>判断验证周报</h1>
        <p>汇总你近一周的判断复盘结果，辅助检验个人判断质量。</p>
      </div>
    </div>

    <div v-if="loading" class="loading-area">
      <n-spin size="large" />
    </div>

    <n-alert v-else-if="errorMessage" type="error" :bordered="false">
      <div class="error-row">
        <span>{{ errorMessage }}</span>
        <n-button size="small" tertiary type="primary" @click="loadRecap">重新加载</n-button>
      </div>
    </n-alert>

    <template v-else-if="recap">
      <n-alert
        v-if="recap.due_count > 0"
        type="info"
        :bordered="false"
        class="top-alert"
      >
        你有 {{ recap.due_count }} 条判断待复盘，完成复盘后周报数据会更完整。
        <n-button size="small" tertiary type="primary" style="margin-left: 8px" @click="router.push('/journal')">
          去复盘
        </n-button>
      </n-alert>

      <n-card class="hero-card">
        <n-text depth="3">统计周期：{{ recap.period_label }}</n-text>
        <p class="summary-text">{{ summaryText }}</p>
        <n-text depth="3" class="disclaimer">{{ recap.disclaimer }}</n-text>
        <n-space :size="12" style="margin-top: 12px">
          <n-button type="primary" @click="router.push('/journal')">打开判断日记</n-button>
          <n-button @click="router.push('/me')">用户中心</n-button>
        </n-space>
      </n-card>

      <n-grid cols="1 s:2 l:4" :x-gap="16" :y-gap="16" responsive="screen" class="metrics-grid">
        <n-grid-item>
          <n-card size="small" class="metric-card">
            <n-text depth="3">系统支持</n-text>
            <div class="metric-value supported">{{ outcomeCounts.supported }}</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card size="small" class="metric-card">
            <n-text depth="3">前提被否定</n-text>
            <div class="metric-value falsified">{{ outcomeCounts.falsified }}</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card size="small" class="metric-card">
            <n-text depth="3">结果不确定</n-text>
            <div class="metric-value uncertain">{{ outcomeCounts.uncertain }}</div>
          </n-card>
        </n-grid-item>
        <n-grid-item>
          <n-card size="small" class="metric-card">
            <n-text depth="3">复盘总数</n-text>
            <div class="metric-value">{{ stats.reviewed_count }}</div>
          </n-card>
        </n-grid-item>
      </n-grid>

      <n-card title="典型复盘案例" size="small" class="section-card">
        <template v-if="recap.highlight_cases?.length">
          <n-space vertical :size="12">
            <div v-for="(item, idx) in recap.highlight_cases" :key="idx" class="case-item">
              <div class="case-header">
                <n-tag size="small" :type="outcomeTagType(item.outcome)">{{ item.outcome_label }}</n-tag>
                <a v-if="item.stock_code" class="stock-link" :href="`/stock/${item.stock_code}`">
                  {{ item.stock_code }}
                </a>
              </div>
              <div class="case-condition">{{ item.condition }}</div>
              <n-text depth="3" class="case-date">复盘日期 {{ item.reviewed_at }}</n-text>
            </div>
          </n-space>
        </template>
        <n-empty v-else description="本周暂无足够复盘案例，欢迎先在判断日记中完成复盘。" size="small" />
      </n-card>

      <n-card title="条件类型表现" size="small" class="section-card">
        <ConditionQualityLeaderboard
          v-if="leaderboard.length > 0"
          :items="leaderboard"
          title=""
          hint="按你近一周已复盘的判断统计各条件类型的支持率。"
          :max-items="8"
        />
        <n-empty v-else description="完成更多复盘后，这里会展示条件类型表现。" size="small" />
      </n-card>

      <n-card title="数据说明" size="small" class="section-card">
        <n-text depth="3">
          本页数据来自你的判断日记在近 {{ recap.window_days }} 天内的复盘记录，仅反映个人历史样本，
          不代表未来收益或买卖建议。生成时间：{{ recap.generated_at }}。
        </n-text>
      </n-card>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NGrid,
  NGridItem,
  NIcon,
  NSpace,
  NSpin,
  NTag,
  NText,
} from 'naive-ui'
import { ArrowBackOutline as ArrowBack } from '@vicons/ionicons5'
import ConditionQualityLeaderboard from '@/components/Journal/ConditionQualityLeaderboard.vue'
import { apiService } from '@/services/api'
import { applyPageSeo } from '@/utils/seo'
import { buildPersonalReviewSummary } from '@/utils/trustStats'
import type { JournalConditionQualityItem } from '@/types/journal'

interface WeeklyRecapCase {
  stock_code: string
  candidate: string
  outcome: string
  outcome_label: string
  condition: string
  reviewed_at: string
}

interface WeeklyRecapStats {
  reviewed_count: number
  pending_count?: number
  support_rate: number | null
  outcome_counts: Record<string, number>
  condition_quality_leaderboard?: JournalConditionQualityItem[]
}

interface WeeklyRecapPayload {
  scope: string
  window_days: number
  period_label: string
  disclaimer: string
  generated_at: string
  due_count: number
  stats: WeeklyRecapStats
  highlight_cases: WeeklyRecapCase[]
}

const router = useRouter()
const loading = ref(true)
const errorMessage = ref('')
const recap = ref<WeeklyRecapPayload | null>(null)

const stats = computed(() => recap.value?.stats ?? {
  reviewed_count: 0,
  support_rate: null,
  outcome_counts: {},
})

const outcomeCounts = computed(() => ({
  supported: stats.value.outcome_counts?.supported ?? 0,
  falsified: stats.value.outcome_counts?.falsified ?? 0,
  uncertain: stats.value.outcome_counts?.uncertain ?? 0,
}))

const leaderboard = computed(
  () => recap.value?.stats?.condition_quality_leaderboard ?? [],
)

const summaryText = computed(() => {
  const personal = buildPersonalReviewSummary(recap.value?.stats)
  if (personal) {
    return `近 ${recap.value?.window_days ?? 7} 天 · ${personal}`
  }
  return '近一周复盘样本仍在积累中，完成判断复盘后这里会展示你的个人验证统计。'
})

function outcomeTagType(outcome: string) {
  if (outcome === 'supported') return 'success'
  if (outcome === 'falsified') return 'error'
  return 'default'
}

async function loadRecap() {
  loading.value = true
  errorMessage.value = ''
  try {
    recap.value = await apiService.getWeeklyRecap(7)
  } catch (error) {
    console.error('加载判断验证周报失败:', error)
    errorMessage.value = '加载失败，请稍后重试'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  applyPageSeo({
    title: '判断验证周报 | Agu AI',
    description: '查看你近一周的判断复盘统计与条件表现，辅助检验个人判断质量。',
    canonicalPath: '/me/weekly-recap',
  })
  loadRecap()
})
</script>

<style scoped>
.weekly-recap-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 24px 20px 48px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 8px 0 6px;
  font-size: 28px;
}

.page-header p {
  margin: 0;
  color: #64748b;
}

.back-btn {
  margin-bottom: 8px;
  padding-left: 0;
}

.loading-area {
  display: flex;
  justify-content: center;
  padding: 80px 0;
}

.error-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.top-alert {
  margin-bottom: 16px;
}

.hero-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.summary-text {
  margin: 12px 0 8px;
  font-size: 16px;
  line-height: 1.6;
  color: #334155;
}

.disclaimer {
  display: block;
  line-height: 1.6;
}

.metrics-grid {
  margin-bottom: 16px;
}

.metric-card {
  border-radius: 14px;
}

.metric-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: #3d5bcc;
}

.metric-value.supported {
  color: #027a48;
}

.metric-value.falsified {
  color: #b42318;
}

.metric-value.uncertain {
  color: #475467;
}

.section-card {
  margin-bottom: 16px;
  border-radius: 16px;
}

.case-item {
  padding: 14px 16px;
  border-radius: 12px;
  background: #f8faff;
  border: 1px solid rgba(61, 91, 204, 0.1);
}

.case-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.stock-link {
  color: #5560d6;
  text-decoration: none;
  font-weight: 600;
}

.case-condition {
  line-height: 1.6;
  color: #334155;
}

.case-date {
  display: block;
  margin-top: 6px;
  font-size: 13px;
}
</style>
