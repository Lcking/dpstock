<template>
  <div class="market-time-card">
    <n-grid :x-gap="16" :y-gap="16" cols="1 s:2 m:4" responsive="screen">
      <!-- 当前时间 -->
      <n-grid-item>
        <div class="time-block current-time-block">
          <p class="time-label">当前时间</p>
          <p class="current-time">{{ marketInfo.currentTime }}</p>
        </div>
      </n-grid-item>
      
      <!-- A股状态 -->
      <n-grid-item>
        <div class="time-block market-block" :class="{'market-open-block': marketInfo.cnMarket.isOpen, 'market-closed-block': !marketInfo.cnMarket.isOpen}">
          <p class="time-label">A股市场</p>
          <div class="market-status" :class="marketInfo.cnMarket.isOpen ? 'status-open' : 'status-closed'">
            <n-tag v-if="marketInfo.cnMarket.isOpen" :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><pulse-icon /></n-icon></template>
              交易中
            </n-tag>
            <n-tag v-else :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><time-icon /></n-icon></template>
              已休市
            </n-tag>
          </div>
          <p class="time-counter">{{ marketInfo.cnMarket.nextTime }}</p>
          <div class="market-progress-container">
            <div class="market-progress-bar" 
                 :class="marketInfo.cnMarket.isOpen ? 'progress-open' : 'progress-closed'"
                 :style="{ width: marketInfo.cnMarket.progressPercentage + '%' }">
            </div>
            <div class="progress-markers" :class="{'reverse-markers': !marketInfo.cnMarket.isOpen}">
              <div class="progress-marker">开盘</div>
              <div class="progress-marker">收盘</div>
            </div>
          </div>
        </div>
      </n-grid-item>

      <!-- 港股状态 -->
      <n-grid-item>
        <div class="time-block market-block" :class="{'market-open-block': marketInfo.hkMarket.isOpen, 'market-closed-block': !marketInfo.hkMarket.isOpen}">
          <p class="time-label">港股市场</p>
          <div class="market-status" :class="marketInfo.hkMarket.isOpen ? 'status-open' : 'status-closed'">
            <n-tag v-if="marketInfo.hkMarket.isOpen" :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><pulse-icon /></n-icon></template>
              交易中
            </n-tag>
            <n-tag v-else :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><time-icon /></n-icon></template>
              已休市
            </n-tag>
          </div>
          <p class="time-counter">{{ marketInfo.hkMarket.nextTime }}</p>
          <div class="market-progress-container">
            <div class="market-progress-bar" 
                 :class="marketInfo.hkMarket.isOpen ? 'progress-open' : 'progress-closed'"
                 :style="{ width: marketInfo.hkMarket.progressPercentage + '%' }">
            </div>
            <div class="progress-markers" :class="{'reverse-markers': !marketInfo.hkMarket.isOpen}">
              <div class="progress-marker">开盘</div>
              <div class="progress-marker">收盘</div>
            </div>
          </div>
        </div>
      </n-grid-item>
      
      <!-- 美股状态 -->
      <n-grid-item>
        <div class="time-block market-block" :class="{'market-open-block': marketInfo.usMarket.isOpen, 'market-closed-block': !marketInfo.usMarket.isOpen}">
          <p class="time-label">美股市场</p>
          <div class="market-status" :class="marketInfo.usMarket.isOpen ? 'status-open' : 'status-closed'">
            <n-tag v-if="marketInfo.usMarket.isOpen" :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><pulse-icon /></n-icon></template>
              交易中
            </n-tag>
            <n-tag v-else :bordered="false" round class="status-tag">
              <template #icon><n-icon size="16"><time-icon /></n-icon></template>
              已休市
            </n-tag>
          </div>
          <p class="time-counter">{{ marketInfo.usMarket.nextTime }}</p>
          <div class="market-progress-container">
            <div class="market-progress-bar" 
                 :class="marketInfo.usMarket.isOpen ? 'progress-open' : 'progress-closed'"
                 :style="{ width: marketInfo.usMarket.progressPercentage + '%' }">
            </div>
            <div class="progress-markers" :class="{'reverse-markers': !marketInfo.usMarket.isOpen}">
              <div class="progress-marker">开盘</div>
              <div class="progress-marker">收盘</div>
            </div>
          </div>
        </div>
      </n-grid-item>
    </n-grid>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount } from 'vue';
