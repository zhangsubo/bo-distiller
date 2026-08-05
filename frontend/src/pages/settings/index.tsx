import React from 'react';
import { Tabs } from 'antd';
import {
  ApiOutlined,
  TagsOutlined,
  ExportOutlined,
  DatabaseOutlined,
  SyncOutlined,
  FileTextOutlined,
} from '@ant-design/icons';
import LLMSettings from './LLMSettings';
import TopicSettings from './TopicSettings';
import OutputSettings from './OutputSettings';
import SourceSettings from './SourceSettings';
import SyncSettings from './SyncSettings';
import PromptSettings from './PromptSettings';

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
    key: 'prompts',
    label: <span><FileTextOutlined /> 提示词</span>,
    children: <PromptSettings />,
  },
  {
    key: 'output',
    label: <span><ExportOutlined /> 输出设置</span>,
    children: <OutputSettings />,
  },
  {
    key: 'sources',
    label: <span><DatabaseOutlined /> 内容源</span>,
    children: <SourceSettings />,
  },
  {
    key: 'sync',
    label: <span><SyncOutlined /> 定时同步</span>,
    children: <SyncSettings />,
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
