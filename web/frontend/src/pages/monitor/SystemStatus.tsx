import React, { useEffect, useState } from 'react';
import { Row, Col, Card, Descriptions, Tag, Statistic, Typography, message } from 'antd';
import {
  CheckCircleOutlined, CloseCircleOutlined, CloudOutlined,
  DatabaseOutlined, ClockCircleOutlined,
} from '@ant-design/icons';
import { monitorApi } from '../../api/monitor';
import type { SystemStatus as SystemStatusType } from '../../types/api';

const SystemStatus: React.FC = () => {
  const [status, setStatus] = useState<SystemStatusType | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => { load(); }, []);

  const load = async () => {
    setLoading(true);
    try {
      const res = await monitorApi.getStatus();
      setStatus(res.data.data);
    } catch {
      message.error('加载状态失败');
    }
    setLoading(false);
  };

  if (!status) return null;

  return (
    <div>
      <Typography.Title level={4}>系统状态</Typography.Title>
      <Row gutter={[16, 16]}>
        <Col xs={24} lg={12}>
          <Card title="系统信息" loading={loading}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="Python 版本">{status.system.python_version}</Descriptions.Item>
              <Descriptions.Item label="操作系统">{status.system.platform}</Descriptions.Item>
              <Descriptions.Item label="项目目录">{status.system.project_root}</Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} lg={12}>
          <Card title="微信 API" loading={loading}>
            <Descriptions column={1} bordered size="small">
              <Descriptions.Item label="连接状态">
                <Tag color={status.services.wechat.has_valid_token ? 'green' : 'red'}
                  icon={status.services.wechat.has_valid_token ? <CheckCircleOutlined /> : <CloseCircleOutlined />}>
                  {status.services.wechat.status}
                </Tag>
              </Descriptions.Item>
              {status.services.wechat.token_expires_in !== undefined && (
                <Descriptions.Item label="Token 剩余">
                  {Math.round(status.services.wechat.token_expires_in / 60)} 分钟
                </Descriptions.Item>
              )}
            </Descriptions>
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="历史天数" value={status.storage.total_days} prefix={<DatabaseOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="存储空间" value={status.storage.total_size_mb} suffix="MB" precision={1} prefix={<CloudOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日文章"
              value={status.today.has_article ? '已生成' : '未生成'}
              prefix={status.today.has_article ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ClockCircleOutlined />} />
          </Card>
        </Col>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic title="今日深度分析"
              value={status.today.has_deep_analysis ? '已生成' : '未生成'}
              prefix={status.today.has_deep_analysis ? <CheckCircleOutlined style={{ color: '#52c41a' }} /> : <ClockCircleOutlined />} />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default SystemStatus;
