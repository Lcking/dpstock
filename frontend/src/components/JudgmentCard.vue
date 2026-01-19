<template>
  <n-card 
    :class="['judgment-card', `status-${judgment.verification_status || 'WAITING'}`]"
    hoverable
    size="small"
  >
    <!-- 1. 紧凑头部: 标的 + 状态 -->
    <template #header>
      <n-space vertical :size="2">
        <n-space align="center" :size="8">
          <n-text strong style="font-size: 15px;">{{ getStockDisplay(judgment) }}</n-text>
          <n-tag :bordered="false" round size="tiny" type="info">
            {{ judgment.verification_period || 1 }}日
          </n-tag>
        </n-space>
        <n-space align="center" :size="4">
          <n-icon :size="14" :color="getStatusColor(judgment.verification_status || 'WAITING')">
            <component :is="getStatusIcon(judgment.verification_status || 'WAITING')" />
          </n-icon>
          <n-text :style="{ color: getStatusColor(judgment.verification_status || 'WAITING'), fontSize: '12px' }">
            {{ getStatusText(judgment.verification_status || 'WAITING') }}
          </n-text>
        </n-space>
      </n-space>
    </template>

    <template #header-extra>
      <n-text depth="3" style="font-size: 11px">
        {{ formatSnapshotTime(judgment.snapshot_time) }}
      </n-text>
    </template>
    
    <!-- 2. 判断前提 (压缩高度) -->
    <div class="premise-section-compact">
      <n-text depth="2" class="premise-text-compact">
        {{ judgment.structure_premise || '无判断前提' }}
      </n-text>
    </div>
    
    <!-- 3. 验证详情与关键位 (横向合并) -->
    <div class="detail-row-compact" v-if="judgment.verification_reason">
      <n-text depth="3" class="label">结果:</n-text>
      <n-text :type="getStatusType(judgment.verification_status || 'WAITING')" class="value small-reason">
        {{ judgment.verification_reason }}
      </n-text>
    </div>
    
    <div v-if="hasKeyLevels(judgment)" class="key-levels-compact">
      <n-space :size="[4, 4]">
        <n-tag 
          v-for="(level, idx) in getKeyLevels(judgment)" 
          :key="idx" 
          size="tiny" 
          :bordered="false"
          round
          class="compact-level-tag"
        >
          {{ level.label.slice(0,1) }}: {{ level.price }}
        </n-tag>
      </n-space>
    </div>
    
    <!-- 4. 底部操作栏 (紧凑) -->
    <template #action>
      <div class="card-action-compact">
        <n-text depth="3" class="check-time-inline">
          检查: {{ formatCheckTime(judgment.last_checked_at) }}
        </n-text>
        <n-button 
          text
          size="tiny" 
          type="primary" 
          @click="$emit('view', judgment.judgment_id)"
        >
          详情 >
        </n-button>
      </div>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { 
  NCard, NTag, NText, NSpace, NButton, NIcon 
} from 'naive-ui';
import { 
  TimeOutline, 
  CheckmarkCircleOutline, 
  CloseCircleOutline, 
  InformationCircleOutline,
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

function getStatusIcon(status: string) {
  const map: any = {
    'WAITING': TimeOutline,
    'CHECKED': InformationCircleOutline,
    'CONFIRMED': CheckmarkCircleOutline,
    'BROKEN': CloseCircleOutline
  };
  return map[status] || InformationCircleOutline;
}

function getStatusColor(status: string): string {
  const map: Record<string, string> = {
    'WAITING': '#8c8c8c',
    'CHECKED': '#1890ff',
    'CONFIRMED': '#52c41a',
    'BROKEN': '#f5222d'
  };
  return map[status] || '#8c8c8c';
}

function getStatusType(status: string): 'default' | 'info' | 'success' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'error'> = {
    'WAITING': 'default',
    'CHECKED': 'info',
    'CONFIRMED': 'success',
    'BROKEN': 'error'
  };
  return map[status] || 'default';
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    'WAITING': '等待',
    'CHECKED': '已结束',
    'CONFIRMED': '成立',
    'BROKEN': '失效'
  };
  return map[status] || '未知';
}

function getStockDisplay(judgment: Judgment): string {
  return judgment.stock_name ? `${judgment.stock_name} (${judgment.stock_code})` : judgment.stock_code;
}

function hasKeyLevels(judgment: Judgment): boolean {
  return !!(judgment.key_levels_snapshot && 
    Array.isArray(judgment.key_levels_snapshot) && 
    judgment.key_levels_snapshot.length > 0);
}

function getKeyLevels(judgment: Judgment): Array<{ label: string; price: string }> {
  if (!hasKeyLevels(judgment)) return [];
  return judgment.key_levels_snapshot.map((level: any) => ({
    label: level.label || level.type || '位',
    price: typeof level.price === 'number' ? level.price.toFixed(1) : level.price
  }));
}

function formatSnapshotTime(time?: string): string {
  if (!time) return '';
  try {
    const dateStr = (time.endsWith('Z') || time.includes('+')) ? time : time + 'Z';
    const date = new Date(dateStr);
    return date.toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return ''; }
}

function formatCheckTime(time?: string): string {
  if (!time) return '--:--';
  try {
    const dateStr = (time.endsWith('Z') || time.includes('+')) ? time : time + 'Z';
    const date = new Date(dateStr);
    return date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return '--:--'; }
}
</script>

<style scoped>
.judgment-card {
  transition: all 0.2s ease;
  border-radius: 8px !important;
  border: 1px solid #f0f0f0;
}

.judgment-card:hover {
  border-color: #1890ff40;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
}

/* 状态彩条 - 极致窄条 */
.status-WAITING { border-left: 3px solid #bfbfbf; }
.status-CONFIRMED { border-left: 3px solid #52c41a; }
.status-BROKEN { border-left: 3px solid #f5222d; }
.status-CHECKED { border-left: 3px solid #1890ff; }

.premise-section-compact {
  margin: 4px 0 8px 0;
  padding: 6px 8px;
  background: #fcfcfc;
  border-radius: 4px;
}

.premise-text-compact {
  font-size: 13px;
  line-height: 1.4;
  color: #595959;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.detail-row-compact {
  display: flex;
  gap: 4px;
  align-items: center;
  margin-bottom: 6px;
  font-size: 12px;
}

.label { flex-shrink: 0; opacity: 0.6; }

.small-reason {
  font-size: 12px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.key-levels-compact {
  margin-top: 4px;
}

.compact-level-tag {
  background-color: #f5f5f5;
  color: #8c8c8c;
  font-size: 10px;
}

.card-action-compact {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 4px 0;
}

.check-time-inline {
  font-size: 10px;
  opacity: 0.7;
}

:deep(.n-card-header) {
  padding: 10px 12px 6px 12px !important;
}

:deep(.n-card__content) {
  padding: 0 12px 8px 12px !important;
}

:deep(.n-card__action) {
  padding: 4px 12px !important;
  background-color: #fafafa60;
}
</style>
