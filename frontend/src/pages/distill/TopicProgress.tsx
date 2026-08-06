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

  // 假设每个主题平均需要 42/13 ≈ 3.2 个批次
  const estimatedBatchesPerTopic = 42 / topics.length;

  return (
    <Card title="主题进度" size="small">
      {topics.length === 0 ? (
        <Empty description="暂无进度" />
      ) : (
        <Row gutter={[16, 12]}>
          {topics.map((topic, index) => {
            const done = topicsDone.includes(topic);
            // 根据批次数估算当前主题的进度
            // 假设按顺序处理，当前正在处理的主题索引
            const currentTopicIndex = Math.floor(totalBatches / estimatedBatchesPerTopic);
            let percent = 0;

            if (done) {
              percent = 100;
            } else if (status.running && index < currentTopicIndex) {
              // 应该已完成但还没有 final 文件
              percent = 95;
            } else if (status.running && index === currentTopicIndex) {
              // 当前正在处理的主题
              const batchesInTopic = totalBatches - (index * estimatedBatchesPerTopic);
              percent = Math.min(90, Math.floor((batchesInTopic / estimatedBatchesPerTopic) * 100));
            } else {
              percent = 0;
            }

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
