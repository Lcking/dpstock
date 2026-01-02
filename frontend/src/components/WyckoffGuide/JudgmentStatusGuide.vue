<template>
  <div class="judgment-status-guide">
    <n-collapse 
      arrow-placement="right"
      :default-expanded-names="[status]"
    >
      <n-collapse-item :title="statusMessage.title" :name="status">
        <template #header-extra>
          <n-tag :type="getStatusTagType(status)" size="small" :bordered="false">
            {{ getStatusLabel(status) }}
          </n-tag>
        </template>

        <div class="status-content">
          <!-- 状态含义 -->
          <div class="status-section">
            <div class="section-label">这意味着:</div>
            <p class="section-text">{{ statusMessage.meaning }}</p>
          </div>

          <!-- 建议 -->
          <div class="status-section">
            <div class="section-label">建议:</div>
            <p class="section-text">{{ statusMessage.suggestion }}</p>
          </div>

          <!-- 学习提示 (仅在 broken 状态) -->
          <n-alert 
            v-if="status === 'broken'" 
            type="info" 
            :bordered="false"
            style="margin-top: 12px;"
          >
            <template #icon>
              <n-icon><SchoolOutline /></n-icon>
            </template>
            <div style="font-size: 13px;">
              <strong>这是学习机会:</strong><br/>
              回顾当初的判断逻辑,找出脆弱的前提。
              承认判断失效,比坚持错误判断更有价值。
            </div>
          </n-alert>
        </div>
      </n-collapse-item>
    </n-collapse>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NCollapse, NCollapseItem, NTag, NAlert, NIcon } from 'naive-ui';
import { SchoolOutline } from '@vicons/ionicons5';
import { getJudgmentStatusMessage } from '@/config/wyckoffGuide';

interface Props {
  status: 'maintained' | 'weakened' | 'broken';
}

const props = defineProps<Props>();

const statusMessage = computed(() => getJudgmentStatusMessage(props.status));

function getStatusTagType(status: string): 'success' | 'warning' | 'error' | 'default' {
  const map: Record<string, 'success' | 'warning' | 'error' | 'default'> = {
    'maintained': 'success',
    'weakened': 'warning',
    'broken': 'default'
  };
  return map[status] || 'default';
}

function getStatusLabel(status: string): string {
  const map: Record<string, string> = {
    'maintained': '前提维持',
    'weakened': '前提削弱',
    'broken': '前提破坏'
  };
  return map[status] || status;
}
</script>

<style scoped>
.judgment-status-guide {
  margin-top: 12px;
}

.status-content {
  padding: 4px 0;
}

.status-section {
  margin-bottom: 16px;
}

.status-section:last-child {
  margin-bottom: 0;
}

.section-label {
  font-size: 13px;
  font-weight: 600;
  color: #6b7280;
  margin-bottom: 6px;
}

.section-text {
  font-size: 13px;
  line-height: 1.6;
  color: #4b5563;
  margin: 0;
}
</style>
