import client from './client';
import type {
  ApiResponse, PaginatedData, SystemStatus, TaskHistory, LogFile, LogContent,
} from '../types/api';

export const monitorApi = {
  getStatus: () =>
    client.get<ApiResponse<SystemStatus>>('/monitor/status'),

  listTasks: (page = 1, pageSize = 20, filters?: { task_type?: string; status?: string }) =>
    client.get<ApiResponse<PaginatedData<TaskHistory>>>('/monitor/tasks', {
      params: { page, page_size: pageSize, ...filters },
    }),

  getTask: (id: number) =>
    client.get<ApiResponse<TaskHistory>>(`/monitor/tasks/${id}`),

  getRunningTasks: () =>
    client.get<ApiResponse<TaskHistory[]>>('/monitor/tasks/running'),

  listLogFiles: () =>
    client.get<ApiResponse<LogFile[]>>('/monitor/logs'),

  getLogContent: (date: string, params?: { level?: string; keyword?: string; offset?: number; limit?: number }) =>
    client.get<ApiResponse<LogContent>>(`/monitor/logs/${date}`, { params }),
};
