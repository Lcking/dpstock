<template>
  <n-modal
    :show="show"
    preset="card"
    title="判断详情"
    style="width: 700px; max-width: 95vw"
    @update:show="$emit('update:show', $event)"
  >
    <div v-if="record" class="detail-dialog-content">
      <!-- Stock Info -->
      <div class="detail-section stock-header">
        <div class="section-header">
          <span class="stock-code">{{ record.ts_code }}</span>
          <n-space>
            <n-tag :type="candidateTagType(record.candidate)" size="medium">
              候选 {{ record.candidate }}
            </n-tag>
            <n-tag :type="statusTagType(record.status)" size="medium">
              {{ statusLabel(record.status) }}
            </n-tag>
          </n-space>
        </div>
      </div>

      <!-- Your Judgment -->
      <div class="detail-section">
        <div class="section-title">📝 你的判断</div>
        <div class="judgment-content">
          <div class="judgment-choice">
            <div class="choice-label">选择的候选项:</div>
            <div class="choice-value">
              <n-tag :type="candidateTagType(record.candidate)" size="large">
                {{ candidateDescription(record) }}
              </n-tag>
            </div>
          </div>

          <div v-if="selectedCandidateDescription(record)" class="candidate-condition">
            <div class="sub-title">候选条件:</div>
            <div class="condition-content">{{ selectedCandidateDescription(record) }}</div>
          </div>
          
          <!-- Selected Premises -->
          <div v-if="record.selected_premises && record.selected_premises.length > 0" class="premises-section">
            <div class="sub-title">判断依据:</div>
            <ul class="premises-list">
              <li v-for="(premise, idx) in record.selected_premises" :key="idx">
                {{ premise }}
              </li>
            </ul>
          </div>

          <!-- Risk Checks -->
          <div v-if="record.selected_risk_checks && record.selected_risk_checks.length > 0" class="risks-section">
            <div class="sub-title">风险检查项:</div>
            <n-space wrap>
              <n-tag v-for="(check, idx) in record.selected_risk_checks" :key="idx" size="small" type="warning">
                {{ check }}
              </n-tag>
            </n-space>
          </div>
        </div>
      </div>

      <!-- Timeline Info -->
      <div class="detail-section">
        <div class="section-title">⏱️ 时间线</div>
        <div class="timeline-grid">
          <div class="timeline-item">
            <n-icon size="16" color="#667eea"><CalendarOutline /></n-icon>
            <span class="label">创建时间:</span>
            <span class="value">{{ formatDate(record.created_at) }}</span>
          </div>
          <div class="timeline-item" v-if="record.validation_date">
            <n-icon size="16" color="#f0a020"><TimeOutline /></n-icon>
            <span class="label">验证截止:</span>
            <span class="value">{{ formatDate(record.validation_date) }}</span>
          </div>
          <div class="timeline-item highlight" v-if="record.days_left !== null && record.status === 'active'">
            <n-icon size="16" color="#18a058"><HourglassOutline /></n-icon>
            <span class="label">剩余天数:</span>
            <span class="value highlight-text">{{ record.days_left }} 天</span>
          </div>
        </div>
      </div>

      <!-- Review Result (if reviewed) -->
      <div class="detail-section" v-if="record.review && record.status === 'reviewed'">
        <div class="section-title">✅ 复盘结果</div>
        <div class="review-info">
          <div class="outcome-row">
            <n-tag :type="outcomeTagType(record.review.outcome)" size="large">
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
          <div class="system-evaluation" v-if="record.review.system_evaluation">
            <div class="notes-label">系统判卷:</div>
            <div class="notes-content">{{ record.review.system_evaluation.summary }}</div>
            <div class="notes-content" v-if="record.review.system_evaluation.actual_path">
              实际路径：{{ record.review.system_evaluation.actual_path }}
            </div>
          </div>
        </div>
      </div>

      <!-- Action Guidance -->
      <div class="detail-section action-guidance">
        <div class="section-title">🎯 下一步行动</div>
        <div class="action-cards">
          <!-- Active status guidance -->
          <n-alert v-if="record.status === 'active'" type="info" :show-icon="true">
            <template #header>等待验证中</template>
            <p>你的判断正在验证期内，还有 <strong>{{ record.days_left }}</strong> 天到期。</p>
            <p>建议：持续观察该股票走势，关注是否符合你的判断逻辑。</p>
          </n-alert>
          
          <!-- Due status guidance -->
          <n-alert v-else-if="record.status === 'due'" type="warning" :show-icon="true">
            <template #header>需要复盘</template>
            <p>验证期已到，是时候回顾你的判断是否正确了。</p>
            <p>复盘可以帮助你改进分析逻辑，提升交易水平。</p>
          </n-alert>
          
          <!-- Reviewed status guidance -->
          <n-alert v-else-if="record.status === 'reviewed'" type="success" :show-icon="true">
            <template #header>已完成复盘</template>
            <p>这条判断已复盘完成，结果: <strong>{{ outcomeLabel(record.review?.outcome || 'uncertain') }}</strong></p>
            <p>你可以重新分析该股票，或查看其他判断记录。</p>
          </n-alert>
        </div>
      </div>

      <!-- Actions -->
      <div class="action-section">
        <n-button type="primary" size="large" @click="goToAnalyze">
          <template #icon><n-icon><AnalyticsOutline /></n-icon></template>
          重新分析该股票
        </n-button>
        <n-button v-if="record.status === 'due'" type="warning" size="large" @click="$emit('review', record)">
          <template #icon><n-icon><CheckmarkCircleOutline /></n-icon></template>
          立即复盘
        </n-button>
      </div>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button type="error" secondary :disabled="!record" @click="handleDelete">
          删除
        </n-button>
        <n-button @click="$emit('update:show', false)">关闭</n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { NModal, NTag, NButton, NSpace, NAlert, NIcon } from 'naive-ui'
