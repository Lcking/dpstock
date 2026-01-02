<template>
  <div class="risk-flag-explainer" :class="{ compact }">
    <div class="explainer-header">
      <n-icon size="18" color="#f59e0b">
        <AlertCircleOutline />
      </n-icon>
      <span class="explainer-title">{{ explanation.title }}</span>
    </div>
    
    <div v-if="!compact" class="explainer-content">
      <p class="explanation-text">{{ explanation.explanation }}</p>
      <div class="reminder-box">
        <n-icon size="16" color="#3b82f6">
          <BulbOutline />
        </n-icon>
        <span class="reminder-text">{{ explanation.reminder }}</span>
      </div>
    </div>
    
    <div v-else class="compact-reminder">
      <n-icon size="14" color="#3b82f6">
        <BulbOutline />
      </n-icon>
      <span class="reminder-text">{{ explanation.reminder }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NIcon } from 'naive-ui';
import { AlertCircleOutline, BulbOutline } from '@vicons/ionicons5';
import { getRiskFlagExplanation } from '@/config/wyckoffGuide';

interface Props {
  flagKey: string;
  compact?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  compact: false
});

const explanation = computed(() => getRiskFlagExplanation(props.flagKey));
</script>

<style scoped>
.risk-flag-explainer {
  padding: 12px;
  background: rgba(245, 158, 11, 0.05);
  border-left: 3px solid #f59e0b;
  border-radius: 6px;
  margin-bottom: 12px;
}

.risk-flag-explainer.compact {
  padding: 8px 12px;
  background: rgba(245, 158, 11, 0.03);
}

.explainer-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.explainer-title {
  font-weight: 600;
  font-size: 14px;
  color: #1f2937;
}

.explainer-content {
  margin-left: 26px;
}

.explanation-text {
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
  margin: 0 0 10px 0;
}

.reminder-box {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  padding: 8px;
  background: rgba(59, 130, 246, 0.08);
  border-radius: 4px;
}

.compact-reminder {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-left: 26px;
}

.reminder-text {
  font-size: 12px;
  color: #1e40af;
  font-weight: 500;
  line-height: 1.5;
}
</style>
