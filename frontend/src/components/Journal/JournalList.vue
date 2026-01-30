<template>
  <div class="journal-list">
    <!-- Header -->
    <div class="journal-header">
      <div class="header-title-row">
        <h2>判断日记</h2>
        <AnchorStatus @show-bind="showBindDialog = true" />
      </div>
      <div class="header-filters">
        <n-space>
          <n-select
            v-model:value="statusFilter"
            :options="statusOptions"
            size="small"
            style="width: 140px"
            @update:value="loadRecords"
          />
          <n-checkbox
            :checked="allSelected"
            :disabled="records.length === 0"
            @update:checked="toggleSelectAll"
          >
            全选本页
          </n-checkbox>
          <n-button
            size="small"
            type="error"
            :disabled="selectedIds.size === 0"
            @click="confirmBatchDelete"
          >
            批量删除
          </n-button>
        </n-space>
      </div>
    </div>

    <!-- Due Notification -->
    <div v-if="dueCount > 0" class="due-notification">
      <n-alert type="warning" :show-icon="true">
        <n-space justify="space-between" align="center">
          <span>你有 {{ dueCount }} 条日记已到期待复盘</span>
          <n-button size="small" @click="statusFilter = 'due'; loadRecords()">
            查看
          </n-button>
        </n-space>
      </n-alert>
    </div>

    <!-- Loading: Skeletons -->
    <div v-if="loading" class="records-list">
      <div v-for="i in 3" :key="i" class="record-card skeleton-card">
        <div class="record-header">
          <n-skeleton text style="width: 120px" />
          <n-skeleton text style="width: 60px" />
        </div>
        <div class="record-body">
          <n-space vertical>
            <n-skeleton text :repeat="2" />
            <n-skeleton text style="width: 80%" />
          </n-space>
        </div>
        <div class="record-footer">
          <n-skeleton text style="width: 80px" />
        </div>
      </div>
    </div>

    <!-- Records List -->
    <div v-else-if="records.length > 0" class="records-list">
      <div 
        v-for="record in records" 
        :key="record.id"
        class="record-card"
        :class="`status-${record.status}`"
        @click="handleRecordClick(record)"
      >
        <!-- Header -->
        <div class="record-header">
          <div class="stock-info">
            <n-checkbox
              :checked="selectedIds.has(record.id)"
              @update:checked="(checked) => toggleSelected(record.id, checked)"
              @click.stop
            />
            <span class="ts-code">{{ record.ts_code }}</span>
            <n-tag :type="candidateTagType(record.candidate)" size="small">
              候选 {{ record.candidate }}
            </n-tag>
          </div>
          <n-tag :type="statusTagType(record.status)" size="small">
            {{ statusLabel(record.status) }}
          </n-tag>
        </div>

        <!-- Body -->
        <div class="record-body">
          <div class="record-meta">
            <span>创建于 {{ formatDate(record.created_at) }}</span>
            <span v-if="record.validation_date">
              验证期至 {{ formatDate(record.validation_date) }}
            </span>
            <span v-if="record.days_left !== null && record.status === 'active'">
              剩余 {{ record.days_left }} 天
            </span>
          </div>

          <!-- Review Result -->
          <div v-if="record.review && record.status === 'reviewed'" class="review-result">
            <n-tag :type="outcomeTagType(record.review.outcome)" size="small">
              {{ outcomeLabel(record.review.outcome) }}
            </n-tag>
            <span class="review-time">
              复盘于 {{ formatDate(record.review.reviewed_at) }}
            </span>
          </div>
        </div>

        <!-- Footer Actions -->
        <div class="record-footer">
          <n-button 
            v-if="record.status === 'due'"
            type="primary"
            size="small"
            @click.stop="showReviewDialog(record)"
          >
            立即复盘
          </n-button>
          <n-button 
            v-else
            text
            size="small"
            @click.stop="handleRecordClick(record)"
          >
            查看详情
          </n-button>
          <n-button
            text
            type="error"
            size="small"
            @click.stop="confirmDelete(record)"
          >
            删除
          </n-button>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div v-else class="empty-state-container">
      <empty-state
        type="journal"
        title="还没有判断日记"
        description="记录你的判断，验证你的逻辑，提升交易水平"
      >
        <n-button type="primary" @click="$router.push('/')">
          去分析
        </n-button>
      </empty-state>
    </div>

    <!-- Detail Dialog -->
    <journal-detail-dialog
      v-model:show="showDetail"
      :record="selectedRecord"
      @review="handleOpenReview"
      @delete="confirmDelete"
    />

    <!-- Review Dialog -->
    <journal-review-dialog
      v-model:show="showReview"
      :record="selectedRecord"
      @reviewed="handleReviewed"
    />

    <!-- Anchor Bind Dialog -->
    <AnchorBindDialog
      v-model:show="showBindDialog"
      @bind-success="handleBindSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { apiService } from '@/services/api'
