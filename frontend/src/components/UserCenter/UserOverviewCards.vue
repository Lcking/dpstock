<template>
  <n-grid cols="1 s:2 xl:4" :x-gap="16" :y-gap="16" responsive="screen">
    <n-grid-item>
      <n-card size="small" class="overview-card">
        <n-space vertical :size="8">
          <n-text depth="3">绑定状态</n-text>
          <n-tag :type="overview.user.is_temporary ? 'warning' : 'success'" size="small">
            {{ overview.user.is_temporary ? '游客 / 临时资产' : '已绑定邮箱' }}
          </n-tag>
          <n-text>{{ overview.user.masked_email || '绑定后可跨设备同步资产' }}</n-text>
          <n-button
            v-if="overview.user.is_temporary"
            size="small"
            type="primary"
            secondary
            @click="$emit('bind')"
          >
            绑定邮箱
          </n-button>
        </n-space>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card size="small" class="overview-card">
        <n-space vertical :size="8">
          <n-text depth="3">当前额度</n-text>
          <n-text class="metric">{{ overview.quota_status.remaining_quota }} / {{ overview.quota_status.total_quota }}</n-text>
          <n-text depth="3">今日已用 {{ overview.quota_status.used_quota }} 次</n-text>
          <n-button size="small" @click="$emit('invite')">额度与邀请</n-button>
        </n-space>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card size="small" class="overview-card">
        <n-space vertical :size="8">
          <n-text depth="3">我的观察</n-text>
          <n-text class="metric">{{ overview.watchlist_count }}</n-text>
          <n-text depth="3">共跟踪 {{ overview.watchlist_items_count }} 只标的</n-text>
          <n-text
            v-if="overview.risk_alert_unread_count > 0"
            class="risk-unread"
          >
            {{ overview.risk_alert_unread_count }} 条风险提醒未读
          </n-text>
          <n-button size="small" @click="$emit('go-watchlist')">查看观察列表</n-button>
        </n-space>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card size="small" class="overview-card">
        <n-space vertical :size="8">
          <n-text depth="3">待复盘</n-text>
          <n-text class="metric">{{ overview.due_count }}</n-text>
          <n-text depth="3">及时复盘，沉淀可验证判断</n-text>
          <n-button size="small" @click="$emit('go-journal')">查看判断日记</n-button>
        </n-space>
      </n-card>
    </n-grid-item>
  </n-grid>

  <n-card v-if="trustSummary || topConditionLabel" size="small" class="trust-card">
    <n-space vertical :size="8">
      <n-text depth="3">历史验证与条件质量</n-text>
      <n-text v-if="trustSummary">{{ trustSummary }}</n-text>
      <n-text v-if="topConditionLabel" depth="3">{{ topConditionLabel }}</n-text>
      <n-text v-if="!trustSummary && !topConditionLabel" depth="3">
        完成判断复盘后，这里会展示系统支持率与条件质量参考。
      </n-text>
      <n-button size="small" @click="$emit('go-journal')">查看判断日记</n-button>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NCard, NGrid, NGridItem, NSpace, NTag, NText } from 'naive-ui'
import { buildTrustSummary, topConditionQualityItem } from '@/utils/trustStats'

const props = defineProps<{
  overview: any
}>()

defineEmits<{
  (e: 'bind'): void
  (e: 'invite'): void
  (e: 'go-watchlist'): void
  (e: 'go-journal'): void
}>()

const trustSummary = computed(() => buildTrustSummary(props.overview?.trust_stats))

const topConditionLabel = computed(() => {
  const top = topConditionQualityItem(props.overview?.trust_stats?.condition_quality_leaderboard)
  if (!top || top.support_rate == null) return ''
  return `样本最多条件：${top.label}（${top.reviewed_count} 条复盘，支持率 ${top.support_rate}%）`
})
</script>

<style scoped>
.overview-card {
  min-height: 180px;
}

.metric {
  font-size: 28px;
  font-weight: 700;
}

.risk-unread {
  color: #b45309;
  font-size: 13px;
}

.trust-card {
  margin-top: 16px;
}
</style>
