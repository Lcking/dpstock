import axios from 'axios';

const adminAxios = axios.create({
  baseURL: '/api/admin',
});

adminAxios.interceptors.request.use((config) => {
  const t = localStorage.getItem('admin_token');
  if (t) {
    config.headers.Authorization = `Bearer ${t}`;
  }
  return config;
});

adminAxios.interceptors.response.use(
  (r) => r,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('admin_token');
    }
    return Promise.reject(err);
  }
);

export const adminApi = {
  login: (username: string, password: string) =>
    adminAxios.post('/login', { username, password }),

  me: () => adminAxios.get('/me'),

  getSettings: () => adminAxios.get('/settings'),
  patchSettings: (body: Record<string, string>) => adminAxios.patch('/settings', body),

  listArticles: (params?: { limit?: number; offset?: number; q?: string }) =>
    adminAxios.get('/articles', { params }),
  getArticle: (id: number) => adminAxios.get(`/articles/${id}`),
  patchArticle: (id: number, body: Record<string, unknown>) =>
    adminAxios.patch(`/articles/${id}`, body),
  deleteArticle: (id: number) => adminAxios.delete(`/articles/${id}`),

  listUsers: (params?: { limit?: number; offset?: number; q?: string; email_verified?: number }) =>
    adminAxios.get('/users', { params }),
  patchUser: (userId: string, status: 'active' | 'disabled') =>
    adminAxios.patch(`/users/${userId}`, { status }),

  inviteSummary: () => adminAxios.get('/invites/summary'),
  inviteRewards: (params?: { limit?: number; offset?: number }) =>
    adminAxios.get('/invites/rewards', { params }),

  listNavLinks: () => adminAxios.get('/nav-links'),
  createNavLink: (body: {
    label: string;
    href: string;
    target?: string;
    rel?: string;
    sort_order?: number;
    enabled?: number;
  }) => adminAxios.post('/nav-links', body),
  patchNavLink: (id: number, body: Record<string, unknown>) =>
    adminAxios.patch(`/nav-links/${id}`, body),
  deleteNavLink: (id: number) => adminAxios.delete(`/nav-links/${id}`),
};