import { 
  NButton, NSpace, NSelect, NTag, NAlert, NSkeleton, NCheckbox, useDialog, useMessage 
} from 'naive-ui'
import JournalReviewDialog from './JournalReviewDialog.vue'
import JournalDetailDialog from './JournalDetailDialog.vue'
import AnchorStatus from '../AnchorStatus.vue'
import AnchorBindDialog from '../AnchorBindDialog.vue'
import EmptyState from '../common/EmptyState.vue'
import type { JournalRecord } from '@/types/journal'

const message = useMessage()
const dialog = useDialog()

// State
const loading = ref(false)
const records = ref<JournalRecord[]>([])
const dueCount = ref(0)
const statusFilter = ref<string>('')
const showReview = ref(false)
const showDetail = ref(false)
const showBindDialog = ref(false)
const selectedRecord = ref<JournalRecord | null>(null)
const selectedIds = ref<Set<string>>(new Set())
const allSelected = computed(() => {
  if (records.value.length === 0) return false
  return records.value.every(record => selectedIds.value.has(record.id))
})

// Options
const statusOptions = [
  { label: '全部', value: '' },
  { label: '活跃中', value: 'active' },
  { label: '待复盘', value: 'due' },
  { label: '已复盘', value: 'reviewed' }
]

// Load records
const loadRecords = async () => {
  loading.value = true
  try {
    const data = await apiService.getJournalRecords({
      status: statusFilter.value || undefined
    })
    records.value = data.records || []
    selectedIds.value = new Set()
  } catch (error) {
    console.error('Load records error:', error)
    message.error('加载失败')
  } finally {
    loading.value = false
  }
}

// Load due count
const loadDueCount = async () => {
  try {
    dueCount.value = await apiService.getDueCount()
  } catch (error) {
    console.error('Load due count error:', error)
  }
}

// Record click - show detail dialog
const handleRecordClick = (record: JournalRecord) => {
  selectedRecord.value = record
  showDetail.value = true
}

// Show review dialog
const showReviewDialog = (record: JournalRecord) => {
  selectedRecord.value = record
  showReview.value = true
}

// Open review from detail dialog
const handleOpenReview = (record: JournalRecord) => {
  showDetail.value = false
  selectedRecord.value = record
  showReview.value = true
}

// After reviewed
const handleReviewed = () => {
  showReview.value = false
  loadRecords()
  loadDueCount()
}

const toggleSelected = (id: string, checked: boolean) => {
  const next = new Set(selectedIds.value)
  if (checked) {
    next.add(id)
  } else {
    next.delete(id)
  }
  selectedIds.value = next
}

const toggleSelectAll = (checked: boolean) => {
  if (!checked) {
    selectedIds.value = new Set()
    return
  }
  selectedIds.value = new Set(records.value.map(record => record.id))
}

