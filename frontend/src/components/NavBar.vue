<template>
  <!-- Fixed glassmorphism header -->
  <n-layout-header class="nav-header">
    <div class="nav-inner">
      <router-link to="/" class="nav-logo">
        <span class="logo-icon">🔮</span>
        <span class="logo-text">Agu AI</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/analysis" class="nav-btn">
          <span class="btn-text">分析专栏</span>
          <span class="btn-glow"></span>
        </router-link>
        
        <router-link to="/journal" class="nav-btn">
          <n-badge :value="notificationStore.pendingReviewCount" :max="99" :offset="[6, -6]">
            <span class="btn-text">判断日记</span>
          </n-badge>
          <span class="btn-glow"></span>
        </router-link>
        
        <a
          v-for="link in links"
          :key="link.text"
          :href="link.href"
          :target="link.target || '_blank'"
          :rel="link.rel || 'noopener'"
          class="nav-btn"
        >
          <span class="btn-text">{{ link.text }}</span>
          <span class="btn-glow"></span>
        </a>
        
        <!-- Quota Status -->
        <QuotaStatus 
          ref="quotaStatusRef"
          @open-invite="showInviteDialog = true"
        />
      </div>
    </div>
  </n-layout-header>
  
  <!-- Invite Dialog -->
  <InviteDialog 
    v-model:show="showInviteDialog"
    :quota-status="quotaStatus"
    @invite-generated="handleInviteGenerated"
  />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue';
import QuotaStatus from './QuotaStatus.vue';
import InviteDialog from './InviteDialog.vue';
import { apiService } from '@/services/api';
import { NBadge } from 'naive-ui';
import { useNotificationStore } from '@/stores/notification';

const notificationStore = useNotificationStore();

interface NavLink {
  text: string
  href: string
  target?: string
  rel?: string
}

const links: NavLink[] = [
  { text: '实盘策略平台', href: 'https://www.qifuapp.net/', target: '_blank', rel: 'noopener sponsored' },
  { text: '配查查', href: 'https://www.peichacha.net/', target: '_blank', rel: 'noopener sponsored' }
];

const showInviteDialog = ref(false);
const quotaStatusRef = ref<any>(null);
const quotaStatus = ref<any>(null);

const handleInviteGenerated = async () => {
  // Refresh quota status after invite generation
  if (quotaStatusRef.value) {
    await quotaStatusRef.value.refresh();
  }
  await loadQuotaStatus();
};

const loadQuotaStatus = async () => {
  try {
    const data = await apiService.getQuotaStatus();
    if (data) {
      quotaStatus.value = data;
    }
  } catch (error) {
    console.error('Failed to load quota status:', error);
  }
};

onMounted(() => {
  loadQuotaStatus();
});
</script>

<style scoped>
/* Glassmorphism Navigation */
.nav-header {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  z-index: 100;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background: rgba(255, 255, 255, 0.75);
  box-shadow: 
    0 4px 30px rgba(0, 0, 0, 0.05),
    0 1px 0 rgba(255, 255, 255, 0.5) inset;
  border-bottom: 1px solid rgba(255, 255, 255, 0.3);
}

/* Push body content below the fixed bar */
:global(body) {
  padding-top: 95px;
}

.nav-inner {
  max-width: 1400px;
  margin: 0 auto;
  height: 64px;
  padding: 0 24px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}

/* Gradient Logo */
.nav-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  font-size: 22px;
  font-weight: 700;
  user-select: none;
  cursor: pointer;
  text-decoration: none;
}

.logo-icon {
  font-size: 26px;
  animation: float 3s ease-in-out infinite;
}

.logo-text {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 50%, #ec4899 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  letter-spacing: -0.02em;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}

.nav-links {
  display: flex;
  gap: 12px;
  align-items: center;
}

/* Modern Button with Glow Effect */
.nav-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  padding: 8px 20px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 500;
  text-decoration: none;
  color: #667eea;
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border: 1px solid rgba(102, 126, 234, 0.3);
  overflow: visible;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.btn-text {
  position: relative;
  z-index: 1;
}

.btn-glow {
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent,
    rgba(102, 126, 234, 0.2),
    transparent
  );
  transition: left 0.5s;
}

.nav-btn:hover {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-color: transparent;
  transform: translateY(-2px);
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.35);
}

.nav-btn:hover .btn-glow {
  left: 100%;
}

.nav-btn:active {
  transform: translateY(0);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .nav-inner {
    height: 56px;
    padding: 0 16px;
  }
  
  :global(body) {
    padding-top: 71px;
  }
  
  .nav-logo {
    font-size: 18px;
    gap: 8px;
  }
  
  .logo-icon {
    font-size: 22px;
  }
  
  .nav-links {
    gap: 8px;
  }
  
  .nav-btn {
    padding: 6px 14px;
    font-size: 13px;
  }
  
  .nav-btn:hover {
    transform: none;
  }
}

@media (max-width: 480px) {
  .nav-btn {
    padding: 5px 12px;
    font-size: 12px;
    border-radius: 16px;
  }
  
  .nav-logo {
    font-size: 16px;
  }
  
  .logo-icon {
    font-size: 20px;
  }
}
</style>