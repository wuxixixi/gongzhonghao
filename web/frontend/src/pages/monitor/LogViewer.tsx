import React, { useEffect, useState, useRef } from 'react';
import { Card, Select, Input, Switch, Button, Space, Typography, Tag, message } from 'antd';
import { ClearOutlined, DownloadOutlined } from '@ant-design/icons';
import { monitorApi } from '../../api/monitor';
import type { LogFile } from '../../types/api';

interface LogLine {
  raw?: string;
  level?: string;
  timestamp?: string;
  logger?: string;
  message?: string;
}

const levelColors: Record<string, string> = {
  ERROR: '#ff4d4f',
  WARNING: '#faad14',
  INFO: '#1890ff',
  DEBUG: '#8c8c8c',
};

const LogViewer: React.FC = () => {
  const [logFiles, setLogFiles] = useState<LogFile[]>([]);
  const [selectedDate, setSelectedDate] = useState('');
  const [lines, setLines] = useState<LogLine[]>([]);
  const [loading, setLoading] = useState(false);
  const [levelFilter, setLevelFilter] = useState<string | undefined>(undefined);
  const [keyword, setKeyword] = useState('');
  const [streaming, setStreaming] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    loadLogFiles();
    return () => stopStream();
  }, []);

  useEffect(() => {
    if (selectedDate && !streaming) loadLogs();
  }, [selectedDate, levelFilter, keyword]);

  const loadLogFiles = async () => {
    try {
      const res = await monitorApi.listLogFiles();
      const files = res.data.data;
      setLogFiles(files);
      if (files.length > 0) setSelectedDate(files[0].date);
    } catch {
      message.error('加载日志文件列表失败');
    }
  };

  const loadLogs = async () => {
    if (!selectedDate) return;
    setLoading(true);
    try {
      const res = await monitorApi.getLogContent(selectedDate, {
        level: levelFilter, keyword: keyword || undefined, offset: 0, limit: 1000,
      });
      setLines(res.data.data.lines);
      scrollToBottom();
    } catch {
      message.error('加载日志失败');
    }
    setLoading(false);
  };

  const startStream = () => {
    const token = localStorage.getItem('access_token');
    const url = `/api/monitor/logs/stream?token=${token}`;
    const es = new EventSource(url);
    eventSourceRef.current = es;
    setStreaming(true);

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setLines((prev) => [...prev.slice(-2000), data]);
        scrollToBottom();
      } catch {}
    };

    es.onerror = () => {
      stopStream();
    };
  };

  const stopStream = () => {
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
      eventSourceRef.current = null;
    }
    setStreaming(false);
  };

  const scrollToBottom = () => {
    setTimeout(() => {
      if (containerRef.current) {
        containerRef.current.scrollTop = containerRef.current.scrollHeight;
      }
    }, 50);
  };

  const getLineLevel = (line: LogLine): string => {
    if (line.level) return line.level.toUpperCase();
    const raw = line.raw || '';
    if (raw.includes('[ERROR]')) return 'ERROR';
    if (raw.includes('[WARNING]')) return 'WARNING';
    if (raw.includes('[INFO]')) return 'INFO';
    if (raw.includes('[DEBUG]')) return 'DEBUG';
    return 'INFO';
  };

  const renderLine = (line: LogLine, i: number) => {
    const level = getLineLevel(line);
    const color = levelColors[level] || '#333';
    const text = line.raw || line.message || JSON.stringify(line);
    return (
      <div key={i} style={{ fontFamily: 'Consolas, monospace', fontSize: 12, lineHeight: '20px', color, whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
        {text}
      </div>
    );
  };

  return (
    <div>
      <Typography.Title level={4}>系统日志</Typography.Title>
      <Card size="small" style={{ marginBottom: 12 }}>
        <Space wrap>
          <Select
            style={{ width: 200 }}
            value={selectedDate}
            onChange={setSelectedDate}
            options={logFiles.map((f) => ({ value: f.date, label: `${f.date} (${f.size_kb}KB)` }))}
            placeholder="选择日期"
          />
          <Select
            style={{ width: 120 }}
            value={levelFilter}
            onChange={setLevelFilter}
            allowClear
            placeholder="日志级别"
            options={[
              { value: 'ERROR', label: <span style={{ color: '#ff4d4f' }}>ERROR</span> },
              { value: 'WARNING', label: <span style={{ color: '#faad14' }}>WARNING</span> },
              { value: 'INFO', label: <span style={{ color: '#1890ff' }}>INFO</span> },
              { value: 'DEBUG', label: <span style={{ color: '#8c8c8c' }}>DEBUG</span> },
            ]}
          />
          <Input.Search
            style={{ width: 200 }}
            placeholder="关键词搜索"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            onSearch={loadLogs}
            allowClear
          />
          <Switch
            checkedChildren="实时" unCheckedChildren="历史"
            checked={streaming}
            onChange={(checked) => checked ? startStream() : stopStream()}
          />
          <Button icon={<ClearOutlined />} onClick={() => setLines([])}>清屏</Button>
          <Tag>{lines.length} 行</Tag>
        </Space>
      </Card>
      <div
        ref={containerRef}
        style={{
          height: 'calc(100vh - 320px)', overflow: 'auto',
          background: '#1e1e1e', padding: 12, borderRadius: 8,
        }}
      >
        {lines.map(renderLine)}
        {lines.length === 0 && (
          <Typography.Text style={{ color: '#666' }}>
            {loading ? '加载中...' : streaming ? '等待新日志...' : '暂无日志数据'}
          </Typography.Text>
        )}
      </div>
    </div>
  );
};

export default LogViewer;
