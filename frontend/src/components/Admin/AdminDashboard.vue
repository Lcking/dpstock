<template>
  <div class="admin-wrap">
    <div class="admin-header">
      <h1>管理后台</h1>
      <n-button quaternary @click="logout">退出</n-button>
    </div>

    <n-tabs type="line" animated v-model:value="tab">
      <n-tab-pane name="settings" tab="模型与设置">
        <n-p depth="3">覆盖环境变量中的 AI 接口（API_KEY 仍仅通过服务器环境变量配置）。</n-p>
        <n-form label-placement="left" label-width="140" style="max-width: 640px">
          <n-form-item label="ai.api_url">
            <n-input v-model:value="settingsForm['ai.api_url']" placeholder="https://..." />
          </n-form-item>
          <n-form-item label="ai.api_model">
            <n-input v-model:value="settingsForm['ai.api_model']" placeholder="模型 id" />
          </n-form-item>
          <n-form-item label="ai.api_timeout">
            <n-input v-model:value="settingsForm['ai.api_timeout']" placeholder="秒，整数" />
          </n-form-item>
          <n-form-item>
            <n-button type="primary" :loading="savingSettings" @click="saveSettings">保存</n-button>
            <n-button style="margin-left: 8px" @click="loadSettings">重新加载</n-button>
          </n-form-item>
        </n-form>
      </n-tab-pane>

      <n-tab-pane name="nav" tab="导航链接">
        <n-button type="primary" size="small" @click="loadNav">刷新</n-button>
        <n-data-table style="margin-top: 12px" :columns="navCols" :data="navRows" :bordered="false" />
        <n-divider>新增</n-divider>
        <n-space vertical style="max-width: 520px">
          <n-input v-model:value="navNew.label" placeholder="文案" />
          <n-input v-model:value="navNew.href" placeholder="https://..." />
          <n-input-number v-model:value="navNew.sort_order" placeholder="排序" />
          <n-button type="primary" @click="createNav">添加</n-button>
        </n-space>
      </n-tab-pane>

      <n-tab-pane name="articles" tab="文章">
        <n-space>
          <n-input v-model:value="articleQ" placeholder="搜索标题/代码" style="width: 220px" />
          <n-button @click="searchArticles">搜索</n-button>
        </n-space>
        <n-data-table style="margin-top: 12px" :columns="articleCols" :data="articleRows" :bordered="false" />
        <n-pagination
          v-if="articleTotal > 0"
          style="margin-top: 12px"
          v-model:page="articlePage"
          v-model:page-size="articlePageSize"
          :item-count="articleTotal"
          :page-sizes="[25, 50, 100]"
          show-size-picker
          @update:page="loadArticles"
          @update:page-size="onArticlePageSizeChange"
        />
        <n-modal v-model:show="articleModal" preset="card" style="width: 900px" title="编辑文章">
          <n-spin :show="articleLoading">
            <n-space vertical>
              <n-input v-model:value="articleEdit.title" placeholder="标题" />
              <n-input v-model:value="articleEdit.stock_code" placeholder="代码" />
              <n-input v-model:value="articleEdit.stock_name" placeholder="名称" />
              <n-input v-model:value="articleEdit.market_type" placeholder="市场" />
              <n-input v-model:value="articleEdit.publish_date" placeholder="发布日 YYYY-MM-DD" />
              <n-input
                v-model:value="articleEdit.content"
                type="textarea"
                placeholder="正文"
                :autosize="{ minRows: 12, maxRows: 40 }"
              />
              <n-button type="primary" @click="saveArticle">保存</n-button>
            </n-space>
          </n-spin>
        </n-modal>
      </n-tab-pane>

      <n-tab-pane name="users" tab="用户">
        <n-space vertical size="small">
          <n-space align="center">
            <n-input v-model:value="userQ" placeholder="user_id / 邮箱 / 昵称" style="width: 240px" />
            <n-button @click="searchUsers">搜索</n-button>
            <n-checkbox v-model:checked="usersOnlyEmailBound" @update:checked="onUsersEmailFilterChange">
              仅显示已绑定邮箱
            </n-checkbox>
          </n-space>
          <n-text depth="3" style="font-size: 12px">
            列表按注册时间倒序；匿名用户多时，可用「仅显示已绑定邮箱」或翻页查看。
          </n-text>
        </n-space>
        <n-data-table style="margin-top: 12px" :columns="userCols" :data="userRows" :bordered="false" />
        <n-pagination
          v-if="userTotal > 0"
          style="margin-top: 12px"
          v-model:page="userPage"
          v-model:page-size="userPageSize"
          :item-count="userTotal"
          :page-sizes="[25, 50, 100]"
          show-size-picker
          @update:page="loadUsers"
          @update:page-size="onUserPageSizeChange"
        />
      </n-tab-pane>

      <n-tab-pane name="invites" tab="邀请拉新">
        <n-descriptions v-if="inviteSummary" bordered size="small" style="max-width: 520px">
          <n-descriptions-item label="生成链接用户数">{{ inviteSummary.invite_codes_total }}</n-descriptions-item>
          <n-descriptions-item label="接受邀请数">{{ inviteSummary.invite_acceptances_total }}</n-descriptions-item>
          <n-descriptions-item label="奖励发放数">{{ inviteSummary.invite_rewards_total }}</n-descriptions-item>
          <n-descriptions-item label="接受率">{{ formatRate(inviteSummary.acceptance_rate) }}</n-descriptions-item>
          <n-descriptions-item label="奖励转化率">{{ formatRate(inviteSummary.reward_rate) }}</n-descriptions-item>
        </n-descriptions>
        <n-p depth="3" style="max-width: 720px; margin-top: 8px">
          生成链接只代表用户打开过邀请功能；接受邀请代表新用户访问过有效邀请链接；奖励发放代表被邀请者完成首次分析。
        </n-p>
        <n-h3 prefix="bar" style="margin-top: 16px">Top 邀请人</n-h3>
        <n-data-table :columns="inviterCols" :data="inviteSummary?.top_inviters || []" :bordered="false" />
        <n-h3 prefix="bar" style="margin-top: 16px">最近奖励</n-h3>
        <n-data-table :columns="rewardCols" :data="rewardRows" :bordered="false" />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>

