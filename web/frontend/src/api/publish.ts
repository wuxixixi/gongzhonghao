import client from './client';
import type { ApiResponse, PaginatedData, PublicationRecord, TokenStatus } from '../types/api';

export const publishApi = {
  createDraft: (date: string, articleType = 'daily_hot') =>
    client.post<ApiResponse<{ media_id: string; title: string; record_id: number }>>(
      `/publish/draft/${date}`, { article_type: articleType }
    ),

  listRecords: (page = 1, pageSize = 20) =>
    client.get<ApiResponse<PaginatedData<PublicationRecord>>>('/publish/records', {
      params: { page, page_size: pageSize },
    }),

  getTokenStatus: () =>
    client.get<ApiResponse<TokenStatus>>('/publish/wechat/token-status'),

  refreshToken: () =>
    client.post<ApiResponse<{ success: boolean }>>('/publish/wechat/refresh-token'),
};
