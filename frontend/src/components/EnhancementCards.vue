<template>
  <div class="enhancement-cards" v-if="enhancements">
    <n-collapse :default-expanded-names="['relative_strength', 'capital_flow']">
      <!-- 相对强弱 -->
      <n-collapse-item 
        name="relative_strength" 
        :disabled="!relativeStrength"
      >
        <template #header>
          <div class="card-header">
            <n-icon :component="TrendingUpOutline" class="header-icon" />
            <span>对照表现</span>
            <n-tag v-if="!relativeStrength" size="small" type="warning">不可用</n-tag>
            <n-tag v-else-if="relativeStrength.degraded" size="small" type="warning">部分数据</n-tag>
          </div>
        </template>
        <div class="card-content" v-if="relativeStrength">
          <p class="summary">{{ relativeStrength.summary }}</p>
          <div class="key-metrics">
            <n-tag 
              v-for="metric in relativeStrength.key_metrics" 
              :key="metric.key"
              :type="getMetricTagType(metric)"
              size="small"
            >
              {{ metric.label }}: {{ formatMetricValue(metric) }}
            </n-tag>
          </div>
        </div>
      </n-collapse-item>

      <!-- 行业位置 -->
      <n-collapse-item 
        name="industry_position"
        :disabled="!industryPosition"
      >
        <template #header>
          <div class="card-header">
            <n-icon :component="BusinessOutline" class="header-icon" />
            <span>行业位置</span>
            <n-tag v-if="!industryPosition" size="small" type="warning">不可用</n-tag>
          </div>
        </template>
        <div class="card-content" v-if="industryPosition">
          <p class="summary">{{ industryPosition.summary }}</p>
          <div class="key-metrics">
            <n-tag 
              v-for="metric in industryPosition.key_metrics" 
              :key="metric.key"
              type="info"
              size="small"
            >
              {{ metric.label }}: {{ metric.value }}
            </n-tag>
          </div>
        </div>
      </n-collapse-item>

      <!-- 资金流向 -->
      <n-collapse-item 
        name="capital_flow"
        :disabled="!capitalFlow"
      >
        <template #header>
          <div class="card-header">
            <n-icon :component="CashOutline" class="header-icon" />
            <span>资金语言</span>
            <n-tag v-if="!capitalFlow" size="small" type="warning">不可用</n-tag>
            <n-tag v-else-if="capitalFlow.degraded" size="small" type="warning">推算数据</n-tag>
          </div>
        </template>
        <div class="card-content" v-if="capitalFlow">
          <p class="summary">{{ capitalFlow.summary }}</p>
          <div class="key-metrics">
            <n-tag 
              v-for="metric in capitalFlow.key_metrics" 
              :key="metric.key"
              :type="getFlowTagType(metric)"
              size="small"
            >
              {{ metric.label }}: {{ formatMetricValue(metric) }}
            </n-tag>
          </div>
        </div>
      </n-collapse-item>

      <!-- 事件提醒 -->
      <n-collapse-item 
        name="events"
        :disabled="!eventsModule"
      >
        <template #header>
          <div class="card-header">
            <n-icon :component="CalendarOutline" class="header-icon" />
            <span>事件提醒</span>
            <n-tag v-if="!eventsModule" size="small" type="warning">不可用</n-tag>
          </div>
        </template>
        <div class="card-content" v-if="eventsModule">
          <p class="summary">{{ eventsModule.summary }}</p>
          <div class="key-metrics">
            <n-tag 
              v-for="metric in eventsModule.key_metrics" 
              :key="metric.key"
              :type="metric.value > 0 ? 'warning' : 'default'"
              size="small"
            >
              {{ metric.label }}: {{ metric.value }}
            </n-tag>
          </div>
        </div>
      </n-collapse-item>
    </n-collapse>

    <!-- 数据来源说明 -->
    <div class="data-source" v-if="enhancements.generated_at">
      <n-text depth="3" style="font-size: 11px;">
        数据来源: Tushare Pro | 更新时间: {{ formatTime(enhancements.generated_at) }}
      </n-text>
    </div>
  </div>

  <!-- 加载状态 -->
  <div v-else-if="loading" class="loading-state">
    <n-spin size="small" />
    <n-text depth="3">加载增强数据...</n-text>
  </div>

  <!-- 错误状态 -->
  <div v-else-if="error" class="error-state">
    <n-alert type="warning" :bordered="false">
      {{ error }}
    </n-alert>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import { 
  NCollapse, NCollapseItem, NTag, NIcon, NText, NSpin, NAlert 
} from 'naive-ui';
import {
  TrendingUpOutline,
  BusinessOutline,
  CashOutline,
  CalendarOutline
} from '@vicons/ionicons5';

