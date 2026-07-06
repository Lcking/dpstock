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
          <n-button
            v-if="overview.risk_alert_unread_count > 0"
            text
            type="warning"
            class="risk-unread-btn"
            @click="$emit('go-watchlist', { focus: 'risk' })"
          >
            {{ overview.risk_alert_unread_count }} 条风险提醒未读 →
          </n-button>
          <n-button size="small" @click="$emit('go-watchlist')">查看观察列表</n-button>
        </n-space>
      </n-card>
    </n-grid-item>

    <n-grid-item>
      <n-card size="small" class="overview-card">
        <n-space vertical :size="8">
          <n-text depth="3">待复盘</n-text>
          <n-text class="metric">{{ overview.due_count }}</n-text>
          <n-text depth="3">共 {{ overview.judgment_count || 0 }} 条判断记录</n-text>
          <n-button size="small" @click="$emit('go-journal')">查看判断日记</n-button>
        </n-space>
      </n-card>
    </n-grid-item>
  </n-grid>

  <n-card size="small" class="trust-card">
    <n-space vertical :size="10">
      <n-text depth="3">我的复盘表现</n-text>
      <n-text v-if="personalSummary">{{ personalSummary }}</n-text>
      <n-text v-else depth="3">完成判断复盘后，这里会展示你的个人支持率与常用条件类型。</n-text>
      <ConditionQualityLeaderboard
        v-if="personalLeaderboard.length > 0"
        :items="personalLeaderboard"
        title="我的条件质量"
        hint="按你已复盘的判断统计各条件类型的支持率。"
        compact
        :max-items="4"
      />
      <n-button size="small" tertiary type="primary" @click="$emit('go-weekly-recap')">
        查看判断验证周报
      </n-button>
      <n-divider style="margin: 4px 0" />
      <n-text depth="3">平台历史验证（全站参考）</n-text>
      <n-text v-if="platformSummary" depth="3">{{ platformSummary }}</n-text>
      <n-text v-else depth="3">平台复盘样本积累中。</n-text>
      <n-button size="small" @click="$emit('go-journal')">去判断日记复盘</n-button>
    </n-space>
  </n-card>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NButton, NCard, NDivider, NGrid, NGridItem, NSpace, NTag, NText } from 'naive-ui'
import ConditionQualityLeaderboard from '@/components/Journal/ConditionQualityLeaderboard.vue'
import { buildPersonalReviewSummary, buildTrustSummary } from '@/utils/trustStats'

const props = defineProps<{
  overview: any
}>()

defineEmits<{
  (e: 'bind'): void
  (e: 'invite'): void
  (e: 'go-watchlist', payload?: { focus?: string }): void
  (e: 'go-journal'): void
  (e: 'go-weekly-recap'): void
}>()

const personalSummary = computed(() =>
  buildPersonalReviewSummary(props.overview?.personal_review_stats)
)

const personalLeaderboard = computed(
  () => props.overview?.personal_review_stats?.condition_quality_leaderboard ?? [],
)

const platformSummary = computed(() => buildTrustSummary(props.overview?.trust_stats))
</script>

<style scoped>
.overview-card {
  min-height: 180px;
}

.metric {
  font-size: 28px;
  font-weight: 700;
}

.risk-unread-btn {
  padding: 0;
  font-size: 13px;
}

.trust-card {
  margin-top: 16px;
}
</style>
