<template>
  <n-card 
    :class="['judgment-card', `status-${judgment.verification_status || 'WAITING'}`]"
    hoverable
  >
    <!-- 1. 状态头部: 图标 + 状态 + 周期 -->
    <template #header>
      <n-space align="center" justify="space-between" style="width: 100%">
        <n-space align="center" :size="8">
          <n-icon :size="20" :color="getStatusColor(judgment.verification_status || 'WAITING')">
            <component :is="getStatusIcon(judgment.verification_status || 'WAITING')" />
          </n-icon>
          <n-text strong :style="{ color: getStatusColor(judgment.verification_status || 'WAITING'), fontSize: '16px' }">
            {{ getStatusText(judgment.verification_status || 'WAITING') }}
          </n-text>
        </n-space>
        
        <n-tag :bordered="false" round size="small" type="info">
          验证周期: {{ judgment.verification_period || 1 }}日
        </n-tag>
      </n-space>
    </template>

    <template #header-extra>
      <n-text depth="3" style="font-size: 12px">
        {{ formatSnapshotTime(judgment.snapshot_time) }}
      </n-text>
    </template>
    
    <!-- 2. 判断前提 (核心内容) -->
    <div class="premise-section">
      <div class="premise-quote">
        <n-icon :size="16" color="#bfbfbf" style="margin-right: 4px"><QuoteIcon /></n-icon>
        <n-text strong class="premise-text">
          {{ judgment.structure_premise || '无判断前提' }}
        </n-text>
      </div>
    </div>
    
    <!-- 3. 股票及验证详情 -->
    <n-divider style="margin: 12px 0" />
    
    <div class="detail-grid">
      <div class="detail-item">
        <n-text depth="3" class="label">标的</n-text>
        <n-text strong class="value">{{ getStockDisplay(judgment) }}</n-text>
      </div>
      
      <div class="detail-item" v-if="judgment.verification_reason">
        <n-text depth="3" class="label">当前结果</n-text>
        <n-text :type="getStatusType(judgment.verification_status || 'WAITING')" class="value reason-text">
          {{ judgment.verification_reason }}
        </n-text>
      </div>
    </div>
    
    <!-- 4. 关键位 (可选) -->
    <div v-if="hasKeyLevels(judgment)" class="key-levels-section">
      <n-space size="small">
        <n-tag 
          v-for="(level, idx) in getKeyLevels(judgment)" 
          :key="idx" 
          size="small" 
          :bordered="false"
          round
          class="level-tag"
        >
          <template #icon>
            <n-icon><LayersOutline /></n-icon>
          </template>
          {{ level.label }}: {{ level.price }}
        </n-tag>
      </n-space>
    </div>
    
    <!-- 6. 操作按钮 -->
    <template #action>
      <n-space justify="space-between" align="center">
        <n-text depth="3" style="font-size: 11px;">
          最近检查: {{ formatCheckTime(judgment.last_checked_at) }}
        </n-text>
        <n-button 
          secondary 
          strong 
          size="small" 
          round
          type="primary" 
          @click="$emit('view', judgment.judgment_id)"
        >
          查看详情
        </n-button>
      </n-space>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { 
  NCard, NTag, NText, NSpace, NButton, NIcon, NDivider 
} from 'naive-ui';
import { 
  TimeOutline, 
  CheckmarkCircleOutline, 
  CloseCircleOutline, 
  InformationCircleOutline,
  LayersOutline,
  ChatbubbleOutline as QuoteIcon
} from '@vicons/ionicons5';

interface Judgment {
  judgment_id: string;
  stock_code: string;
  stock_name?: string;
  structure_premise: string;
  verification_period: number;
  verification_status?: string;
  verification_reason?: string;
  last_checked_at?: string;
  snapshot_time?: string;
  key_levels_snapshot?: any;
  structure_type?: string;
}

defineProps<{
  judgment: Judgment;
}>();

defineEmits(['view']);

// 状态图标映射
function getStatusIcon(status: string) {
  const map: any = {
    'WAITING': TimeOutline,
    'CHECKED': InformationCircleOutline,
    'CONFIRMED': CheckmarkCircleOutline,
    'BROKEN': CloseCircleOutline
  };
  return map[status] || InformationCircleOutline;
}

// 状态颜色映射
function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    'WAITING': '#8c8c8c',
    'CHECKED': '#1890ff',
    'CONFIRMED': '#52c41a',
    'BROKEN': '#f5222d'
  };
  return map[status] || '#8c8c8c';
}

// 状态类型映射 (Naive UI 专用)
function getStatusType(status: string): 'default' | 'info' | 'success' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'error'> = {
    'WAITING': 'default',
    'CHECKED': 'info',
    'CONFIRMED': 'success',
    'BROKEN': 'error'
  };
  return map[status] || 'default';
}

// 状态文案
function getStatusText(status: string): string {
  const map: Record<string, string> = {
    'WAITING': '等待验证',
    'CHECKED': '周期结束',
    'CONFIRMED': '前提成立',
    'BROKEN': '前提失效'
  };
  return map[status] || '未知状态';
}

function getStockDisplay(judgment: Judgment): string {
  if (judgment.stock_name) {
    return `${judgment.stock_name} (${judgment.stock_code})`;
  }
  return judgment.stock_code;
}

function hasKeyLevels(judgment: Judgment): boolean {
  return !!(judgment.key_levels_snapshot && 
    Array.isArray(judgment.key_levels_snapshot) && 
    judgment.key_levels_snapshot.length > 0);
}

function getKeyLevels(judgment: Judgment): Array<{ label: string; price: string }> {
  if (!hasKeyLevels(judgment)) return [];
  
  return judgment.key_levels_snapshot.map((level: any) => ({
    label: level.label || level.type || '关键位',
    price: typeof level.price === 'number' ? level.price.toFixed(2) : level.price
  }));
}

function formatSnapshotTime(time?: string): string {
  if (!time) return '';
  try {
    const date = new Date(time);
    return date.toLocaleDateString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
  } catch {
    return '';
  }
}

function formatCheckTime(time?: string): string {
  if (!time) return '未检查';
  try {
    const date = new Date(time);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
  } catch {
    return '未检查';
  }
}
</script>

<style scoped>
.judgment-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  border-radius: 12px !important;
  overflow: hidden;
  border: 1px solid #f0f0f0;
}

.judgment-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
  border-color: #e6f7ff;
}

/* 状态侧边指示线 */
.status-WAITING { border-top: 4px solid #8c8c8c; }
.status-CONFIRMED { border-top: 4px solid #52c41a; }
.status-BROKEN { border-top: 4px solid #f5222d; }
.status-CHECKED { border-top: 4px solid #1890ff; }

.premise-section {
  margin: 8px 0;
}

.premise-quote {
  padding: 12px;
  background: #f9f9f9;
  border-radius: 8px;
  display: flex;
  align-items: flex-start;
}

.premise-text {
  font-size: 15px;
  line-height: 1.6;
  color: #1f1f1f;
  flex: 1;
}

.detail-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-bottom: 12px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
}

.detail-item .label {
  font-size: 12px;
  flex-shrink: 0;
}

.detail-item .value {
  font-size: 14px;
  text-align: right;
  word-break: break-all;
}

.reason-text {
  font-style: italic;
  font-size: 13px !important;
}

.key-levels-section {
  margin: 12px 0;
}

.level-tag {
  background-color: #f0f5ff;
}

:deep(.n-card-header) {
  padding-bottom: 8px !important;
}

:deep(.n-card__action) {
  background-color: #fafafa;
  padding: 10px 16px !important;
}
</style>