interface KeyMetric {
  key: string;
  label: string;
  value: any;
  unit?: string;
}

interface ModuleResult {
  available: boolean;
  degraded: boolean;
  degrade_reason?: string;
  summary: string;
  key_metrics: KeyMetric[];
}

interface EnhancementsData {
  version: string;
  generated_at: string;
  available_modules: string[];
  relative_strength?: ModuleResult;
  industry_position?: ModuleResult;
  capital_flow?: ModuleResult;
  events?: ModuleResult;
}

const props = defineProps<{
  stockCode: string;
}>();

const enhancements = ref<EnhancementsData | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

// Computed properties to avoid repeated optional chaining in template
const relativeStrength = computed(() => {
  const m = enhancements.value?.relative_strength;
  return m?.available ? m : null;
});

const industryPosition = computed(() => {
  const m = enhancements.value?.industry_position;
  return m?.available ? m : null;
});

const capitalFlow = computed(() => {
  const m = enhancements.value?.capital_flow;
  return m?.available ? m : null;
});

const eventsModule = computed(() => {
  const m = enhancements.value?.events;
  return m?.available ? m : null;
});

async function fetchEnhancements() {
  if (!props.stockCode) return;
  
  loading.value = true;
  error.value = null;
  
  try {
    const response = await fetch(`/api/enhancements/${props.stockCode}`);
    if (response.ok) {
      enhancements.value = await response.json();
    } else {
      const errData = await response.json();
      error.value = errData.detail || '获取增强数据失败';
    }
  } catch (e) {
    error.value = '网络错误，无法获取增强数据';
    console.error(e);
  } finally {
    loading.value = false;
  }
}

function formatMetricValue(metric: KeyMetric): string {
  if (metric.value === null || metric.value === undefined) return '--';
  if (metric.unit === 'pct') return `${metric.value}%`;
  if (metric.unit === '亿') return `${metric.value}亿`;
  return String(metric.value);
}

type TagType = 'default' | 'success' | 'error' | 'warning' | 'info' | 'primary';

function getMetricTagType(metric: KeyMetric): TagType {
  if (metric.key.includes('excess') && typeof metric.value === 'number') {
    if (metric.value >= 1.5) return 'success';
    if (metric.value <= -1.5) return 'error';
  }
  return 'default';
}

function getFlowTagType(metric: KeyMetric): TagType {
  if (metric.key === 'flow_label') {
    if (metric.value === '承接放量') return 'success';
    if (metric.value === '分歧放量') return 'warning';
    if (metric.value === '缩量观望') return 'default';
  }
  if (metric.key === 'net_inflow_today' && typeof metric.value === 'number') {
    return metric.value > 0 ? 'success' : 'error';
  }
  return 'default';
}

function formatTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN', { 
      month: '2-digit', 
      day: '2-digit', 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  } catch {
    return isoString;
  }
}

onMounted(() => {
  fetchEnhancements();
});

watch(() => props.stockCode, () => {
  fetchEnhancements();
});
</script>

<style scoped>
.enhancement-cards {
  margin: 16px 0;
  border: 1px solid var(--n-border-color);
  border-radius: 8px;
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  font-size: 16px;
  color: var(--n-text-color-3);
}

.card-content {
  padding: 8px 0;
}

.summary {
  margin: 0 0 8px 0;
  font-size: 13px;
  line-height: 1.5;
  color: var(--n-text-color-2);
}

.key-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.data-source {
  padding: 8px 16px;
  text-align: right;
  border-top: 1px solid var(--n-border-color);
  background: var(--n-color-embedded);
}

.loading-state,
.error-state {
  padding: 16px;
  text-align: center;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}
</style>
