import React, { useEffect, useState } from 'react';
import { Table, Tag, Typography, message } from 'antd';
import { publishApi } from '../../api/publish';
import type { PublicationRecord } from '../../types/api';

const statusLabels: Record<string, { text: string; color: string }> = {
  draft_created: { text: '草稿已创建', color: 'blue' },
  published: { text: '已发布', color: 'green' },
  deleted: { text: '已删除', color: 'default' },
};

const PublishHistory: React.FC = () => {
  const [records, setRecords] = useState<PublicationRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);

  useEffect(() => { load(); }, [page]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await publishApi.listRecords(page, 20);
      setRecords(res.data.data.items);
      setTotal(res.data.data.total);
    } catch {
      message.error('加载发布记录失败');
    }
    setLoading(false);
  };

  const columns = [
    { title: 'ID', dataIndex: 'id', key: 'id', width: 60 },
    { title: '日期', dataIndex: 'article_date', key: 'date', width: 80 },
    {
      title: '类型', dataIndex: 'article_type', key: 'type', width: 100,
      render: (t: string) => <Tag>{t === 'deep_analysis' ? '深度分析' : '每日热点'}</Tag>,
    },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: 'Media ID', dataIndex: 'media_id', key: 'media', ellipsis: true, width: 180 },
    {
      title: '状态', dataIndex: 'status', key: 'status', width: 110,
      render: (s: string) => {
        const info = statusLabels[s] || { text: s, color: 'default' };
        return <Tag color={info.color}>{info.text}</Tag>;
      },
    },
    { title: '操作者', dataIndex: 'published_by_name', key: 'publisher', width: 80 },
    {
      title: '时间', dataIndex: 'created_at', key: 'created', width: 170,
      render: (t: string | null) => t ? new Date(t).toLocaleString('zh-CN') : '-',
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>发布历史</Typography.Title>
      <Table columns={columns} dataSource={records} rowKey="id" loading={loading} size="middle"
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => setPage(p), showTotal: (t) => `共 ${t} 条` }} />
    </div>
  );
};

export default PublishHistory;
