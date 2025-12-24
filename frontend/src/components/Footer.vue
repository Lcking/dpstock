<template>
  <footer class="site-footer">
    <div class="footer-container">
      <div class="footer-links">
        <a href="/sitemap.xml" target="_blank" class="footer-link">Sitemap</a>
        <span class="divider">|</span>
        <router-link to="/analysis" class="footer-link">分析专栏</router-link>
        <span class="divider">|</span>
        <a href="https://github.com/Lcking/dpstock" target="_blank" rel="noopener" class="footer-link">GitHub</a>
      </div>
      <div class="footer-copyright">
        © {{ currentYear }} Agu AI - 智能股票分析平台
      </div>
      <div class="footer-disclaimer">
        投资有风险，入市需谨慎。本平台分析仅供参考，不构成投资建议。
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
const currentYear = new Date().getFullYear();
</script>

<style scoped>
.site-footer {
  margin-top: auto;
  padding: 32px 20px;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border-top: 1px solid rgba(102, 126, 234, 0.1);
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.footer-links {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.footer-link {
  color: #667eea;
  text-decoration: none;
  font-size: 14px;
  transition: color 0.2s;
}

.footer-link:hover {
  color: #764ba2;
  text-decoration: underline;
}

.divider {
  color: #cbd5e1;
}

.footer-copyright {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 8px;
}

.footer-disclaimer {
  font-size: 12px;
  color: #94a3b8;
}

@media (max-width: 480px) {
  .site-footer {
    padding: 24px 16px;
  }
  
  .footer-links {
    gap: 6px;
  }
  
  .footer-link {
    font-size: 13px;
  }
}
</style>
