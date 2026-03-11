import { create } from 'zustand';
import { authApi } from '../api/auth';
import type { UserInfo } from '../types/api';

interface AuthState {
  user: UserInfo | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (username: string, password: string) => Promise<boolean>;
  logout: () => Promise<void>;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  isAuthenticated: !!localStorage.getItem('access_token'),
  loading: false,

  login: async (username: string, password: string) => {
    try {
      set({ loading: true });
      const res = await authApi.login(username, password);
      const { access_token, refresh_token, user } = res.data.data;
      localStorage.setItem('access_token', access_token);
      localStorage.setItem('refresh_token', refresh_token);
      set({ user, isAuthenticated: true, loading: false });
      return true;
    } catch {
      set({ loading: false });
      return false;
    }
  },

  logout: async () => {
    try {
      await authApi.logout();
    } catch { /* ignore */ }
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    set({ user: null, isAuthenticated: false });
  },

  checkAuth: async () => {
    const token = localStorage.getItem('access_token');
    if (!token) {
      set({ isAuthenticated: false, user: null });
      return;
    }
    try {
      const res = await authApi.me();
      set({ user: res.data.data, isAuthenticated: true });
    } catch {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      set({ user: null, isAuthenticated: false });
    }
  },
}));
