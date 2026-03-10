import client from './client';
import type {
  ApiResponse, PaginatedData, ArticleSummary, ArticleDetail,
  RawDataItem, SelectedDataItem, RunReport, DeepAnalysisItem, DeepAnalysisDetail,
} from '../types/api';

export const contentApi = {
  listArticles: (page = 1, pageSize = 20) =>
    client.get<ApiResponse<PaginatedData<ArticleSummary>>>('/content/articles', {
      params: { page, page_size: pageSize },
    }),

  getArticle: (date: string) =>
    client.get<ApiResponse<ArticleDetail>>(`/content/articles/${date}`),

  updateArticle: (date: string, contentMarkdown: string) =>
    client.put<ApiResponse<null>>(`/content/articles/${date}`, { content_markdown: contentMarkdown }),

  deleteArticle: (date: string) =>
    client.delete<ApiResponse<null>>(`/content/articles/${date}`),

  getImageUrl: (date: string, filename: string) =>
    `/api/content/articles/${date}/images/${filename}`,

  getRawData: (date: string) =>
    client.get<ApiResponse<RawDataItem[]>>(`/content/articles/${date}/raw-data`),

  getSelectedData: (date: string) =>
    client.get<ApiResponse<SelectedDataItem[]>>(`/content/articles/${date}/selected-data`),

  getReport: (date: string) =>
    client.get<ApiResponse<RunReport>>(`/content/articles/${date}/report`),

  generateDaily: (skipPublish = false, force = false) =>
    client.post<ApiResponse<{ task_id: number; status: string }>>('/content/generate/daily', {
      skip_publish: skipPublish, force,
    }),

  generateDeepAnalysis: (skipPublish = false) =>
    client.post<ApiResponse<{ task_id: number; status: string }>>('/content/generate/deep-analysis', {
      skip_publish: skipPublish,
    }),

  listDeepAnalysis: (page = 1, pageSize = 20) =>
    client.get<ApiResponse<PaginatedData<DeepAnalysisItem>>>('/content/deep-analysis', {
      params: { page, page_size: pageSize },
    }),

  getDeepAnalysis: (date: string) =>
    client.get<ApiResponse<DeepAnalysisDetail>>(`/content/deep-analysis/${date}`),

  getDeepImageUrl: (date: string, filename: string) =>
    `/api/content/deep-analysis/${date}/images/${filename}`,
};
