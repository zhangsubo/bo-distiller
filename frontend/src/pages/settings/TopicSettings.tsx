import React, { useEffect, useState } from 'react';
import { Table, Tag, Input, Button, Space, message, Spin } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useTopicsConfig, useSaveTopicsConfig } from '../../hooks/useConfig';
import type { TopicsConfig } from '../../api/types';

interface TopicRow {
  name: string;
  keywords: string[];
  description: string;
  priority: number;
  parent: string | null;
}

const TopicSettings: React.FC = () => {
  const { data, isLoading } = useTopicsConfig();
  const saveMutation = useSaveTopicsConfig();
  const [topics, setTopics] = useState<TopicRow[]>([]);

  useEffect(() => {
    if (data?.config?.predefined_topics) {
      const rows: TopicRow[] = Object.entries(data.config.predefined_topics).map(([name, cfg]) => ({
        name,
        keywords: cfg.keywords || [],
        description: cfg.description || '',
        priority: cfg.priority ?? 99,
        parent: cfg.parent || null,
      }));
      rows.sort((a, b) => a.priority - b.priority);
      setTopics(rows);
    }
  }, [data]);

  const handleKeywordChange = (name: string, newKeywords: string[]) => {
    setTopics((prev) =>
      prev.map((t) => (t.name === name ? { ...t, keywords: newKeywords } : t)),
    );
  };

  const handleSave = async () => {
    if (!data?.config) return;
    const predefined: Record<string, unknown> = {};
    topics.forEach((t) => {
      predefined[t.name] = {
        keywords: t.keywords,
        description: t.description,
        priority: t.priority,
        parent: t.parent,
      };
    });

    const updated: TopicsConfig = {
      ...data.config,
      predefined_topics: predefined as TopicsConfig['predefined_topics'],
    };

    try {
      await saveMutation.mutateAsync(updated);
      message.success('主题配置已保存');
    } catch {
      message.error('保存失败');
    }
  };

  const columns: ColumnsType<TopicRow> = [
    {
      title: '优先级',
      dataIndex: 'priority',
      width: 70,
      sorter: (a, b) => a.priority - b.priority,
    },
    {
      title: '主题名称',
      dataIndex: 'name',
      width: 140,
      render: (text: string) => <strong>{text}</strong>,
    },
    {
      title: '描述',
      dataIndex: 'description',
      width: 200,
      ellipsis: true,
    },
    {
      title: '父主题',
      dataIndex: 'parent',
      width: 100,
      render: (text: string | null) => text ? <Tag>{text}</Tag> : '-',
    },
    {
      title: '关键词',
      dataIndex: 'keywords',
      render: (keywords: string[], record: TopicRow) => (
        <Space wrap>
          {keywords.map((kw) => (
            <Tag
              key={kw}
              closable
              onClose={() =>
                handleKeywordChange(record.name, keywords.filter((k) => k !== kw))
              }
            >
              {kw}
            </Tag>
          ))}
        </Space>
      ),
    },
  ];

  if (isLoading) return <Spin />;

  return (
    <div>
      <Table
        columns={columns}
        dataSource={topics}
        rowKey="name"
        size="small"
        pagination={false}
        style={{ marginBottom: 16 }}
      />
      <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
        保存主题配置
      </Button>
    </div>
  );
};

export default TopicSettings;
