import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Button, Tag, Spin, Space, Descriptions, Card, Collapse, Typography } from 'antd';
import { ArrowLeftOutlined, LinkOutlined, UserOutlined, GlobalOutlined } from '@ant-design/icons';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { useArticle } from '../../hooks/useArticles';
import { formatDate } from '../../utils/format';

const { Text } = Typography;

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

  const meta = (article.metadata || {}) as Record<string, unknown>;
  const tags = (meta.tags as string[]) || [];
  const domain = (meta.domain as string) || '';
  const insight = meta.insight as { summary?: string; qas?: Array<{ q: string; a: string }> } | undefined;
  const annotations = meta.annotations as Array<{ content?: string }> | undefined;

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
        <Button icon={<ArrowLeftOutlined />} onClick={() => navigate('/articles')}>
          返回
        </Button>
        {article.url && (
          <a href={article.url} target="_blank" rel="noopener noreferrer">
            <Button icon={<LinkOutlined />}>查看原文</Button>
          </a>
        )}
      </div>

      {/* 文章标题 */}
      <h1 style={{ fontSize: 22, fontWeight: 600, marginBottom: 16, lineHeight: 1.4 }}>
        {article.title}
      </h1>

      {/* 元信息 */}
      <Descriptions size="small" column={4} style={{ marginBottom: 24 }}>
        {article.author && (
          <Descriptions.Item label={<><UserOutlined /> 作者</>}>
            {article.author}
          </Descriptions.Item>
        )}
        {domain && (
          <Descriptions.Item label={<><GlobalOutlined /> 来源</>}>
            {domain}
          </Descriptions.Item>
        )}
        <Descriptions.Item label="收藏时间">
          {formatDate(article.fetched_date)}
        </Descriptions.Item>
      </Descriptions>

      {/* 标签 */}
      {tags.length > 0 && (
        <div style={{ marginBottom: 20 }}>
          {tags.map((tag) => (
            <Tag key={tag} color="blue" style={{ marginBottom: 4 }}>
              {tag}
            </Tag>
          ))}
        </div>
      )}

      {/* AI 摘要 */}
      {insight?.summary && (
        <Card
          size="small"
          title="AI 摘要"
          style={{ marginBottom: 20, background: '#f6ffed', borderColor: '#b7eb8f' }}
        >
          <div style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{insight.summary}</div>
        </Card>
      )}

      {/* 文章正文 */}
      <Card size="small" title="正文" style={{ marginBottom: 20 }}>
        <div className="markdown-body" style={{ lineHeight: 1.9, fontSize: 15 }}>
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {article.content || '（无内容）'}
          </ReactMarkdown>
        </div>
      </Card>

      {/* Q&A */}
      {insight?.qas && insight.qas.length > 0 && (
        <Card size="small" title="AI 提炼的问答" style={{ marginBottom: 20 }}>
          <Collapse
            size="small"
            items={insight.qas.map((qa, i) => ({
              key: String(i),
              label: <Text strong>{qa.q}</Text>,
              children: <div style={{ lineHeight: 1.8, whiteSpace: 'pre-wrap' }}>{qa.a}</div>,
            }))}
          />
        </Card>
      )}

      {/* 批注 */}
      {annotations && annotations.length > 0 && (
        <Card size="small" title="批注" style={{ marginBottom: 20 }}>
          {annotations.map((ann, i) => (
            <div key={i} style={{ padding: '8px 0', borderBottom: '1px solid #f0f0f0' }}>
              {ann.content || JSON.stringify(ann)}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
};

export default ArticleDetail;
