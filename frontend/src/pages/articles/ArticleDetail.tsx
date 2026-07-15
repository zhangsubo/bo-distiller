import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Tag, Spin, Space, Descriptions } from 'antd';
import { ArrowLeftOutlined, LinkOutlined } from '@ant-design/icons';
import { useArticle } from '../../hooks/useArticles';
import { formatDate } from '../../utils/format';

const ArticleDetail: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  const { data, isLoading } = useArticle(id || null);
  const article = data?.data;

  if (isLoading) {
    return (
      <div style={{ textAlign: 'center', padding: 60 }}>
        <Spin size="large" />
      </div>
    );
  }

  if (!article) {
    return <div>文章不存在</div>;
  }

  // 构建 Cubox 链接
  const cuboxUrl = article.url || '#';

  return (
    <div>
      {/* 顶栏 */}
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
          <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/articles')}>
            返回
          </Button>
          <Tag color="blue">{article.source_name}</Tag>
        </Space>
        <a href={cuboxUrl} target="_blank" rel="noopener noreferrer">
          <Button icon={<LinkOutlined />}>查看 Cubox 原文</Button>
        </a>
      </div>

      {/* 文章标题 */}
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 16, lineHeight: 1.4 }}>
        {article.title}
      </h1>

      {/* 元信息 */}
      <Descriptions size="small" column={3} style={{ marginBottom: 24 }}>
        <Descriptions.Item label="来源">
          <Tag color="blue">{article.source_name}</Tag>
        </Descriptions.Item>
        <Descriptions.Item label="抓取时间">{formatDate(article.fetched_date)}</Descriptions.Item>
        <Descriptions.Item label="Cubox ID">{String(article.metadata?.cubox_id || '-')}</Descriptions.Item>
      </Descriptions>

      {/* 文章内容 - 富文本展示 */}
      <div
        style={{
          padding: 24,
          background: '#fafafa',
          borderRadius: 8,
          lineHeight: 1.9,
          fontSize: 15,
        }}
      >
        {article.content ? (
          article.content.split('\n').map((paragraph, i) => (
            <p key={i} style={{ marginBottom: 12 }}>
              {paragraph}
            </p>
          ))
        ) : (
          <p style={{ color: '#999' }}>（无内容）</p>
        )}
      </div>
    </div>
  );
};

export default ArticleDetail;
