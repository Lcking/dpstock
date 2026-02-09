<template>
  <div class="value-loop">
    <div class="loop-slogan">
      <div class="slogan-badge">核心价值闭环</div>
      <div class="slogan-text">把每一次交易，变成一次可复用的判断。</div>
    </div>
    <div class="loop-steps">
      <div class="step" v-for="step in steps" :key="step.label">
        <div class="step-icon" aria-hidden="true">{{ step.icon }}</div>
        <div class="step-label">{{ step.label }}</div>
        <div class="step-desc">{{ step.desc }}</div>
      </div>
      <div class="step-arrow" v-for="i in 3" :key="'arrow-' + i">→</div>
    </div>
    <div class="loop-return">
      <svg class="return-arc" viewBox="0 0 600 32" preserveAspectRatio="none">
        <path d="M540 2 C560 2, 580 16, 580 28 L20 28 C20 16, 0 2, 60 2" fill="none" stroke="url(#loopGrad)" stroke-width="2" stroke-dasharray="6 4" />
        <defs>
          <linearGradient id="loopGrad" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stop-color="#667eea" stop-opacity="0.6" />
            <stop offset="100%" stop-color="#764ba2" stop-opacity="0.6" />
          </linearGradient>
        </defs>
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
  margin-bottom: 20px;
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

.loop-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0;
  margin-bottom: 6px;
}

.step {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  min-width: 90px;
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
  font-size: 20px;
  color: #667eea;
  font-weight: 700;
  margin: 0 12px;
  padding-bottom: 36px;
}

.loop-return {
  position: relative;
  height: 32px;
  max-width: 520px;
  margin: 0 auto;
}

.return-arc {
  width: 100%;
  height: 32px;
}

.return-label {
  position: absolute;
  bottom: 4px;
  left: 50%;
  transform: translateX(-50%);
  font-size: 11px;
  color: #667eea;
  font-weight: 600;
  background: rgba(102, 126, 234, 0.08);
  padding: 2px 12px;
  border-radius: 999px;
}

/* Mobile */
@media (max-width: 640px) {
  .value-loop {
    padding: 16px 12px 12px;
    margin: 12px 0;
  }

  .slogan-text {
    font-size: 15px;
  }

  .step {
    min-width: 64px;
  }

  .step-icon {
    font-size: 22px;
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
    font-size: 16px;
    margin: 0 6px;
    padding-bottom: 28px;
  }
}
</style>
