import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Space, Typography, Input, message, Spin, Row, Col } from 'antd';
import { ArrowLeftOutlined, SaveOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import remarkGfm from 'remark-gfm';
import { contentApi } from '../../api/articles';

const { TextArea } = Input;

const ArticleEditor: React.FC = () => {
  const { date } = useParams<{ date: string }>();
  const navigate = useNavigate();
  const [content, setContent] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (date) loadArticle();
  }, [date]);

  const loadArticle = async () => {
    if (!date) return;
    setLoading(true);
    try {
      const res = await contentApi.getArticle(date);
      setContent(res.data.data.content_markdown || '');
    } catch {
      message.error('加载文章失败');
    }
    setLoading(false);
  };

  const handleSave = async () => {
    if (!date) return;
    setSaving(true);
    try {
      await contentApi.updateArticle(date, content);
      message.success('保存成功');
    } catch {
      message.error('保存失败');
    }
    setSaving(false);
  };

  if (loading) return <Spin size="large" style={{ display: 'block', margin: '100px auto' }} />;

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 16 }}>
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate(`/articles/${date}`)}>返回</Button>
          <Typography.Title level={4} style={{ margin: 0 }}>编辑文章 - {date}</Typography.Title>
        </Space>
        <Button type="primary" icon={<SaveOutlined />} loading={saving} onClick={handleSave}>
          保存
        </Button>
      </div>
      <Row gutter={16} style={{ height: 'calc(100vh - 250px)' }}>
        <Col span={12}>
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>Markdown 编辑</Typography.Text>
          <TextArea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            style={{ height: '100%', fontFamily: 'monospace', fontSize: 14 }}
          />
        </Col>
        <Col span={12}>
          <Typography.Text type="secondary" style={{ display: 'block', marginBottom: 8 }}>实时预览</Typography.Text>
          <div style={{
            height: '100%', overflow: 'auto', padding: 16,
            border: '1px solid #d9d9d9', borderRadius: 8, background: '#fafafa',
          }}>
            <ReactMarkdown rehypePlugins={[rehypeRaw]} remarkPlugins={[remarkGfm]}
              components={{
                img: ({ src, alt }) => {
                  const imgSrc = src?.startsWith('http') ? src : contentApi.getImageUrl(date!, src || '');
                  return <img src={imgSrc} alt={alt} style={{ maxWidth: '100%' }} />;
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        </Col>
      </Row>
    </div>
  );
};

export default ArticleEditor;
