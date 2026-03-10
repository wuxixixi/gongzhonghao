import React, { useEffect, useState } from 'react';
import { Table, Tag, Typography, message, Button, Space } from 'antd';
import { EyeOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { contentApi } from '../../api/articles';
import type { DeepAnalysisItem } from '../../types/api';

const DeepAnalysisList: React.FC = () => {
  const [items, setItems] = useState<DeepAnalysisItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const navigate = useNavigate();

  useEffect(() => { load(); }, [page]);

  const load = async () => {
    setLoading(true);
    try {
      const res = await contentApi.listDeepAnalysis(page, 20);
      setItems(res.data.data.items);
      setTotal(res.data.data.total);
    } catch {
      message.error('加载失败');
    }
    setLoading(false);
  };

  const columns = [
    { title: '日期', dataIndex: 'date_formatted', key: 'date', width: 120 },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '图片', dataIndex: 'images_count', key: 'images', width: 70, align: 'center' as const },
    {
      title: '状态', key: 'status', width: 100,
      render: (_: unknown, r: DeepAnalysisItem) => {
        if (r.status === 'success') return <Tag color="success">成功</Tag>;
        if (r.status === 'failed') return <Tag color="error">失败</Tag>;
        return <Tag>{r.status || '未知'}</Tag>;
      },
    },
    {
      title: '操作', key: 'action', width: 80,
      render: (_: unknown, r: DeepAnalysisItem) => (
        <Button type="link" size="small" icon={<EyeOutlined />}
          onClick={() => navigate(`/articles/${r.date}`)}>
          查看
        </Button>
      ),
    },
  ];

  return (
    <div>
      <Typography.Title level={4}>深度分析</Typography.Title>
      <Table columns={columns} dataSource={items} rowKey="date" loading={loading} size="middle"
        pagination={{ current: page, total, pageSize: 20, onChange: (p) => setPage(p), showTotal: (t) => `共 ${t} 条` }} />
    </div>
  );
};

export default DeepAnalysisList;
