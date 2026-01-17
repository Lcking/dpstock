<template>
  <div class="my-judgments-container">
    <n-card title="我的判断记录">
      <template #header-extra>
        <n-space align="center">
          <!-- Anchor Status -->
          <AnchorStatus @show-bind="showBindDialog = true" />
          
          <n-divider vertical />
          
          <n-text depth="3">共 {{ judgments.length }} 条</n-text>
          <n-button size="small" @click="loadJudgments">
            <template #icon>
              <n-icon><RefreshIcon /></n-icon>
            </template>
            刷新
          </n-button>
        </n-space>
      </template>

      <n-data-table
        :columns="columns"
        :data="judgments"
        :loading="loading"
        :pagination="{ pageSize: 10 }"
        :row-key="(row: Judgment) => row.judgment_id"
        :bordered="false"
        striped
      />

      <template v-if="judgments.length === 0 && !loading">
        <n-empty description="暂无判断记录" size="large">
          <template #icon>
            <n-icon><DocumentIcon /></n-icon>
          </template>
          <template #extra>
            <n-button @click="$router.push('/')">
              去分析页面
            </n-button>
          </template>
        </n-empty>
      </template>
    </n-card>

    <!-- Judgment Detail Modal -->
    <n-modal
      v-model:show="showDetailModal"
      preset="card"
      title="判断详情"
      style="width: 90%; max-width: 800px;"
      :bordered="false"
      size="huge"
    >
      <template v-if="selectedJudgment">
        <n-descriptions bordered :column="2">
          <n-descriptions-item label="股票代码">
            {{ selectedJudgment.stock_code }}
          </n-descriptions-item>
          <n-descriptions-item label="快照时间">
            {{ new Date(selectedJudgment.snapshot_time).toLocaleString('zh-CN') }}
          </n-descriptions-item>
          <n-descriptions-item label="结构类型">
            {{ getStructureTypeName(selectedJudgment.structure_type) }}
          </n-descriptions-item>
          <n-descriptions-item label="MA200位置">
            {{ getMA200PositionName(selectedJudgment.ma200_position) }}
          </n-descriptions-item>
          <n-descriptions-item label="阶段">
            {{ getPhaseName(selectedJudgment.phase) }}
          </n-descriptions-item>
          <n-descriptions-item label="选择前提">
            {{ selectedJudgment.selected_candidates.join(', ') }}
          </n-descriptions-item>
          <n-descriptions-item label="验证周期">
            {{ selectedJudgment.verification_period || 7 }} 天
          </n-descriptions-item>
        </n-descriptions>

        <n-divider>当前验证状态</n-divider>

        <template v-if="selectedJudgment.latest_check">
          <n-space vertical>
            <n-space align="center">
              <n-text strong>结构状态:</n-text>
              <n-tag
                :type="statusConfig[selectedJudgment.latest_check.current_structure_status].color as any"
                size="medium"
              >
                {{ statusConfig[selectedJudgment.latest_check.current_structure_status].icon }}
                {{ statusConfig[selectedJudgment.latest_check.current_structure_status].text }}
              </n-tag>
            </n-space>

            <!-- Wyckoff II Status Guide -->
            <JudgmentStatusGuide
              :status="selectedJudgment.latest_check.current_structure_status"
            />

            <n-space align="center">
              <n-text strong>当前价格:</n-text>
              <n-text>{{ selectedJudgment.latest_check.current_price.toFixed(2) }}</n-text>
            </n-space>

            <n-space align="center">
              <n-text strong>价格变化:</n-text>
              <n-text
                :type="selectedJudgment.latest_check.price_change_pct >= 0 ? 'success' : 'error'"
              >
                {{ (selectedJudgment.latest_check.price_change_pct >= 0 ? '+' : '') }}
                {{ selectedJudgment.latest_check.price_change_pct.toFixed(2) }}%
              </n-text>
            </n-space>

            <n-space vertical v-if="selectedJudgment.latest_check.reasons.length > 0">
              <n-text strong>验证原因:</n-text>
              <ul style="margin: 0; padding-left: 20px;">
                <li v-for="(reason, idx) in selectedJudgment.latest_check.reasons" :key="idx">
                  {{ reason }}
                </li>
              </ul>
            </n-space>

            <n-text depth="3" style="font-size: 12px;">
              验证时间: {{ selectedJudgment.latest_check.verification_time ? new Date(selectedJudgment.latest_check.verification_time).toLocaleString('zh-CN') : '未知' }}
            </n-text>
          </n-space>
        </template>

        <template v-else>
          <n-empty description="暂无验证数据" size="small" />
        </template>
      </template>
    </n-modal>
    
    <!-- Anchor Bind Dialog -->
    <AnchorBindDialog
      v-model:show="showBindDialog"
      @bind-success="handleBindSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, h } from 'vue';
