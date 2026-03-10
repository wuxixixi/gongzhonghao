import React, { useEffect, useState } from 'react';
import { Table, Tag, Typography, Select, Space, message } from 'antd';
import { monitorApi } from '../../api/monitor';
import type { TaskHistory as TaskHistoryType } from '../../types/api';

const statusColors: Record<string, string> = {
  success: 'green',
  failed: 'red',
  running: 'blue',
  pending: 'orange',
};

const typeLabels: Record<string, string> = {
  daily_hot: '每日热点',
  deep_analysis: '深度分析',
};

const TaskHistory: React.FC = () => {
  const [tasks, setTasks] = useState<TaskHistoryType[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState<string | undefined>(undefined);
  const [statusFilter, setStatusFilter] = useState<string | undefined>(undefined);

  useEffect(() => { load(); }, [page, typeFilter, statusFilter]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await monitorApi.listTasks(page, 20, {
        task_type: typeFilter,
        status: statusFilter,
      });
      setTasks(res.data.data.items);
      setTotal(res.data.data.total);
    } catch {
      message.error('加载失败');
    }
    setLoading(false);
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    {
      title: '类型', dataIndex: 'task_type', key: 'type', width: 100,
      render: (t: string) => <Tag>{typeLabels[t] || t}</Tag>,
    },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 80,
      render: (s: string) => <Tag color={statusColors[s]}>{s}</Tag>,
    },
    { title: '触发者', dataIndex: 'triggered_by_name', key: 'trigger', width: 80 },
    { title: '关联日期', dataIndex: 'article_date', key: 'date', width: 80 },
    {
      title: '开始时间', dataIndex: 'started_at', key: 'started', width: 170,
      render: (t: string | null) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
    {
      title: '耗时', dataIndex: 'duration_seconds', key: 'duration', width: 80,
      render: (d: number | null) => d ? `${d.toFixed(1)}s` : '-',
    },
    {
      title: '错误', dataIndex: 'error_message', key: 'error', ellipsis: true,
      render: (e: string | null) => e ? <Typography.Text type="danger" ellipsis>{e}</Typography.Text> : '-',
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>任务历史</Typography.Title>
        <Space>
          <Select style={{ width: 120 }} placeholder="任务类型" allowClear value={typeFilter} onChange={setTypeFilter}
            options={[{ value: 'daily_hot', label: '每日热点' }, { value: 'deep_analysis', label: '深度分析' }]} />
          <Select style={{ width: 100 }} placeholder="状态" allowClear value={statusFilter} onChange={setStatusFilter}
            options={[{ value: 'success', label: '成功' }, { value: 'failed', label: '失败' }, { value: 'running', label: '运行中' }, { value: 'pending', label: '等待中' }]} />
        </Space>
      </div>
      <Table columns={columns} dataSource={tasks} rowKey="id" loading={loading} size="middle"
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => setPage(p), showTotal: (t) => `共 ${t} 条` }} />
    </div>
  );
};

export default TaskHistory;
