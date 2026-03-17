<template>
  <!-- Sticky glassmorphism header -->
  <n-layout-header class="nav-header">
    <div class="nav-inner">
      <router-link to="/" class="nav-logo">
        <span class="logo-icon">🔮</span>
        <span class="logo-text">Agu AI</span>
      </router-link>
      <div class="nav-links">
        <router-link to="/analysis" class="nav-btn">
          <span class="btn-text">分析专栏</span>
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
        </a>

        <button
          v-if="anchorMode === 'anonymous'"
          type="button"
          class="nav-btn nav-btn-button bind-btn"
          @click="showBindDialog = true"
        >
          <span class="btn-text">绑定邮箱</span>
        </button>

        <n-dropdown trigger="click" :options="myMenuOptions" @select="handleMyMenuSelect">
          <button class="nav-btn nav-btn-button" type="button">
            <n-badge :value="notificationStore.pendingReviewCount" :max="99" :offset="[0, 4]">
              <span class="btn-text">我的</span>
            </n-badge>
            <n-icon size="14" class="dropdown-icon">
              <CaretDownOutline />
            </n-icon>
          </button>
        </n-dropdown>
        
        <!-- Quota Status -->
        <QuotaStatus 
          ref="quotaStatusRef"
          @open-invite="showInviteDialog = true"
        />
      </div>
    </div>
  </n-layout-header>
  <div class="nav-spacer" :style="{ height: `${navSpacerHeight}px` }" aria-hidden="true"></div>
  
  <!-- Invite Dialog -->
  <InviteDialog 
    v-model:show="showInviteDialog"
    :quota-status="quotaStatus"
    @invite-generated="handleInviteGenerated"
  />

  <AnchorBindDialog
    v-model:show="showBindDialog"
    @bind-success="handleBindSuccess"
  />
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, nextTick } from 'vue';
import { useRouter } from 'vue-router';
import QuotaStatus from './QuotaStatus.vue';
import InviteDialog from './InviteDialog.vue';
import AnchorBindDialog from './AnchorBindDialog.vue';
import { apiService } from '@/services/api';
import { NBadge, NDropdown, NIcon } from 'naive-ui';
import { CaretDownOutline } from '@vicons/ionicons5';
import { useNotificationStore } from '@/stores/notification';

const router = useRouter();
const notificationStore = useNotificationStore();

interface NavLink {
  text: string
  href: string
  target?: string
  rel?: string
}

const links: NavLink[] = [
  { text: '实盘策略平台', href: 'https://www.qifuapp.net/', target: '_blank', rel: 'noopener sponsored' }
];

const myMenuOptions = [
  { label: '我的观察', key: '/watchlist' },
  { label: '判断日记', key: '/journal' },
  { label: '用户中心', key: '/me' },
  { label: '额度与邀请', key: 'quota-invite' }
];

const showInviteDialog = ref(false);
const showBindDialog = ref(false);
const quotaStatusRef = ref<any>(null);
const quotaStatus = ref<any>(null);
const anchorMode = ref<'anonymous' | 'anchor'>('anonymous');
const navSpacerHeight = ref(84);
const headerEl = ref<HTMLElement | null>(null);
let resizeObserver: ResizeObserver | null = null;

const updateNavSpacerHeight = () => {
  navSpacerHeight.value = headerEl.value?.offsetHeight ?? 84;
};

const handleMyMenuSelect = (key: string) => {
  if (key === 'quota-invite') {
    showInviteDialog.value = true;
    return;
  }
  router.push(key);
};

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

const loadAnchorStatus = async () => {
  try {
    const data = await apiService.getAnchorStatus();
    anchorMode.value = data?.mode === 'anchor' ? 'anchor' : 'anonymous';
  } catch (error) {
    console.error('Failed to load anchor status:', error);
    anchorMode.value = 'anonymous';
  }
};

const handleBindSuccess = async () => {
  anchorMode.value = 'anchor';
  await loadQuotaStatus();
};

onMounted(() => {
  loadQuotaStatus();
  loadAnchorStatus();

  nextTick(() => {
    headerEl.value = document.querySelector('.nav-header');
    updateNavSpacerHeight();

    if (typeof ResizeObserver !== 'undefined' && headerEl.value) {
      resizeObserver = new ResizeObserver(() => updateNavSpacerHeight());
      resizeObserver.observe(headerEl.value);
    }

    window.addEventListener('resize', updateNavSpacerHeight);
  });
});

onBeforeUnmount(() => {
  resizeObserver?.disconnect();
  window.removeEventListener('resize', updateNavSpacerHeight);
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
  backdrop-filter: blur(22px);
  -webkit-backdrop-filter: blur(22px);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 
    0 10px 36px rgba(79, 93, 160, 0.10),
    0 1px 0 rgba(255, 255, 255, 0.68) inset;
  border-bottom: 1px solid rgba(91, 103, 241, 0.10);
}

.nav-spacer {
  width: 100%;
  flex-shrink: 0;
}

.nav-inner {
  max-width: 1400px;
  margin: 0 auto;
  height: 68px;
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
  color: #1f2540;
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
  letter-spacing: -0.03em;
}

@keyframes float {
  0%, 100% { transform: translateY(0px); }
  50% { transform: translateY(-3px); }
}

.nav-links {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

/* Modern Button with Glow Effect */
.nav-btn {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border-radius: 24px;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  color: #5560d6;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(91, 103, 241, 0.16);
  overflow: visible;
  box-shadow: 0 8px 18px rgba(148, 163, 184, 0.12);
  transition: background 0.3s cubic-bezier(0.4, 0, 0.2, 1), color 0.3s cubic-bezier(0.4, 0, 0.2, 1), border-color 0.3s cubic-bezier(0.4, 0, 0.2, 1), box-shadow 0.3s cubic-bezier(0.4, 0, 0.2, 1), transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.nav-btn-button {
  font: inherit;
  cursor: pointer;
}

.bind-btn {
  color: #6d28d9;
  border-color: rgba(124, 58, 237, 0.22);
}

.btn-text {
  position: relative;
  z-index: 1;
}

.dropdown-icon {
  position: relative;
  z-index: 1;
}

.nav-btn:hover {
  background: linear-gradient(135deg, #5b67f1 0%, #7c54d9 100%);
  color: white;
  border-color: transparent;
  box-shadow: 0 12px 24px rgba(91, 103, 241, 0.24);
  transform: translateY(-1px);
}

.nav-btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.3);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .nav-inner {
    height: 60px;
    padding: 0 16px;
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
    padding: 6px 12px;
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