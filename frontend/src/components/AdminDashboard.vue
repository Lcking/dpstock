<template>
  <div class="admin-dashboard">
    <n-page-header title="系统管理后台" subtitle="数据概览与用户清单">
      <template #extra>
        <n-button secondary type="error" @click="handleLogout">退出管理</n-button>
      </template>
    </n-page-header>

    <n-grid :cols="4" :x-gap="12" style="margin-top: 20px">
      <n-gi>
        <n-statistic label="已绑定用户" :value="stats.total_anchors">
          <template #prefix>
            <n-icon><UserIcon /></n-icon>
          </template>
        </n-statistic>
      </gi>
      <n-gi>
        <n-statistic label="总判断数" :value="stats.total_judgments">
          <template #prefix>
            <n-icon><FileIcon /></n-icon>
          </template>
        </n-statistic>
      </gi>
      <n-gi>
        <n-statistic label="24h新增用户" :value="stats.recent_anchors_24h">
          <template #prefix>
            <n-icon><TrendIcon /></n-icon>
          </template>
        </n-statistic>
      </gi>
      <n-gi>
        <n-statistic label="结构成立数" :value="stats.confirmed_judgments">
          <template #prefix>
            <n-icon><CheckIcon /></n-icon>
          </template>
        </n-statistic>
      </gi>
    </n-grid>

    <n-divider />

    <n-card title="注册用户列表 (最近 50 名)" style="margin-top: 12px">
      <n-table :bordered="false" :single-line="false">
        <thead>
          <tr>
            <th>邮箱 (脱敏)</th>
            <th>唯一 ID</th>
            <th>绑定时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.anchor_id">
            <td>
              <n-tag type="info" size="small">{{ user.email }}</n-tag>
            </td>
            <td><n-text depth="3" style="font-size: 12px">{{ user.anchor_id }}</n-text></td>
            <td>{{ formatDate(user.created_at) }}</td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="3" style="text-align: center; padding: 40px">
              <n-empty description="暂无已绑定用户" />
            </td>
          </tr>
        </tbody>
      </n-table>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { 
  NPageHeader, NGrid, NGi, NStatistic, NIcon, NCard, 
  NTable, NTag, NText, NDivider, NButton, NEmpty, useMessage 
} from 'naive-ui';
import { 
  PersonOutline as UserIcon, 
  StatsChartOutline as TrendIcon,
  DocumentTextOutline as FileIcon,
  CheckmarkCircleOutline as CheckIcon
} from '@vicons/ionicons5';

const stats = ref<any>({
  total_anchors: 0,
  total_judgments: 0,
  recent_anchors_24h: 0,
  confirmed_judgments: 0
});

const users = ref<any[]>([]);
const message = useMessage();
const adminToken = localStorage.getItem('admin_token') || 'stock-admin-2026';

async function fetchStats() {
  try {
    const res = await fetch('/api/admin/stats', {
      headers: { 'X-Admin-Token': adminToken }
    });
    if (res.ok) {
      stats.value = await res.json();
    } else {
      message.error('无法获取统计数据, 请核对管理权限');
    }
  } catch (err) {
    console.error(err);
  }
}

async function fetchUsers() {
  try {
    const res = await fetch('/api/admin/users', {
      headers: { 'X-Admin-Token': adminToken }
    });
    if (res.ok) {
      users.value = await res.json();
    }
  } catch (err) {
    console.error(err);
  }
}

function formatDate(dateStr: string) {
  if (!dateStr) return '';
  const date = new Date(dateStr.endsWith('Z') ? dateStr : dateStr + 'Z');
  return date.toLocaleString();
}

function handleLogout() {
  localStorage.removeItem('admin_token');
  window.location.reload();
}

onMounted(() => {
  fetchStats();
  fetchUsers();
});
</script>

<style scoped>
.admin-dashboard {
  padding: 24px;
  background: #fdfdfd;
  min-height: 100vh;
}
</style>
