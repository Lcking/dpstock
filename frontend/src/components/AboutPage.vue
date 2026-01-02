<template>
  <div class="about-page">
    <n-layout-content class="about-container">
      <!-- Hero Section -->
      <section class="hero-section">
        <h1 class="page-title">关于我们</h1>
        <p class="hero-subtitle">
          我们不是来给你答案的,<br/>
          而是帮助你弄清楚:<br/>
          你是在什么前提下做出判断的。
        </p>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 2: 我们不做什么 -->
      <section class="content-section">
        <h2 class="section-title">我们刻意不提供以下内容:</h2>
        <n-list class="principle-list">
          <n-list-item>买卖建议</n-list-item>
          <n-list-item>目标价或胜率</n-list-item>
          <n-list-item>趋势预测或信号</n-list-item>
          <n-list-item>"看涨 / 看跌"的结论</n-list-item>
        </n-list>
        <p class="section-note">
          不是因为我们做不到,<br/>
          而是因为这些内容往往会掩盖判断的前提。
        </p>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 3: 我们在做什么 -->
      <section class="content-section">
        <h2 class="section-title">那么,我们在做什么?</h2>
        <div class="section-content">
          <p class="emphasis-text">我们只做一件事:</p>
          <p>把判断的前提说清楚,并记录下来。</p>
          <p>每一次分析,关注的都不是"会不会涨",而是:</p>
          <ul class="feature-list">
            <li>当前结构是否稳定</li>
            <li>哪些条件一旦发生,结构就会改变</li>
            <li>哪些地方最容易被误读</li>
          </ul>
          <p class="section-note">
            判断在这里不是结论,<br/>
            而是一种可以被验证、也可以被否定的假设。
          </p>
        </div>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 4: 判断如何被对待 -->
      <section class="content-section">
        <h2 class="section-title">在这里,判断意味着什么?</h2>
        <n-blockquote class="philosophy-quote">
          当你保存一个判断时,<br/>
          你并不是在预测未来,<br/>
          而是在声明:<br/>
          "在这些条件成立之前,我接受这个判断。"
        </n-blockquote>
        <p class="section-note">
          市场随后只做一件事:<br/>
          验证这些条件是否仍然成立。
        </p>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 5: 判断失败 -->
      <section class="content-section">
        <h2 class="section-title">判断失败,并不等于做错</h2>
        <div class="section-content">
          <p>当某个前提不再成立时,</p>
          <p>我们不会用"洗盘""意外"来解释它。</p>
          <p>它只意味着:</p>
          <p class="emphasis-text">市场并没有按照你当初接受的条件运行。</p>
          <p class="section-note">
            在这里,<br/>
            允许判断失败,本身就是纪律的一部分。
          </p>
        </div>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 6: 为什么限制 -->
      <section class="content-section">
        <h2 class="section-title">为什么我们刻意让你慢下来?</h2>
        <div class="section-content">
          <p>你可能注意到,我们限制了每日可分析的新标的数量,</p>
          <p>并在关键节点要求你确认自己的判断。</p>
          <p>这些设计并不是为了限制你,</p>
          <p>而是因为我们相信:</p>
          <p class="emphasis-text highlight">
            专注于少数标的的结构变化,<br/>
            比反复查看大量技术报告更重要。
          </p>
        </div>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 7: 适合谁/不适合谁 -->
      <section class="content-section">
        <h2 class="section-title">这不是一个适合所有人的工具</h2>
        <n-grid :cols="1" :x-gap="24" :y-gap="24" responsive="screen" :item-responsive="true">
          <n-grid-item :span="24" :md="12">
            <n-card size="small" :bordered="false" class="fit-card fit-yes">
              <template #header>
                <span class="fit-title">✓ 适合你,如果你:</span>
              </template>
              <ul class="fit-list">
                <li>愿意承认不确定性</li>
                <li>能接受判断可能失败</li>
                <li>重视结构与前提</li>
              </ul>
            </n-card>
          </n-grid-item>
          <n-grid-item :span="24" :md="12">
            <n-card size="small" :bordered="false" class="fit-card fit-no">
              <template #header>
                <span class="fit-title">✗ 可能不适合你,如果你:</span>
              </template>
              <ul class="fit-list">
                <li>希望快速得到答案</li>
                <li>期待明确的买卖信号</li>
                <li>不愿回看和修正判断</li>
              </ul>
            </n-card>
          </n-grid-item>
        </n-grid>
      </section>

      <n-divider class="section-divider" />

      <!-- Section 8: 免责声明 -->
      <section class="disclaimer-section">
        <p class="disclaimer-text">
          本产品仅用于结构分析与判断验证,<br/>
          不构成任何投资建议。<br/>
          所有决策请基于你的独立判断。
        </p>
      </section>
    </n-layout-content>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue';
