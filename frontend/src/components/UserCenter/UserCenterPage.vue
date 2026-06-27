<template>
  <div class="user-center-page">
    <div class="page-header">
      <div>
        <h1>我的</h1>
        <p>在这里统一查看绑定状态、额度、观察与判断资产。</p>
      </div>
    </div>

    <n-alert
      v-if="overview?.user?.is_temporary && guestAssetSummary"
      type="warning"
      :bordered="false"
      class="top-alert"
    >
      {{ guestAssetSummary }}
      <template v-if="overview.watchlist_items_count > 0 || overview.judgment_count > 0">
        <n-button size="small" type="primary" secondary style="margin-top: 8px" @click="showBindDialog = true">
          立即绑定邮箱
        </n-button>
      </template>
    </n-alert>

    <n-alert
      v-else-if="overview?.user?.is_temporary"
      type="warning"
      :bordered="false"
      class="top-alert"
    >
      当前仍是游客模式。绑定邮箱后，你的观察列表和判断日记可长期保存，并支持跨设备同步。
    </n-alert>

    <n-alert
      v-if="overview?.due_count > 0"
      type="info"
      :bordered="false"
      class="top-alert"
    >
      你有 {{ overview.due_count }} 条判断待复盘，及时复盘有助于沉淀个人验证记录。
      <n-button size="small" tertiary type="primary" style="margin-left: 8px" @click="router.push('/journal')">
        去复盘
      </n-button>
    </n-alert>

    <div v-if="loading" class="loading-area">
      <n-grid cols="1 s:2 xl:4" :x-gap="16" :y-gap="16" responsive="screen">
        <n-grid-item v-for="idx in 4" :key="idx">
          <n-card size="small">
            <n-skeleton text :repeat="4" />
          </n-card>
        </n-grid-item>
      </n-grid>
      <n-card size="small" class="trust-skeleton-card">
        <n-skeleton text :repeat="3" />
      </n-card>
    </div>

    <n-alert v-else-if="errorMessage" type="error" :bordered="false" class="top-alert">
      <div class="error-alert-content">
        <span>{{ errorMessage }}</span>
        <n-button size="small" tertiary type="primary" @click="loadOverview">重新加载</n-button>
      </div>
    </n-alert>

    <template v-else-if="overview">
      <UserOverviewCards
        :overview="overview"
        @bind="showBindDialog = true"
        @invite="showInviteDialog = true"
        @go-watchlist="handleGoWatchlist"
        @go-journal="router.push('/journal')"
      />

      <n-grid cols="1 xl:3" :x-gap="16" :y-gap="16" responsive="screen" class="content-grid">
        <n-grid-item span="1 xl:2">
          <n-card title="最近判断" size="small">
            <template v-if="overview.recent_judgments?.length">
              <n-space vertical :size="12">
                <div
                  v-for="record in overview.recent_judgments"
                  :key="record.id"
                  class="judgment-item judgment-item-clickable"
                  role="button"
                  tabindex="0"
                  @click="handleJudgmentClick(record)"
                  @keydown.enter.prevent="handleJudgmentClick(record)"
                >
                  <div class="judgment-item-header">
                    <strong>{{ record.ts_code }}</strong>
                    <n-tag size="small" :type="record.status === 'due' ? 'warning' : 'info'">
                      {{ statusLabel(record.status) }}
                    </n-tag>
                  </div>
                  <div class="judgment-item-meta">
                    候选 {{ record.candidate }} · {{ formatDate(record.created_at) }}
                  </div>
                </div>
              </n-space>
            </template>
            <n-empty v-else description="还没有判断记录" size="small" />
          </n-card>
        </n-grid-item>

        <n-grid-item>
          <n-card title="通知设置" size="small" class="settings-card">
            <n-space vertical :size="10">
              <div class="notify-pref-row">
                <div>
                  <div class="notify-pref-title">邮件风险提醒</div>
                  <n-text depth="3" class="notify-pref-hint">
                    自选股命中 ST / 连板等风险标签时，收盘后发送摘要邮件。
                  </n-text>
                </div>
                <n-switch
                  :value="riskAlertEmailEnabled"
                  :disabled="notifyPrefDisabled"
                  :loading="notifyPrefSaving"
                  @update:value="handleNotifyPrefChange"
                />
              </div>
              <n-text v-if="notifyPrefHint" depth="3" class="notify-pref-note">
                {{ notifyPrefHint }}
              </n-text>
            </n-space>
          </n-card>

          <n-card title="下一步动作" size="small" class="actions-card">
            <n-space vertical :size="12">
              <n-button
                v-if="overview.risk_alert_unread_count > 0"
                block
                type="warning"
                secondary
                @click="handleGoWatchlist({ focus: 'risk' })"
              >
                查看 {{ overview.risk_alert_unread_count }} 条风险提醒
              </n-button>
              <n-button block @click="router.push('/watchlist')">去我的观察</n-button>
              <n-button block @click="router.push('/journal')">去判断日记</n-button>
              <n-button block @click="showInviteDialog = true">额度与邀请</n-button>
              <n-button
                v-if="overview.user.is_temporary"
                block
                type="primary"
                @click="showBindDialog = true"
              >
                绑定邮箱
              </n-button>
            </n-space>
          </n-card>
        </n-grid-item>
      </n-grid>
    </template>

    <AnchorBindDialog v-model:show="showBindDialog" @bind-success="handleBindSuccess" />
    <InviteDialog
      v-model:show="showInviteDialog"
      :quota-status="overview?.quota_status"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NGrid,
  NGridItem,
  NSkeleton,
  NSpace,
  NSwitch,
  NTag,
  NText,
  useMessage,
} from 'naive-ui'
import { apiService } from '@/services/api'
import { applyPageSeo } from '@/utils/seo'
import AnchorBindDialog from '@/components/AnchorBindDialog.vue'
import InviteDialog from '@/components/InviteDialog.vue'
import UserOverviewCards from './UserOverviewCards.vue'

