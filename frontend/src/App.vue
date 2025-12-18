<template>
  <n-config-provider :theme="theme">
    <n-message-provider>
      <n-loading-bar-provider>
        <n-dialog-provider>
          <n-notification-provider>
            <n-layout>
                <NavBar />
            <router-view />
             </n-layout>
          </n-notification-provider>
        </n-dialog-provider>
      </n-loading-bar-provider>
    </n-message-provider>
  </n-config-provider>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import NavBar from '@/components/NavBar.vue'
import { 
  NConfigProvider, 
  NMessageProvider, 
  NLoadingBarProvider, 
  NDialogProvider, 
  NNotificationProvider, 
} from 'naive-ui'

// 主题设置 (默认使用亮色主题)
const theme = ref<any>(null) // 可以切换为 darkTheme 以启用暗色模式
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
</style>