<script setup lang="ts">
import { h, onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';
import type { DataTableColumns } from 'naive-ui';
import {
  NButton,
  NCheckbox,
  NDataTable,
  NDescriptions,
  NDescriptionsItem,
  NDivider,
  NForm,
  NFormItem,
  NH3,
  NInput,
  NInputNumber,
  NModal,
  NP,
  NPagination,
  NSpace,
  NSpin,
  NTabPane,
  NTabs,
  NText,
  useMessage,
} from 'naive-ui';
import { adminApi } from '@/services/adminApi';

const router = useRouter();
const message = useMessage();
const tab = ref('settings');

const settingsForm = ref<Record<string, string>>({
  'ai.api_url': '',
  'ai.api_model': '',
  'ai.api_timeout': '',
});
const savingSettings = ref(false);

async function loadSettings() {
  try {
    const { data } = await adminApi.getSettings();
    const eff = (data as { effective?: Record<string, string> }).effective || {};
    settingsForm.value = {
      'ai.api_url': eff['ai.api_url'] ?? '',
      'ai.api_model': eff['ai.api_model'] ?? '',
      'ai.api_timeout': eff['ai.api_timeout'] ?? '',
    };
  } catch {
    message.error('加载设置失败');
  }
}

async function saveSettings() {
  savingSettings.value = true;
  try {
    const body: Record<string, string> = {};
    for (const k of ['ai.api_url', 'ai.api_model', 'ai.api_timeout']) {
      const v = settingsForm.value[k]?.trim();
      if (v) body[k] = v;
    }
    if (Object.keys(body).length === 0) {
      message.warning('请至少填写一项再保存');
      return;
    }
    await adminApi.patchSettings(body);
    message.success('已保存（新分析请求将使用新配置）');
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败');
  } finally {
    savingSettings.value = false;
  }
}

const navRows = ref<any[]>([]);
const navNew = ref({ label: '', href: '', sort_order: 0 as number | null });
async function loadNav() {
  try {
    const { data } = await adminApi.listNavLinks();
    navRows.value = data.links || [];
  } catch {
    message.error('加载导航失败');
  }
}
async function createNav() {
  if (!navNew.value.label || !navNew.value.href) {
    message.warning('请填写文案与链接');
    return;
  }
  try {
    await adminApi.createNavLink({
      label: navNew.value.label,
      href: navNew.value.href,
      sort_order: navNew.value.sort_order ?? 0,
    });
    message.success('已添加');
    navNew.value = { label: '', href: '', sort_order: 0 };
    await loadNav();
  } catch (e: any) {
    message.error(e.response?.data?.detail || '添加失败');
  }
}
const navCols: DataTableColumns<any> = [
  { title: 'ID', key: 'id', width: 60 },
  { title: '文案', key: 'label' },
  { title: '链接', key: 'href', ellipsis: { tooltip: true } },
  { title: '排序', key: 'sort_order', width: 70 },
  {
    title: '启用',
    key: 'enabled',
    width: 70,
    render: (row) => (row.enabled ? '是' : '否'),
  },
  {
    title: '操作',
    key: 'actions',
    width: 160,
    render: (row) =>
      h(NSpace, {}, () => [
        h(
          NButton,
          {
            size: 'small',
            onClick: () => toggleNav(row),
          },
          () => (row.enabled ? '禁用' : '启用')
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            quaternary: true,
            onClick: () => removeNav(row.id),
          },
          () => '删'
        ),
      ]),
  },
];