import { 
  CalendarOutline, 
  TimeOutline, 
  HourglassOutline,
  AnalyticsOutline,
  CheckmarkCircleOutline
} from '@vicons/ionicons5'
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
  (e: 'delete', record: JournalRecord): void
}>()

const router = useRouter()

// Navigate to home to re-analyze
const goToAnalyze = () => {
  if (props.record) {
    emit('update:show', false)
    router.push({ path: '/', query: { code: props.record.ts_code } })
  }
}

const handleDelete = () => {
  if (!props.record) return
  emit('delete', props.record)
}

// Helpers
const candidateTagType = (candidate: string) => {
  const map: Record<string, 'success' | 'info' | 'warning'> = { 
    A: 'success', B: 'info', C: 'warning' 
  }
  return map[candidate] || 'info'
}

const selectedCandidateDescription = (record: JournalRecord) => {
  const fromSnapshot = record.constraints?.selected_candidate_description
  if (typeof fromSnapshot === 'string' && fromSnapshot.trim()) {
    return fromSnapshot
  }

  const candidates = record.constraints?.candidates
  if (Array.isArray(candidates)) {
    const matched = candidates.find((candidate: any) => {
      return String(candidate?.option_id || candidate?.id || '').toUpperCase() === record.candidate
    })
    if (typeof matched?.description === 'string' && matched.description.trim()) {
      return matched.description
    }
  }

  if (candidates && typeof candidates === 'object') {
    const description = candidates[record.candidate]
    if (typeof description === 'string' && description.trim()) {
      return description
    }
  }

  return ''
}

const candidateDescription = (record: JournalRecord) => {
  const description = selectedCandidateDescription(record)
  return description ? `候选 ${record.candidate}` : `候选 ${record.candidate}`
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
    active: '验证中', 
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
  border-radius: 12px;
}

.stock-header {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.stock-code {
  font-size: 28px;
  font-weight: 700;
  color: var(--n-text-color);
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin-bottom: 14px;
  color: var(--n-text-color);
}

.judgment-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.judgment-choice {
  display: flex;
  align-items: center;
  gap: 12px;
}

.choice-label {
  color: var(--n-text-color-3);
  font-size: 14px;
}

.sub-title {
  font-size: 13px;
  color: var(--n-text-color-2);
  margin-bottom: 8px;
  font-weight: 500;
}

.premises-list {
  margin: 0;
  padding-left: 20px;
}

.premises-list li {
  margin-bottom: 6px;
  color: var(--n-text-color);
  font-size: 14px;
  line-height: 1.5;
}

.condition-content {
  padding: 10px 12px;
  background: var(--n-color);
  border-radius: 8px;
  color: var(--n-text-color);
  font-size: 14px;
  line-height: 1.6;
}

.timeline-grid {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  background: var(--n-color);
  border-radius: 8px;
}

.timeline-item .label {
  color: var(--n-text-color-3);
  font-size: 13px;
  min-width: 80px;
}

.timeline-item .value {
  font-size: 14px;
  font-weight: 500;
}

.timeline-item.highlight {
  background: rgba(24, 160, 88, 0.1);
  border: 1px solid rgba(24, 160, 88, 0.2);
}

.highlight-text {
  color: #18a058;
  font-weight: 600;
}

.review-info {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.outcome-row {
  display: flex;
  align-items: center;
  gap: 16px;
}

.review-time {
  font-size: 13px;
  color: var(--n-text-color-3);
}

.notes-label {
  font-size: 13px;
  color: var(--n-text-color-3);
  margin-bottom: 6px;
}

.notes-content {
  font-size: 14px;
  line-height: 1.6;
  padding: 12px;
  background: var(--n-color);
  border-radius: 8px;
  white-space: pre-wrap;
}

.action-guidance {
  background: transparent;
  padding: 0;
}

.action-guidance .section-title {
  margin-bottom: 12px;
}

.action-section {
  display: flex;
  gap: 12px;
  margin-top: 20px;
  flex-wrap: wrap;
}

@media (max-width: 480px) {
  .section-header {
    flex-direction: column;
    align-items: flex-start;
  }
  
  .stock-code {
    font-size: 24px;
  }
  
  .action-section {
    flex-direction: column;
  }
  
  .action-section .n-button {
    width: 100%;
  }
}
</style>
