<template>
  <n-card 
    v-if="hasRiskFlags" 
    size="small" 
    class="judgment-pre-reminder"
    :bordered="false"
  >
    <template #header>
      <div class="reminder-header">
        <n-icon size="20" color="#3b82f6">
          <BulbOutline />
        </n-icon>
        <span class="reminder-title">💡 判断前的提醒</span>
      </div>
    </template>

    <div class="reminder-content">
      <p class="reminder-intro">
        判断是对<strong>当前结构前提</strong>的记录,不是对未来的预测。
        选择判断候选项时,请明确您认为的<strong>关键前提</strong>是什么。
      </p>

      <n-collapse 
        v-if="riskFlags.length > 0"
        :default-expanded-names="expandByDefault ? ['risks'] : []"
        arrow-placement="right"
      >
        <n-collapse-item title="当前分析识别到以下认知风险" name="risks">
          <RiskFlagExplainer
            v-for="flag in riskFlags"
            :key="flag"
            :flag-key="flag"
            :compact="true"
          />
        </n-collapse-item>
      </n-collapse>

      <n-alert 
        type="info" 
        :bordered="false" 
        style="margin-top: 12px;"
        :show-icon="false"
      >
        <div style="font-size: 12px;">
          判断可能失败,这不代表分析错误。这是市场动态的正常表现。
        </div>
      </n-alert>
    </div>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NCard, NIcon, NCollapse, NCollapseItem, NAlert } from 'naive-ui';
import { BulbOutline } from '@vicons/ionicons5';
import RiskFlagExplainer from './RiskFlagExplainer.vue';

interface Props {
  riskFlags?: string[];
  expandByDefault?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  riskFlags: () => [],
  expandByDefault: false
});

const hasRiskFlags = computed(() => props.riskFlags.length > 0);
</script>

<style scoped>
.judgment-pre-reminder {
  background: linear-gradient(135deg, rgba(59, 130, 246, 0.03) 0%, rgba(147, 197, 253, 0.05) 100%);
  border-left: 3px solid #3b82f6;
  margin-bottom: 20px;
}

.reminder-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reminder-title {
  font-size: 15px;
  font-weight: 600;
  color: #1f2937;
}

.reminder-content {
  font-size: 13px;
  line-height: 1.6;
}

.reminder-intro {
  margin: 0 0 12px 0;
  color: #4b5563;
}

.reminder-intro strong {
  color: #1f2937;
  font-weight: 600;
}
</style>