const router = useRouter()
const message = useMessage()

const loading = ref(false)
const overview = ref<any>(null)
const errorMessage = ref('')
const showBindDialog = ref(false)
const showInviteDialog = ref(false)
const notifyPrefSaving = ref(false)

const guestAssetSummary = computed(() => {
  if (!overview.value?.user?.is_temporary) return ''
  const watchCount = overview.value.watchlist_items_count || 0
  const judgmentCount = overview.value.judgment_count || 0
  if (watchCount <= 0 && judgmentCount <= 0) return ''
  const parts: string[] = []
  if (watchCount > 0) parts.push(`${watchCount} 只观察标的`)
  if (judgmentCount > 0) parts.push(`${judgmentCount} 条判断记录`)
  return `你当前已有 ${parts.join('、')}，绑定邮箱后可跨设备长期保存。`
})

const riskAlertEmailEnabled = computed(() =>
  Boolean(overview.value?.user?.notify_pref?.risk_alert_email)
)

const notifyPrefDisabled = computed(() => {
  if (!overview.value?.user) return true
  if (overview.value.user.is_temporary) return true
  if (!overview.value.user.email_verified) return true
  return false
})

const notifyPrefHint = computed(() => {
  if (!overview.value?.user) return ''
  if (overview.value.user.is_temporary) {
    return '绑定并验证邮箱后，可接收自选风险邮件提醒。'
  }
  if (!overview.value.user.email_verified) {
    return '邮箱验证完成后即可开启邮件提醒。'
  }
  return ''
})

const handleJudgmentClick = (record: { id: string; status?: string }) => {
  router.push({
    path: '/journal',
    query: {
      record: record.id,
      ...(record.status === 'due' ? { action: 'review' } : {}),
    },
  })
}

const handleNotifyPrefChange = async (enabled: boolean) => {
  if (notifyPrefDisabled.value || notifyPrefSaving.value) return
  notifyPrefSaving.value = true
  try {
    const data = await apiService.updateNotifyPref(enabled)
    if (overview.value?.user) {
      overview.value = {
        ...overview.value,
        user: {
          ...overview.value.user,
          notify_pref: data.notify_pref,
        },
      }
    }
    message.success(enabled ? '已开启邮件风险提醒' : '已关闭邮件风险提醒')
  } catch (error) {
    console.error('Update notify pref error:', error)
    message.error('更新通知设置失败')
  } finally {
    notifyPrefSaving.value = false
  }
}

const handleGoWatchlist = (payload?: { focus?: string }) => {
  if (payload?.focus === 'risk') {
    router.push({ path: '/watchlist', query: { focus: 'risk' } })
    return
  }
  router.push('/watchlist')
}

const loadOverview = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    overview.value = await apiService.getUserCenterOverview()
  } catch (error) {
    console.error('Load user center overview error:', error)
    overview.value = null
    errorMessage.value = '加载用户中心失败，请稍后重试。'
    message.error('加载用户中心失败')
  } finally {
    loading.value = false
  }
}

const handleBindSuccess = async () => {
  message.success('邮箱已绑定，个人资产已升级为长期保存')
  await loadOverview()
}

const statusLabel = (status: string) => {
  const map: Record<string, string> = {
    active: '活跃',
    due: '待复盘',
    reviewed: '已复盘',
    archived: '已归档'
  }
  return map[status] || status
}

const formatDate = (value: string) => {
  if (!value) return '--'
  return new Date(value).toLocaleDateString('zh-CN')
}

onMounted(() => {
  applyPageSeo({
    title: '用户中心 | Agu AI',
    description: '查看绑定状态、额度、观察与判断资产。',
    canonicalPath: '/me',
    robots: 'noindex, nofollow',
  })
  loadOverview()
})
</script>

<style scoped>
.user-center-page {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.page-header {
  margin-bottom: 20px;
}

.page-header h1 {
  margin: 0 0 8px;
  font-size: 28px;
}

.page-header p {
  margin: 0;
  color: var(--n-text-color-3);
}

.top-alert {
  margin-bottom: 20px;
}

.error-alert-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.loading-area {
  display: flex;
  flex-direction: column;
  gap: 16px;
  padding: 8px 0 40px;
}

.trust-skeleton-card {
  margin-top: 4px;
}

.content-grid {
  margin-top: 20px;
}

.judgment-item {
  padding: 12px;
  border: 1px solid var(--n-border-color);
  border-radius: 10px;
  background: var(--n-color-embedded);
}

.judgment-item-clickable {
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease;
}

.judgment-item-clickable:hover,
.judgment-item-clickable:focus-visible {
  border-color: var(--n-primary-color);
  background: var(--n-color-hover);
  outline: none;
}

.settings-card {
  margin-bottom: 16px;
}

.notify-pref-row {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.notify-pref-title {
  font-weight: 600;
  margin-bottom: 4px;
}

.notify-pref-hint,
.notify-pref-note {
  font-size: 13px;
  line-height: 1.5;
}

.judgment-item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.judgment-item-meta {
  margin-top: 6px;
  font-size: 13px;
  color: var(--n-text-color-3);
}
</style>
