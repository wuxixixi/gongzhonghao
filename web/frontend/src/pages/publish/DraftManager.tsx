import React, { useEffect, useState } from 'react';
import { Table, Tag, Button, Typography, Space, message, Popconfirm } from 'antd';
import { CloudUploadOutlined } from '@ant-design/icons';
import { publishApi } from '../../api/publish';
import { contentApi } from '../../api/articles';
import type { ArticleSummary } from '../../types/api';

const DraftManager: React.FC = () => {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState<string | null>(null);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const res = await contentApi.listArticles(1, 50);
      setArticles(res.data.data.items.filter((a) => a.has_article));
    } catch {
      message.error('加载失败');
    }
    setLoading(false);
  };

  const handlePublish = async (date: string, type: string) => {
    setPublishing(date + type);
    try {
      await publishApi.createDraft(date, type);
      message.success('草稿创建成功');
    } catch (e: any) {
      message.error(e.response?.data?.message || '发布失败');
    }
    setPublishing(null);
  };

  const columns = [
    { title: '日期', dataIndex: 'date_formatted', key: 'date', width: 120 },
    { title: '标题', dataIndex: 'article_title', key: 'title', ellipsis: true },
    {
      title: '状态', key: 'status', width: 80,
      render: (_: unknown, r: ArticleSummary) => {
        if (r.task_status === 'success') return <Tag color="green">成功</Tag>;
        return <Tag>{r.task_status || '-'}</Tag>;
      },
    },
    {
      title: '深度分析', key: 'deep', width: 90,
      render: (_: unknown, r: ArticleSummary) => r.has_deep_analysis ? <Tag color="purple">有</Tag> : <Tag>无</Tag>,
    },
    {
      title: '操作', key: 'action', width: 240,
      render: (_: unknown, r: ArticleSummary) => (
        <Space>
          <Popconfirm title="确定创建每日热点草稿？" onConfirm={() => handlePublish(r.date, 'daily_hot')}>
            <Button size="small" type="primary" icon={<CloudUploadOutlined />}
              loading={publishing === r.date + 'daily_hot'}>
              发布热点
            </Button>
          </Popconfirm>
          {r.has_deep_analysis && (
            <Popconfirm title="确定创建深度分析草稿？" onConfirm={() => handlePublish(r.date, 'deep_analysis')}>
              <Button size="small" icon={<CloudUploadOutlined />}
                loading={publishing === r.date + 'deep_analysis'}>
                发布分析
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>草稿管理</Typography.Title>
      <Table columns={columns} dataSource={articles} rowKey="date" loading={loading} size="middle"
        pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }} />
    </div>
  );
};

export default DraftManager;
