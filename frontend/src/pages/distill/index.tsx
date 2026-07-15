import React from 'react';
import { Row, Col } from 'antd';
import DistillControls from './DistillControls';
import StepTimeline from './StepTimeline';
import TopicProgress from './TopicProgress';
import LogConsole from './LogConsole';

const DistillPage: React.FC = () => {
  return (
    <div>
      <h2 style={{ marginBottom: 24 }}>蒸馏进度</h2>
      <Row gutter={[16, 16]}>
        <Col span={24}>
          <DistillControls />
        </Col>
        <Col span={24}>
          <StepTimeline />
        </Col>
        <Col span={24}>
          <TopicProgress />
        </Col>
        <Col span={24}>
          <LogConsole />
        </Col>
      </Row>
    </div>
  );
};

export default DistillPage;
