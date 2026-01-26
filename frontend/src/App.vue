<template>
  <n-config-provider :theme="theme">
    <n-message-provider>
      <n-loading-bar-provider>
        <n-dialog-provider>
          <n-notification-provider>
            <n-layout class="app-layout">
                <NavBar />
                <main class="main-content">
                  <router-view />
                </main>
                <Footer />
            </n-layout>
          </n-notification-provider>
        </n-dialog-provider>
      </n-loading-bar-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import NavBar from '@/components/NavBar.vue'
import Footer from '@/components/Footer.vue'
import { NLayout } from 'naive-ui'
import { 
  NConfigProvider, 
  NMessageProvider, 
  NLoadingBarProvider, 
  NDialogProvider, 
  NNotificationProvider, 
} from 'naive-ui'
import { getOrCreateUserId } from '@/utils/cookies'
import { getOrCreateAnonymousId } from '@/utils/anonymousId'
import { useNotificationStore } from '@/stores/notification'

// 主题设置 (默认使用亮色主题)
const theme = ref<any>(null) // 可以切换为 darkTheme 以启用暗色模式

const notificationStore = useNotificationStore()

// Initialize user identity on app mount
onMounted(() => {
  // Initialize cookie-based user ID (for quota system)
  getOrCreateUserId();
  
  // Initialize anonymous ID (for anchor system)
  getOrCreateAnonymousId();
  
  // Start polling for notifications
  notificationStore.startPolling();
  
  console.log('[App] User identity initialized');
});
</script>

<style>
/* App-level styles - complement style.css */
body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  margin: 0;
  padding: 0;
  min-height: 100vh;
}

.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.main-content {
  flex: 1;
}
</style>
