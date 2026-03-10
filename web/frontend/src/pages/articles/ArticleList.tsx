import React, { useEffect, useState } from 'react';
import { Table, Tag, Space, Button, Typography, message, Popconfirm, Segmented } from 'antd';
import { EyeOutlined, DeleteOutlined, CalendarOutlined, UnorderedListOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { contentApi } from '../../api/articles';
import type { ArticleSummary } from '../../types/api';

const ArticleList: React.FC = () => {
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  useEffect(() => { loadArticles(); }, [page]);

  const loadArticles = async () => {
    setLoading(true);
    try {
      const res = await contentApi.listArticles(page, 20);
      setArticles(res.data.data.items);
      setTotal(res.data.data.total);
    } catch {
      message.error('加载文章列表失败');
    }
    setLoading(false);
  };

  const handleDelete = async (date: string) => {
    try {
      await contentApi.deleteArticle(date);
      message.success('删除成功');
      loadArticles();
    } catch {
      message.error('删除失败');
    }
  };

  const columns = [
    {
      title: '日期', dataIndex: 'date_formatted', key: 'date', width: 120,
      render: (text: string, record: ArticleSummary) => (
        <a onClick={() => navigate(`/articles/${record.date}`)}>{text}</a>
      ),
    },
    {
      title: '标题', dataIndex: 'article_title', key: 'title', ellipsis: true,
      render: (text: string, record: ArticleSummary) => text || <Typography.Text type="secondary">未生成</Typography.Text>,
    },
    {
      title: '采集', dataIndex: 'raw_data_count', key: 'raw', width: 70, align: 'center' as const,
    },
    {
      title: '筛选', dataIndex: 'selected_count', key: 'selected', width: 70, align: 'center' as const,
    },
    {
      title: '图片', dataIndex: 'images_count', key: 'images', width: 70, align: 'center' as const,
    },
    {
      title: '状态', key: 'status', width: 100,
      render: (_: unknown, record: ArticleSummary) => {
        const s = record.task_status;
        if (s === 'success') return <Tag color="success">成功</Tag>;
        if (s === 'failed') return <Tag color="error">失败</Tag>;
        if (!record.has_article) return <Tag>无文章</Tag>;
        return <Tag color="default">{s || '未知'}</Tag>;
      },
    },
    {
      title: '深度分析', key: 'deep', width: 90, align: 'center' as const,
      render: (_: unknown, record: ArticleSummary) =>
        record.has_deep_analysis ? <Tag color="purple">有</Tag> : <Tag>无</Tag>,
    },
    {
      title: '耗时', key: 'duration', width: 80,
      render: (_: unknown, record: ArticleSummary) =>
        record.duration_seconds ? `${record.duration_seconds.toFixed(0)}s` : '-',
    },
    {
      title: '操作', key: 'action', width: 120,
      render: (_: unknown, record: ArticleSummary) => (
        <Space>
          <Button type="link" size="small" icon={<EyeOutlined />}
            onClick={() => navigate(`/articles/${record.date}`)}>
            查看
          </Button>
          <Popconfirm title="确定删除该日所有数据？" onConfirm={() => handleDelete(record.date)}>
            <Button type="link" size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Typography.Title level={4} style={{ margin: 0 }}>每日文章</Typography.Title>
      </div>
      <Table
        columns={columns}
        dataSource={articles}
        rowKey="date"
        loading={loading}
        pagination={{
          current: page, total, pageSize: 20, showTotal: (t) => `共 ${t} 条`,
          onChange: (p) => setPage(p),
        }}
        size="middle"
      />
    </div>
  );
};

export default ArticleList;