import { 
  NLayoutContent, 
  NDivider, 
  NList, 
  NListItem, 
  NBlockquote,
  NGrid,
  NGridItem,
  NCard
} from 'naive-ui';

// SEO: Set page title and meta description
onMounted(() => {
  document.title = '关于我们 - Aguai';
  
  // Set meta description if not already set
  let metaDescription = document.querySelector('meta[name="description"]');
  if (!metaDescription) {
    metaDescription = document.createElement('meta');
    metaDescription.setAttribute('name', 'description');
    document.head.appendChild(metaDescription);
  }
  metaDescription.setAttribute('content', 'Aguai 是一个结构前提判断与验证工具,不提供买卖建议,强调专注、纪律与可证伪的判断。');
});
</script>

<style scoped>
.about-page {
  min-height: 100vh;
  background: #fafafa;
}

.about-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 60px 24px;
}

/* Hero Section */
.hero-section {
  text-align: center;
  padding: 40px 0 60px;
}

.page-title {
  font-size: 42px;
  font-weight: 700;
  color: #1a1a1a;
  margin: 0 0 32px 0;
  letter-spacing: -0.5px;
}

.hero-subtitle {
  font-size: 20px;
  line-height: 1.8;
  color: #4a4a4a;
  font-weight: 400;
  margin: 0;
}

/* Section Divider */
.section-divider {
  margin: 48px 0;
  opacity: 0.3;
}

/* Content Sections */
.content-section {
  padding: 24px 0;
}

.section-title {
  font-size: 24px;
  font-weight: 600;
  color: #2a2a2a;
  margin: 0 0 24px 0;
  letter-spacing: -0.3px;
}

.section-content {
  font-size: 16px;
  line-height: 1.8;
  color: #4a4a4a;
}

.section-content p {
  margin: 0 0 12px 0;
}

.section-note {
  margin-top: 20px;
  font-size: 15px;
  line-height: 1.7;
  color: #6a6a6a;
  font-style: italic;
}

.emphasis-text {
  font-weight: 600;
  color: #2a2a2a;
}

.highlight {
  padding: 16px 20px;
  background: rgba(59, 130, 246, 0.05);
  border-left: 3px solid #3b82f6;
  margin: 20px 0;
}

/* Lists */
.principle-list {
  margin: 16px 0;
  background: transparent;
}

.principle-list :deep(.n-list-item) {
  padding: 12px 0;
  font-size: 16px;
  color: #4a4a4a;
}

.feature-list {
  list-style: none;
  padding: 0;
  margin: 16px 0;
}

.feature-list li {
  padding: 8px 0 8px 24px;
  position: relative;
  font-size: 16px;
  color: #4a4a4a;
}

.feature-list li::before {
  content: "•";
  position: absolute;
  left: 8px;
  color: #3b82f6;
  font-weight: bold;
}

/* Philosophy Quote */
.philosophy-quote {
  margin: 24px 0;
  padding: 24px 28px;
  font-size: 17px;
  line-height: 1.8;
  color: #3a3a3a;
  background: rgba(0, 0, 0, 0.02);
  border-left: 4px solid #3b82f6;
}

/* Fit Cards */
.fit-card {
  background: rgba(0, 0, 0, 0.02);
  height: 100%;
}

.fit-yes {
  border-left: 3px solid #10b981;
}

.fit-no {
  border-left: 3px solid #ef4444;
}

.fit-title {
  font-size: 16px;
  font-weight: 600;
  color: #2a2a2a;
}

.fit-list {
  list-style: none;
  padding: 0;
  margin: 0;
}

.fit-list li {
  padding: 8px 0;
  font-size: 15px;
  color: #4a4a4a;
  line-height: 1.6;
}

/* Disclaimer */
.disclaimer-section {
  padding: 32px 0 0;
  text-align: center;
}

.disclaimer-text {
  font-size: 13px;
  line-height: 1.7;
  color: #9a9a9a;
  margin: 0;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .about-container {
    padding: 40px 20px;
  }

  .page-title {
    font-size: 32px;
    margin-bottom: 24px;
  }

  .hero-subtitle {
    font-size: 17px;
  }

  .section-title {
    font-size: 20px;
  }

  .section-content,
  .principle-list :deep(.n-list-item),
  .feature-list li {
    font-size: 15px;
  }

  .philosophy-quote {
    font-size: 16px;
    padding: 20px 20px;
  }

  .section-divider {
    margin: 32px 0;
  }
}

@media (max-width: 480px) {
  .about-container {
    padding: 32px 16px;
  }

  .page-title {
    font-size: 28px;
  }

  .hero-subtitle {
    font-size: 16px;
  }
}
</style>
