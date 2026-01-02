<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    title="邀请好友,解锁更多额度"
    style="width: 90%; max-width: 500px;"
    :bordered="false"
  >
    <div class="invite-dialog-content">
      <!-- Invite Explanation -->
      <n-alert type="info" :bordered="false" style="margin-bottom: 16px;">
        <template #icon>
          <n-icon><GiftOutline /></n-icon>
        </template>
        <div>
          <strong>邀请奖励规则</strong>
          <ul style="margin: 8px 0 0 0; padding-left: 20px;">
            <li>分享邀请链接给朋友</li>
            <li>好友完成首次分析后,您获得 <strong>+5 次</strong> 额度</li>
            <li>每日最多获得 <strong>20 次</strong> 邀请额度</li>
          </ul>
        </div>
      </n-alert>

      <!-- Current Status -->
      <n-card size="small" :bordered="false" style="margin-bottom: 16px; background: var(--n-color-embedded);">
        <n-space vertical :size="8">
          <div style="display: flex; justify-content: space-between;">
            <span>今日邀请奖励:</span>
            <strong>{{ inviteQuota }} / 20 次</strong>
          </div>
          <div style="display: flex; justify-content: space-between;">
            <span>今日总额度:</span>
            <strong>{{ totalQuota }} 次</strong>
          </div>
        </n-space>
      </n-card>

      <!-- Invite Link -->
      <div v-if="inviteUrl">
        <n-text strong style="display: block; margin-bottom: 8px;">您的邀请链接:</n-text>
        <n-input
          :value="inviteUrl"
          readonly
          type="textarea"
          :autosize="{ minRows: 2, maxRows: 3 }"
          style="margin-bottom: 12px;"
        />
        <n-space>
          <n-button type="primary" @click="copyInviteLink">
            <template #icon>
              <n-icon><CopyOutline /></n-icon>
            </template>
            复制链接
          </n-button>
          <n-button @click="shareInviteLink" v-if="canShare">
            <template #icon>
              <n-icon><ShareOutline /></n-icon>
            </template>
            分享
          </n-button>
        </n-space>
      </div>

      <!-- Loading State -->
      <div v-else-if="loading" style="text-align: center; padding: 20px;">
        <n-spin size="medium" />
        <div style="margin-top: 12px;">生成邀请链接中...</div>
      </div>

      <!-- Error State -->
      <n-alert v-else-if="error" type="error" :bordered="false">
        {{ error }}
      </n-alert>

      <!-- Disclaimer -->
      <n-divider style="margin: 20px 0;" />
      <n-text depth="3" style="font-size: 12px;">
        💡 提示: 邀请机制旨在引导专注与纪律,而非营销手段。请分享给真正需要的朋友。
      </n-text>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue';
import {
  NModal,
  NAlert,
  NCard,
  NSpace,
  NText,
  NInput,
  NButton,
  NIcon,
  NSpin,
  NDivider,
  useMessage
} from 'naive-ui';
import {
  GiftOutline,
  CopyOutline,
  ShareOutline
} from '@vicons/ionicons5';
import { apiService } from '@/services/api';

interface Props {
  show: boolean;
  quotaStatus?: any;
}

const props = defineProps<Props>();
const emit = defineEmits(['update:show', 'inviteGenerated']);

const message = useMessage();

const showModal = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
});

const loading = ref(false);
const error = ref('');
const inviteUrl = ref('');
const inviteCode = ref('');

const inviteQuota = computed(() => props.quotaStatus?.invite_quota || 0);
const totalQuota = computed(() => props.quotaStatus?.total_quota || 5);

const canShare = computed(() => {
  return navigator.share !== undefined;
});

// Generate invite code when modal opens
watch(() => props.show, async (newShow) => {
  if (newShow && !inviteUrl.value) {
    await generateInviteCode();
  }
});

const generateInviteCode = async () => {
  loading.value = true;
  error.value = '';
  
  try {
    const data = await apiService.generateInviteCode();
    if (data) {
      inviteCode.value = data.invite_code;
      inviteUrl.value = data.invite_url;
      emit('inviteGenerated', data);
    }
  } catch (err: any) {
    error.value = err.response?.data?.detail?.message || '生成邀请链接失败';
  } finally {
    loading.value = false;
  }
};

const copyInviteLink = async () => {
  try {
    await navigator.clipboard.writeText(inviteUrl.value);
    message.success('邀请链接已复制到剪贴板');
  } catch (err) {
    message.error('复制失败,请手动复制');
  }
};

const shareInviteLink = async () => {
  if (!canShare.value) return;
  
  try {
    await navigator.share({
      title: 'Agu AI 股票分析平台邀请',
      text: '我在使用 Agu AI 进行股票分析,邀请你一起使用!',
      url: inviteUrl.value
    });
  } catch (err) {
    // User cancelled share or error occurred
    console.log('Share cancelled or failed:', err);
  }
};
</script>

<style scoped>
.invite-dialog-content {
  padding: 4px 0;
}
</style>
