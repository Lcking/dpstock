<template>
  <div class="help-page-container">
    <n-button class="back-button" quaternary @click="$router.push('/')">
      <template #icon><n-icon><ArrowBack /></n-icon></template>
      返回首页
    </n-button>

    <article class="help-content">
      <header class="help-header">
        <h1>📚 判断验证功能说明</h1>
        <p class="subtitle">了解如何使用判断追踪功能，提升投资分析能力</p>
      </header>

      <section class="help-section">
        <h2>🎯 功能概述</h2>
        <p>
          判断验证是一个自动化系统，用于追踪您保存的判断是否准确。系统会在您保存判断后的一段时间内，
          自动检查市场走势是否符合您的判断，帮助您回顾和改进分析方法。
        </p>
      </section>

      <section class="help-section">
        <h2>📊 字段说明</h2>
        
        <div class="field-explanation">
          <h3>1. 当前状态（Current Status）</h3>
          <n-alert type="info" :bordered="false">
            <strong>可能的值：</strong>
            <ul>
              <li><strong>未验证（Unverified）</strong>：判断刚保存，还未到验证时间</li>
              <li><strong>已验证（Verified）</strong>：系统已完成验证</li>
              <li><strong>验证中（Verifying）</strong>：正在验证过程中</li>
            </ul>
          </n-alert>
          <p class="field-note">
            <strong>为什么显示"未验证"？</strong><br>
            判断刚保存时，默认状态是"未验证"。系统需要等待一段时间（如7天、30天）后才能验证判断是否准确。
            这是正常的初始状态。
          </p>
        </div>

        <div class="field-explanation">
          <h3>2. 价格变化（Price Change）</h3>
          <n-alert type="success" :bordered="false">
            <strong>含义：</strong>
            <p>从保存判断时的价格到验证时的价格变化百分比</p>
            <ul>
              <li>例如：<span class="example-positive">+5.2%</span> 表示价格上涨了5.2%</li>
              <li>例如：<span class="example-negative">-3.1%</span> 表示价格下跌了3.1%</li>
            </ul>
          </n-alert>
          <p class="field-note">
            <strong>用途：</strong>帮助您了解市场实际走势，与您的判断对比，评估判断准确性。<br>
            <strong>为什么现在是空的？</strong>判断还未验证，验证完成后会自动填充。
          </p>
        </div>

        <div class="field-explanation">
          <h3>3. 原因（Reason）</h3>
          <n-alert type="warning" :bordered="false">
            <strong>含义：</strong>
            <p>系统对验证结果的解释，说明为什么判断被认为是正确或错误的</p>
            <strong>可能的内容：</strong>
            <ul>
              <li>"价格突破了关键压力位，符合上升结构判断"</li>
              <li>"价格跌破支撑位，结构前提被破坏"</li>
              <li>"价格在区间内震荡，结构维持判断正确"</li>
            </ul>
          </n-alert>
          <p class="field-note">
            <strong>为什么现在是空的？</strong>判断还未验证，验证完成后会自动生成。
          </p>
        </div>
      </section>

      <section class="help-section">
        <h2>🔄 验证流程</h2>
        <div class="flow-diagram">
          <div class="flow-step">
            <div class="step-number">1</div>
            <div class="step-content">
              <h4>用户保存判断</h4>
              <p>选择候选项和风险检查项</p>
            </div>
          </div>
          <div class="flow-arrow">↓</div>
          <div class="flow-step">
            <div class="step-number">2</div>
            <div class="step-content">
              <h4>状态：未验证</h4>
              <p>系统记录判断和当前价格</p>
            </div>
          </div>
          <div class="flow-arrow">↓</div>
          <div class="flow-step">
            <div class="step-number">3</div>
            <div class="step-content">
              <h4>等待验证期</h4>
              <p>通常为7天或30天</p>
            </div>
          </div>
          <div class="flow-arrow">↓</div>
          <div class="flow-step">
            <div class="step-number">4</div>
            <div class="step-content">
              <h4>系统自动验证</h4>
              <p>获取最新行情数据并分析</p>
            </div>
          </div>
          <div class="flow-arrow">↓</div>
          <div class="flow-step">
            <div class="step-number">5</div>
            <div class="step-content">
              <h4>状态：已验证</h4>
              <p>填充价格变化和原因</p>
            </div>
          </div>
        </div>
      </section>

      <section class="help-section">
        <h2>💡 验证逻辑示例</h2>
        <n-card title="示例：上升结构判断" :bordered="false" class="example-card">
          <p><strong>假设用户选择了候选项 A：</strong></p>
          <p class="example-text">"上升结构延续，价格保持在MA200上方运行"</p>
          
          <h4>验证条件：</h4>
          <ul>
            <li>检查7天后价格是否仍在MA200上方</li>
            <li>检查关键支撑位是否守住</li>
            <li>检查成交量配合情况</li>
          </ul>

          <h4>可能的结果：</h4>
          <div class="result-example success">
            <strong>✅ 验证通过</strong>
            <p>价格变化：<span class="example-positive">+3.5%</span></p>
            <p>原因："价格持续在MA200上方运行，关键支撑位守住，结构前提成立"</p>
          </div>

          <div class="result-example failure">
            <strong>❌ 验证失败</strong>
            <p>价格变化：<span class="example-negative">-5.2%</span></p>
            <p>原因："价格跌破MA200，关键支撑位失守，结构前提被破坏"</p>
          </div>
        </n-card>
      </section>

      <section class="help-section">
        <h2>🔒 数据隐私保护</h2>
        <n-alert type="success" :bordered="false" class="privacy-alert">
          <template #header>
            <strong>您的数据完全私密</strong>
          </template>
          <p>我们非常重视您的隐私。所有判断验证数据都存储在您的浏览器本地，不会上传到服务器。</p>
        </n-alert>

        <div class="privacy-details">
          <h3>📍 数据存储位置</h3>
          <p>
            所有判断数据都保存在您浏览器的 <code>localStorage</code> 中，这意味着：
          </p>
          <ul>
            <li>数据只存在于您当前使用的浏览器中</li>
            <li>其他人无法访问您的判断数据</li>
            <li>我们的服务器不会收集或存储您的判断记录</li>
          </ul>

          <h3>🔐 隐私保证</h3>
          <ul>
            <li><strong>不上传</strong>：判断数据不会发送到任何服务器</li>
            <li><strong>不共享</strong>：您的判断记录不会与任何第三方共享</li>
            <li><strong>不追踪</strong>：我们不会追踪您的判断历史</li>
          </ul>

          <h3>🗑️ 数据管理</h3>
          <p>您可以随时管理自己的数据：</p>
          <ul>
            <li><strong>查看数据</strong>：在"我的判断"页面查看所有保存的判断</li>
            <li><strong>清除数据</strong>：清除浏览器缓存会删除所有判断数据</li>
            <li><strong>导出数据</strong>：（未来功能）支持导出判断数据到本地文件</li>
          </ul>

          <n-alert type="warning" :bordered="false" class="privacy-note">
            <template #header>
              <strong>⚠️ 注意事项</strong>
            </template>
            <ul>
              <li>更换浏览器或设备后，之前的判断数据将无法访问</li>
              <li>清除浏览器缓存会永久删除所有判断数据</li>
              <li>建议定期截图保存重要的判断记录</li>
            </ul>
          </n-alert>
        </div>
      </section>

      <section class="help-section">
        <h2>❓ 常见问题</h2>
        <n-collapse>
          <n-collapse-item title="为什么我的判断一直显示'未验证'？" name="1">
            <p>这是正常的。系统需要等待一段时间后才能验证。验证周期通常是7天或30天。</p>
          </n-collapse-item>
          <n-collapse-item title="价格变化和原因什么时候会显示？" name="2">
            <p>验证完成后会自动显示。在验证之前，这两个字段都是空的。</p>
          </n-collapse-item>
          <n-collapse-item title="我可以手动触发验证吗？" name="3">
            <p>目前不支持手动验证。系统会自动在设定的时间后进行验证。</p>
          </n-collapse-item>
          <n-collapse-item title="验证结果会影响什么？" name="4">
            <p>验证结果主要用于：</p>
            <ul>
              <li>帮助您回顾和学习</li>
              <li>统计判断准确率</li>
              <li>改进分析方法</li>
            </ul>
          </n-collapse-item>
        </n-collapse>
      </section>

      <footer class="help-footer">
        <n-divider />
        <p class="footer-note">
          如有其他问题，请通过 <a href="https://jsj.top/f/GXpvZu" target="_blank" rel="noopener">建议意见</a> 反馈给我们。
        </p>
      </footer>
    </article>
  </div>
