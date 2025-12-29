import { createRouter, createWebHistory } from 'vue-router';
import type { RouteRecordRaw } from 'vue-router';
import { apiService } from '@/services/api';
import StockAnalysisApp from '@/components/StockAnalysisApp.vue';
import LoginPage from '@/components/LoginPage.vue';
import AnalysisList from '@/components/AnalysisList.vue';
import ArticleDetail from '@/components/ArticleDetail.vue';

const routes: Array<RouteRecordRaw> = [
  {
    path: '/',
    name: 'Home',
    component: StockAnalysisApp,
    meta: { requiresAuth: true }
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginPage,
    meta: { requiresAuth: false }
  },
  {
    path: '/analysis',
    name: 'AnalysisList',
    component: AnalysisList,
    meta: { requiresAuth: true }
  },
  {
    path: '/analysis/:id',
    name: 'ArticleDetail',
    component: ArticleDetail,
    meta: { requiresAuth: true }
  },
  {
    path: '/my-judgments',
    name: 'MyJudgments',
    component: () => import('@/components/MyJudgments.vue'),
    meta: { requiresAuth: false }  // Anonymous via cookie
  },
  {
    path: '/help/judgment-verification',
    name: 'JudgmentHelp',
    component: () => import('@/components/JudgmentHelp.vue'),
    meta: {
      requiresAuth: false,
      title: '判断验证功能说明 - Agu AI 智能股票分析',
      description: '了解如何使用判断追踪功能，提升投资分析能力。详细说明验证状态、价格变化和验证原因等字段含义。'
    }
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/'
  }
];

const router = createRouter({
  history: createWebHistory(),
  routes
});

// 全局前置守卫
router.beforeEach(async (to, from, next) => {
  console.log(`路由跳转: 从 ${from.path} 到 ${to.path}`);

  // 如果已经在登录页面，直接通过
  if (to.path === '/login') {
    next();
    return;
  }

  // 检查路由是否需要认证
  if (to.matched.some(record => record.meta.requiresAuth)) {
    console.log('当前路由需要认证');

    try {
      // 先检查系统是否需要登录
      const requireLogin = await apiService.checkNeedLogin();
      console.log('系统是否需要登录:', requireLogin);

      if (!requireLogin) {
        // 系统不需要登录，直接通过
        console.log('系统不需要登录，允许访问');
        next();
        return;
      }

      // 系统需要登录，检查本地是否有token
      const token = localStorage.getItem('token');
      if (!token) {
        console.log('本地没有token，跳转到登录页');
        next({ name: 'Login' });
        return;
      }

      const isAuthenticated = await apiService.checkAuth();
      console.log('认证检查结果:', isAuthenticated);

      if (!isAuthenticated) {
        // 未登录，重定向到登录页
        console.log('认证失败，跳转到登录页');
        next({ name: 'Login' });
      } else {
        // 已登录，允许访问
        console.log('认证成功，允许访问');
        next();
      }
    } catch (error) {
      console.error('认证检查失败:', error);
      // 网络错误时不跳转登录，采用乐观策略允许访问
      // 只有明确的认证失败才跳转登录页
      const isNetworkError = error instanceof TypeError ||
        (error as any)?.code === 'ERR_NETWORK' ||
        (error as any)?.message?.includes('Network');
      if (isNetworkError) {
        console.log('网络错误，允许访问');
        next();
      } else {
        next({ name: 'Login' });
      }
    }
  } else {
    // 不需要认证的路由，直接访问
    console.log('当前路由不需要认证，直接访问');
    next();
  }
});

export default router; 