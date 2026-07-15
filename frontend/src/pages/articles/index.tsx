import React, { useState } from 'react';
import { Table, Input, Select, Space, Card, Tag, Button, message, Popconfirm, Row, Col, Statistic } from 'antd';
import { SearchOutlined, ReloadOutlined, DeleteOutlined, CloudSyncOutlined } from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { useArticles, useDeleteArticle, useArticleStats, useSyncCubox } from '../../hooks/useArticles';
import { SOURCE_TYPES, PAGE_SIZE } from '../../utils/constants';
import { formatShortDate } from '../../utils/format';
import type { Article } from '../../api/types';

const ArticlesPage: React.FC = () => {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [sourceType, setSourceType] = useState<string | undefined>();

  const { data, isLoading, refetch } = useArticles({
    page,
    page_size: PAGE_SIZE,
    search: search || undefined,
    source_type: sourceType,
  });

  const { data: stats } = useArticleStats();
  const deleteMutation = useDeleteArticle();
  const syncMutation = useSyncCubox();

  const handleSync = async () => {
    try {
      const result = await syncMutation.mutateAsync();
      message.success(result.message);
    } catch (err: unknown) {
      message.error((err as Error).message || '同步失败');
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await deleteMutation.mutateAsync(id);
      message.success('已删除');
    } catch {
      message.error('删除失败');
    }
  };

  const columns: ColumnsType<Article> = [
    {
      title: '标题',
      dataIndex: 'title',
      key: 'title',
      ellipsis: true,
      width: '50%',
      render: (text: string, record: Article) => (
        <a onClick={() => navigate(`/articles/${record.id}`)} style={{ cursor: 'pointer' }}>
          {text}
        </a>
      ),
    },
    {
      title: '来源',
      key: 'source',
      width: 120,
      render: (_: unknown, record: Article) => (
        <Tag color="blue">{record.source_name}</Tag>
      ),
    },
    {
      title: '抓取时间',
      dataIndex: 'fetched_date',
      key: 'fetched_date',
      width: 130,
      render: (text: string) => formatShortDate(text),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: Article) => (
        <Popconfirm
          title="确定删除此文章？"
          onConfirm={() => handleDelete(record.id)}
          okText="删除"
          cancelText="取消"
        >
          <Button type="text" danger size="small" icon={<DeleteOutlined />} />
        </Popconfirm>
      ),
    },
  ];

  const totalArticles = stats?.data?.total_articles ?? data?.pagination?.total ?? 0;
  const sourceCount = stats?.data?.sources?.length ?? 0;

  return (
    <div>
      {/* 统计卡片 */}
      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small">
            <Statistic title="总文章数" value={totalArticles} />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic title="内容源" value={sourceCount} suffix="个" />
          </Card>
        </Col>
        <Col span={8}>
          <Card size="small">
            <Statistic
              title="数据库大小"
              value={stats?.data?.db_size ? (stats.data.db_size / 1024 / 1024).toFixed(1) : 0}
              suffix="MB"
            />
          </Card>
        </Col>
      </Row>

      {/* 筛选栏 */}
      <Space style={{ marginBottom: 16 }} wrap>
        <Input
          placeholder="搜索标题或内容"
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          allowClear
          style={{ width: 280 }}
        />
        <Select
          placeholder="来源筛选"
          value={sourceType}
          onChange={(v) => { setSourceType(v); setPage(1); }}
          allowClear
          style={{ width: 150 }}
          options={SOURCE_TYPES}
        />
        <Button
          type="primary"
          icon={<CloudSyncOutlined />}
          onClick={handleSync}
          loading={syncMutation.isPending}
        >
          同步 Cubox
        </Button>
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>
          刷新
        </Button>
      </Space>

      {/* 文章列表 */}
      <Table
        columns={columns}
        dataSource={data?.data || []}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{
          current: page,
          pageSize: PAGE_SIZE,
          total: data?.pagination?.total || 0,
          showTotal: (total) => `共 ${total} 条`,
          showSizeChanger: false,
          onChange: setPage,
        }}
      />
    </div>
  );
};

export default ArticlesPage;
