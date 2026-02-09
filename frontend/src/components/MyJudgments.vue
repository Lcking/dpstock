<template>
  <div class="my-judgments-container">
    <n-card title="我的判断">
      <template #header-extra>
        <n-space align="center">
          <!-- Anchor Status -->
          <AnchorStatus @show-bind="showBindDialog = true" />
          
          <n-divider vertical />
          
          <n-text depth="3">共 {{ judgments.length }} 条</n-text>
          <n-button size="small" @click="loadJudgments">
            <template #icon>
              <n-icon><RefreshIcon /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>

      <!-- Main Content -->
      <n-spin :show="loading">
        <n-space vertical size="large">
          <!-- Status Filter -->
          <n-space align="center">
            <n-text>筛选:</n-text>
            <n-select
              v-model:value="statusFilter"
              :options="statusFilterOptions"
              style="width: 150px;"
              size="small"
            />
          </n-space>

          <!-- Judgment Cards -->
          <template v-if="filteredJudgments.length > 0">
            <n-grid :cols="1" :x-gap="16" :y-gap="16">
              <n-grid-item v-for="judgment in filteredJudgments" :key="judgment.judgment_id">
                <JudgmentCard :judgment="judgment as any" @view="handleViewDetail" />
              </n-grid-item>
            </n-grid>
          </template>

          <!-- Empty State -->
          <template v-else-if="!loading">
            <n-empty description="暂无判断记录" size="large">
              <template #icon>
                <n-icon><DocumentIcon /></n-icon>
              </template>
              <template #extra>
                <n-button @click="$router.push('/')">
                  去分析页面
                </n-button>
              </template>
            </n-empty>
          </template>
        </n-space>
      </n-spin>
    </n-card>

    <!-- Judgment Detail Modal - Simplified for V1 -->
    <n-modal
      v-model:show="showDetailModal"
      preset="card"
      title="判断详情"
      style="width: 90%; max-width: 800px;"
      :bordered="false"
      size="huge"
    >
      <template v-if="selectedJudgment">
        <!-- 1. Judgment Premise -->
        <n-descriptions bordered :column="1">
          <n-descriptions-item label="判断前提">
            {{ selectedJudgment.structure_premise || '无判断前提' }}
          </n-descriptions-item>
        </n-descriptions>

        <!-- 2. Structure Snapshot (Read-only) -->
        <n-divider>保存时的结构</n-divider>
        <n-descriptions bordered :column="2">
          <n-descriptions-item label="股票代码">
            {{ selectedJudgment.stock_code }}
          </n-descriptions-item>
          <n-descriptions-item label="快照时间">
            {{ formatDateTime(selectedJudgment.snapshot_time) }}
          </n-descriptions-item>
          <n-descriptions-item label="结构类型">
            {{ getStructureTypeName(selectedJudgment.structure_type) }}
          </n-descriptions-item>
          <n-descriptions-item label="MA200位置">
            {{ getMA200PositionName(selectedJudgment.ma200_position) }}
          </n-descriptions-item>
          <n-descriptions-item label="阶段">
            {{ getPhaseName(selectedJudgment.phase) }}
          </n-descriptions-item>
          <n-descriptions-item label="验证周期">
            {{ selectedJudgment.verification_period || 1 }} 天
          </n-descriptions-item>
        </n-descriptions>

        <!-- 3. Verification Result -->
        <n-divider>验证结果</n-divider>
        <n-alert 
          :type="getVerificationAlertType(selectedJudgment.verification_status)" 
          :title="getVerificationStatusText(selectedJudgment.verification_status)"
        >
          {{ selectedJudgment.verification_reason || '等待验证' }}
        </n-alert>

        <!-- 4. Verification Records (if exists) -->
        <template v-if="selectedJudgment.latest_check">
          <n-divider>验证记录</n-divider>
          <n-space vertical>
            <n-text depth="3" style="font-size: 12px;">
              检查时间: {{ formatDateTime(selectedJudgment.latest_check.verification_time || selectedJudgment.last_checked_at) }}
            </n-text>
            <n-ul v-if="selectedJudgment.latest_check.reasons && selectedJudgment.latest_check.reasons.length > 0">
              <n-li v-for="(reason, idx) in selectedJudgment.latest_check.reasons" :key="idx">
                {{ reason }}
              </n-li>
            </n-ul>
          </n-space>
        </template>

        <!-- Delete Button -->
        <n-divider />
        <n-space justify="end">
          <n-popconfirm
            @positive-click="handleDelete(selectedJudgment.judgment_id)"
            positive-text="确认删除"
            negative-text="取消"
          >
            <template #trigger>
              <n-button type="error" secondary>
                删除此判断
              </n-button>
            </template>
            确定要删除这条判断吗?此操作不可撤销。
          </n-popconfirm>
        </n-space>
      </template>
    </n-modal>
    
    <!-- Anchor Bind Dialog -->
    <AnchorBindDialog
      v-model:show="showBindDialog"
      @bind-success="handleBindSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue';
