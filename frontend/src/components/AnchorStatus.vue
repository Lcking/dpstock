<template>
  <div class="anchor-status">
    <n-text v-if="mode === 'anonymous'" depth="3" :style="{ fontSize: textSize }">
      保存方式: <n-text type="warning">本设备</n-text> (存在丢失风险)
      <n-button text type="primary" size="small" @click="emit('show-bind')">
        绑定邮箱
      </n-button>
    </n-text>
    
    <n-text v-else-if="mode === 'restore'" depth="3" :style="{ fontSize: textSize }">
      保存方式: <n-text type="warning">需重新验证</n-text>
      <n-button text type="primary" size="small" @click="emit('show-bind')">
        验证邮箱恢复
      </n-button>
    </n-text>

    <n-text v-else depth="3" :style="{ fontSize: textSize }">
      保存方式: <n-text type="success">已绑定邮箱</n-text> (长期保存)
      <n-tag size="small" :bordered="false" style="margin-left: 8px;">
        {{ maskedEmail }}
      </n-tag>
    </n-text>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { NText, NButton, NTag } from 'naive-ui';
import { getMaskedEmail } from '@/utils/anchorToken';
import { syncAnchorSession, type AnchorSessionMode } from '@/utils/anchorSession';

interface Props {
  textSize?: string;
}

withDefaults(defineProps<Props>(), {
  textSize: '13px'
});

const emit = defineEmits(['show-bind']);

const mode = ref<AnchorSessionMode>('anonymous');
const maskedEmail = ref<string>('');

async function refreshStatus() {
  const session = await syncAnchorSession();
  mode.value = session;
  maskedEmail.value = session === 'anchor' ? (getMaskedEmail() || '') : '';
}

onMounted(() => {
  void refreshStatus();
});

defineExpose({ updateStatus: refreshStatus });
</script>

<style scoped>
.anchor-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
