import React, { useEffect, useMemo, useState } from 'react';
import { Input, Empty, Spin, Tree, Tag, Breadcrumb } from 'antd';
import type { TreeDataNode } from 'antd';
import { SearchOutlined, FileTextOutlined, BookOutlined } from '@ant-design/icons';
import { useNavigate, useParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { useKnowledgeDocs, useKnowledgeSearch, useKnowledgeTopic } from '../../hooks/useKnowledge';
import { fetchKnowledgeTopic } from '../../api/knowledge';
import type { KnowledgeEntry, KnowledgeTopicDetail } from '../../api/types';
import { formatDate } from '../../utils/format';
import MarkdownRenderer from '../../components/Markdown/MarkdownRenderer';

const ENTRY_SEP = '::';

/** 在主题详情里按 id 找条目 */
function findEntry(topic: KnowledgeTopicDetail | undefined, entryId: string | null) {
  if (!topic || !entryId) return null;
  for (const section of topic.sections) {
    const hit = section.entries.find((e) => e.id === entryId);
    if (hit) return hit;
  }
  return null;
}

const KnowledgePage: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { name } = useParams<{ name?: string }>();
  const selectedTopic = name || null;

  const [searchQuery, setSearchQuery] = useState('');
  const [selectedEntryId, setSelectedEntryId] = useState<string | null>(null);
  const [loadedTopics, setLoadedTopics] = useState<Record<string, KnowledgeTopicDetail>>({});
  const [expandedKeys, setExpandedKeys] = useState<React.Key[]>([]);

  const { data, isLoading } = useKnowledgeDocs();
  const { data: searchResults } = useKnowledgeSearch(searchQuery);
  const { data: topicDetail, isLoading: topicLoading } = useKnowledgeTopic(selectedTopic);

  const docs = useMemo(() => data?.documents || [], [data]);
  const showingSearch = searchQuery.length >= 2;

  // 左侧树：一级主题，二级条目（展开时懒加载）
  const treeData: TreeDataNode[] = useMemo(
    () =>
      docs.map((doc) => {
        const detail = loadedTopics[doc.name];
        const children = detail
          ? detail.sections.flatMap((section) =>
              section.entries.map((entry) => ({
                key: `${doc.name}${ENTRY_SEP}${entry.id}`,
                title: entry.title,
                isLeaf: true,
              })),
            )
          : undefined;
        return {
          key: doc.name,
          title: `${doc.title || doc.name}（${doc.entry_count}）`,
          children,
          isLeaf: detail ? (children && children.length > 0 ? false : true) : false,
        };
      }),
    [docs, loadedTopics],
  );

  const loadTopic = async (topicName: string) => {
    const detail = await queryClient.fetchQuery({
      queryKey: ['knowledgeTopic', topicName],
      queryFn: () => fetchKnowledgeTopic(topicName),
    });
    setLoadedTopics((prev) => ({ ...prev, [topicName]: detail }));
    return detail;
  };

  const selectTopic = (topicName: string | null) => {
    setSelectedEntryId(null);
    navigate(topicName ? `/knowledge/${encodeURIComponent(topicName)}` : '/knowledge');
  };

  const onTreeSelect = (keys: React.Key[]) => {
    const key = keys[0];
    if (key == null) return;
    const keyStr = String(key);
    if (keyStr.includes(ENTRY_SEP)) {
      const [topicName, entryId] = keyStr.split(ENTRY_SEP);
      if (topicName !== selectedTopic) {
        navigate(`/knowledge/${encodeURIComponent(topicName)}`);
      }
      setSelectedEntryId(entryId);
    } else {
      selectTopic(keyStr);
    }
  };

  const onTreeExpand = async (keys: React.Key[], info: { node: TreeDataNode; expanded: boolean }) => {
    setExpandedKeys(keys);
    const key = String(info.node.key);
    if (info.expanded && !key.includes(ENTRY_SEP) && !loadedTopics[key]) {
      await loadTopic(key);
    }
  };

  // 直接通过 URL 进入某个主题时，自动展开并加载该主题的条目
  useEffect(() => {
    if (!selectedTopic) return;
    setExpandedKeys((prev) => (prev.includes(selectedTopic) ? prev : [...prev, selectedTopic]));
    if (!loadedTopics[selectedTopic]) {
      loadTopic(selectedTopic);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTopic]);

  const selectedEntry = findEntry(topicDetail, selectedEntryId);

  // ==================== 右侧内容 ====================

  const renderHome = () => (
    <div>
      <h2 style={{ marginTop: 0 }}>知识库</h2>
      <p style={{ color: '#666' }}>
        共 {docs.length} 个主题、{docs.reduce((sum, d) => sum + (d.entry_count || 0), 0)} 个知识条目
      </p>
      {docs.map((doc) => (
        <div
          key={doc.name}
          onClick={() => selectTopic(doc.name)}
          style={{
            padding: '12px 0',
            borderBottom: '1px solid #f0f0f0',
            cursor: 'pointer',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <BookOutlined style={{ color: '#1677ff' }} />
            <span style={{ fontSize: 15, fontWeight: 600, color: '#1677ff' }}>
              {doc.title || doc.name}
            </span>
            <Tag>{doc.entry_count} 条目</Tag>
            {doc.modified && (
              <span style={{ fontSize: 12, color: '#999', marginLeft: 'auto' }}>
                更新于 {formatDate(doc.modified)}
              </span>
            )}
          </div>
        </div>
      ))}
    </div>
  );

  const renderSearchResults = () => {
    const results = searchResults?.results || [];
    if (results.length === 0) return <Empty description="没有匹配的内容" />;
    return (
      <div>
        <h3 style={{ marginTop: 0 }}>搜索「{searchQuery}」</h3>
        {results.map((r) => (
          <div
            key={r.name}
            onClick={() => selectTopic(r.name)}
            style={{ padding: '12px 0', borderBottom: '1px solid #f0f0f0', cursor: 'pointer' }}
          >
            <span style={{ fontSize: 15, fontWeight: 600, color: '#1677ff' }}>{r.title || r.name}</span>
            {r.snippet && (
              <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>{r.snippet}</div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderEntry = (entry: KnowledgeEntry) => (
    <div>
      <Breadcrumb
        style={{ marginBottom: 16 }}
        items={[
          { title: <a onClick={() => selectTopic(null)}>知识库</a> },
          { title: <a onClick={() => setSelectedEntryId(null)}>{topicDetail?.title || selectedTopic}</a> },
          { title: entry.title },
        ]}
      />
      <h2 style={{ marginTop: 0 }}>{entry.title}</h2>
      {entry.summary && (
        <p style={{ fontSize: 15, color: '#333', fontWeight: 500 }}>{entry.summary}</p>
      )}
      {entry.description && <p style={{ color: '#555', lineHeight: 1.8 }}>{entry.description}</p>}
      {entry.official && entry.official !== '未提供' && !entry.official.startsWith('暂无') && (
        <p style={{ color: '#555' }}>
          <strong>官方地址：</strong>
          {/^https?:\/\//.test(entry.official) ? (
            <a href={entry.official} target="_blank" rel="noreferrer">{entry.official}</a>
          ) : (
            entry.official
          )}
        </p>
      )}
      {entry.extra.map((f) => (
        <p key={f.key} style={{ color: '#555' }}>
          <strong>{f.key}：</strong>
          {f.value}
        </p>
      ))}
      {entry.articles.length > 0 && (
        <div style={{ marginTop: 16 }}>
          <strong>涉及文章：</strong>
          <ul style={{ paddingLeft: 20, marginTop: 8 }}>
            {entry.articles.map((a, i) => (
              <li key={i} style={{ marginBottom: 4 }}>
                <a href={a.url} target="_blank" rel="noreferrer">{a.title}</a>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );

  const renderTopic = () => {
    if (topicLoading) {
      return <div style={{ textAlign: 'center', padding: 60 }}><Spin size="large" /></div>;
    }
    if (!topicDetail) return <Empty description="主题不存在" />;

    // 非「分类→条目」结构的主题，回退渲染原始 markdown
    if (topicDetail.sections.length === 0) {
      return (
        <div>
          <Breadcrumb
            style={{ marginBottom: 16 }}
            items={[
              { title: <a onClick={() => selectTopic(null)}>知识库</a> },
              { title: topicDetail.title || selectedTopic },
            ]}
          />
          <div className="markdown-body">
            <MarkdownRenderer content={topicDetail.raw} />
          </div>
        </div>
      );
    }

    const totalEntries = topicDetail.sections.reduce((sum, s) => sum + s.entries.length, 0);
    return (
      <div>
        <Breadcrumb
          style={{ marginBottom: 16 }}
          items={[
            { title: <a onClick={() => selectTopic(null)}>知识库</a> },
            { title: topicDetail.title || selectedTopic },
          ]}
        />
        <h2 style={{ marginTop: 0, marginBottom: 4 }}>{topicDetail.title || selectedTopic}</h2>
        {topicDetail.summary && (
          <p style={{ color: '#666', marginTop: 0 }}>
            {topicDetail.summary} · 已提炼 {totalEntries} 个知识条目
          </p>
        )}
        {topicDetail.sections.map((section) => (
          <div key={section.title} style={{ marginTop: 24 }}>
            <h3 style={{ borderBottom: '1px solid #f0f0f0', paddingBottom: 8 }}>{section.title}</h3>
            {section.entries.map((entry) => (
              <div
                key={entry.id}
                onClick={() => setSelectedEntryId(entry.id)}
                style={{ padding: '10px 0', borderBottom: '1px dashed #f5f5f5', cursor: 'pointer' }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <FileTextOutlined style={{ color: '#1677ff' }} />
                  <span style={{ fontSize: 14, fontWeight: 600, color: '#1677ff' }}>{entry.title}</span>
                </div>
                {entry.summary && (
                  <div style={{ fontSize: 13, color: '#777', marginTop: 4, paddingLeft: 22 }}>
                    {entry.summary}
                  </div>
                )}
              </div>
            ))}
          </div>
        ))}
      </div>
    );
  };

  const renderContent = () => {
    if (showingSearch) return renderSearchResults();
    if (!selectedTopic) return renderHome();
    if (selectedEntry) return renderEntry(selectedEntry);
    return renderTopic();
  };

  const selectedKeys = selectedEntry
    ? [`${selectedTopic}${ENTRY_SEP}${selectedEntry.id}`]
    : selectedTopic
      ? [selectedTopic]
      : [];

  return (
    <div style={{ display: 'flex', gap: 0, height: 'calc(100vh - 128px)' }}>
      {/* 左侧 wiki 导航树 */}
      <div
        style={{
          width: 280,
          flexShrink: 0,
          borderRight: '1px solid #f0f0f0',
          paddingRight: 12,
          marginRight: 24,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        <Input
          placeholder="搜索知识库..."
          prefix={<SearchOutlined />}
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          allowClear
          style={{ marginBottom: 12 }}
        />
        <div style={{ flex: 1, overflow: 'auto' }}>
          {isLoading ? (
            <div style={{ textAlign: 'center', padding: 40 }}><Spin /></div>
          ) : docs.length === 0 ? (
            <Empty description="暂无知识库文档" />
          ) : (
            <Tree
              treeData={treeData}
              selectedKeys={selectedKeys}
              expandedKeys={expandedKeys}
              onSelect={onTreeSelect}
              onExpand={onTreeExpand}
            />
          )}
        </div>
      </div>
      {/* 右侧内容区 */}
      <div style={{ flex: 1, overflow: 'auto', minWidth: 0 }}>{renderContent()}</div>
    </div>
  );
};

export default KnowledgePage;
