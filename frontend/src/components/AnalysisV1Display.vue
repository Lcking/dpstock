<template>
  <div class="analysis-v1-display">
    <!-- Section 1: 结构快照 -->
    <div class="analysis-section structure-snapshot">
      <h3 class="section-title">📊 结构快照</h3>
      <n-descriptions :column="2" bordered size="small">
        <n-descriptions-item label="结构类型">
          <n-tag :type="getStructureTypeColor(data.structure_snapshot.structure_type)" size="small">
            {{ getStructureTypeName(data.structure_snapshot.structure_type) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="MA200位置">
          <n-tag :type="getMA200PositionColor(data.structure_snapshot.ma200_position)" size="small">
            {{ getMA200PositionName(data.structure_snapshot.ma200_position) }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="阶段">
          <n-tag size="small">{{ getPhaseName(data.structure_snapshot.phase) }}</n-tag>
        </n-descriptions-item>
      </n-descriptions>
      
      <div class="key-levels" v-if="data.structure_snapshot.key_levels.length > 0">
        <h4>关键价格位</h4>
        <n-space>
          <n-tag v-for="level in data.structure_snapshot.key_levels" :key="level.label" type="info" size="small">
            {{ level.label }}: {{ level.price.toFixed(2) }}
          </n-tag>
        </n-space>
      </div>
      
      <div class="trend-description markdown-content" v-html="renderMarkdown(data.structure_snapshot.trend_description)"></div>
    </div>

    <!-- Section 2: 形态拟合 -->
    <div class="analysis-section pattern-fitting">
      <h3 class="section-title">📐 形态拟合</h3>
      <n-descriptions :column="2" bordered size="small">
        <n-descriptions-item label="形态类型">
          <n-tag size="small">{{ getPatternTypeName(data.pattern_fitting.pattern_type) }}</n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="完成度" v-if="data.pattern_fitting.completion_rate !== null">
          <n-progress 
            type="line" 
            :percentage="data.pattern_fitting.completion_rate" 
            :show-indicator="true"
            :height="12"
          />
        </n-descriptions-item>
      </n-descriptions>
      <div class="pattern-description markdown-content" v-html="renderMarkdown(data.pattern_fitting.pattern_description)"></div>
    </div>

    <!-- Section 3: 指标翻译 -->
    <div class="analysis-section indicator-translate">
      <h3 class="section-title">📈 指标翻译</h3>
      <div v-if="turnoverIndicator" class="turnover-highlight">
        <div class="turnover-highlight-header">
          <strong>换手率</strong>
          <n-tag :type="getSignalColor(turnoverIndicator.signal)" size="small">
            {{ turnoverActivityLabel }}
          </n-tag>
        </div>
        <div class="turnover-highlight-value">{{ turnoverIndicator.value }}</div>
        <div class="turnover-highlight-note">
          {{ extractPlainText(turnoverIndicator.interpretation) }}
        </div>
        <div class="turnover-highlight-tip">
          它回答的是“这只股票当前热不热”，不等同于资金净流入或主力净买入。
        </div>
      </div>
      <div class="indicators-list">
        <div v-for="indicator in displayIndicators" :key="indicator.name" class="indicator-item">
          <div class="indicator-header">
            <strong>{{ indicator.name }}</strong>
            <n-tag :type="getSignalColor(indicator.signal)" size="small">
              {{ getSignalName(indicator.signal) }}
            </n-tag>
          </div>
          <div class="indicator-value">值: {{ indicator.value }}</div>
          <div class="indicator-interpretation markdown-content" v-html="renderMarkdown(indicator.interpretation)"></div>
        </div>
      </div>
      <n-alert type="info" :bordered="false" class="global-note">
        <div class="markdown-content" v-html="renderMarkdown(data.indicator_translate.global_note)"></div>
      </n-alert>
    </div>

    <!-- Section 4: 误读风险 -->
    <div class="analysis-section risk-of-misreading">
      <h3 class="section-title">⚠️ 误读风险</h3>
      <n-alert :type="getRiskLevelType(data.risk_of_misreading.risk_level)" :bordered="false">
        <template #header>
          风险等级: {{ getRiskLevelName(data.risk_of_misreading.risk_level) }}
        </template>
        <ul class="risk-factors">
          <li v-for="(factor, idx) in data.risk_of_misreading.risk_factors" :key="idx">
            {{ factor }}
          </li>
        </ul>
        <div class="risk-flags" v-if="data.risk_of_misreading.risk_flags.length > 0">
          <n-space>
            <n-tag v-for="flag in data.risk_of_misreading.risk_flags" :key="flag" type="warning" size="small">
              {{ flag }}
            </n-tag>
          </n-space>
        </div>
        <div class="caution-note markdown-content">
          <strong>注意:</strong>
          <div v-html="renderMarkdown(data.risk_of_misreading.caution_note)"></div>
        </div>
      </n-alert>
    </div>

    <!-- Tushare Enhancement Cards (新增增强数据卡片区) -->
    <div class="analysis-section enhancements-section" v-if="stockCode">
      <h3 class="section-title">📊 数据增强</h3>
      <EnhancementCards :stock-code="stockCode" />
    </div>

    <!-- Section 5: 判断区 -->
    <!-- Wyckoff II Pre-Judgment Reminder -->
    <JudgmentPreReminder
      v-if="!hideJudgmentZone"
      :risk-flags="data.risk_of_misreading?.risk_flags || []"
      :expand-by-default="false"
    />

    <div v-if="!hideJudgmentZone" class="analysis-section judgment-zone">
      <h3 class="section-title">🎯 判断区</h3>
      
      <n-radio-group v-model:value="selectedCandidate" class="candidates-group">
        <n-space vertical>
          <n-radio
            v-for="candidate in data.judgment_zone.candidates"
            :key="candidate.option_id"
            :value="candidate.option_id"
            class="candidate-radio"
          >
            <div class="candidate-content">
              <strong class="candidate-id">{{ candidate.option_id }}.</strong>
              <span class="candidate-description markdown-content" v-html="renderMarkdown(candidate.description)"></span>
            </div>
          </n-radio>
        </n-space>
      </n-radio-group>

      <n-divider />

      <div class="risk-checks">
        <h4>风险检查项</h4>
        <n-checkbox-group v-model:value="selectedRiskChecks">
          <n-space vertical>
            <n-checkbox
              v-for="(check, idx) in data.judgment_zone.risk_checks"
              :key="idx"
              :value="check"
            >
              {{ check }}
            </n-checkbox>
          </n-space>
        </n-checkbox-group>
      </div>

      <div class="verification-period">
        <h4>验证周期</h4>
        <n-radio-group v-model:value="selectedPeriod" size="small">
          <n-radio-button :value="1">1天</n-radio-button>
          <n-radio-button :value="3">3天</n-radio-button>
          <n-radio-button :value="7">7天</n-radio-button>
          <n-radio-button :value="30">30天</n-radio-button>
        </n-radio-group>
        <div class="period-hint">
          <n-text depth="3" style="font-size: 12px;">这将决定并在多长时间内追踪验证此判断是否成立</n-text>
        </div>
      </div>


      <n-alert type="info" :bordered="false" class="judgment-note">
        {{ data.judgment_zone.note }}
      </n-alert>

      <n-button
        type="primary"
        size="large"
        block
        @click="handleSaveJudgment"
        :disabled="!selectedCandidate || selectedRiskChecks.length === 0"
        :loading="saving"
        class="save-judgment-button"
      >
        <template #icon>
          <n-icon><BookmarkOutline /></n-icon>
        </template>
        保存我的判断
      </n-button>
    </div>

    <!-- Wyckoff II Judgment Confirm Dialog -->
    <JudgmentConfirmDialog
      v-model:show="showJudgmentConfirm"
      :judgment-candidate="selectedCandidate"
      :risk-flags="data.risk_of_misreading?.risk_flags || []"
      :stock-code="stockCode"
      :stock-name="stockName"
      @confirm="confirmSaveJudgment"
      @cancel="showJudgmentConfirm = false"
    />
    
    <!-- Anchor Bind Dialog -->
    <AnchorBindDialog
      v-model:show="showBindDialog"
      @bind-success="handleBindSuccess"
    />
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue';
import JudgmentConfirmDialog from '@/components/WyckoffGuide/JudgmentConfirmDialog.vue';
import JudgmentPreReminder from '@/components/WyckoffGuide/JudgmentPreReminder.vue';
import AnchorBindDialog from '@/components/AnchorBindDialog.vue';
import EnhancementCards from '@/components/EnhancementCards.vue';
import {
  NDescriptions,
  NDescriptionsItem,
  NTag,
  NSpace,
  NProgress,
  NAlert,
  NRadioGroup,
  NRadio,
  NRadioButton,
  NCheckboxGroup,
  NCheckbox,
  NDivider,
  NButton,
  NIcon,
  useMessage
} from 'naive-ui';
import { BookmarkOutline } from '@vicons/ionicons5';
import { apiService } from '@/services/api';
import { hasAnchorToken } from '@/utils/anchorToken';
import MarkdownIt from 'markdown-it';

// 初始化 Markdown 渲染器
const md = new MarkdownIt({
  html: false,        // 不允许 HTML 标签
  breaks: true,       // 将换行符转换为 <br>
  linkify: true,      // 自动转换 URL 为链接
  typographer: true   // 启用智能引号和其他排版优化
});

// Markdown 渲染函数
function renderMarkdown(text: string): string {
  if (!text) return '';
  return md.render(text);
}

function extractPlainText(text: string): string {
  return text.replace(/\*\*/g, '').replace(/\n+/g, ' ').trim();
}

interface Props {
  data: any; // Analysis V1 data
  stockCode: string;
  stockName: string;
  hideJudgmentZone?: boolean; // 是否隐藏判断区（用于存档文章）
}

const props = defineProps<Props>();
const emit = defineEmits(['saved']);

const message = useMessage();
const selectedCandidate = ref<string>('');
const selectedRiskChecks = ref<string[]>([]);
const selectedPeriod = ref(7); // 默认7天
const saving = ref(false);
const showJudgmentConfirm = ref(false);
const showBindDialog = ref(false);

// Judgment count for bind trigger
const JUDGMENT_COUNT_KEY = 'aguai_judgment_count';

const turnoverIndicator = computed(() => {
  const indicators = props.data?.indicator_translate?.indicators;
  if (!Array.isArray(indicators)) return null;
  return indicators.find((item: any) => item?.name === '换手率') || null;
});

const displayIndicators = computed(() => {
  const indicators = props.data?.indicator_translate?.indicators;
  if (!Array.isArray(indicators)) return [];
  return indicators.filter((item: any) => item?.name !== '换手率');
});

const turnoverActivityLabel = computed(() => {
  const signal = turnoverIndicator.value?.signal;
  if (signal === 'weakening') return '低活跃';
  if (signal === 'neutral') return '正常活跃';
  if (signal === 'strengthening') return '高活跃';
  if (signal === 'extreme') return '极高活跃';
  return '热度参考';
});

// 辅助函数：结构类型
function getStructureTypeName(type: string): string {
  const map: Record<string, string> = {
    'uptrend': '上升',
    'downtrend': '下降',
    'consolidation': '盘整'
  };
  return map[type] || type;
}

function getStructureTypeColor(type: string): 'success' | 'error' | 'warning' {
  const map: Record<string, 'success' | 'error' | 'warning'> = {
    'uptrend': 'success',
    'downtrend': 'error',
    'consolidation': 'warning'
  };
  return map[type] || 'warning';
}

// 辅助函数：MA200位置
function getMA200PositionName(pos: string): string {
  const map: Record<string, string> = {
    'above': '上方',
    'below': '下方',
    'near': '接近',
    'no_data': '无数据'
  };
  return map[pos] || pos;
}

function getMA200PositionColor(pos: string): 'success' | 'error' | 'info' {
  const map: Record<string, 'success' | 'error' | 'info'> = {
    'above': 'success',
    'below': 'error',
    'near': 'info',
    'no_data': 'info'
  };
  return map[pos] || 'info';
}

// 辅助函数：阶段
function getPhaseName(phase: string): string {
  const map: Record<string, string> = {
    'early': '早期',
    'middle': '中期',
    'late': '后期',
    'unclear': '不明'
  };
  return map[phase] || phase;
}

// 辅助函数：形态类型
function getPatternTypeName(type: string): string {
  const map: Record<string, string> = {
    'head_shoulders': '头肩形态',
    'double_top_bottom': '双顶/双底',
    'triangle': '三角形',
    'channel': '通道',
    'wedge': '楔形',
    'flag': '旗形',
    'none': '无明显形态'
  };
  return map[type] || type;
}

// 辅助函数：信号
function getSignalName(signal: string): string {
  const map: Record<string, string> = {
    'strengthening': '强化',
    'weakening': '弱化',
    'extreme': '极值',
    'neutral': '中性'
  };
  return map[signal] || signal;
}

function getSignalColor(signal: string): 'success' | 'error' | 'warning' | 'info' {
  const map: Record<string, 'success' | 'error' | 'warning' | 'info'> = {
    'strengthening': 'success',
    'weakening': 'error',
    'extreme': 'warning',
    'neutral': 'info'
  };
  return map[signal] || 'info';
}

// 辅助函数：风险等级
function getRiskLevelName(level: string): string {
  const map: Record<string, string> = {
    'high': '高风险',
    'medium': '中风险',
    'low': '低风险'
  };
  return map[level] || level;
}

function getRiskLevelType(level: string): 'error' | 'warning' | 'success' {
  const map: Record<string, 'error' | 'warning' | 'success'> = {
    'high': 'error',
    'medium': 'warning',
    'low': 'success'
  };
  return map[level] || 'warning';
}

// 保存判断 - 显示确认对话框
async function handleSaveJudgment() {
  if (!selectedCandidate.value || selectedRiskChecks.value.length === 0) {
    message.warning('请选择判断候选项并确认风险检查项');
    return;
  }

  // 显示 Wyckoff II 确认对话框
  showJudgmentConfirm.value = true;
}

// 确认保存判断 (用户在对话框中确认后)
async function confirmSaveJudgment() {
  saving.value = true;
  try {
    // 构造符合 Journal API CreateRecordRequest 的数据格式
    const recordRequest = {
      ts_code: props.stockCode,
      selected_candidate: selectedCandidate.value, // 单个字符: A/B/C
      selected_premises: [
        `结构类型: ${getStructureTypeName(props.data.structure_snapshot.structure_type)}`,
        `MA200位置: ${getMA200PositionName(props.data.structure_snapshot.ma200_position)}`,
        `阶段: ${getPhaseName(props.data.structure_snapshot.phase)}`,
        `形态: ${getPatternTypeName(props.data.pattern_fitting.pattern_type)}`
      ],
      selected_risk_checks: selectedRiskChecks.value,
      constraints: {
        structure_type: props.data.structure_snapshot.structure_type,
        ma200_position: props.data.structure_snapshot.ma200_position,
        phase: props.data.structure_snapshot.phase,
        pattern_type: props.data.pattern_fitting.pattern_type,
        key_levels: props.data.structure_snapshot.key_levels,
        snapshot_time: new Date().toISOString()
      },
      validation_period_days: selectedPeriod.value
    };

    const response = await apiService.saveJudgment(recordRequest);
    
    if (response && (response.id || response.judgment_id)) {
      if (response.is_temporary) {
        message.success('判断已保存到临时日记，绑定后可长期追踪与复盘');
        message.info('绑定后可持续追踪复盘，绑定后资产不会因换设备或清缓存而丢失。');
      } else {
        message.success('判断已保存！可在"判断日记"中查看');
      }
      emit('saved', response.id || response.judgment_id);
      
      // Trigger bind dialog on 2nd judgment
      checkAndTriggerBind();
    } else {
      message.error('保存失败，请重试');
    }
  } catch (error: any) {
    console.error('保存判断失败:', error);
    if (error.response?.status === 409) {
      message.error('判断重复，保存失败');
    } else if (error.response?.status === 422) {
      const details = error.response.data?.detail;
      const detailStr = Array.isArray(details) 
        ? details.map((d: any) => `${d.loc?.join('.') || 'field'}: ${d.msg}`).join('; ')
        : JSON.stringify(details);
      message.error(`数据格式错误: ${detailStr}`);
    } else {
      message.error('保存失败，请重试');
    }
  } finally {
    saving.value = false;
  }
}

// Check if should trigger bind dialog
function checkAndTriggerBind() {
  // Don't show if already bound
  if (hasAnchorToken()) return;
  
  // Increment judgment count
  let count = parseInt(localStorage.getItem(JUDGMENT_COUNT_KEY) || '0');
  count++;
  localStorage.setItem(JUDGMENT_COUNT_KEY, count.toString());

  if (count === 1) {
    message.info('绑定后可持续追踪复盘，绑定后资产不会因换设备或清缓存而丢失。');
  }
  
  // Show bind dialog on 2nd judgment
  if (count === 2) {
    setTimeout(() => {
      showBindDialog.value = true;
    }, 1000); // Delay 1s for better UX
  }
}

// Handle bind success
function handleBindSuccess(data: any) {
  console.log('[AnalysisV1Display] Bind success:', data);
  message.success(`已绑定邮箱,迁移了 ${data.migrated_count} 条判断`);
}
</script>

<style scoped>
.analysis-v1-display {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.analysis-section {
  padding: 16px;
  background: var(--n-color);
  border-radius: 8px;
  border: 1px solid var(--n-border-color);
}

.section-title {
  margin: 0 0 16px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--n-text-color);
}

.key-levels {
  margin-top: 16px;
}

.key-levels h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
}

.trend-description,
.pattern-description {
  margin: 12px 0 0 0;
  line-height: 1.6;
  color: var(--n-text-color-2);
}

.indicators-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 16px;
}

.turnover-highlight {
  margin-bottom: 16px;
  padding: 14px 16px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.12), rgba(118, 75, 162, 0.12));
  border: 1px solid rgba(102, 126, 234, 0.18);
}

