<template>
  <div class="share-buttons">
    <div class="share-title">分享到</div>
    <div class="share-icons">
      <!-- 微信 -->
      <n-popover trigger="click" placement="top">
        <template #trigger>
          <button class="share-btn wechat" title="分享到微信">
            <n-icon size="20">
              <LogoWechat />
            </n-icon>
          </button>
        </template>
        <div class="qrcode-container">
          <div class="qrcode-title">微信扫码分享</div>
          <img :src="wechatQrCode" alt="微信二维码" class="qrcode-image" />
        </div>
      </n-popover>

      <!-- 微博 -->
      <button class="share-btn weibo" @click="shareToWeibo" title="分享到微博">
        <n-icon size="20">
          <ShareSocial />
        </n-icon>
      </button>

      <!-- Twitter -->
      <button class="share-btn twitter" @click="shareToTwitter" title="分享到 Twitter">
        <n-icon size="20">
          <LogoTwitter />
        </n-icon>
      </button>

      <!-- Facebook -->
      <button class="share-btn facebook" @click="shareToFacebook" title="分享到 Facebook">
        <n-icon size="20">
          <LogoFacebook />
        </n-icon>
      </button>

      <!-- 复制链接 -->
      <button class="share-btn copy" @click="copyLink" title="复制链接">
        <n-icon size="20">
          <CopyOutline />
        </n-icon>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { NIcon, NPopover, useMessage } from 'naive-ui';
import { 
  LogoWechat, 
  ShareSocial, 
  LogoTwitter, 
  LogoFacebook,
  CopyOutline 
} from '@vicons/ionicons5';

const props = defineProps<{
  url: string;
  title: string;
}>();

const message = useMessage();

// 生成微信二维码
const wechatQrCode = computed(() => {
  return `https://api.qrserver.com/v1/create-qr-code/?size=200x200&data=${encodeURIComponent(props.url)}`;
});

// 分享到微博
function shareToWeibo() {
  const weiboUrl = `https://service.weibo.com/share/share.php?url=${encodeURIComponent(props.url)}&title=${encodeURIComponent(props.title)}`;
  window.open(weiboUrl, '_blank', 'width=600,height=400');
}

// 分享到 Twitter
function shareToTwitter() {
  const twitterUrl = `https://twitter.com/intent/tweet?text=${encodeURIComponent(props.title)}&url=${encodeURIComponent(props.url)}`;
  window.open(twitterUrl, '_blank', 'width=600,height=400');
}

// 分享到 Facebook
function shareToFacebook() {
  const facebookUrl = `https://www.facebook.com/sharer/sharer.php?u=${encodeURIComponent(props.url)}`;
  window.open(facebookUrl, '_blank', 'width=600,height=400');
}

// 复制链接
async function copyLink() {
  try {
    await navigator.clipboard.writeText(props.url);
    message.success('链接已复制到剪贴板');
  } catch (error) {
    message.error('复制失败，请手动复制');
  }
}
</script>

<style scoped>
.share-buttons {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 16px 0;
  padding: 12px 0;
}

.share-title {
  font-size: 14px;
  color: #666;
  font-weight: 500;
}

.share-icons {
  display: flex;
  gap: 8px;
}

.share-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.3s ease;
  color: white;
}

.share-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.share-btn.wechat {
  background: linear-gradient(135deg, #09bb07, #00d100);
}

.share-btn.weibo {
  background: linear-gradient(135deg, #e6162d, #ff5722);
}

.share-btn.twitter {
  background: linear-gradient(135deg, #1da1f2, #0d8bd9);
}

.share-btn.facebook {
  background: linear-gradient(135deg, #1877f2, #0c63d4);
}

.share-btn.copy {
  background: linear-gradient(135deg, #666, #888);
}

.qrcode-container {
  text-align: center;
  padding: 12px;
}

.qrcode-title {
  font-size: 14px;
  color: #333;
  margin-bottom: 12px;
  font-weight: 500;
}

.qrcode-image {
  width: 200px;
  height: 200px;
  border-radius: 8px;
}

/* 移动端适配 */
@media (max-width: 768px) {
  .share-buttons {
    flex-wrap: wrap;
  }

  .share-btn {
    width: 32px;
    height: 32px;
  }

  .qrcode-image {
    width: 160px;
    height: 160px;
  }
}
</style>
