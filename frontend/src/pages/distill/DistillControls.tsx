import React, { useState } from 'react';
import { Card, Select, Radio, Button, Space, message } from 'antd';
import { PlayCircleOutlined, PauseCircleOutlined } from '@ant-design/icons';
import { useDistillStatus, useStartDistill, useStopDistill } from '../../hooks/useDistillProgress';
import { LLM_MODELS } from '../../utils/constants';

const DistillControls: React.FC = () => {
  const [model, setModel] = useState<string>('minimax');
  const [incremental, setIncremental] = useState(true);
  const { data } = useDistillStatus();
  const startMutation = useStartDistill();
  const stopMutation = useStopDistill();

  const running = data?.data?.running ?? false;

  // 当任务运行时，使用后端返回的实际模型和模式
  const displayModel = running && data?.data?.model ? data.data.model : model;
  const displayIncremental = running && data?.data?.incremental !== undefined ? data.data.incremental : incremental;

  const handleStart = async () => {
    try {
      await startMutation.mutateAsync({ model, incremental });
      message.success('蒸馏任务已启动');
    } catch (err: unknown) {
      message.error((err as Error).message || '启动失败');
    }
  };

  const handleStop = async () => {
    try {
      await stopMutation.mutateAsync();
      message.success('已停止');
    } catch {
      message.error('停止失败');
    }
  };

  return (
    <Card title="蒸馏控制" size="small">
      <Space wrap>
        <span>模型：</span>
        <Select
          value={displayModel}
          onChange={setModel}
          style={{ width: 150 }}
          disabled={running}
          options={LLM_MODELS.map((m) => ({ label: m, value: m }))}
        />
        <span>模式：</span>
        <Radio.Group
          value={displayIncremental}
          onChange={(e) => setIncremental(e.target.value)}
          disabled={running}
        >
          <Radio value={true}>增量</Radio>
          <Radio value={false}>全量</Radio>
        </Radio.Group>
        {running ? (
          <Button
            danger
            icon={<PauseCircleOutlined />}
            onClick={handleStop}
            loading={stopMutation.isPending}
          >
            停止
          </Button>
        ) : (
          <Button
            type="primary"
            icon={<PlayCircleOutlined />}
            onClick={handleStart}
            loading={startMutation.isPending}
          >
            开始蒸馏
          </Button>
        )}
      </Space>
    </Card>
  );
};

export default DistillControls;