async function toggleNav(row: any) {
  try {
    const on = Number(row.enabled) === 1;
    await adminApi.patchNavLink(row.id, { enabled: on ? 0 : 1 });
    await loadNav();
  } catch {
    message.error('更新失败');
  }
}
async function removeNav(id: number) {
  try {
    await adminApi.deleteNavLink(id);
    message.success('已删除');
    await loadNav();
  } catch {
    message.error('删除失败');
  }
}

const articleQ = ref('');
const articleRows = ref<any[]>([]);
const articlePage = ref(1);
const articlePageSize = ref(50);
const articleTotal = ref(0);
const articleModal = ref(false);
const articleLoading = ref(false);
const articleEdit = ref<Record<string, string>>({});
let articleEditId = 0;

async function loadArticles() {
  try {
    const offset = (articlePage.value - 1) * articlePageSize.value;
    const { data } = await adminApi.listArticles({
      limit: articlePageSize.value,
      offset,
      q: articleQ.value || undefined,
    });
    articleRows.value = data.articles || [];
    articleTotal.value = typeof data.total === 'number' ? data.total : articleRows.value.length;
  } catch {
    message.error('加载文章失败');
  }
}

function searchArticles() {
  articlePage.value = 1;
  loadArticles();
}

function onArticlePageSizeChange() {
  articlePage.value = 1;
  loadArticles();
}
async function openArticle(row: any) {
  articleEditId = row.id;
  articleModal.value = true;
  articleLoading.value = true;
  try {
    const { data } = await adminApi.getArticle(row.id);
    articleEdit.value = {
      title: data.title || '',
      stock_code: data.stock_code || '',
      stock_name: data.stock_name || '',
      market_type: data.market_type || '',
      publish_date: data.publish_date || '',
      content: data.content || '',
    };
  } catch {
    message.error('加载详情失败');
    articleModal.value = false;
  } finally {
    articleLoading.value = false;
  }
}
async function saveArticle() {
  try {
    await adminApi.patchArticle(articleEditId, { ...articleEdit.value });
    message.success('已保存');
    articleModal.value = false;
    await loadArticles();
  } catch (e: any) {
    message.error(e.response?.data?.detail || '保存失败');
  }
}
async function delArticle(id: number) {
  try {
    await adminApi.deleteArticle(id);
    message.success('已删除');
    await loadArticles();
  } catch {
    message.error('删除失败');
  }
}
const articleCols: DataTableColumns<any> = [
  { title: 'ID', key: 'id', width: 70 },
  { title: '标题', key: 'title', ellipsis: { tooltip: true } },
  { title: '代码', key: 'stock_code', width: 100 },
  { title: '发布日', key: 'publish_date', width: 120 },
  { title: '正文长度', key: 'content_length', width: 90 },
  {
    title: '操作',
    key: 'a',
    width: 160,
    render: (row) =>
      h(NSpace, {}, () => [
        h(NButton, { size: 'small', onClick: () => openArticle(row) }, () => '编辑'),
        h(
          NButton,
          { size: 'small', type: 'error', quaternary: true, onClick: () => delArticle(row.id) },
          () => '删'
        ),
      ]),
  },
];

