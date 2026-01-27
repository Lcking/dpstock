<template>
  <n-modal
    :show="show"
    preset="card"
    title="判断详情"
    style="width: 600px; max-width: 95vw"
    @update:show="$emit('update:show', $event)"
  >
    <div v-if="record" class="detail-dialog-content">
      <!-- Stock Info -->
      <div class="detail-section">
        <div class="section-header">
          <span class="stock-code">{{ record.ts_code }}</span>
          <n-tag :type="statusTagType(record.status)" size="small">
            {{ statusLabel(record.status) }}
          </n-tag>
        </div>
      </div>

      <!-- Judgment Info -->
      <div class="detail-section">
        <div class="section-title">判断信息</div>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">选择候选:</span>
            <n-tag :type="candidateTagType(record.candidate)" size="small">
              候选 {{ record.candidate }}
            </n-tag>
          </div>
          <div class="info-item">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatDate(record.created_at) }}</span>
          </div>
          <div class="info-item" v-if="record.validation_date">
            <span class="label">验证截止:</span>
            <span class="value">{{ formatDate(record.validation_date) }}</span>
          </div>
          <div class="info-item" v-if="record.days_left !== null && record.status === 'active'">
            <span class="label">剩余天数:</span>
            <span class="value highlight">{{ record.days_left }} 天</span>
          </div>
        </div>
      </div>

      <!-- Review Result (if reviewed) -->
      <div class="detail-section" v-if="record.review && record.status === 'reviewed'">
        <div class="section-title">复盘结果</div>
        <div class="review-info">
          <div class="outcome-row">
            <n-tag :type="outcomeTagType(record.review.outcome)" size="medium">
              {{ outcomeLabel(record.review.outcome) }}
            </n-tag>
            <span class="review-time">
              复盘于 {{ formatDate(record.review.reviewed_at) }}
            </span>
          </div>
          <div class="review-notes" v-if="record.review.notes">
            <div class="notes-label">复盘笔记:</div>
            <div class="notes-content">{{ record.review.notes }}</div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="action-section">
        <n-button type="primary" @click="goToAnalyze">
          重新分析该股票
        </n-button>
        <n-button v-if="record.status === 'due'" @click="$emit('review', record)">
          立即复盘
        </n-button>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="$emit('update:show', false)">关闭</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { NModal, NTag, NButton, NSpace } from 'naive-ui'
import { useRouter } from 'vue-router'
import type { JournalRecord } from '@/types/journal'

interface Props {
  show: boolean
  record: JournalRecord | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'review', record: JournalRecord): void
}>()

const router = useRouter()

// Navigate to home to re-analyze
const goToAnalyze = () => {
  if (props.record) {
    emit('update:show', false)
    router.push({ path: '/', query: { code: props.record.ts_code } })
  }
}

// Helpers
const candidateTagType = (candidate: string) => {
  const map: Record<string, 'success' | 'info' | 'warning'> = { 
    A: 'success', B: 'info', C: 'warning' 
  }
  return map[candidate] || 'info'
}

const statusTagType = (status: string) => {
  const map: Record<string, 'info' | 'warning' | 'success' | 'default'> = { 
    active: 'info', 
    due: 'warning', 
    reviewed: 'success',
    archived: 'default'
  }
  return map[status] || 'default'
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = { 
    active: '活跃中', 
    due: '待复盘', 
    reviewed: '已复盘',
    archived: '已归档'
  }
  return map[status] || status
}

const outcomeTagType = (outcome: string) => {
  const map: Record<string, 'success' | 'error' | 'warning'> = { 
    supported: 'success', 
    falsified: 'error', 
    uncertain: 'warning' 
  }
  return map[outcome] || 'warning'
}

const outcomeLabel = (outcome: string) => {
  const map: Record<string, string> = {
    supported: '前提得到支持',
    falsified: '前提被证伪',
    uncertain: '结果不确定'
  }
  return map[outcome] || outcome
}

const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style scoped>
.detail-dialog-content {
  padding: 4px 0;
}

.detail-section {
  margin-bottom: 20px;
  padding: 16px;
  background: var(--n-color-hover);
  border-radius: 8px;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stock-code {
  font-size: 24px;
  font-weight: 700;
  color: var(--n-text-color);
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 12px;
  color: var(--n-text-color-2);
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.info-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-item .label {
  color: var(--n-text-color-3);
  font-size: 13px;
}

.info-item .value {
  font-size: 14px;
  font-weight: 500;
}

.info-item .value.highlight {
  color: var(--n-color-target);
}

.review-info {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.outcome-row {
  display: flex;
  align-items: center;
  gap: 12px;
}

.review-time {
  font-size: 13px;
  color: var(--n-text-color-3);
}

.notes-label {
  font-size: 13px;
  color: var(--n-text-color-3);
  margin-bottom: 4px;
}

.notes-content {
  font-size: 14px;
  line-height: 1.6;
  padding: 8px;
  background: var(--n-color);
  border-radius: 4px;
}

.action-section {
  display: flex;
  gap: 12px;
  margin-top: 16px;
}

@media (max-width: 480px) {
  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
