import React from 'react';
import { Card, Steps } from 'antd';
import { useDistillStatus } from '../../hooks/useDistillProgress';

const stepMap: Record<string, number> = {
  idle: -1,
  started: 0,
  fetch: 0,
  clean: 1,
  classify: 2,
  synthesize: 3,
  done: 4,
  stopped: -1,
};

const stepItems = [
  { title: '获取文章' },
  { title: '清洗内容' },
  { title: '主题分类' },
  { title: '知识合成' },
];

const StepTimeline: React.FC = () => {
  const { data } = useDistillStatus();
  const status = data?.data;
  const currentStep = status ? (stepMap[status.step] ?? -1) : -1;

  return (
    <Card title="步骤进度" size="small">
      <Steps
        current={currentStep >= 0 ? currentStep : 0}
        status={status?.error ? 'error' : currentStep >= 4 ? 'finish' : 'process'}
        items={stepItems}
      />
    </Card>
  );
};

export default StepTimeline;
