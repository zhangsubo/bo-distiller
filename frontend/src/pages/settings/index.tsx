import React from 'react';
import { Tabs } from 'antd';
import { ApiOutlined, TagsOutlined, ExportOutlined } from '@ant-design/icons';
import LLMSettings from './LLMSettings';
import TopicSettings from './TopicSettings';
import OutputSettings from './OutputSettings';

const tabItems = [
  {
    key: 'llm',
    label: <span><ApiOutlined /> LLM 配置</span>,
    children: <LLMSettings />,
  },
  {
    key: 'topics',
    label: <span><TagsOutlined /> 主题配置</span>,
    children: <TopicSettings />,
  },
  {
    key: 'output',
    label: <span><ExportOutlined /> 输出设置</span>,
    children: <OutputSettings />,
  },
];

const SettingsPage: React.FC = () => {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>设置管理</h2>
      <Tabs items={tabItems} />
    </div>
  );
};

export default SettingsPage;
