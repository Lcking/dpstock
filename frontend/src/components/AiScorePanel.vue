<template>
  <div class="ai-score-panel" :class="{ compact }">
    <!-- Skeleton / placeholder -->
    <template v-if="loading && !aiScore">
      <div class="panel-header">
        <div class="title">AI 综合评分</div>
        <div class="meta skeleton-pill"></div>
      </div>
      <div class="skeleton-row">
        <div class="skeleton-box score"></div>
        <div class="skeleton-box label"></div>
      </div>
      <div class="skeleton-lines">
        <div class="skeleton-line long"></div>
        <div class="skeleton-line medium"></div>
        <div class="skeleton-line short"></div>
      </div>
      <div class="skeleton-bars">
        <div class="skeleton-bar" v-for="i in 4" :key="i"></div>
      </div>
    </template>

    <template v-else-if="aiScore">
      <div class="panel-header">
        <div class="title">
          AI 综合评分
          <span class="version">v{{ aiScore.version }}</span>
        </div>
        <n-tag v-if="aiScore.overall.degraded" type="warning" size="small" :bordered="false">
          降级
        </n-tag>
      </div>

      <div class="overall">
        <div class="overall-left">
          <div class="overall-score">{{ aiScore.overall.score }}</div>
          <div class="overall-label">
            <n-tag :type="labelTagType" size="small" :bordered="false">
              {{ aiScore.overall.label }}
            </n-tag>
          </div>
        </div>
        <div class="overall-right">
          <div class="confidence-row">
            <div class="confidence-label">置信度</div>
            <div class="confidence-value">{{ formatConfidence(aiScore.overall.confidence) }}</div>
          </div>
          <n-progress
            type="line"
            :percentage="Math.round(aiScore.overall.confidence * 100)"
            :height="10"
            :show-indicator="false"
          />
        </div>
      </div>

      <div class="dimensions">
        <div class="dim" v-for="d in aiScore.dimensions" :key="d.id">
          <div class="dim-head">
            <div class="dim-name">
              {{ d.name }}
              <span class="dim-weight">({{ Math.round(d.weight * 100) }}%)</span>
            </div>
            <div class="dim-score">
              {{ d.score }}
              <span v-if="!d.available" class="dim-flag">不可用</span>
              <span v-else-if="d.degraded" class="dim-flag">降级</span>
            </div>
          </div>
          <n-progress
            type="line"
            :percentage="d.score"
            :height="10"
            :show-indicator="false"
          />
        </div>
      </div>

      <div class="one-liner" v-if="aiScore.explain?.one_liner && !compact">
        {{ aiScore.explain.one_liner }}
      </div>

      <div class="actions" v-if="!compact">
        <n-button size="tiny" quaternary @click="expanded = !expanded">
          {{ expanded ? '收起评分依据' : '展开评分依据' }}
        </n-button>
      </div>

      <div class="details" v-if="expanded && !compact">
        <div class="detail-dim" v-for="d in aiScore.dimensions" :key="d.id">
          <div class="detail-title">{{ d.name }}</div>

          <div class="detail-block" v-if="d.evidence?.length">
            <div class="detail-label">evidence</div>
            <ul class="detail-list">
              <li v-for="(e, idx) in d.evidence.slice(0, 2)" :key="idx">{{ e }}</li>
            </ul>
          </div>

          <div class="detail-block" v-if="d.contrib?.length">
            <div class="detail-label">contrib</div>
            <ul class="detail-list">
              <li v-for="(c, idx) in d.contrib" :key="idx">
                <span class="mono">{{ c.key }}</span>
                <span class="impact" :class="{ pos: c.impact > 0, neg: c.impact < 0 }">
                  {{ formatImpact(c.impact) }}
                </span>
                <span class="note">{{ c.note }}</span>
              </li>
            </ul>
          </div>
        </div>

        <div class="disclaimer" v-if="aiScore.explain?.notes?.length">
          <div v-for="(n, idx) in aiScore.explain.notes" :key="idx">{{ n }}</div>
        </div>
      </div>
    </template>

    <template v-else>
      <div class="empty" v-if="!compact">
        暂无评分数据
      </div>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NProgress, NTag, NButton } from 'naive-ui'
import type { AiScore } from '@/types'

const props = defineProps<{
  aiScore?: AiScore | null
  loading?: boolean
  compact?: boolean
}>()

const expanded = ref(false)