</template>

<script setup lang="ts">
import { NButton, NIcon, NAlert, NCard, NCollapse, NCollapseItem, NDivider } from 'naive-ui';
import { ArrowBackOutline as ArrowBack } from '@vicons/ionicons5';
</script>

<style scoped>
.help-page-container {
  max-width: 900px;
  margin: 0 auto;
  padding: 40px 20px;
  background: white;
  min-height: 100vh;
}

.back-button {
  margin-bottom: 24px;
}

.help-content {
  background: #ffffff;
}

.help-header {
  text-align: center;
  margin-bottom: 48px;
  padding-bottom: 24px;
  border-bottom: 2px solid #f1f5f9;
}

.help-header h1 {
  font-size: 2.5rem;
  font-weight: 800;
  color: #1e293b;
  margin-bottom: 12px;
}

.subtitle {
  font-size: 1.1rem;
  color: #64748b;
  margin: 0;
}

.help-section {
  margin-bottom: 48px;
}

.help-section h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1e293b;
  margin-bottom: 20px;
  padding-left: 12px;
  border-left: 4px solid #6366f1;
}

.help-section p {
  font-size: 1.05rem;
  line-height: 1.8;
  color: #334155;
  margin-bottom: 16px;
}

.field-explanation {
  margin-bottom: 32px;
}

