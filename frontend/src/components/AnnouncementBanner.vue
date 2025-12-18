<template>
  <div v-if="showAnnouncement" class="announcement-container mobile-announcement-container" :class="{ 'login-page-announcement mobile-login-announcement': isLoginPage }">
    <n-card class="announcement-card mobile-card" :class="{ 'login-card-style': isLoginPage }">
      <template #header>
        <div class="announcement-header mobile-announcement-header">
          <n-icon size="18" :component="InformationCircleIcon" class="info-icon" />
          <span>系统公告</span>
        </div>
      </template>
      <div class="announcement-content mobile-announcement-content" v-html="processedContent"></div>
      <div class="announcement-timer mobile-announcement-timer">{{ remainingTimeText }}</div>
      <template #action>
        <n-button quaternary circle size="small" @click="closeAnnouncement" class="mobile-touch-target">
          <template #icon>
            <n-icon :component="CloseIcon" />
          </template>
        </n-button>
      </template>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { NCard, NIcon, NButton } from 'naive-ui';
import { InformationCircleOutline as InformationCircleIcon } from '@vicons/ionicons5';
import { Close as CloseIcon } from '@vicons/ionicons5';
import { useRoute } from 'vue-router';

const props = defineProps<{
  content: string;
  autoCloseTime?: number;
}>();

const emit = defineEmits<{
  (e: 'close'): void;
}>();

const route = useRoute();
const isLoginPage = computed(() => route.path === '/login');

const showAnnouncement = ref(true);
const remainingTime = ref(props.autoCloseTime || 5);
const timer = ref<number | null>(null);

const remainingTimeText = computed(() => {
  return `${remainingTime.value}秒后自动关闭`;
});

const processedContent = computed(() => {
  // 处理文本中的URL
  const urlRegex = /(https?:\/\/[^\s]+)/g;
  return props.content.replace(
    urlRegex, 
    '<a href="$1" target="_blank" class="announcement-link">$1</a>'
  );
});

function closeAnnouncement() {
  showAnnouncement.value = false;
  if (timer.value !== null) {
    window.clearInterval(timer.value);
    timer.value = null;
  }
  emit('close');
}

function updateTimer() {
  if (remainingTime.value <= 1) {
    closeAnnouncement();
  } else {
    remainingTime.value--;
  }
}

onMounted(() => {
  timer.value = window.setInterval(updateTimer, 1000);
});

onBeforeUnmount(() => {
  if (timer.value !== null) {
    window.clearInterval(timer.value);
  }
});
</script>

<style scoped>
.announcement-container {
  position: fixed;
  top: 1rem;
  right: 1rem;
  max-width: 24rem;
  z-index: 50;
  animation: fadeInDown 0.4s cubic-bezier(0.16, 1, 0.3, 1);
}

.announcement-card {
  border-left: 4px solid #667eea;
  box-shadow: 0 8px 32px rgba(31, 38, 135, 0.15);
  border-radius: 12px;
  overflow: hidden;
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  background-color: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-left-width: 4px;
}

.announcement-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 600;
  font-size: 1rem;
  color: #1f2937;
}

.info-icon {
  color: #667eea;
}

.announcement-content {
  margin-bottom: 0.75rem;
  white-space: pre-line;
  color: #4b5563;
  line-height: 1.5;
  font-size: 0.95rem;
}

.announcement-timer {
  font-size: 0.75rem;
  color: #9ca3af;
  font-weight: 500;
}

.announcement-link {
  color: #667eea;
  text-decoration: underline;
  font-weight: 500;
}

@keyframes fadeInDown {
  from {
    opacity: 0;
    transform: translateY(-20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 登录页面适配 */
.login-page-announcement {
  z-index: 1000;
  top: 1.5rem;
  right: 1.5rem;
}

.login-card-style {
  background: rgba(255, 255, 255, 0.85);
  backdrop-filter: blur(20px);
  border-left: 4px solid #2080f0;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.2);
}
</style>
