import type { MarketTimeInfo } from '@/types';
import { marked } from 'marked';

// 防抖函数
export function debounce<T extends (...args: any[]) => any>(
  func: T,
  wait: number
): (...args: Parameters<T>) => void {
  let timeout: number | null = null;

  return function (...args: Parameters<T>): void {
    const later = () => {
      timeout = null;
      func(...args);
    };

    if (timeout !== null) {
      clearTimeout(timeout);
    }
    timeout = window.setTimeout(later, wait);
  };
}

// 格式化市值
export function formatMarketValue(value: number): string {
  if (!value) return '未知';

  if (value >= 1000000000000) {
    return (value / 1000000000000).toFixed(2) + '万亿';
  } else if (value >= 100000000) {
    return (value / 100000000).toFixed(2) + '亿';
  } else if (value >= 10000) {
    return (value / 10000).toFixed(2) + '万';
  } else {
    return value.toFixed(2);
  }
}

// 解析Markdown
export function parseMarkdown(text: string): string {
  try {
    const result = marked(text);
    if (typeof result === 'string') {
      return result;
    }
    return '';
  } catch (e) {
    console.error('解析Markdown出错:', e);
    return text;
  }
}

// 更新市场时间信息
export function updateMarketTimeInfo(): MarketTimeInfo {
  const now = new Date();
  const dayOfWeek = now.getDay(); // 0=周日, 6=周六
  const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;

  // 当前时间
  const currentTime = now.toLocaleTimeString('zh-CN', { hour12: false });

  // 周末所有市场休市
  if (isWeekend) {
    return {
      currentTime,
      cnMarket: { isOpen: false, nextTime: '周末休市，周一开盘' },
      hkMarket: { isOpen: false, nextTime: '周末休市，周一开盘' },
      usMarket: { isOpen: false, nextTime: '周末休市，周一开盘' }
    };
  }

  // 中国时间
  const cnOptions = { timeZone: 'Asia/Shanghai', hour12: false } as Intl.DateTimeFormatOptions;
  const cnTime = now.toLocaleString('zh-CN', cnOptions);
  const cnHour = new Date(cnTime).getHours();
  const cnMinute = new Date(cnTime).getMinutes();

  // A股市场状态
  const cnMarketOpen = (cnHour === 9 && cnMinute >= 30) || (cnHour === 10) ||
    (cnHour === 11 && cnMinute <= 30) ||
    (cnHour >= 13 && cnHour < 15);

  const cnNextTime = getNextTimeText(cnMarketOpen, cnHour, cnMinute, 9, 30, 15, 0);

  // 港股市场状态（与A股相同时区）
  const hkMarketOpen = (cnHour === 9 && cnMinute >= 30) ||
    (cnHour === 10) || (cnHour === 11) ||
    (cnHour >= 13 && cnHour < 16);

  const hkNextTime = getNextTimeText(hkMarketOpen, cnHour, cnMinute, 9, 30, 16, 0);

  // 获取美国东部时间
  const usOptions = { timeZone: 'America/New_York', hour12: false } as Intl.DateTimeFormatOptions;
  const usTime = now.toLocaleString('zh-CN', usOptions);
  const usHour = new Date(usTime).getHours();
  const usMinute = new Date(usTime).getMinutes();

  // 美股市场状态
  const usMarketOpen = (usHour >= 9 && usHour < 16) ||
    (usHour === 16 && usMinute === 0);

  const usNextTime = getNextTimeText(usMarketOpen, usHour, usMinute, 9, 30, 16, 0);

  return {
    currentTime,
    cnMarket: { isOpen: cnMarketOpen, nextTime: cnNextTime },
    hkMarket: { isOpen: hkMarketOpen, nextTime: hkNextTime },
    usMarket: { isOpen: usMarketOpen, nextTime: usNextTime }
  };
}

// 辅助函数：获取距离下一次开/闭市的时间文本
function getNextTimeText(
  isOpen: boolean,
  currentHour: number,
  currentMinute: number,
  openHour: number,
  openMinute: number,
  closeHour: number,
  closeMinute: number
): string {
  if (isOpen) {
    // 计算距离收盘时间
    let timeToCloseMinutes = (closeHour - currentHour) * 60 + (closeMinute - currentMinute);

    if (timeToCloseMinutes <= 0) {
      return '即将收盘';
    }

    const hours = Math.floor(timeToCloseMinutes / 60);
    const minutes = timeToCloseMinutes % 60;

    return `距离收盘还有 ${hours}小时${minutes}分钟`;
  } else {
    // 计算距离开盘时间
    let nextOpenHour = openHour;
    let nextOpenMinute = openMinute;
    let isNextDay = false;

    if (currentHour >= closeHour) {
      // 已经过了今天的收盘时间，下一个开盘是明天
      isNextDay = true;
    } else if (currentHour < openHour || (currentHour === openHour && currentMinute < openMinute)) {
      // 还没到今天的开盘时间
      isNextDay = false;
    } else {
      // 当前处于盘中休息时间，下一个开盘时间是当天下午
      nextOpenHour = 13;
      nextOpenMinute = 0;
    }

    let timeToOpenMinutes;

    if (isNextDay) {
      timeToOpenMinutes = (24 - currentHour + nextOpenHour) * 60 + (nextOpenMinute - currentMinute);
    } else {
      timeToOpenMinutes = (nextOpenHour - currentHour) * 60 + (nextOpenMinute - currentMinute);
    }

    if (timeToOpenMinutes <= 0) {
      return '即将开盘';
    }

    const hours = Math.floor(timeToOpenMinutes / 60);
    const minutes = timeToOpenMinutes % 60;

    return `距离开盘还有 ${hours}小时${minutes}分钟`;
  }
}

// 获取品类名称
export function getCategoryName(marketType: string): string {
  const categoryMap: Record<string, string> = {
    'A': '股票',
    'HK': '股票',
    'US': '股票',
    'ETF': 'ETF',
    'LOF': 'LOF'
  };
  return categoryMap[marketType] || '股票';
}