const userQ = ref('');
const userRows = ref<any[]>([]);
const userPage = ref(1);
const userPageSize = ref(50);
const userTotal = ref(0);
const usersOnlyEmailBound = ref(false);

async function loadUsers() {
  try {
    const offset = (userPage.value - 1) * userPageSize.value;
    const { data } = await adminApi.listUsers({
      limit: userPageSize.value,
      offset,
      q: userQ.value || undefined,
      has_email: usersOnlyEmailBound.value ? 1 : undefined,
    });
    userRows.value = data.users || [];
    userTotal.value = typeof data.total === 'number' ? data.total : userRows.value.length;
  } catch {
    message.error('加载用户失败');
  }
}

function searchUsers() {
  userPage.value = 1;
  loadUsers();
}

function onUserPageSizeChange() {
  userPage.value = 1;
  loadUsers();
}

function onUsersEmailFilterChange() {
  userPage.value = 1;
  loadUsers();
}
async function setUserStatus(userId: string, status: 'active' | 'disabled') {
  try {
    await adminApi.patchUser(userId, status);
    message.success('已更新');
    await loadUsers();
  } catch {
    message.error('更新失败');
  }
}
const userCols: DataTableColumns<any> = [
  { title: 'user_id', key: 'user_id', ellipsis: { tooltip: true } },
  { title: '邮箱', key: 'primary_email', ellipsis: { tooltip: true } },
  { title: 'verified', key: 'email_verified', width: 90 },
  { title: '状态', key: 'status', width: 90 },
  {
    title: '操作',
    key: 'x',
    width: 160,
    render: (row) =>
      h(NSpace, {}, () => [
        h(
          NButton,
          {
            size: 'small',
            disabled: row.status === 'disabled',
            onClick: () => setUserStatus(row.user_id, 'disabled'),
          },
          () => '禁用'
        ),
        h(
          NButton,
          {
            size: 'small',
            disabled: row.status === 'active',
            onClick: () => setUserStatus(row.user_id, 'active'),
          },
          () => '启用'
        ),
      ]),
  },
];

const inviteSummary = ref<any>(null);
const rewardRows = ref<any[]>([]);

function formatRate(value: number | null | undefined) {
  if (typeof value !== 'number') return '—';
  return `${value.toFixed(1)}%`;
}
const inviterCols: DataTableColumns<any> = [
  { title: 'inviter_id', key: 'inviter_id', ellipsis: { tooltip: true } },
  { title: '次数', key: 'invite_count', width: 80 },
];
const rewardCols: DataTableColumns<any> = [
  { title: 'id', key: 'id', width: 60 },
  { title: '邀请人', key: 'inviter_id', ellipsis: { tooltip: true } },
  { title: '被邀请', key: 'invitee_id', ellipsis: { tooltip: true } },
  { title: 'code', key: 'invite_code', width: 100 },
  { title: 'quota', key: 'reward_quota', width: 70 },
  { title: '日期', key: 'reward_date', width: 110 },
];

async function loadInvites() {
  try {
    const [s, r] = await Promise.all([adminApi.inviteSummary(), adminApi.inviteRewards({ limit: 50 })]);
    inviteSummary.value = s.data;
    rewardRows.value = r.data.rewards || [];
  } catch {
    message.error('加载邀请数据失败');
  }
}

function logout() {
  localStorage.removeItem('admin_token');
  router.replace('/admin/login');
}

onMounted(async () => {
  try {
    await adminApi.me();
  } catch {
    message.error('登录已失效');
    router.replace('/admin/login');
    return;
  }
  await Promise.all([loadSettings(), loadNav(), loadArticles(), loadUsers(), loadInvites()]);
});
</script>

<style scoped>
.admin-wrap {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px 16px 48px;
}
.admin-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;
}
.admin-header h1 {
  margin: 0;
  font-size: 1.35rem;
}
</style>
