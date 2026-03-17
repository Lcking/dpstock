<template>
  <div class="user-center-page">
    <div class="page-header">
      <div>
        <h1>我的</h1>
        <p>在这里统一查看绑定状态、额度、观察与判断资产。</p>
      </div>
    </div>

    <n-alert
      v-if="overview?.user?.is_temporary"
      type="warning"
      :bordered="false"
      class="top-alert"
    >
      当前仍是游客模式。绑定邮箱后，你的观察列表和判断日记可长期保存，并支持跨设备同步。
    </n-alert>

    <div v-if="loading" class="loading-area">
      <n-spin size="large" />
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
        @go-watchlist="router.push('/watchlist')"
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
                  class="judgment-item"
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
          <n-card title="下一步动作" size="small">
            <n-space vertical :size="12">
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
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import {
  NAlert,
  NButton,
  NCard,
  NEmpty,
  NGrid,
  NGridItem,
  NSpace,
  NSpin,
  NTag,
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
  justify-content: center;
  padding: 80px 0;
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
