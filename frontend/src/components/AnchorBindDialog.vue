<template>
  <n-modal
    v-model:show="showModal"
    preset="card"
    :title="step === 1 ? '绑定凭证,长期保存判断' : '输入验证码'"
    style="width: 90%; max-width: 480px;"
    :closable="true"
    @update:show="handleClose"
  >
    <!-- Step 1: 输入邮箱 -->
    <div v-if="step === 1" class="bind-step">
      <n-alert type="info" :bordered="false" style="margin-bottom: 16px;">
        当前判断仅保存在本设备。绑定邮箱后,可长期保存并跨设备恢复。
      </n-alert>
      
      <n-form ref="emailFormRef" :model="formData" :rules="emailRules">
        <n-form-item path="email" label="邮箱地址">
          <n-input
            v-model:value="formData.email"
            placeholder="输入邮箱"
            type="text"
            :disabled="sending"
            @keyup.enter="sendCode"
          />
        </n-form-item>
      </n-form>
      
      <n-space vertical :size="12">
        <n-button
          type="primary"
          block
          :loading="sending"
          :disabled="!formData.email || sending"
          @click="sendCode"
        >
          {{ sending ? '发送中...' : '获取验证码' }}
        </n-button>
        
        <n-button block @click="handleClose">
          继续匿名
        </n-button>
      </n-space>
    </div>
    
    <!-- Step 2: 输入验证码 -->
    <div v-if="step === 2" class="bind-step">
      <n-alert type="success" :bordered="false" style="margin-bottom: 16px;">
        验证码已发送到 <strong>{{ maskedEmail }}</strong>
        <br/>
        <n-text depth="3" style="font-size: 12px;">
          开发环境:请查看服务器日志获取验证码
        </n-text>
      </n-alert>
      
      <n-form ref="codeFormRef" :model="formData" :rules="codeRules">
        <n-form-item path="code" label="验证码">
          <n-input
            v-model:value="formData.code"
            placeholder="输入6位验证码"
            maxlength="6"
            :disabled="binding"
            @keyup.enter="verifyAndBind"
          />
        </n-form-item>
      </n-form>
      
      <n-space vertical :size="12">
        <n-button
          type="primary"
          block
          :loading="binding"
          :disabled="formData.code.length !== 6 || binding"
          @click="verifyAndBind"
        >
          {{ binding ? '验证中...' : '确认绑定' }}
        </n-button>
        
        <n-button block @click="step = 1" :disabled="binding">
          返回修改邮箱
        </n-button>
      </n-space>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import {
  NModal,
  NAlert,
  NForm,
  NFormItem,
  NInput,
  NButton,
  NSpace,
  NText,
  useMessage,
  type FormInst,
  type FormRules
} from 'naive-ui';
import { apiService } from '@/services/api';
import { saveAnchorToken, saveMaskedEmail } from '@/utils/anchorToken';

interface Props {
  show: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits(['update:show', 'bind-success']);

const message = useMessage();

// Form refs
const emailFormRef = ref<FormInst | null>(null);
const codeFormRef = ref<FormInst | null>(null);

// State
const step = ref(1); // 1=输入邮箱, 2=输入验证码
const sending = ref(false);
const binding = ref(false);

const formData = ref({
  email: '',
  code: ''
});

// Computed
const showModal = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
});

const maskedEmail = computed(() => {
  const email = formData.value.email;
  if (!email) return '';
  
  const [local, domain] = email.split('@');
  if (local.length <= 2) {
    return `${local[0]}***@${domain}`;
  }
  return `${local[0]}***${local[local.length - 1]}@${domain}`;
});

// Form rules
const emailRules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '邮箱格式不正确', trigger: 'blur' }
  ]
};

const codeRules: FormRules = {
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 6, message: '验证码为6位数字', trigger: 'blur' }
  ]
};

// Methods
async function sendCode() {
  if (!emailFormRef.value) return;
  
  try {
    await emailFormRef.value.validate();
  } catch {
    return;
  }
  
  sending.value = true;
  
  try {
    const response = await apiService.sendVerificationCode(formData.value.email);
    
    if (response.ok) {
      message.success(response.message || '验证码已发送');
      step.value = 2;
    } else {
      message.error(response.message || '发送失败');
    }
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '发送验证码失败';
    message.error(errorMsg);
  } finally {
    sending.value = false;
  }
}

async function verifyAndBind() {
  if (!codeFormRef.value) return;
  
  try {
    await codeFormRef.value.validate();
  } catch {
    return;
  }
  
  binding.value = true;
  
  try {
    const response = await apiService.verifyAndBind(
      formData.value.email,
      formData.value.code
    );
    
    // Save token and masked email
    saveAnchorToken(response.token);
    saveMaskedEmail(response.masked_email);
    
    message.success(`绑定成功!已迁移 ${response.migrated_count} 条判断`);
    
    // Emit success event
    emit('bind-success', {
      anchor_id: response.anchor_id,
      migrated_count: response.migrated_count,
      masked_email: response.masked_email
    });
    
    // Close modal
    handleClose();
    
  } catch (error: any) {
    const errorMsg = error.response?.data?.detail || '绑定失败';
    message.error(errorMsg);
  } finally {
    binding.value = false;
  }
}

function handleClose() {
  showModal.value = false;
  
  // Reset form after close
  setTimeout(() => {
    step.value = 1;
    formData.value.email = '';
    formData.value.code = '';
  }, 300);
}
</script>

<style scoped>
.bind-step {
  padding: 8px 0;
}
</style>
