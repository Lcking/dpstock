<template>
  <div class="admin-login">
    <n-card title="管理后台登录" class="card">
      <n-form @submit.prevent="handleLogin">
        <n-form-item label="用户名">
          <n-input v-model:value="username" placeholder="ADMIN_USERNAME" autocomplete="username" />
        </n-form-item>
        <n-form-item label="密码">
          <n-input
            v-model:value="password"
            type="password"
            placeholder="密码"
            autocomplete="current-password"
            show-password-on="click"
            @keyup.enter="handleLogin"
          />
        </n-form-item>
        <n-button type="primary" block :loading="loading" @click="handleLogin">登录</n-button>
      </n-form>
    </n-card>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { useRouter, useRoute } from 'vue-router';
import { NCard, NForm, NFormItem, NInput, NButton, useMessage } from 'naive-ui';
import { adminApi } from '@/services/adminApi';

const router = useRouter();
const route = useRoute();
const message = useMessage();
const username = ref('');
const password = ref('');
const loading = ref(false);

async function handleLogin() {
  loading.value = true;
  try {
    const { data } = await adminApi.login(username.value.trim(), password.value);
    if (data.access_token) {
      localStorage.setItem('admin_token', data.access_token);
      message.success('登录成功');
      const redirect = (route.query.redirect as string) || '/admin';
      await router.replace(redirect);
    }
  } catch (e: any) {
    const detail = e.response?.data?.detail;
    message.error(typeof detail === 'string' ? detail : '登录失败');
  } finally {
    loading.value = false;
  }
}
</script>

<style scoped>
.admin-login {
  min-height: 60vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}
.card {
  width: 100%;
  max-width: 400px;
}
</style>
