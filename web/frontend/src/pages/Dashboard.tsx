import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Statistic, Button, Space, List, Tag, Typography, message } from 'antd';
import {
  FileTextOutlined, DatabaseOutlined, CheckCircleOutlined,
  ClockCircleOutlined, RocketOutlined, ExperimentOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { monitorApi } from '../api/monitor';
import { contentApi } from '../api/articles';
import type { SystemStatus, ArticleSummary } from '../types/api';

const Dashboard: React.FC = () => {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [articles, setArticles] = useState<ArticleSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState<string | null>(null);
  const navigate = useNavigate();

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setLoading(true);
    try {
      const [statusRes, articlesRes] = await Promise.all([
        monitorApi.getStatus(),
        contentApi.listArticles(1, 7),
      ]);
      setStatus(statusRes.data.data);
      setArticles(articlesRes.data.data.items);
    } catch {
      message.error('加载数据失败');
    }
    setLoading(false);
  };

  const handleGenerate = async (type: 'daily' | 'deep') => {
    setGenerating(type);
    try {
      if (type === 'daily') {
        await contentApi.generateDaily(true);
      } else {
        await contentApi.generateDeepAnalysis(true);
      }
      message.success('任务已提交，请在任务历史中查看进度');
    } catch (e: any) {
      message.error(e.response?.data?.message || '提交失败');
    }
    setGenerating(null);
  };

  const statusColor = (s: string | null) => {
    if (s === 'success') return 'success';
    if (s === 'failed') return 'error';
    if (s === 'running') return 'processing';
    return 'default';
  };

  return (
    <div>
      <Typography.Title level={4}>工作台</Typography.Title>

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="今日文章"
              value={status?.today.has_article ? '已生成' : '未生成'}
              prefix={status?.today.has_article ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="深度分析"
              value={status?.today.has_deep_analysis ? '已生成' : '未生成'}
              prefix={status?.today.has_deep_analysis ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ClockCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="历史文章"
              value={status?.storage.total_days || 0}
              suffix="天"
              prefix={<DatabaseOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="存储空间"
              value={status?.storage.total_size_mb || 0}
              suffix="MB"
              precision={1}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginTop: 16 }}>
        <Col xs={24} lg={16}>
          <Card title="最近文章" loading={loading}>
            <List
              dataSource={articles}
              renderItem={(item) => (
                <List.Item
                  actions={[
                    <a key="view" onClick={() => navigate(`/articles/${item.date}`)}>查看</a>,
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        <span>{item.article_title || `${item.date_formatted} 文章`}</span>
                        <Tag color={statusColor(item.task_status)}>{item.task_status || '无状态'}</Tag>
                        {item.has_deep_analysis && <Tag color="purple">有深度分析</Tag>}
                      </Space>
                    }
                    description={`${item.date_formatted} | 采集 ${item.raw_data_count} 条 | 筛选 ${item.selected_count} 条 | ${item.images_count} 张图片`}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col xs={24} lg={8}>
          <Card title="快捷操作">
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <Button
                type="primary" icon={<RocketOutlined />} block
                loading={generating === 'daily'}
                onClick={() => handleGenerate('daily')}
              >
                生成今日热点 (不发布)
              </Button>
              <Button
                icon={<ExperimentOutlined />} block
                loading={generating === 'deep'}
                onClick={() => handleGenerate('deep')}
              >
                生成深度分析 (不发布)
              </Button>
              <Button icon={<ThunderboltOutlined />} block onClick={() => navigate('/monitor/history')}>
                查看任务历史
              </Button>
              <Button icon={<FileTextOutlined />} block onClick={() => navigate('/articles')}>
                浏览所有文章
              </Button>
            </Space>

            <Card size="small" title="微信 Token" style={{ marginTop: 16 }}>
              <Tag color={status?.services.wechat.has_valid_token ? 'green' : 'red'}>
                {status?.services.wechat.status || '未知'}
              </Tag>
              {status?.services.wechat.token_expires_in && (
                <Typography.Text type="secondary" style={{ marginLeft: 8 }}>
                  {Math.round(status.services.wechat.token_expires_in / 60)} 分钟后过期
                </Typography.Text>
              )}
            </Card>
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Dashboard;