import { NGrid, NGridItem, NTag, NIcon } from 'naive-ui';
import { 
  PulseOutline as PulseIcon,
  TimeOutline as TimeIcon,
} from '@vicons/ionicons5';
import { updateMarketTimeInfo } from '@/utils';
import type { MarketTimeInfo, MarketStatus } from '@/types';

const marketInfo = ref<MarketTimeInfo>({
  currentTime: '',
  cnMarket: { isOpen: false, nextTime: '' },
  hkMarket: { isOpen: false, nextTime: '' },
  usMarket: { isOpen: false, nextTime: '' }
});

let intervalId: number | null = null;

function updateMarketTime() {
  const baseInfo = updateMarketTimeInfo();
  
  // 计算各市场的进度百分比
  marketInfo.value = {
    currentTime: baseInfo.currentTime,
    cnMarket: {
      ...baseInfo.cnMarket,
      progressPercentage: calculateProgressPercentage(baseInfo.cnMarket)
    },
    hkMarket: {
      ...baseInfo.hkMarket,
      progressPercentage: calculateProgressPercentage(baseInfo.hkMarket)
    },
    usMarket: {
      ...baseInfo.usMarket,
      progressPercentage: calculateProgressPercentage(baseInfo.usMarket)
    }
  };
}

// 计算进度百分比的函数
function calculateProgressPercentage(market: MarketStatus): number {
  const timeText = market.nextTime;
  if (!timeText) return 50;
  
  try {
    if (timeText.includes("已休市") || timeText.includes("已闭市")) {
      return market.isOpen ? 100 : 0;
    }
    
    if (timeText.includes("即将开市") || timeText.includes("即将开盘")) {
      return market.isOpen ? 5 : 95;
    }
    
    let hours = 0;
    let minutes = 0;
    
    const hourMinuteMatch = timeText.match(/(\d+)\s*小时\s*(\d+)\s*分钟/);
    if (hourMinuteMatch) {
      hours = parseInt(hourMinuteMatch[1]);
      minutes = parseInt(hourMinuteMatch[2]);
    } else {
      const hourMatch = timeText.match(/(\d+)\s*小时/);
      const minuteMatch = timeText.match(/(\d+)\s*分钟/);
      hours = hourMatch ? parseInt(hourMatch[1]) : 0;
      minutes = minuteMatch ? parseInt(minuteMatch[1]) : 0;
    }
    
    const totalMinutes = hours * 60 + minutes;
    
    let tradingMinutes = 240; 
    let nonTradingMinutes = 1200;
    
    if (timeText.includes("A股") || timeText.includes("沪深") || 
        (!timeText.includes("港股") && !timeText.includes("美股"))) {
      tradingMinutes = 240;
      nonTradingMinutes = 1200;
    } else if (timeText.includes("港股")) {
      tradingMinutes = 390;
      nonTradingMinutes = 1050;
    } else if (timeText.includes("美股")) {
      tradingMinutes = 390;
      nonTradingMinutes = 1050;
    }
    
    if (market.isOpen) {
      if (timeText.includes("距离收市") || timeText.includes("距离闭市") || 
          timeText.includes("距离休市") || timeText.includes("距离收盘")) {
        const tradedMinutes = tradingMinutes - totalMinutes;
        const percentage = (tradedMinutes / tradingMinutes) * 100;
        return Math.max(0, Math.min(100, percentage));
      } else {
        return 5;
      }
    } else {
      if (timeText.includes("距离开市") || timeText.includes("距离开盘")) {
        const closedMinutes = nonTradingMinutes - totalMinutes;
        const percentage = (closedMinutes / nonTradingMinutes) * 100;
        return Math.max(0, Math.min(100, 100 - percentage));
      } else {
        return 5;
      }
    }
  } catch (error) {
    console.error("计算市场进度时出错:", error);
    return market.isOpen ? 50 : 5;
  }
}

onMounted(() => {
  updateMarketTime();
  intervalId = window.setInterval(updateMarketTime, 1000);
});

onBeforeUnmount(() => {
  if (intervalId !== null) {
    window.clearInterval(intervalId);
    intervalId = null;
  }
});
</script>