const confirmDelete = (record: JournalRecord) => {
  if (!record?.id) return
  dialog.warning({
    title: '确认删除',
    content: `确定要删除 ${record.ts_code} 的判断记录吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await handleDeleteRecords([record.id])
    }
  })
}

const confirmBatchDelete = () => {
  if (selectedIds.value.size === 0) return
  dialog.warning({
    title: '确认批量删除',
    content: `确定要删除选中的 ${selectedIds.value.size} 条记录吗？此操作不可恢复。`,
    positiveText: '删除',
    negativeText: '取消',
    onPositiveClick: async () => {
      await handleDeleteRecords(Array.from(selectedIds.value))
    }
  })
}

const handleDeleteRecords = async (ids: string[]) => {
  try {
    for (const id of ids) {
      await apiService.deleteJournalRecord(id)
    }
    message.success('删除成功')
    showDetail.value = false
    selectedRecord.value = null
    loadRecords()
    loadDueCount()
  } catch (error) {
    console.error('Delete record error:', error)
    message.error('删除失败')
  }
}

// After bind success
const handleBindSuccess = (data: any) => {
  message.success(`已绑定邮箱，迁移了 ${data.migrated_count || 0} 条记录`)
  loadRecords()
}

// Tag types
const candidateTagType = (candidate: string) => {
  const map = { A: 'success', B: 'info', C: 'warning' }
  return map[candidate as 'A' | 'B' | 'C'] as 'success' | 'info' | 'warning'
}

const statusTagType = (status: string) => {
  const map = { 
    active: 'info', 
    due: 'warning', 
    reviewed: 'success',
    archived: 'default'
  }
  return map[status as keyof typeof map] as 'info' | 'warning' | 'success' | 'default'
}

const statusLabel = (status: string) => {
  const map = { 
    active: '活跃', 
    due: '待复盘', 
    reviewed: '已复盘',
    archived: '已归档'
  }
  return map[status as keyof typeof map] || status
}

const outcomeTagType = (outcome: string) => {
  const map = { 
    supported: 'success', 
    falsified: 'error', 
    uncertain: 'warning' 
  }
  return map[outcome as keyof typeof map] as 'success' | 'error' | 'warning'
}

const outcomeLabel = (outcome: string) => {
  const map = {
    supported: '前提得到支持',
    falsified: '前提被证伪',
    uncertain: '结果不确定'
  }
  return map[outcome as keyof typeof map] || outcome
}

// Format date
const formatDate = (dateStr: string) => {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN', { 
    year: 'numeric', 
    month: '2-digit', 
    day: '2-digit' 
  })
}

onMounted(() => {
  loadRecords()
  loadDueCount()
})
</script>

<style scoped>
.journal-list {
  padding: 20px;
  padding-top: 40px;
  max-width: 1200px;
  margin: 0 auto;
}

.journal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  flex-wrap: wrap;
  gap: 12px;
}

.header-title-row {
  display: flex;
  align-items: center;
  gap: 16px;
  flex-wrap: wrap;
}

.journal-header h2 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
}

.due-notification {
  margin-bottom: 20px;
}

.loading-container {
  display: flex;
  justify-content: center;
  padding: 60px 0;
}

.records-list {
  display: grid;
  gap: 16px;
}

.record-card {
  padding: 16px;
  background: var(--n-color);
  border: 1px solid var(--n-border-color);
  border-left: 4px solid var(--n-border-color);
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.record-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.record-card.status-active {
  border-left-color: #2080f0;
}

.record-card.status-due {
  border-left-color: #f0a020;
}

.record-card.status-reviewed {
  border-left-color: #18a058;
}

.record-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.stock-info {
  display: flex;
  align-items: center;
  gap: 8px;
}

.ts-code {
  font-size: 16px;
  font-weight: 600;
}

.record-body {
  margin-bottom: 12px;
}

.record-meta {
  display: flex;
  gap: 16px;
  font-size: 13px;
  color: var(--n-text-color-3);
  margin-bottom: 8px;
}

.review-result {
  display: flex;
  align-items: center;
  gap: 12px;
}

.review-time {
  font-size: 13px;
  color: var(--n-text-color-3);
}

.record-footer {
  display: flex;
  gap: 8px;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}
</style>
