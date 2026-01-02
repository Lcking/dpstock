<template>
  <div class="quota-status">
    <n-space align="center" :size="8">
      <!-- Quota Display -->
      <n-tooltip trigger="hover">
        <template #trigger>
          <n-tag 
            :type="getQuotaType()" 
            size="small"
            :bordered="false"
            style="cursor: pointer"
            @click="handleQuotaClick"
          >
            <template #icon>
              <n-icon>
                <AnalyticsOutline />
              </n-icon>
            </template>
            {{ quotaText }}
          </n-tag>
        </template>
        <div style="max-width: 250px;">
          <div><strong>今日分析额度</strong></div>
          <div style="margin-top: 4px;">
            基础: {{ status?.base_quota || 5 }} 次<br/>
            邀请奖励: {{ status?.invite_quota || 0 }} 次<br/>
            已用: {{ status?.used_quota || 0 }} 次
          </div>
          <div style="margin-top: 8px; font-size: 12px; opacity: 0.8;">
            点击查看详情或邀请好友解锁更多额度
          </div>
        </div>
      </n-tooltip>

      <!-- Invite Button -->
      <n-button 
        size="tiny" 
        secondary
        @click="$emit('openInvite')"
      >
        <template #icon>
          <n-icon><ShareSocialOutline /></n-icon>
        </template>
        邀请
      </n-button>
    </n-space>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { NSpace, NTag, NTooltip, NButton, NIcon } from 'naive-ui';
import { AnalyticsOutline, ShareSocialOutline } from '@vicons/ionicons5';
import { apiService } from '@/services/api';

const emit = defineEmits(['openInvite', 'quotaClick']);

const status = ref<any>(null);
const loading = ref(false);

const quotaText = computed(() => {
  if (!status.value) return '加载中...';
  const remaining = status.value.remaining_quota || 0;
  const total = status.value.total_quota || 5;
  return `${remaining}/${total}`;
});

const getQuotaType = () => {
  if (!status.value) return 'default';
  const remaining = status.value.remaining_quota || 0;
  const total = status.value.total_quota || 5;
  const percentage = (remaining / total) * 100;
  
  if (percentage > 50) return 'success';
  if (percentage > 20) return 'warning';
  return 'error';
};

const loadQuotaStatus = async () => {
  loading.value = true;
  try {
    const data = await apiService.getQuotaStatus();
    if (data) {
      status.value = data;
    }
  } catch (error) {
    console.error('Failed to load quota status:', error);
  } finally {
    loading.value = false;
  }
};

const handleQuotaClick = () => {
  emit('quotaClick', status.value);
};

// Load on mount
onMounted(() => {
  loadQuotaStatus();
});

// Expose refresh method
defineExpose({
  refresh: loadQuotaStatus
});
</script>

<style scoped>
.quota-status {
  display: inline-flex;
  align-items: center;
}
</style>