.turnover-highlight-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.turnover-highlight-value {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 700;
  color: var(--n-text-color);
}

.turnover-highlight-note {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--n-text-color-2);
}

.turnover-highlight-tip {
  margin-top: 8px;
  font-size: 12px;
  line-height: 1.5;
  color: var(--n-text-color-3);
}

.indicator-item {
  padding: 12px;
  background: var(--n-color-embedded);
  border-radius: 6px;
}

.indicator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.indicator-value {
  font-size: 13px;
  color: var(--n-text-color-2);
  margin-bottom: 4px;
}

.indicator-interpretation {
  font-size: 13px;
  line-height: 1.5;
  color: var(--n-text-color-3);
}

.global-note {
  margin-top: 12px;
}

.risk-factors {
  margin: 8px 0;
  padding-left: 20px;
}

.risk-factors li {
  margin-bottom: 4px;
  line-height: 1.5;
}

.risk-flags {
  margin: 12px 0;
}

.caution-note {
  margin: 12px 0 0 0;
  line-height: 1.6;
}

.candidates-group {
  width: 100%;
}

.candidate-radio {
  width: 100%;
  padding: 12px;
  border: 1px solid var(--n-border-color);
  border-radius: 6px;
  transition: all 0.3s;
}

.candidate-radio:hover {
  background: var(--n-color-hover);
  border-color: var(--n-color-target);
}

