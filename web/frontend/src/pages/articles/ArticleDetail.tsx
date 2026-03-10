import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, Typography, Button, Space, Tag, Descriptions, Table, Image, message, Card, Spin, Popconfirm } from 'antd';
import { EditOutlined, CloudUploadOutlined, ReloadOutlined, ArrowLeftOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { contentApi } from '../../api/articles';
import { publishApi } from '../../api/publish';
import type { ArticleDetail as ArticleDetailType, RawDataItem, SelectedDataItem, RunReport } from '../../types/api';

const ArticleDetail: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const [article, setArticle] = useState<ArticleDetailType | null>(null);
  const [rawData, setRawData] = useState<RawDataItem[]>([]);
  const [selectedData, setSelectedData] = useState<SelectedDataItem[]>([]);
  const [report, setReport] = useState<RunReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [publishing, setPublishing] = useState(false);

  useEffect(() => {
    if (date) loadData();
  }, [date]);

  const loadData = async () => {
    if (!date) return;
    setLoading(true);
    try {
      const res = await contentApi.getArticle(date);
      setArticle(res.data.data);
    } catch {
      message.error('加载文章失败');
    }
    // 加载附加数据（不阻塞）
    try { const r = await contentApi.getRawData(date); setRawData(r.data.data || []); } catch {}
    try { const r = await contentApi.getSelectedData(date); setSelectedData(r.data.data || []); } catch {}
    try { const r = await contentApi.getReport(date); setReport(r.data.data || null); } catch {}
    setLoading(false);
  };

  const handlePublish = async () => {
    if (!date) return;
    setPublishing(true);
    try {
      await publishApi.createDraft(date);
      message.success('草稿创建成功');
    } catch (e: any) {
      message.error(e.response?.data?.message || '发布失败');
    }
    setPublishing(false);
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;
  if (!article) return <Typography.Text>文章不存在</Typography.Text>;

  const rawColumns = [
    { title: '来源', dataIndex: 'source', key: 'source', width: 100, render: (s: string) => <Tag>{s}</Tag> },
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '摘要', dataIndex: 'summary', key: 'summary', ellipsis: true, width: 300 },
    { title: '链接', dataIndex: 'url', key: 'url', width: 80, render: (u: string) => <a href={u} target="_blank" rel="noreferrer">打开</a> },
  ];

  const selectedColumns = [
    { title: '标题', dataIndex: 'title', key: 'title', ellipsis: true },
    { title: '来源', dataIndex: 'source', key: 'source', width: 100, render: (s: string) => <Tag>{s}</Tag> },
    { title: '评分', dataIndex: 'score', key: 'score', width: 70, render: (s: number) => <Tag color={s >= 8 ? 'red' : s >= 6 ? 'orange' : 'default'}>{s}</Tag> },
    { title: '分类', dataIndex: 'category', key: 'category', width: 100 },
    { title: '理由', dataIndex: 'reason', key: 'reason', ellipsis: true },
  ];

  return (
    <div>
      <Space style={{ marginBottom: 16 }}>
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/articles')}>返回</Button>
        <Typography.Title level={4} style={{ margin: 0 }}>
          {article.article_title || article.date_formatted}
        </Typography.Title>
      </Space>

      <Space style={{ marginBottom: 16, float: 'right' }}>
        <Button icon={<EditOutlined />} onClick={() => navigate(`/articles/${date}/edit`)}>编辑</Button>
        <Button type="primary" icon={<CloudUploadOutlined />} loading={publishing} onClick={handlePublish}>
          发布到微信
        </Button>
      </Space>

      <div style={{ clear: 'both' }} />

      <Tabs defaultActiveKey="preview" items={[
        {
          key: 'preview', label: '文章预览',
          children: (
            <div>
              {article.images.includes('cover.png') && (
                <div style={{ marginBottom: 16, textAlign: 'center' }}>
                  <Image src={contentApi.getImageUrl(date!, 'cover.png')} alt="封面" style={{ maxHeight: 300 }} />
                </div>
              )}
              <div className="article-preview" style={{ maxWidth: 800, margin: '0 auto' }}>
                <ReactMarkdown
                  rehypePlugins={[rehypeRaw]}
                  remarkPlugins={[remarkGfm]}
                  components={{
                    img: ({ src, alt, ...props }) => {
                      const imgSrc = src?.startsWith('http') ? src : contentApi.getImageUrl(date!, src || '');
                      return <Image src={imgSrc} alt={alt} style={{ maxWidth: '100%' }} {...props} />;
                    },
                  }}
                >
                  {article.content_markdown}
                </ReactMarkdown>
              </div>
              {article.images.length > 0 && (
                <Card title="文章配图" size="small" style={{ marginTop: 16 }}>
                  <Image.PreviewGroup>
                    <Space wrap>
                      {article.images.map((img) => (
                        <Image key={img} src={contentApi.getImageUrl(date!, img)} width={150} height={100}
                          style={{ objectFit: 'cover' }} />
                      ))}
                    </Space>
                  </Image.PreviewGroup>
                </Card>
              )}
            </div>
          ),
        },
        {
          key: 'data', label: `采集数据 (${rawData.length})`,
          children: (
            <div>
              <Typography.Title level={5}>筛选结果 ({selectedData.length} 条)</Typography.Title>
              <Table columns={selectedColumns} dataSource={selectedData} rowKey="title" size="small" pagination={false} style={{ marginBottom: 24 }} />
              <Typography.Title level={5}>原始采集 ({rawData.length} 条)</Typography.Title>
              <Table columns={rawColumns} dataSource={rawData} rowKey={(r) => r.url || r.title} size="small"
                pagination={{ pageSize: 20, showTotal: (t) => `共 ${t} 条` }} />
            </div>
          ),
        },
        {
          key: 'report', label: '运行报告',
          children: report ? (
            <Descriptions bordered column={2}>
              <Descriptions.Item label="状态"><Tag color={report.status === 'success' ? 'green' : 'red'}>{report.status}</Tag></Descriptions.Item>
              <Descriptions.Item label="耗时">{report.duration_seconds?.toFixed(1)}s</Descriptions.Item>
              <Descriptions.Item label="采集数">{report.collected_count}</Descriptions.Item>
              <Descriptions.Item label="筛选数">{report.selected_count}</Descriptions.Item>
              <Descriptions.Item label="图片数">{report.images_generated}</Descriptions.Item>
              <Descriptions.Item label="已创建草稿"><Tag color={report.draft_created ? 'green' : 'default'}>{report.draft_created ? '是' : '否'}</Tag></Descriptions.Item>
              <Descriptions.Item label="生成时间" span={2}>{report.generated_at}</Descriptions.Item>
              {report.errors?.length > 0 && (
                <Descriptions.Item label="错误" span={2}>
                  {report.errors.map((e, i) => <div key={i} style={{ color: 'red' }}>{e}</div>)}
                </Descriptions.Item>
              )}
            </Descriptions>
          ) : <Typography.Text type="secondary">暂无运行报告</Typography.Text>,
        },
      ]} />
    </div>
  );
};

export default ArticleDetail;