import JudgmentCard from '@/components/JudgmentCard.vue';
import AnchorStatus from '@/components/AnchorStatus.vue';
import AnchorBindDialog from '@/components/AnchorBindDialog.vue';
import {
  NCard,
  NButton,
  NSpace,
  NText,
  NIcon,
  NEmpty,
  NDivider,
  NPopconfirm,
  NModal,
  NDescriptions,
  NDescriptionsItem,
  NGrid,
  NGridItem,
  NSpin,
  NSelect,
  NAlert,
  NUl,
  NLi,
  useMessage
} from 'naive-ui';
import {
  RefreshOutline as RefreshIcon,
  DocumentTextOutline as DocumentIcon
} from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import type { Judgment } from '@/types/judgment';

const message = useMessage();

// State
const loading = ref(false);
const judgments = ref<Judgment[]>([]);
const showDetailModal = ref(false);
const selectedJudgment = ref<Judgment | null>(null);
const showBindDialog = ref(false);

// Status filter
const statusFilter = ref<string>('all');
const statusFilterOptions = [
  { label: '全部', value: 'all' },
  { label: '等待验证', value: 'WAITING' },
  { label: '前提成立', value: 'CONFIRMED' },
  { label: '前提失效', value: 'BROKEN' },
  { label: '周期结束', value: 'CHECKED' }
];

// Filtered judgments
const filteredJudgments = computed(() => {
  if (statusFilter.value === 'all') {
    return judgments.value;
  }
  return judgments.value.filter(j => 
    (j as any).verification_status === statusFilter.value
  );
});

// Load judgments
async function loadJudgments() {
  loading.value = true;
  try {
    const response = await apiService.getMyJudgments(50);
    judgments.value = response.judgments || [];
    console.log('[MyJudgments] Loaded judgments:', judgments.value.length);
  } catch (error) {
    console.error('[MyJudgments] Load failed:', error);
    message.error('加载判断列表失败');
  } finally {
    loading.value = false;
  }
}

// View detail
function handleViewDetail(judgmentId: string) {
  const judgment = judgments.value.find(j => j.judgment_id === judgmentId);
  if (judgment) {
    selectedJudgment.value = judgment;
    showDetailModal.value = true;
  }
}

// Delete judgment
async function handleDelete(judgmentId: string) {
  try {
    await apiService.deleteJudgment(judgmentId);
    message.success('删除成功');
    
    // Remove from list
    judgments.value = judgments.value.filter(j => j.judgment_id !== judgmentId);
    
    // Close modal
    showDetailModal.value = false;
    selectedJudgment.value = null;
  } catch (error: any) {
    console.error('[MyJudgments] Delete failed:', error);
    
    if (error.response?.status === 403) {
      message.error('无权删除此判断');
    } else if (error.response?.status === 404) {
      message.error('判断不存在');
    } else {
      message.error('删除失败');
    }
  }
}

// Handle bind success
function handleBindSuccess(data: any) {
  console.log('[MyJudgments] Bind success:', data);
  message.success('绑定成功! 正在重新加载判断列表\u2026');
  
  // Reload judgments after binding
  setTimeout(() => {
    loadJudgments();
  }, 500);
}

// Helper functions
function getStructureTypeName(type: string): string {
  const map: Record<string, string> = {
    'consolidation': '盘整',
    'uptrend': '上升',
    'downtrend': '下降'
  };
  return map[type] || type;
}

function getMA200PositionName(position: string): string {
  const map: Record<string, string> = {
    'above': '上方',
    'below': '下方',
    'near': '接近',
    'no_data': '无数据'
  };
  return map[position] || position;
}

function getPhaseName(phase: string): string {
  const map: Record<string, string> = {
    'early': '早期',
    'middle': '中期',
    'late': '后期',
    'unclear': '不明'
  };
  return map[phase] || phase;
}

function getVerificationStatusText(status?: string): string {
  const map: Record<string, string> = {
    'WAITING': '等待验证',
    'CHECKED': '周期结束',
    'CONFIRMED': '前提成立',
    'BROKEN': '前提失效'
  };
  return map[status || 'WAITING'] || '未知状态';
}

function getVerificationAlertType(status?: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'warning' | 'error'> = {
    'WAITING': 'default',
    'CHECKED': 'info',
    'CONFIRMED': 'success',
    'BROKEN': 'error'
  };
  return map[status || 'WAITING'] || 'default';
}

function formatDateTime(dateStr?: string): string {
  if (!dateStr) return '--';
  
  try {
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch {
    return dateStr;
  }
}

// Lifecycle
onMounted(() => {
  loadJudgments();
});
</script>

<style scoped>
.my-judgments-container {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}
</style>
