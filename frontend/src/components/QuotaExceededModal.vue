<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    title="今日分析额度已用完"
    style="width: 90%; max-width: 480px;"
    :bordered="false"
    :closable="true"
  >
    <div class="quota-exceeded-content">
      <!-- Main Message -->
      <n-alert type="warning" :bordered="false" style="margin-bottom: 16px;">
        <template #icon>
          <n-icon><AlertCircleOutline /></n-icon>
        </template>
        <div style="white-space: pre-line;">{{ errorMessage }}</div>
      </n-alert>

      <!-- Analyzed Stocks Today -->
      <div v-if="analyzedStocks && analyzedStocks.length > 0" style="margin-bottom: 16px;">
        <n-text strong style="display: block; margin-bottom: 8px;">今日已分析的股票:</n-text>
        <n-space>
          <n-tag
            v-for="stock in analyzedStocks"
            :key="stock"
            size="small"
            type="info"
          >
            {{ stock }}
          </n-tag>
        </n-space>
        <n-text depth="3" style="display: block; margin-top: 8px; font-size: 12px;">
          💡 您可以重新查看这些股票的分析,不会消耗额度
        </n-text>
      </div>

      <!-- Suggestions -->
      <n-card size="small" :bordered="false" style="background: var(--n-color-embedded); margin-bottom: 16px;">
        <n-text strong style="display: block; margin-bottom: 12px;">解决方案:</n-text>
        <n-space vertical :size="12">
          <div style="display: flex; align-items: flex-start;">
            <n-icon size="20" style="margin-right: 8px; margin-top: 2px; flex-shrink: 0;">
              <MailOutline />
            </n-icon>
            <div>
              <strong>绑定邮箱</strong>
              <div style="font-size: 12px; opacity: 0.8;">绑定后可解锁邀请奖励与更多额度，并避免资产因换设备丢失</div>
            </div>
          </div>

          <div style="display: flex; align-items: flex-start;">
            <n-icon size="20" style="margin-right: 8px; margin-top: 2px; flex-shrink: 0;">
              <RefreshOutline />
            </n-icon>
            <div>
              <strong>重新分析今日股票</strong>
              <div style="font-size: 12px; opacity: 0.8;">深化对已分析股票的判断</div>
            </div>
          </div>

          <div style="display: flex; align-items: flex-start;">
            <n-icon size="20" style="margin-right: 8px; margin-top: 2px; flex-shrink: 0;">
              <ShareSocialOutline />
            </n-icon>
            <div>
              <strong>邀请好友解锁额度</strong>
              <div style="font-size: 12px; opacity: 0.8;">每成功邀请1人,获得+5次额度</div>
            </div>
          </div>

          <div style="display: flex; align-items: flex-start;">
            <n-icon size="20" style="margin-right: 8px; margin-top: 2px; flex-shrink: 0;">
              <TimeOutline />
            </n-icon>
            <div>
              <strong>明日额度自动恢复</strong>
              <div style="font-size: 12px; opacity: 0.8;">每天凌晨重置为基础额度</div>
            </div>
          </div>
        </n-space>
      </n-card>

      <!-- Philosophy -->
      <n-alert type="info" :bordered="false">
        <template #icon>
          <n-icon><BulbOutline /></n-icon>
        </template>
        <strong>💡 提示:</strong> 专注少数标的,比广撒网更有价值
      </n-alert>
    </div>

    <template #footer>
      <n-space justify="end">
        <n-button @click="showModal = false">
          知道了
        </n-button>
        <n-button secondary @click="handleBind">
          绑定邮箱
        </n-button>
        <n-button type="primary" @click="handleInvite">
          <template #icon>
            <n-icon><ShareSocialOutline /></n-icon>
          </template>
          邀请好友
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
  NText,
  NTag,
  NButton,
  NIcon
} from 'naive-ui';
import {
  AlertCircleOutline,
  RefreshOutline,
  ShareSocialOutline,
  TimeOutline,
  BulbOutline
} from '@vicons/ionicons5';
import { MailOutline } from '@vicons/ionicons5';

interface Props {
  show: boolean;
  errorData?: any;
}

const props = defineProps<Props>();
const emit = defineEmits(['update:show', 'openInvite', 'openBind']);

const showModal = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
});

const errorMessage = computed(() => {
  return props.errorData?.message || '今日新股票分析次数已用完';
});

const analyzedStocks = computed(() => {
  return props.errorData?.analyzed_stocks_today || [];
});

const handleInvite = () => {
  showModal.value = false;
  emit('openInvite');
};

const handleBind = () => {
  showModal.value = false;
  emit('openBind');
};
</script>

<style scoped>
.quota-exceeded-content {
  padding: 4px 0;
}
</style>
