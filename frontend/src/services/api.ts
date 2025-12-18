import axios from 'axios';
import type { AnalyzeRequest, SearchResult, LoginRequest, LoginResponse } from '@/types';

// API前缀
const API_PREFIX = '/api';

// 创建axios实例
const axiosInstance = axios.create({
  baseURL: API_PREFIX
});

// 请求拦截器，添加token
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器，处理401错误
axiosInstance.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    if (error.response && error.response.status === 401) {
      // 清除token
      localStorage.removeItem('token');
      // 不要在这里跳转，避免循环重定向
    }
    return Promise.reject(error);
  }
);

export const apiService = {
  // 用户登录
  login: async (request: LoginRequest): Promise<LoginResponse> => {
    try {
      const response = await axiosInstance.post('/login', request);
      if (response.data.access_token) {
        localStorage.setItem('token', response.data.access_token);
      }
      return response.data;
    } catch (error: any) {
      if (error.response) {
        return {
          success: false,
          message: error.response.data.detail || '登录失败',
        };
      }
      return {
        success: false,
        message: error.message || '登录失败'
      };
    }
  },

  // 全局搜索
  searchGlobal: async (keyword: string, marketType: string = 'ALL'): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_global', {
        params: { keyword, market_type: marketType }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('全局搜索时出错:', error);
      return [];
    }
  },

  // 检查认证状态
  checkAuth: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/check_auth');
      return response.data.authenticated === true;
    } catch (error) {
      // 认证失败，清除token
      localStorage.removeItem('token');
      return false;
    }
  },

  // 登出
  logout: () => {
    localStorage.removeItem('token');
    // 简化登出逻辑
    window.location.href = '/login';
  },

  // 分析股票
  analyzeStocks: async (request: AnalyzeRequest) => {
    return axiosInstance.post('/analyze', request, {
      responseType: 'stream'
    });
  },

  // 搜索美股
  searchUsStocks: async (keyword: string): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_us_stocks', {
        params: { keyword }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索美股时出错:', error);
      return [];
    }
  },

  // 搜索 A 股
  searchAShares: async (keyword: string): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_a_shares', {
        params: { keyword }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索 A 股时出错:', error);
      return [];
    }
  },

  // 搜索港股
  searchHKShares: async (keyword: string): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_hk_shares', {
        params: { keyword }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索港股时出错:', error);
      return [];
    }
  },

  // 搜索基金
  searchFunds: async (keyword: string, marketType: string = 'ETF'): Promise<SearchResult[]> => {
    try {
      const response = await axiosInstance.get('/search_funds', {
        params: { keyword, market_type: marketType }
      });
      return response.data.results || [];
    } catch (error) {
      console.error('搜索基金时出错:', error);
      return [];
    }
  },

  // 获取公告配置
  getConfig: async () => {
    try {
      const response = await axiosInstance.get('/config');
      return response.data;
    } catch (error) {
      console.error('获取配置时出错:', error);
      return {
        announcement: ''
      };
    }
  },

  // 检查是否需要登录
  checkNeedLogin: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/need_login');
      return response.data.require_login;
    } catch (error) {
      console.error('检查是否需要登录时出错:', error);
      // 默认为需要登录，确保安全
      return true;
    }
  },

  // 获取K线数据
  getKlineData: async (code: string, marketType: string = 'A', days: number = 100) => {
    try {
      const response = await axiosInstance.get(`/kline/${code}`, {
        params: { market_type: marketType, days }
      });
      return response.data;
    } catch (error) {
      console.error('获取K线数据时出错:', error);
      return { error: '获取K线数据失败' };
    }
  },

  // 获取文章列表
  getArticles: async (limit: number = 20, offset: number = 0, q?: string) => {
    try {
      const response = await axiosInstance.get('/articles', {
        params: { limit, offset, q }
      });
      return response.data.articles || [];
    } catch (error) {
      console.error('获取文章列表时出错:', error);
      return [];
    }
  },

  // 获取文章详情
  getArticleDetail: async (articleId: number) => {
    try {
      const response = await axiosInstance.get(`/articles/${articleId}`);
      return response.data;
    } catch (error) {
      console.error('获取文章详情时出错:', error);
      return null;
    }
  }
};
