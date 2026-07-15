import React, { useState } from 'react';
import { Row, Col, Card, Input, Tag, Empty, Spin, Button } from 'antd';
import { SearchOutlined, FileTextOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { useKnowledgeDocs, useKnowledgeSearch } from '../../hooks/useKnowledge';
import { formatFileSize, formatDate } from '../../utils/format';

const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const { data, isLoading } = useKnowledgeDocs();
  const { data: searchResults } = useKnowledgeSearch(searchQuery);

  const docs = data?.documents || [];
  const showingSearch = searchQuery.length >= 2;
  const searchItems = (searchResults?.results || []).map((r) => ({
    name: r.name,
    title: r.title,
    size: 0,
    modified: '',
    snippet: r.snippet || '',
  }));
  const displayItems: Array<{ name: string; title: string; size: number; modified: string; snippet?: string }> =
    showingSearch ? searchItems : docs;

  // 提取文章数（从文件名或标题推断）
  const getArticleCount = (title: string): string => {
    const match = title.match(/(\d+)\s*篇/);
    return match ? match[1] : '';
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
        <h2 style={{ margin: 0 }}>知识库</h2>
        <Input
          placeholder="搜索知识库..."
          prefix={<SearchOutlined />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          allowClear
          style={{ width: 300 }}
        />
      </div>

      {isLoading ? (
        <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>
      ) : displayItems.length === 0 ? (
        <Empty description="暂无知识库文档" />
      ) : (
        <Row gutter={[16, 16]}>
          {displayItems.map((doc) => (
            <Col key={doc.name} xs={24} sm={12} md={8} lg={6}>
              <Card
                hoverable
                onClick={() => navigate(`/knowledge/${doc.name}`)}
                style={{ height: '100%' }}
              >
                <Card.Meta
                  avatar={<FileTextOutlined style={{ fontSize: 24, color: '#1677ff' }} />}
                  title={doc.title || doc.name}
                  description={
                    <div>
                      {doc.size > 0 && (
                        <Tag>{formatFileSize(doc.size)}</Tag>
                      )}
                      {getArticleCount(doc.title) && (
                        <Tag color="blue">{getArticleCount(doc.title)} 篇</Tag>
                      )}
                      {doc.modified && (
                        <div style={{ fontSize: 12, color: '#999', marginTop: 4 }}>
                          {formatDate(doc.modified)}
                        </div>
                      )}
                      {showingSearch && doc.snippet && (
                        <div style={{ fontSize: 12, color: '#666', marginTop: 8 }}>
                          {doc.snippet}
                        </div>
                      )}
                    </div>
                  }
                />
              </Card>
            </Col>
          ))}
        </Row>
      )}
    </div>
  );
};

export default KnowledgePage;
