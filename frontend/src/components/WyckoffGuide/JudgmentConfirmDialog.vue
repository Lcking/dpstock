<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    title="⏸️ 保存判断前的最后确认"
    style="width: 90%; max-width: 560px;"
    :bordered="false"
    :closable="true"
  >
    <div class="judgment-confirm-content">
      <!-- 用户选择的判断 -->
      <n-alert type="info" :bordered="false" style="margin-bottom: 16px;">
        <template #icon>
          <n-icon><CheckmarkCircleOutline /></n-icon>
        </template>
        <div>
          <strong>您选择的判断:</strong>
          <div style="margin-top: 4px; font-size: 15px;">{{ judgmentCandidate }}</div>
          <div v-if="stockCode" style="margin-top: 4px; font-size: 13px; opacity: 0.8;">
            股票: {{ stockCode }} {{ stockName ? `(${stockName})` : '' }}
          </div>
        </div>
      </n-alert>

      <!-- 判断前提确认 -->
      <n-card size="small" :bordered="false" style="background: var(--n-color-embedded); margin-bottom: 16px;">
        <div style="font-weight: 600; margin-bottom: 12px;">请再次确认您的判断前提:</div>
        <n-space vertical :size="8">
          <div style="display: flex; align-items: flex-start; gap: 8px;">
            <span style="color: #3b82f6;">•</span>
            <span style="font-size: 13px;">您认为当前最关键的结构特征是什么?</span>
          </div>
          <div style="display: flex; align-items: flex-start; gap: 8px;">
            <span style="color: #3b82f6;">•</span>
            <span style="font-size: 13px;">如果这个判断被削弱,您能接受吗?</span>
          </div>
          <div style="display: flex; align-items: flex-start; gap: 8px;">
            <span style="color: #3b82f6;">•</span>
            <span style="font-size: 13px;">您是否已经考虑了反向可能性?</span>
          </div>
        </n-space>
      </n-card>

      <!-- 显示相关 risk_flags (最多2条) -->
      <div v-if="relevantRiskFlags.length > 0" style="margin-bottom: 16px;">
        <div style="font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #6b7280;">
          当前分析识别到以下认知风险:
        </div>
        <RiskFlagExplainer
          v-for="flag in relevantRiskFlags"
          :key="flag"
          :flag-key="flag"
        />
      </div>

      <!-- 底部提醒 -->
      <n-alert type="default" :bordered="false">
        <template #icon>
          <n-icon><InformationCircleOutline /></n-icon>
        </template>
        <div style="font-size: 13px;">
          这不是阻止您保存判断,只是提醒您:<br/>
          <strong>判断是用来验证的,不是用来证明自己正确的。</strong>
        </div>
      </n-alert>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="handleCancel">
          取消
        </n-button>
        <n-button type="primary" @click="handleConfirm">
          我已理解,保存判断
        </n-button>
      </n-space>
    </template>
  </n-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import {
  NModal,
  NAlert,
  NCard,
  NSpace,
  NButton,
  NIcon
} from 'naive-ui';
import {
  CheckmarkCircleOutline,
  InformationCircleOutline
} from '@vicons/ionicons5';
import RiskFlagExplainer from './RiskFlagExplainer.vue';

interface Props {
  show: boolean;
  judgmentCandidate: string;
  riskFlags?: string[];
  stockCode?: string;
  stockName?: string;
}

const props = withDefaults(defineProps<Props>(), {
  riskFlags: () => [],
  stockCode: '',
  stockName: ''
});

const emit = defineEmits<{
  'update:show': [value: boolean];
  'confirm': [];
  'cancel': [];
}>();

const showModal = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
});

// 只显示前2个 risk_flags,避免信息过载
const relevantRiskFlags = computed(() => {
  return props.riskFlags.slice(0, 2);
});

function handleConfirm() {
  emit('confirm');
  showModal.value = false;
}

function handleCancel() {
  emit('cancel');
  showModal.value = false;
}
</script>

<style scoped>
.judgment-confirm-content {
  padding: 4px 0;
}
</style>