import JudgmentStatusGuide from '@/components/WyckoffGuide/JudgmentStatusGuide.vue';
import AnchorStatus from '@/components/AnchorStatus.vue';
import AnchorBindDialog from '@/components/AnchorBindDialog.vue';
import {
  NCard,
  NDataTable,
  NButton,
  NSpace,
  NText,
  NIcon,
  NProgress,
  NEmpty,
  NTag,
  NCollapse,
  NDivider,
  NCollapseItem,
  NPopconfirm,
  NModal,
  NDescriptions,
  NDescriptionsItem,
  useMessage,
  type DataTableColumns
} from 'naive-ui';
import {
  RefreshOutline as RefreshIcon,
  DocumentTextOutline as DocumentIcon
} from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import type { Judgment } from '@/types/judgment';

const message = useMessage();

const loading = ref(false);
const judgments = ref<Judgment[]>([]);
const showDetailModal = ref(false);
const selectedJudgment = ref<Judgment | null>(null);
const showBindDialog = ref(false);


// 状态标签配置
const statusConfig = {
  maintained: { color: 'success', icon: '🟢', text: '保持' },
  weakened: { color: 'warning', icon: '🟡', text: '削弱' },
  broken: { color: 'error', icon: '🔴', text: '破坏' }
};

// 表格列定义
const columns: DataTableColumns<Judgment> = [
  {
    title: '股票代码',
    key: 'stock_code',
    width: 100,
    fixed: 'left'
  },
  {
    title: '结构类型',
    key: 'structure_type',
    width: 100,
    render(row: Judgment) {
      const typeMap: Record<string, string> = {
        'consolidation': '盘整',
        'uptrend': '上升',
        'downtrend': '下降'
      };
      return typeMap[row.structure_type] || row.structure_type;
    }
  },
  {
    title: 'MA200位置',
    key: 'ma200_position',
    width: 100,
    render(row: Judgment) {
      const posMap: Record<string, string> = {
        'above': '上方',
        'below': '下方',
        'near': '接近',
        'no_data': '无数据'
      };
      return posMap[row.ma200_position] || row.ma200_position;
    }
  },
  {
    title: '阶段',
    key: 'phase',
    width: 80,
    render(row: Judgment) {
      const phaseMap: Record<string, string> = {
        'early': '早期',
        'middle': '中期',
        'late': '后期',
        'unclear': '不明'
      };
      return phaseMap[row.phase] || row.phase;
    }
  },
  {
    title: '选择前提',
    key: 'selected_candidates',
    width: 100,
    render(row: Judgment) {
      return row.selected_candidates.join(', ');
    }
  },
  {
    title: '验证进度',
    key: 'progress',
    width: 140,
    render(row: Judgment) {
      if (!row.latest_check) return h(NTag, { size: 'small', type: 'default', bordered: false }, { default: () => '等待验证' });

      // 如果结构破坏，直接显示失效及天数
      const status = row.latest_check.current_structure_status;
      const createdTime = new Date(row.created_at).getTime();
      const checkTime = new Date(row.latest_check.check_time).getTime(); // 使用检查时间更准确
      const daysPassed = Math.ceil((checkTime - createdTime) / (1000 * 60 * 60 * 24));
      const period = row.verification_period || 7;
      
      // 1. 结构已被破坏
      if (status === 'broken') {
        return h(NTag, { size: 'small', type: 'error' }, { default: () => `❌ DAY ${daysPassed} 失效` });
      }

      // 2. 验证期满且维持
      if (daysPassed >= period && (status === 'maintained' || status === 'weakened')) {
         return h(NTag, { size: 'small', type: 'success' }, { default: () => `✅ 成功 (${period}天)` });
      }

      // 3. 进行中
      return h(
        NSpace,
        { size: 'small', align: 'center' },
        { 
          default: () => [
            h(NProgress, {
              type: 'circle',
              percentage: Math.min(100, Math.round((daysPassed / period) * 100)),
              style: { width: '24px', height: '24px' },
              showIndicator: false
            }),
            h('span', `DAY ${daysPassed}/${period}`)
          ]
        }
      );
    }
  },
  {
    title: '当前状态',
    key: 'status',
    width: 100,
    render(row: Judgment) {
      if (!row.latest_check) {
        return h(NTag, { size: 'small', type: 'default' }, { default: () => '未验证' });
      }
      
      const status = row.latest_check.current_structure_status;
      const config = statusConfig[status];
      
      return h(
        NTag,
        { size: 'small', type: config.color as any },
        { default: () => `${config.icon} ${config.text}` }
      );
    }
  },
  {
    title: '价格变化',
    key: 'price_change',
    width: 100,
    render(row: Judgment) {
      if (!row.latest_check) return '--';
      
      const pct = row.latest_check.price_change_pct;
      const sign = pct >= 0 ? '+' : '';
      const color = pct >= 0 ? 'success' : 'error';
      
      return h(
        NText,
        { type: color as any },
        { default: () => `${sign}${pct.toFixed(2)}%` }
      );
    }
  },
  {
    title: '原因',
    key: 'reasons',
    width: 300,
    render(row: Judgment) {
      if (!row.latest_check || !row.latest_check.reasons.length) {
        return '--';
      }
      
      return h(
        NCollapse,
        { defaultExpandedNames: [] },
        {
          default: () => h(
            NCollapseItem,
            { title: `查看原因 (${row.latest_check!.reasons.length})`, name: '1' },
            {
              default: () => h(
                'ul',
                { style: 'margin: 0; padding-left: 20px;' },
                row.latest_check!.reasons.map(reason => 
                  h('li', { style: 'margin: 4px 0;' }, reason)
                )
              )
            }
          )
        }
      );
    }
  },
  {
    title: '快照时间',
    key: 'snapshot_time',
    width: 150,
    render(row: Judgment) {
      return new Date(row.snapshot_time).toLocaleString('zh-CN');
    }
  },
  {
    title: '操作',
    key: 'actions',
    width: 150,
    fixed: 'right',
    render(row: Judgment) {
      return h(
        NSpace,
        { size: 'small' },
        {
          default: () => [
            h(
              NButton,
              {
                size: 'small',
                onClick: () => viewDetail(row.judgment_id)
              },
              { default: () => '查看详情' }
            ),
            h(
              NPopconfirm,
              {
                onPositiveClick: () => handleDelete(row.judgment_id),
                positiveText: '确认删除',
                negativeText: '取消'
              },
              {
                default: () => '确定要删除这条判断吗?此操作不可撤销。',
                trigger: () => h(
                  NButton,
                  {
                    size: 'small',
                    type: 'error',
                    secondary: true
                  },
                  { default: () => '删除' }
                )
              }
            )
          ]
        }
      );
    }
  }
];

