<template>
  <div class="value-loop">
    <div class="loop-slogan">
      <div class="slogan-badge">核心价值闭环</div>
      <div class="slogan-text">把每一次交易，变成一次可复用的判断。</div>
    </div>
    <div class="loop-steps">
      <template v-for="(step, idx) in steps" :key="step.label">
        <div class="step">
          <div class="step-icon" aria-hidden="true">{{ step.icon }}</div>
          <div class="step-label">{{ step.label }}</div>
          <div class="step-desc">{{ step.desc }}</div>
        </div>
        <div v-if="idx < steps.length - 1" class="step-arrow" aria-hidden="true">
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
            <path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
        </div>
      </template>
    </div>
    <div class="loop-return">
      <svg class="return-arc" viewBox="0 0 600 36" preserveAspectRatio="none">
        <defs>
          <linearGradient id="loopGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#667eea" stop-opacity="0.5" />
            <stop offset="50%" stop-color="#764ba2" stop-opacity="0.5" />
            <stop offset="100%" stop-color="#667eea" stop-opacity="0.5" />
          </linearGradient>
          <marker id="arrowLeft" markerWidth="6" markerHeight="6" refX="3" refY="3" orient="auto">
            <path d="M6 0 L0 3 L6 6" fill="none" stroke="#667eea" stroke-width="1.5" opacity="0.6"/>
          </marker>
        </defs>
        <path d="M540 4 Q580 4, 580 20 L580 28 Q580 34, 540 34 L60 34 Q20 34, 20 28 L20 20 Q20 4, 60 4"
              fill="none" stroke="url(#loopGrad)" stroke-width="1.5" stroke-dasharray="6 4"
              marker-start="url(#arrowLeft)" />
      </svg>
      <div class="return-label">循环闭环</div>
    </div>
  </div>
</template>

<script setup lang="ts">
const steps = [
  { icon: '🔍', label: '分析', desc: 'AI 智能诊股' },
  { icon: '💾', label: '保存', desc: '记录判断依据' },
  { icon: '📊', label: '跟踪', desc: '验证期追踪' },
  { icon: '✅', label: '复盘', desc: '闭环改进' }
]
</script>

<style scoped>
.value-loop {
  margin: 20px 0;
  padding: 24px 20px 16px;
  border-radius: 16px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  border: 1px solid rgba(102, 126, 234, 0.12);
  text-align: center;
}

.loop-slogan {
  margin-bottom: 24px;
}

.slogan-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  color: #667eea;
  background: rgba(102, 126, 234, 0.1);
  border: 1px solid rgba(102, 126, 234, 0.2);
  border-radius: 999px;
  padding: 4px 16px;
  margin-bottom: 10px;
  letter-spacing: 0.08em;
}

.slogan-text {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  letter-spacing: 0.02em;
}

/* Steps row: step → arrow → step → arrow → step → arrow → step */
.loop-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  margin-bottom: 8px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 90px;
  flex-shrink: 0;
}

.step-icon {
  font-size: 28px;
  width: 52px;
  height: 52px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.9);
  border: 2px solid rgba(102, 126, 234, 0.25);
  box-shadow: 0 2px 8px rgba(102, 126, 234, 0.1);
}

.step-label {
  font-size: 14px;
  font-weight: 700;
  color: #374151;
}

.step-desc {
  font-size: 11px;
  color: #6b7280;
  white-space: nowrap;
}

.step-arrow {
  display: flex;
  align-items: center;
  justify-content: center;
  color: #667eea;
  margin: 0 8px;
  padding-top: 14px; /* align arrow vertically with icon centers */
  flex-shrink: 0;
}

.step-arrow svg {
  width: 24px;
  height: 24px;
}

/* Return arc */
.loop-return {
  position: relative;
  height: 36px;
  max-width: 520px;
  margin: 0 auto;
}

.return-arc {
  width: 100%;
  height: 36px;
}

.return-label {
  position: absolute;
  bottom: 6px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: #667eea;
  font-weight: 600;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.06) 0%, rgba(118, 75, 162, 0.06) 100%);
  padding: 2px 12px;
  border-radius: 999px;
  white-space: nowrap;
}

/* ===== Mobile ===== */
@media (max-width: 640px) {
  .value-loop {
    padding: 16px 8px 12px;
    margin: 12px 0;
  }

  .slogan-text {
    font-size: 15px;
  }

  .step {
    min-width: 60px;
  }

  .step-icon {
    font-size: 20px;
    width: 40px;
    height: 40px;
  }

  .step-label {
    font-size: 12px;
  }

  .step-desc {
    font-size: 10px;
  }

  .step-arrow {
    margin: 0 4px;
    padding-top: 10px;
  }

  .step-arrow svg {
    width: 18px;
    height: 18px;
  }
}

/* Very small screens */
@media (max-width: 380px) {
  .step {
    min-width: 50px;
  }

  .step-icon {
    font-size: 18px;
    width: 34px;
    height: 34px;
  }

  .step-label {
    font-size: 11px;
  }

  .step-desc {
    display: none;
  }

  .step-arrow {
    margin: 0 2px;
    padding-top: 6px;
  }

  .step-arrow svg {
    width: 14px;
    height: 14px;
  }
}
</style>