.field-explanation h3 {
  font-size: 1.3rem;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 12px;
}

.field-explanation ul {
  margin: 12px 0;
  padding-left: 24px;
}

.field-explanation li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.field-note {
  margin-top: 16px;
  padding: 12px 16px;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 0.95rem;
  line-height: 1.6;
}

.example-positive {
  color: #059669;
  font-weight: 600;
}

.example-negative {
  color: #dc2626;
  font-weight: 600;
}

.flow-diagram {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 24px;
  background: #f8fafc;
  border-radius: 12px;
}

.flow-step {
  display: flex;
  align-items: center;
  gap: 16px;
  width: 100%;
  max-width: 500px;
  padding: 16px 20px;
  background: white;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.step-number {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #6366f1;
  color: white;
  border-radius: 50%;
  font-weight: 700;
  font-size: 1.2rem;
}

.step-content h4 {
  margin: 0 0 4px 0;
  font-size: 1.1rem;
  font-weight: 600;
  color: #1e293b;
}

.step-content p {
  margin: 0;
  font-size: 0.9rem;
  color: #64748b;
}

.flow-arrow {
  font-size: 2rem;
  color: #6366f1;
  margin: 8px 0;
}

.example-card {
  margin-top: 16px;
  background: #f8fafc;
}

.example-text {
  padding: 12px 16px;
  background: white;
  border-left: 4px solid #6366f1;
  border-radius: 4px;
  font-style: italic;
  margin: 12px 0;
}

.result-example {
  margin-top: 16px;
  padding: 16px;
  border-radius: 8px;
}

.result-example.success {
  background: rgba(5, 150, 105, 0.1);
  border: 1px solid rgba(5, 150, 105, 0.3);
}

.result-example.failure {
  background: rgba(220, 38, 38, 0.1);
  border: 1px solid rgba(220, 38, 38, 0.3);
}

.result-example strong {
  display: block;
  margin-bottom: 8px;
  font-size: 1.1rem;
}

.result-example p {
  margin: 4px 0;
  font-size: 0.95rem;
}

.help-footer {
  margin-top: 64px;
  text-align: center;
}

.footer-note {
  color: #64748b;
  font-size: 0.95rem;
}

.footer-note a {
  color: #6366f1;
  text-decoration: none;
}

.footer-note a:hover {
  text-decoration: underline;
}

.privacy-alert {
  margin-bottom: 24px;
}

.privacy-details {
  margin-top: 24px;
}

.privacy-details h3 {
  font-size: 1.2rem;
  font-weight: 600;
  color: #0f172a;
  margin: 24px 0 12px 0;
}

.privacy-details code {
  padding: 2px 8px;
  background: #f1f5f9;
  border-radius: 4px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 0.9em;
  color: #6366f1;
}

.privacy-details ul {
  margin: 12px 0;
  padding-left: 24px;
}

.privacy-details li {
  margin-bottom: 8px;
  line-height: 1.6;
}

.privacy-note {
  margin-top: 20px;
}

.privacy-note ul {
  margin: 8px 0 0 0;
  padding-left: 20px;
}

.privacy-note li {
  margin-bottom: 6px;
}

@media (max-width: 768px) {
  .help-page-container {
    padding: 20px 16px;
  }

  .help-header h1 {
    font-size: 2rem;
  }

  .help-section h2 {
    font-size: 1.5rem;
  }

  .flow-step {
    flex-direction: column;
    text-align: center;
  }
}
</style>