<style scoped>
/* Modern Glassmorphism Market Time Card */
.market-time-card {
  margin-bottom: 1.5rem;
  padding: 1.25rem;
  border-radius: 24px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.5);
  box-shadow: 
    0 8px 32px rgba(102, 126, 234, 0.1),
    0 2px 8px rgba(0, 0, 0, 0.05);
  transition: transform 0.3s ease;
}

.market-time-card:hover {
  transform: translateY(-2px);
  background: rgba(255, 255, 255, 0.85);
}

/* Grid Layout */
:deep(.n-grid) {
  justify-content: center;
  width: 100%;
}

:deep(.n-grid-item) {
  display: flex;
  justify-content: center;
}

/* Time Block Base */
.time-block {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 1rem;
  border-radius: 16px;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  height: 100%;
  box-sizing: border-box;
  width: 100%;
  min-height: 160px;
  justify-content: center;
  position: relative;
  overflow: hidden;
}

/* Current Time Block */
.current-time-block {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.05) 0%, rgba(118, 75, 162, 0.05) 100%);
  border: 1px solid rgba(102, 126, 234, 0.15);
}

.current-time-block:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  border-color: rgba(102, 126, 234, 0.3);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
}

/* Market Block */
.market-block {
  border: 1px solid transparent;
}

/* Open Market */
.market-open-block {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.05) 0%, rgba(5, 150, 105, 0.02) 100%);
  border-color: rgba(16, 185, 129, 0.2);
}

.market-open-block:hover {
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.1) 0%, rgba(5, 150, 105, 0.05) 100%);
  border-color: rgba(16, 185, 129, 0.35);
  box-shadow: 0 4px 12px rgba(16, 185, 129, 0.15);
}

.market-open-block::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
}

/* Closed Market */
.market-closed-block {
  background: rgba(156, 163, 175, 0.05);
  border-color: rgba(156, 163, 175, 0.15);
  opacity: 0.9;
}

.market-closed-block:hover {
  background: rgba(156, 163, 175, 0.1);
  border-color: rgba(156, 163, 175, 0.3);
  opacity: 1;
}

.market-closed-block::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 4px;
  background: linear-gradient(90deg, #9ca3af 0%, #6b7280 100%);
}

/* Typography */
.time-label {
  font-size: 0.85rem;
  color: #6b7280;
  margin-bottom: 0.5rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.current-time {
  font-size: 2.2rem;
  font-weight: 700;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
  margin: 0;
  font-variant-numeric: tabular-nums;
  letter-spacing: -1px;
}

.time-counter {
  font-size: 0.85rem;
  color: #6b7280;
  margin-top: 0.75rem;
  width: 100%;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

/* Market Status Tag */
.market-status {
  min-height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-tag {
  padding: 0 12px !important;
  height: 28px !important;
  font-size: 0.8rem !important;
  font-weight: 600 !important;
}

.status-open .status-tag {
  background: rgba(16, 185, 129, 0.1);
  color: #059669;
}

.status-closed .status-tag {
  background: rgba(107, 114, 128, 0.1);
  color: #6b7280;
}

/* Progress Bar */
.market-progress-container {
  width: 80%;
  height: 4px;
  background: rgba(0, 0, 0, 0.05);
  border-radius: 2px;
  margin-top: 0.75rem;
  position: relative;
  overflow: visible;
}

.market-progress-bar {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
  position: relative;
}

.progress-open {
  background: linear-gradient(90deg, #10b981 0%, #059669 100%);
  box-shadow: 0 0 8px rgba(16, 185, 129, 0.4);
}

.progress-open::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: linear-gradient(90deg, transparent, rgba(255,255,255,0.5), transparent);
  background-size: 200% 100%;
  animation: shimmer 2s infinite;
}

.progress-closed {
  background: #9ca3af;
}

/* Markers */
.progress-markers {
  position: absolute;
  top: -16px;
  left: 0;
  width: 100%;
  display: flex;
  justify-content: space-between;
  font-size: 0.65rem;
  color: #9ca3af;
  font-weight: 500;
}

.reverse-markers {
  flex-direction: row-reverse;
}

@keyframes shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .market-time-card {
    padding: 1rem;
    margin-bottom: 1rem;
    border-radius: 16px;
  }
  
  .time-block {
    padding: 0.75rem;
    min-height: 140px;
  }
  
  .current-time {
    font-size: 1.75rem;
  }
}
</style>