// 加载判断列表
async function loadJudgments() {
  loading.value = true;
  try {
    const response = await apiService.getMyJudgments(50);
    judgments.value = response.judgments || [];
  } catch (error) {
    console.error('加载判断列表失败:', error);
    message.error('加载判断列表失败');
  } finally {
    loading.value = false;
  }
}

// Handle bind success
function handleBindSuccess(data: any) {
  console.log('[MyJudgments] Bind success:', data);
  message.success(`已绑定邮箱,迁移了 ${data.migrated_count} 条判断`);
  // Reload judgments to reflect ownership change
  loadJudgments();
}

// 删除判断
async function handleDelete(judgmentId: string) {
  try {
    await apiService.deleteJudgment(judgmentId);
    message.success('删除成功');
    // Reload judgments
    await loadJudgments();
  } catch (error: any) {
    console.error('删除失败:', error);
    message.error(error.response?.data?.detail || '删除失败');
  }
}

// 查看详情
function viewDetail(judgmentId: string) {
  const judgment = judgments.value.find(j => j.judgment_id === judgmentId);
  if (judgment) {
    selectedJudgment.value = judgment;
    showDetailModal.value = true;
  }
}

// Helper functions for display names
function getStructureTypeName(type: string): string {
  const map: Record<string, string> = {
    'consolidation': '盘整',
    'uptrend': '上升',
    'downtrend': '下降'
  };
  return map[type] || type;
}

function getMA200PositionName(pos: string): string {
  const map: Record<string, string> = {
    'above': '上方',
    'below': '下方',
    'near': '接近',
    'no_data': '无数据'
  };
  return map[pos] || pos;
}

function getPhaseName(phase: string): string {
  const map: Record<string, string> = {
    'early': '早期',
    'middle': '中期',
    'late': '后期',
    'unclear': '不明'
  };
  return map[phase] || phase;
}

// 组件挂载时加载数据
onMounted(() => {
  loadJudgments();
});
</script>

<style scoped>
.my-judgments-container {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

@media (max-width: 768px) {
  .my-judgments-container {
    padding: 10px;
  }
}
</style>
