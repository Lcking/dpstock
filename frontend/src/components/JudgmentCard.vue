<template>
  <n-card 
    :class="['judgment-card', `status-${judgment.verification_status || 'WAITING'}`]"
    hoverable
  >
    <!-- 1. 状态标签 + 验证周期 (最突出) -->
    <template #header>
      <n-space align="center">
        <n-tag 
          :type="getStatusType(judgment.verification_status || 'WAITING')" 
          size="large" 
          strong
        >
          {{ getStatusText(judgment.verification_status || 'WAITING') }}
        </n-tag>
        <n-tag type="default" size="medium" :bordered="false">
          {{ judgment.verification_period || 1 }}日
        </n-tag>
      </n-space>
    </template>
    
    <!-- 2. 判断前提 (最醒目,完整展示) -->
    <div class="premise-section">
      <n-text strong style="font-size: 16px; line-height: 1.6; color: #262626;">
        {{ judgment.structure_premise || '无判断前提' }}
      </n-text>
    </div>
    
    <!-- 3. 标的信息 -->
    <div class="stock-section">
      <n-text depth="2" style="font-size: 14px;">
        {{ getStockDisplay(judgment) }}
      </n-text>
    </div>
    
    <!-- 4. 关键位 (可选) -->
    <div v-if="hasKeyLevels(judgment)" class="key-levels-section">
      <n-space size="small">
        <n-tag 
          v-for="(level, idx) in getKeyLevels(judgment)" 
          :key="idx" 
          size="small" 
          :bordered="false"
          type="default"
        >
          {{ level.label }}: {{ level.price }}
        </n-tag>
      </n-space>
    </div>
    
    <!-- 5. 最近检查时间 -->
    <div class="check-time-section">
      <n-text depth="3" style="font-size: 12px;">
        最近检查: {{ formatCheckTime(judgment.last_checked_at) }}
      </n-text>
    </div>
    
    <!-- 6. 操作按钮 -->
    <template #action>
      <n-button text type="primary" @click="$emit('view', judgment.judgment_id)">
        查看
      </n-button>
    </template>
  </n-card>
</template>

<script setup lang="ts">
import { NCard, NTag, NText, NSpace, NButton } from 'naive-ui';

interface Judgment {
  judgment_id: string;
  stock_code: string;
  stock_name?: string;
  structure_premise: string;
  verification_period: number;
  verification_status?: string;
  last_checked_at?: string;
  key_levels_snapshot?: any;
}

defineProps<{
  judgment: Judgment;
}>();

const emit = defineEmits<{
  view: [judgmentId: string];
}>();

// 状态类型映射
function getStatusType(status: string): 'default' | 'info' | 'success' | 'error' {
  const map: Record<string, 'default' | 'info' | 'success' | 'error'> = {
    'WAITING': 'default',
    'CHECKED': 'info',
    'CONFIRMED': 'success',
    'BROKEN': 'error'
  };
  return map[status] || 'default';
}

// 状态文案映射 (固定枚举)
function getStatusText(status: string): string {
  const map: Record<string, string> = {
    'WAITING': '等待验证',
    'CHECKED': '周期结束',
    'CONFIRMED': '前提成立',
    'BROKEN': '前提失效'
  };
  return map[status] || '未知状态';
}

// 股票显示
function getStockDisplay(judgment: Judgment): string {
  if (judgment.stock_name) {
    return `${judgment.stock_name} (${judgment.stock_code})`;
  }
  return judgment.stock_code;
}

// 检查是否有关键位
function hasKeyLevels(judgment: Judgment): boolean {
  return !!(judgment.key_levels_snapshot && 
    Array.isArray(judgment.key_levels_snapshot) && 
    judgment.key_levels_snapshot.length > 0);
}

// 获取关键位列表
function getKeyLevels(judgment: Judgment): Array<{ label: string; price: string }> {
  if (!hasKeyLevels(judgment)) return [];
  
  return judgment.key_levels_snapshot.map((level: any) => ({
    label: level.label || level.type || '关键位',
    price: typeof level.price === 'number' ? level.price.toFixed(2) : level.price
  }));
}

// 格式化检查时间
function formatCheckTime(time?: string): string {
  if (!time) return '未检查';
  
  try {
    const date = new Date(time);
    return date.toLocaleString('zh-CN', { 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  } catch {
    return '未检查';
  }
}
</script>

<style scoped>
.judgment-card {
  transition: all 0.3s ease;
}

.judgment-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

/* 状态颜色 - 左侧边框 */
.status-WAITING {
  border-left: 4px solid #d9d9d9;
}

.status-CONFIRMED {
  border-left: 4px solid #52c41a;
}

.status-BROKEN {
  border-left: 4px solid #ff4d4f;
}

.status-CHECKED {
  border-left: 4px solid #1890ff;
}

/* 判断前提区域 - 最醒目 */
.premise-section {
  margin: 16px 0;
  padding: 12px;
  background: #fafafa;
  border-radius: 4px;
  border-left: 3px solid #1890ff;
}

/* 股票信息 */
.stock-section {
  margin: 12px 0;
}

/* 关键位 */
.key-levels-section {
  margin: 12px 0;
}

/* 检查时间 */
.check-time-section {
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
</style>