const labelTagType = computed(() => {
  const s = props.aiScore?.overall?.score ?? 0
  if (s >= 80) return 'success'
  if (s >= 65) return 'info'
  if (s >= 45) return 'warning'
  return 'error'
})

function formatConfidence(v: number) {
  return `${Math.round(v * 100)}%`
}

function formatImpact(v: number) {
  const sign = v > 0 ? '+' : ''
  return `${sign}${v.toFixed(2)}`
}
</script>

<style scoped>
.ai-score-panel {
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 12px;
  padding: 12px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(8px);
}

.ai-score-panel.compact {
  padding: 10px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 10px;
}

.title {
  font-weight: 700;
  color: #111827;
  display: flex;
  gap: 8px;
  align-items: baseline;
}

.version {
  font-size: 12px;
  color: #6b7280;
  font-weight: 600;
}

.overall {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 12px;
  align-items: center;
  margin-bottom: 12px;
}

.compact .overall {
  grid-template-columns: 100px 1fr;
}

.overall-left {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.overall-score {
  font-size: 34px;
  line-height: 1;
  font-weight: 800;
  color: #111827;
}

.confidence-row {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #6b7280;
  margin-bottom: 6px;
}

.dimensions {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.dim-head {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}

.dim-name {
  font-size: 13px;
  font-weight: 700;
  color: #111827;
}

.dim-weight {
  font-weight: 600;
  color: #6b7280;
  margin-left: 6px;
}

.dim-score {
  font-size: 13px;
  font-weight: 800;
  color: #111827;
  display: flex;
  gap: 8px;
  align-items: center;
}

.dim-flag {
  font-size: 11px;
  font-weight: 700;
  color: #b45309;
  background: rgba(245, 158, 11, 0.14);
  padding: 2px 6px;
  border-radius: 999px;
}

.one-liner {
  margin-top: 10px;
  font-size: 12px;
  color: #374151;
  line-height: 1.6;
}

.actions {
  margin-top: 10px;
  display: flex;
  justify-content: flex-end;
}

.details {
  margin-top: 12px;
  border-top: 1px dashed rgba(0, 0, 0, 0.08);
  padding-top: 12px;
}

.detail-dim + .detail-dim {
  margin-top: 12px;
}

.detail-title {
  font-weight: 800;
  font-size: 13px;
  color: #111827;
  margin-bottom: 8px;
}

.detail-label {
  font-size: 11px;
  font-weight: 800;
  color: #6b7280;
  margin-bottom: 6px;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.detail-list {
  margin: 0;
  padding-left: 18px;
  color: #374151;
  font-size: 12px;
  line-height: 1.6;
}

.detail-list li {
  margin: 4px 0;
}

.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace;
  font-weight: 700;
  color: #111827;
  margin-right: 8px;
}

.impact {
  font-weight: 800;
  margin-right: 8px;
}

.impact.pos {
  color: #059669;
}

.impact.neg {
  color: #dc2626;
}

.note {
  color: #6b7280;
}

.disclaimer {
  margin-top: 12px;
  font-size: 12px;
  color: #6b7280;
  line-height: 1.6;
}

/* Skeleton */
.skeleton-pill {
  width: 72px;
  height: 16px;
  border-radius: 999px;
  background: rgba(102, 126, 234, 0.14);
}

.skeleton-row {
  display: flex;
  gap: 10px;
  align-items: center;
  margin-bottom: 10px;
}

.skeleton-box {
  background: rgba(102, 126, 234, 0.10);
  border-radius: 10px;
  animation: shimmer 1.4s infinite;
}

.skeleton-box.score {
  width: 90px;
  height: 34px;
}

.skeleton-box.label {
  width: 90px;
  height: 22px;
}

.skeleton-lines {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin: 8px 0 10px;
}

.skeleton-line {
  height: 10px;
  border-radius: 8px;
  background: rgba(102, 126, 234, 0.10);
  animation: shimmer 1.4s infinite;
}

.skeleton-line.long { width: 100%; }
.skeleton-line.medium { width: 80%; }
.skeleton-line.short { width: 60%; }

.skeleton-bars {
  display: grid;
  grid-template-columns: 1fr;
  gap: 10px;
}

.skeleton-bar {
  height: 10px;
  border-radius: 8px;
  background: rgba(102, 126, 234, 0.10);
  animation: shimmer 1.4s infinite;
}

@keyframes shimmer {
  0% { opacity: 0.65; }
  50% { opacity: 1; }
  100% { opacity: 0.65; }
}
</style>

