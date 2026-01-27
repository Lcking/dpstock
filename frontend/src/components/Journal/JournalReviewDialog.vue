<template>
  <n-modal
    :show="show"
    preset="card"
    title="复盘判断记录"
    style="width: 600px"
    @update:show="$emit('update:show', $event)"
  >
    <div v-if="record" class="review-dialog-content">
      <!-- Record Info -->
      <div class="record-info">
        <div class="info-row">
          <span class="label">股票:</span>
          <span class="value">{{ record.ts_code }}</span>
        </div>
        <div class="info-row">
          <span class="label">候选:</span>
          <n-tag :type="candidateTagType(record.candidate)" size="small">
            {{ record.candidate }}
          </n-tag>
        </div>
        <div class="info-row">
          <span class="label">创建时间:</span>
          <span class="value">{{ formatDate(record.created_at) }}</span>
        </div>
      </div>

      <!-- Notes Input -->
      <div class="notes-section">
        <div class="section-title">复盘笔记</div>
        <n-input
          v-model:value="notes"
          type="textarea"
          placeholder="记录你的复盘思考（选填，不超过200字）"
          :rows="5"
          :maxlength="200"
          show-count
        />
      </div>

      <!-- Hint -->
      <n-alert type="info" size="small" style="margin-top: 16px">
        系统将自动评估判断前提的验证结果，你可以添加自己的复盘笔记作为补充。
      </n-alert>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="$emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="reviewing" @click="handleReview">
          提交复盘
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, watch } from 'vue'
import { NModal, NInput, NTag, NButton, NSpace, NAlert, useMessage } from 'naive-ui'
import { apiService } from '@/services/api'
import type { JournalRecord } from '@/types/journal'

interface Props {
  show: boolean
  record: JournalRecord | null
}

const props = defineProps<Props>()

const emit = defineEmits<{
  (e: 'update:show', value: boolean): void
  (e: 'reviewed'): void
}>()

const message = useMessage()

// State
const reviewing = ref(false)
const notes = ref('')

// Watch show prop to reset notes
watch(() => props.show, (newShow) => {
  if (newShow) {
    notes.value = ''
  }
})

// Submit review
const handleReview = async () => {
  if (!props.record) return

  reviewing.value = true
  try {
    await apiService.reviewRecord(props.record.id, notes.value)

    message.success('复盘完成')
    emit('reviewed')
    emit('update:show', false)
  } catch (error) {
    console.error('Review error:', error)
    message.error('复盘失败')
  } finally {
    reviewing.value = false
  }
}

// Helpers
const candidateTagType = (candidate: string) => {
  const map = { A: 'success', B: 'info', C: 'warning' }
  return map[candidate as 'A' | 'B' | 'C'] as 'success' | 'info' | 'warning'
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
.review-dialog-content {
  padding: 4px 0;
}

.record-info {
  margin-bottom: 20px;
  padding: 12px;
  background: var(--n-color-hover);
  border-radius: 6px;
}

.info-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 6px 0;
}

.info-row .label {
  min-width: 80px;
  color: var(--n-text-color-3);
  font-size: 14px;
}

.info-row .value {
  font-size: 14px;
  font-weight: 500;
}

.notes-section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