.candidate-content {
  display: flex;
  gap: 8px;
  align-items: flex-start;
}

.candidate-id {
  flex-shrink: 0;
  color: var(--n-color-target);
}

.candidate-description {
  flex: 1;
  line-height: 1.6;
}

.risk-checks {
  margin: 16px 0;
}

.risk-checks h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 500;
}

.verification-period {
  margin: 16px 0;
}

.verification-period h4 {
  margin: 0 0 8px 0;
  font-size: 14px;
  font-weight: 500;
}

.period-hint {
  margin-top: 4px;
}

.judgment-note {
  margin: 16px 0;
}

.save-judgment-button {
  margin-top: 16px;
}

/* Markdown 渲染内容样式 */
.markdown-content {
  line-height: 1.8;
}

.markdown-content p {
  margin: 8px 0;
}

.markdown-content ul,
.markdown-content ol {
  margin: 8px 0;
  padding-left: 24px;
}

.markdown-content li {
  margin: 4px 0;
  line-height: 1.6;
}

.markdown-content strong {
  font-weight: 600;
  color: var(--n-text-color);
}

.markdown-content code {
  padding: 2px 6px;
  background: var(--n-color-embedded);
  border-radius: 3px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
}

.markdown-content pre {
  padding: 12px;
  background: var(--n-color-embedded);
  border-radius: 6px;
  overflow-x: auto;
}

.markdown-content pre code {
  padding: 0;
  background: none;
}

.markdown-content blockquote {
  margin: 8px 0;
  padding-left: 12px;
  border-left: 3px solid var(--n-border-color);
  color: var(--n-text-color-2);
}

</style>
