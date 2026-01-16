<template>
  <div class="anchor-status">
    <n-text v-if="mode === 'anonymous'" depth="3" :style="{ fontSize: textSize }">
      保存方式: <n-text type="warning">本设备</n-text> (存在丢失风险)
      <n-button text type="primary" size="small" @click="emit('show-bind')">
        绑定邮箱
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
import { hasAnchorToken, getMaskedEmail } from '@/utils/anchorToken';

interface Props {
  textSize?: string;
}

withDefaults(defineProps<Props>(), {
  textSize: '13px'
});

const emit = defineEmits(['show-bind']);

// State
const mode = ref<'anonymous' | 'anchor'>('anonymous');
const maskedEmail = ref<string>('');

// Check anchor status on mount
onMounted(() => {
  if (hasAnchorToken()) {
    mode.value = 'anchor';
    maskedEmail.value = getMaskedEmail() || '';
  }
});

// Expose method to update status after binding
function updateStatus() {
  if (hasAnchorToken()) {
    mode.value = 'anchor';
    maskedEmail.value = getMaskedEmail() || '';
  }
}

defineExpose({ updateStatus });
</script>

<style scoped>
.anchor-status {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
</style>
