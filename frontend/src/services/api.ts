import axios from 'axios';
import type { AnalyzeRequest, SearchResult, LoginRequest, LoginResponse, MarketOverviewItem } from '@/types';
import type { JournalListResponse } from '@/types/journal';
import type { Watchlist, WatchlistSummary } from '@/types/watchlist';

const API_PREFIX = '/api';

const axiosInstance = axios.create({
  baseURL: API_PREFIX
});

// ---------------------------------------------------------------------------
// Legacy token migration: move old aguai_anchor_token → token
// Runs once on module load so existing users keep their identity.
// ---------------------------------------------------------------------------
(function migrateOldAnchorToken() {
  const oldAnchor = localStorage.getItem('aguai_anchor_token');
  if (oldAnchor && !localStorage.getItem('token')) {
    localStorage.setItem('token', oldAnchor);
    localStorage.removeItem('aguai_anchor_token');
    console.log('[Auth] Migrated legacy anchor token → unified token');
  } else if (oldAnchor) {
    localStorage.removeItem('aguai_anchor_token');
    console.log('[Auth] Cleared stale anchor token (unified token already present)');
  }
})();

// ---------------------------------------------------------------------------
// Request interceptor — single Authorization header + anonymous ID
// ---------------------------------------------------------------------------
axiosInstance.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    const anonymousId = localStorage.getItem('aguai_anonymous_id');
    if (anonymousId) {
      config.headers['X-Anonymous-Id'] = anonymousId;
    }

    return config;
  },
  (error) => Promise.reject(error),
);

// ---------------------------------------------------------------------------
// Response interceptor — clear token on 401
// ---------------------------------------------------------------------------
axiosInstance.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      localStorage.removeItem('token');
    }
    return Promise.reject(error);
  },
);

