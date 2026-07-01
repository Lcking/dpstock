<template>
  <footer class="site-footer">
    <div class="footer-container">
      <div class="footer-links">
        <a href="/sitemap.xml" target="_blank" class="footer-link">Sitemap</a>
        <span class="divider">|</span>
        <router-link to="/analysis" class="footer-link">分析专栏</router-link>
        <span class="divider">|</span>
        <a href="/stocks" class="footer-link">个股列表</a>
        <span class="divider">|</span>
        <a href="/risk-stocks" class="footer-link">风险股清单</a>
        <span class="divider">|</span>
        <router-link to="/help/judgment-verification" class="footer-link">判断验证说明</router-link>
        <span class="divider">|</span>
        <a href="/review/weekly" class="footer-link">判断验证周报</a>
        <span class="divider">|</span>
        <router-link to="/about" class="footer-link">关于我们</router-link>
        <span class="divider">|</span>
        <a href="https://jsj.top/f/GXpvZu" target="_blank" rel="noopener" class="footer-link">建议意见</a>
      </div>
      <div class="footer-copyright">
        © {{ currentYear }} Agu AI - 智能股票分析平台
      </div>
      <div class="footer-disclaimer">
        投资有风险，入市需谨慎。本平台分析仅供参考，不构成投资建议。
      </div>
      <div v-if="accuracySummary" class="footer-accuracy">
        {{ accuracySummary }}
      </div>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue';
import { apiService } from '@/services/api';

const currentYear = new Date().getFullYear();
const accuracySummary = ref('');

onMounted(async () => {
  const stats = await apiService.getJudgmentAccuracyStats(90);
  if (stats?.reviewed_count > 0 && stats.support_rate != null) {
    accuracySummary.value = `近 ${stats.window_days} 天历史验证：已复盘 ${stats.reviewed_count} 条，系统支持率 ${stats.support_rate}%（仅供参考）`;
  }
});
</script>

<style scoped>
.site-footer {
  margin-top: auto;
  padding: 32px 20px;
  background: linear-gradient(135deg, rgba(91, 103, 241, 0.06) 0%, rgba(124, 84, 217, 0.06) 100%);
  border-top: 1px solid rgba(91, 103, 241, 0.10);
  backdrop-filter: blur(10px);
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
  color: #5560d6;
  text-decoration: none;
  font-size: 14px;
  font-weight: 600;
  transition: color 0.2s ease, opacity 0.2s ease;
}

.footer-link:hover {
  color: #7c54d9;
  opacity: 0.92;
}

.divider {
  color: #cbd5e1;
}

.footer-copyright {
  font-size: 14px;
  color: #667085;
  margin-bottom: 8px;
}

.footer-disclaimer {
  font-size: 12px;
  color: #98a2b3;
}

.footer-accuracy {
  margin-top: 8px;
  font-size: 12px;
  color: #64748b;
  line-height: 1.5;
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
