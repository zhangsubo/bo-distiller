import React from 'react';
import { Card, Progress, Row, Col, Empty } from 'antd';
import { useDistillStatus } from '../../hooks/useDistillProgress';

const TopicProgress: React.FC = () => {
  const { data } = useDistillStatus();
  const status = data?.data;

  if (!status) return <Card title="主题进度"><Empty /></Card>;

  const topicsDone = status.topics_done || [];
  const totalBatches = status.cache.batch_count;
  const totalFinal = status.cache.final_count;

  // 从 topics_done 推断完成百分比
  // 如果有 final 文件说明已完成，否则根据 batch 数估算
  const topics = [
    'AI编程工具', '开源项目', 'Claude专题', '编程开发', '工具软件',
    '教程指南', '数据资产', 'AI模型', '产品设计', '效率方法',
    'AI应用', '自媒体', '其他',
  ];

  return (
    <Card title="主题进度" size="small">
      {topics.length === 0 ? (
        <Empty description="暂无进度" />
      ) : (
        <Row gutter={[16, 12]}>
          {topics.map((topic) => {
            const done = topicsDone.includes(topic);
            const percent = done ? 100 : (status.running ? 50 : 0);
            return (
              <Col key={topic} span={8}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <span style={{ width: 100, fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {topic}
                  </span>
                  <Progress
                    percent={percent}
                    size="small"
                    status={done ? 'success' : 'active'}
                    style={{ flex: 1, marginBottom: 0 }}
                  />
                </div>
              </Col>
            );
          })}
        </Row>
      )}
      <div style={{ marginTop: 12, fontSize: 12, color: '#999' }}>
        已完成 {totalFinal} 个主题 · 批次文件 {totalBatches} 个
      </div>
    </Card>
  );
};

export default TopicProgress;
