import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Spin, Tag, Space } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';
import { useKnowledgeDoc } from '../../hooks/useKnowledge';
import MarkdownRenderer from '../../components/Markdown/MarkdownRenderer';

const KnowledgeViewer: React.FC = () => {
  const { name } = useParams<{ name: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useKnowledgeDoc(name || null);

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!data) {
    return <div>文档不存在</div>;
  }

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
          paddingBottom: 16,
          borderBottom: '1px solid #f0f0f0',
        }}
      >
        <Space>
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/knowledge')}>
            返回
          </Button>
          <span style={{ fontSize: 16, fontWeight: 600 }}>{data.name}</span>
          <Tag>{(data.content.length / 1024).toFixed(1)} KB</Tag>
        </Space>
      </div>
      <div className="markdown-body">
        <MarkdownRenderer content={data.content} />
      </div>
    </div>
  );
};

export default KnowledgeViewer;
