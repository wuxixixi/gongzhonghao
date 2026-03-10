export interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

export interface PaginatedData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface UserInfo {
  id: number;
  username: string;
  role: 'admin' | 'editor';
  is_active: boolean;
  created_at: string | null;
  last_login_at: string | null;
}

export interface LoginResponse {
  access_token: string;
  refresh_token: string;
  user: UserInfo;
}

export interface ArticleSummary {
  date: string;
  date_formatted: string;
  has_article: boolean;
  has_deep_analysis: boolean;
  article_title: string;
  images_count: number;
  raw_data_count: number;
  selected_count: number;
  task_status: string | null;
  duration_seconds: number | null;
}

export interface ArticleDetail extends ArticleSummary {
  content_markdown: string;
  content_html: string;
  images: string[];
}

export interface DeepAnalysisItem {
  date: string;
  date_formatted: string;
  title: string;
  images_count: number;
  status: string | null;
}

export interface DeepAnalysisDetail {
  date: string;
  title: string;
  content_markdown: string;
  content_html?: string;
  images: string[];
  report?: RunReport;
}

export interface RawDataItem {
  source: string;
  title: string;
  summary: string;
  url: string;
  published_at: string;
  tags: string[];
  extra: Record<string, unknown>;
}

export interface SelectedDataItem {
  title: string;
  source: string;
  score: number;
  reason: string;
  category: string;
  url: string;
}

export interface RunReport {
  status: string;
  collected_count: number;
  selected_count: number;
  article_title: string;
  images_generated: number;
  draft_created: boolean;
  errors: string[];
  duration_seconds: number;
  from_cache: boolean;
  generated_at: string;
}

export interface ConfigItem {
  id: number;
  category: string;
  key: string;
  value: string;
  value_type: string;
  is_secret: boolean;
  description: string;
  updated_at: string | null;
}

export interface SystemStatus {
  system: {
    python_version: string;
    platform: string;
    project_root: string;
  };
  services: {
    wechat: {
      status: string;
      has_valid_token: boolean;
      token_expires_in?: number;
    };
  };
  storage: {
    total_days: number;
    total_size_mb: number;
  };
  today: {
    date: string;
    has_article: boolean;
    has_deep_analysis: boolean;
  };
}

export interface TaskHistory {
  id: number;
  task_type: string;
  status: string;
  triggered_by: number | null;
  triggered_by_name: string;
  started_at: string | null;
  finished_at: string | null;
  duration_seconds: number | null;
  report: RunReport | null;
  error_message: string | null;
  article_date: string | null;
  created_at: string | null;
}

export interface LogFile {
  name: string;
  date: string;
  size_kb: number;
}

export interface LogContent {
  lines: Array<{ raw?: string; [key: string]: unknown }>;
  total: number;
  offset: number;
}

export interface PublicationRecord {
  id: number;
  article_date: string;
  article_type: string;
  title: string;
  media_id: string;
  status: string;
  published_by: number | null;
  published_by_name: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface TokenStatus {
  status: string;
  has_valid_token: boolean;
  expires_in_seconds?: number;
}