export const apiService = {
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

  checkAuth: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/check_auth');
      return response.data.authenticated === true;
    } catch (error) {
      localStorage.removeItem('token');
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('token');
    window.location.href = '/login';
  },

  analyzeStocks: async (request: AnalyzeRequest) => {
    return axiosInstance.post('/analyze', request, {
      responseType: 'stream'
    });
  },

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

  getMarketOverview: async (): Promise<{ items: MarketOverviewItem[]; updated_at: number | null }> => {
    try {
      const response = await axiosInstance.get('/market-overview');
      return {
        items: response.data.items || [],
        updated_at: response.data.updated_at ?? null,
      };
    } catch (error) {
      console.error('获取首页指数概览时出错:', error);
      return {
        items: [],
        updated_at: null,
      };
    }
  },

  checkNeedLogin: async (): Promise<boolean> => {
    try {
      const response = await axiosInstance.get('/need_login');
      return response.data.require_login;
    } catch (error) {
      console.error('检查是否需要登录时出错:', error);
      return true;
    }
  },

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

  getArticleDetail: async (articleId: number) => {
    try {
      const response = await axiosInstance.get(`/articles/${articleId}`);
      return response.data;
    } catch (error) {
      console.error('获取文章详情时出错:', error);
      return null;
    }
  },

  // ========== Judgment API ==========

  saveJudgment: async (data: any) => {
    try {
      const response = await axiosInstance.post('/journal', data);
      return response.data;
    } catch (error) {
      console.error('保存判断时出错:', error);
      throw error;
    }
  },

  getMyJudgments: async (limit: number = 50) => {
    try {
      const response = await axiosInstance.get('/v1/me/judgments', {
        params: { limit }
      });
      return response.data;
    } catch (error) {
      console.error('获取判断列表时出错:', error);
      return { user_id: '', total: 0, judgments: [] };
    }
  },

  getJudgmentDetail: async (judgmentId: string) => {
    try {
      const response = await axiosInstance.get(`/v1/judgments/${judgmentId}`);
      return response.data;
    } catch (error) {
      console.error('获取判断详情时出错:', error);
      return null;
    }
  },

  getDueCount: async (): Promise<number> => {
    try {
      const response = await axiosInstance.get('/journal/due-count');
      return response.data.due_count || 0;
    } catch (error) {
      console.error('获取待复盘数量时出错:', error);
      return 0;
    }
  },

  getJournalRecords: async (params: { status?: string, ts_code?: string, page?: number } = {}): Promise<JournalListResponse> => {
    try {
      const response = await axiosInstance.get('/journal', { params });
      return response.data;
    } catch (error) {
      console.error('获取日记列表时出错:', error);
      throw error;
    }
  },

  reviewRecord: async (recordId: string, notes: string | null) => {
    try {
      const response = await axiosInstance.post(`/journal/${recordId}/review`, { notes });
      return response.data;
    } catch (error) {
      console.error('复盘保存时出错:', error);
      throw error;
    }
  },

  deleteJournalRecord: async (recordId: string) => {
    try {
      const response = await axiosInstance.delete(`/journal/${recordId}`);
      return response.data;
    } catch (error) {
      console.error('删除判断记录时出错:', error);
      throw error;
    }
  },

  deleteJudgment: async (judgmentId: string): Promise<void> => {
    const response = await axiosInstance.delete(`/v1/judgments/${judgmentId}`);
    return response.data;
  },

  // ========== Watchlist API ==========

  getWatchlists: async (): Promise<Watchlist[]> => {
    try {
      const response = await axiosInstance.get('/watchlists');
      return response.data || [];
    } catch (error) {
      console.error('获取观察列表时出错:', error);
      return [];
    }
  },

  createWatchlist: async (name: string): Promise<Watchlist> => {
    const response = await axiosInstance.post('/watchlists', { name });
    return response.data;
  },

  getWatchlistSummary: async (
    watchlistId: string,
    params: { sort?: string; filters?: string[] } = {}
  ): Promise<WatchlistSummary> => {
    const response = await axiosInstance.get(`/watchlists/${watchlistId}/summary`, {
      params: {
        sort: params.sort,
        filters: params.filters?.join(',') || undefined
      }
    });
    return response.data;
  },

  getUserCenterOverview: async () => {
    const response = await axiosInstance.get('/user-center/overview');
    return response.data;
  },

  addWatchlistSymbols: async (watchlistId: string, tsCodes: string[]) => {
    const response = await axiosInstance.post(`/watchlists/${watchlistId}/symbols`, {
      ts_codes: tsCodes
    });
    return response.data;
  },

  removeWatchlistSymbol: async (watchlistId: string, tsCode: string) => {
    const response = await axiosInstance.delete(`/watchlists/${watchlistId}/symbols/${tsCode}`);
    return response.data;
  },

  // ========== Quota API ==========

  getQuotaStatus: async () => {
    try {
      const response = await axiosInstance.get('/v1/quota/status');
      return response.data;
    } catch (error) {
      console.error('获取额度状态时出错:', error);
      return null;
    }
  },

  checkQuota: async (stockCode: string) => {
    try {
      const response = await axiosInstance.post('/v1/quota/check', {
        stock_code: stockCode
      });
      return response.data;
    } catch (error) {
      console.error('检查额度时出错:', error);
      throw error;
    }
  },

  // ========== Invite API ==========

  generateInviteCode: async () => {
    try {
      const response = await axiosInstance.post('/v1/invite/generate');
      return response.data;
    } catch (error) {
      console.error('生成邀请码时出错:', error);
      throw error;
    }
  },

  acceptInvite: async (code: string) => {
    try {
      const response = await axiosInstance.get('/v1/invite/accept', {
        params: { code }
      });
      return response.data;
    } catch (error) {
      console.error('接受邀请时出错:', error);
      throw error;
    }
  },

  // ========== Anchor API (Email Binding) ==========

  sendVerificationCode: async (email: string) => {
    try {
      const response = await axiosInstance.post('/anchor/send_code', {
        email
      });
      return response.data;
    } catch (error: any) {
      console.error('发送验证码时出错:', error);
      throw error;
    }
  },

  verifyAndBind: async (email: string, code: string) => {
    try {
      const response = await axiosInstance.post('/anchor/verify_and_bind', {
        email,
        code
      });
      return response.data;
    } catch (error: any) {
      console.error('验证绑定时出错:', error);
      throw error;
    }
  },

  getAnchorStatus: async () => {
    try {
      const response = await axiosInstance.get('/anchor/status');
      return response.data;
    } catch (error) {
      console.error('获取anchor状态时出错:', error);
      return { mode: 'anonymous' };
    }
  }
};
