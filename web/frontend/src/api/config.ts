import client from './client';
import type { ApiResponse, ConfigItem } from '../types/api';

export const configApi = {
  getAll: () =>
    client.get<ApiResponse<Record<string, ConfigItem[]>>>('/config'),

  getCategory: (category: string) =>
    client.get<ApiResponse<ConfigItem[]>>(`/config/${category}`),

  updateCategory: (category: string, updates: Record<string, string>) =>
    client.put<ApiResponse<null>>(`/config/${category}`, updates),

  testLlm: () => client.post<ApiResponse<{ response: string }>>('/config/test/llm'),
  testWechat: () => client.post<ApiResponse<{ has_token: boolean }>>('/config/test/wechat'),
  testImage: () => client.post<ApiResponse<{ provider: string }>>('/config/test/image'),
};
