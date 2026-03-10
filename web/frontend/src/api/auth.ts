import client from './client';
import type { ApiResponse, LoginResponse, UserInfo } from '../types/api';

export const authApi = {
  login: (username: string, password: string) =>
    client.post<ApiResponse<LoginResponse>>('/auth/login', { username, password }),

  logout: () => client.post<ApiResponse<null>>('/auth/logout'),

  refresh: () => client.post<ApiResponse<{ access_token: string }>>('/auth/refresh'),

  me: () => client.get<ApiResponse<UserInfo>>('/auth/me'),

  listUsers: () => client.get<ApiResponse<UserInfo[]>>('/auth/users'),

  createUser: (data: { username: string; password: string; role: string }) =>
    client.post<ApiResponse<UserInfo>>('/auth/users', data),

  updateUser: (id: number, data: Partial<{ role: string; is_active: boolean; password: string }>) =>
    client.put<ApiResponse<UserInfo>>(`/auth/users/${id}`, data),

  deleteUser: (id: number) => client.delete<ApiResponse<null>>(`/auth/users/${id}`),
};
