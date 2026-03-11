import React, { useEffect, useState } from 'react';
import { Tabs, Form, Input, InputNumber, Select, Button, Card, Typography, message, Space, Tag } from 'antd';
import { SaveOutlined, ApiOutlined } from '@ant-design/icons';
import { configApi } from '../../api/config';
import type { ConfigItem } from '../../types/api';

const categoryLabels: Record<string, string> = {
  llm: 'LLM 设置',
  image: '图片生成',
  wechat: '微信公众号',
  collector: '采集设置',
  article: '文章设置',
  proxy: '代理/网络',
};

const ConfigPanel: React.FC = () => {
  const [configs, setConfigs] = useState<Record<string, ConfigItem[]>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState<string | null>(null);
  const [testing, setTesting] = useState<string | null>(null);

  useEffect(() => { loadConfigs(); }, []);

  const loadConfigs = async () => {
    setLoading(true);
    try {
      const res = await configApi.getAll();
      setConfigs(res.data.data);
    } catch {
      message.error('加载配置失败');
    }
    setLoading(false);
  };

  const handleSave = async (category: string, values: Record<string, string>) => {
    setSaving(category);
    try {
      await configApi.updateCategory(category, values);
      message.success('配置已保存');
      loadConfigs();
    } catch {
      message.error('保存失败');
    }
    setSaving(null);
  };

  const handleTest = async (type: 'llm' | 'wechat' | 'image') => {
    setTesting(type);
    try {
      let res;
      if (type === 'llm') res = await configApi.testLlm();
      else if (type === 'wechat') res = await configApi.testWechat();
      else res = await configApi.testImage();
      message.success(res.data.message);
    } catch (e: any) {
      message.error(e.response?.data?.message || '测试失败');
    }
    setTesting(null);
  };

  const renderForm = (category: string, items: ConfigItem[]) => {
    const initialValues: Record<string, string> = {};
    items.forEach((item) => { initialValues[item.key] = item.value; });

    return (
      <Form
        layout="vertical"
        initialValues={initialValues}
        onFinish={(values) => handleSave(category, values)}
        key={category + JSON.stringify(initialValues)}
      >
        {items.map((item) => (
          <Form.Item
            key={item.key}
            name={item.key}
            label={<Space>{item.key}<Typography.Text type="secondary">{item.description}</Typography.Text></Space>}
          >
            {item.is_secret ? (
              <Input.Password placeholder={`输入新的 ${item.key}`} />
            ) : item.value_type === 'int' ? (
              <InputNumber style={{ width: '100%' }} />
            ) : item.key === 'LLM_PROVIDER' ? (
              <Select options={[{ value: 'dmxapi', label: 'DMXAPI (云端)' }, { value: 'ollama', label: 'Ollama (本地)' }]} />
            ) : item.key === 'IMAGE_PROVIDER' ? (
              <Select options={[{ value: 'v3', label: 'Ideogram V3' }, { value: 'flux', label: 'Flux' }]} />
            ) : (
              <Input />
            )}
          </Form.Item>
        ))}
        <Form.Item>
          <Space>
            <Button type="primary" htmlType="submit" icon={<SaveOutlined />}
              loading={saving === category}>
              保存
            </Button>
            {category === 'llm' && (
              <Button icon={<ApiOutlined />} loading={testing === 'llm'} onClick={() => handleTest('llm')}>
                测试 LLM 连接
              </Button>
            )}
            {category === 'wechat' && (
              <Button icon={<ApiOutlined />} loading={testing === 'wechat'} onClick={() => handleTest('wechat')}>
                测试微信连接
              </Button>
            )}
            {category === 'image' && (
              <Button icon={<ApiOutlined />} loading={testing === 'image'} onClick={() => handleTest('image')}>
                测试图片生成
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>
    );
  };

  const tabItems = Object.entries(categoryLabels).map(([key, label]) => ({
    key,
    label,
    children: configs[key] ? renderForm(key, configs[key]) : <Typography.Text type="secondary">无配置项</Typography.Text>,
  }));

  return (
    <div>
      <Typography.Title level={4}>系统配置</Typography.Title>
      <Card loading={loading}>
        <Tabs items={tabItems} tabPosition="left" />
      </Card>
    </div>
  );
};

export default ConfigPanel;
