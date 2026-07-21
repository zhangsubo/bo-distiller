import React, { useEffect } from 'react';
import {
  Form,
  Input,
  InputNumber,
  Switch,
  Checkbox,
  Button,
  Card,
  Statistic,
  Space,
  Popconfirm,
  Tag,
  message,
  Spin,
  Row,
  Col,
  Divider,
} from 'antd';
import { useWeChatStatus, useWeChatConfig, useSaveWeChatConfig, useBackfillWeChat, useRetryFailedWeChat } from '../../hooks/useSystemSettings';
import type { WeChatConfig } from '../../api/types';

const FORMAT_OPTIONS = [
  { label: 'Markdown', value: 'markdown' },
  { label: 'HTML', value: 'html' },
];

const WeChatSettings: React.FC = () => {
  const [form] = Form.useForm();
  const { data: statusData } = useWeChatStatus();
  const { data: configData, isLoading } = useWeChatConfig();
  const saveMutation = useSaveWeChatConfig();
  const backfillMutation = useBackfillWeChat();
  const retryMutation = useRetryFailedWeChat();

  useEffect(() => {
    if (configData?.config) {
      form.setFieldsValue(configData.config);
    }
  }, [configData, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await saveMutation.mutateAsync(values as WeChatConfig);
      message.success('微信下载配置已保存');
    } catch {
      message.error('保存失败');
    }
  };

  const handleBackfill = async () => {
    try {
      const res = await backfillMutation.mutateAsync();
      message.success(`已入队 ${res.enqueued} 篇待下载文章`);
    } catch {
      message.error('回填失败');
    }
  };

  const handleRetry = async () => {
    try {
      const res = await retryMutation.mutateAsync();
      message.success(res.reset > 0 ? `已重置 ${res.reset} 个失败任务` : '没有失败任务');
    } catch {
      message.error('重试失败');
    }
  };

  const stats = statusData?.stats;
  const current = statusData?.current;

  if (isLoading) return <Spin />;

  return (
    <div>
      <Form form={form} layout="vertical">
        <Space wrap size="large">
          <Form.Item name="enabled" label="启用下载" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="requests_per_minute" label="限速（次/分钟）">
            <InputNumber min={1} max={60} style={{ width: 120 }} />
          </Form.Item>
          <Form.Item
            name="formats"
            label="下载格式"
            rules={[
              {
                validator: (_, value) =>
                  Array.isArray(value) && value.length > 0
                    ? Promise.resolve()
                    : Promise.reject(new Error('至少选择一种格式')),
              },
            ]}
          >
            <Checkbox.Group options={FORMAT_OPTIONS} />
          </Form.Item>
        </Space>

        <Space wrap size="large">
          <Form.Item name="api_base" label="API 地址" style={{ width: 320 }}>
            <Input placeholder="https://down.mptext.top" />
          </Form.Item>
          <Form.Item name="api_token" label="API Token" style={{ width: 320 }}>
            <Input.Password placeholder="留空则按游客 1 次/分钟限速" />
          </Form.Item>
          <Form.Item name="storage_dir" label="存储目录" style={{ width: 320 }}>
            <Input placeholder="./data/wechat_articles" />
          </Form.Item>
        </Space>

        <Space wrap size="large">
          <Form.Item name="download_on_sync" label="同步后自动下载" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="write_back_content" label="回写正文到文章库" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item name="localize_images" label="图片本地化" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Space>

        <Form.Item>
          <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
            保存配置
          </Button>
        </Form.Item>
      </Form>

      <Divider />

      <Card
        title="下载队列状态"
        size="small"
        extra={
          current?.worker_alive != null && (
            <Tag color={current.worker_alive ? 'green' : 'default'}>
              {current.worker_alive ? 'Worker 运行中' : 'Worker 未运行'}
            </Tag>
          )
        }
      >
        <Row gutter={24}>
          <Col span={5}>
            <Statistic title="待下载" value={stats?.pending ?? 0} />
          </Col>
          <Col span={5}>
            <Statistic title="下载中" value={stats?.downloading ?? 0} valueStyle={{ color: '#1677ff' }} />
          </Col>
          <Col span={5}>
            <Statistic title="已完成" value={stats?.done ?? 0} valueStyle={{ color: '#3f8600' }} />
          </Col>
          <Col span={5}>
            <Statistic title="失败" value={stats?.failed ?? 0} valueStyle={{ color: '#cf1322' }} />
          </Col>
        </Row>

        <div style={{ margin: '16px 0' }}>
          当前处理中：{current?.title ? <strong>{current.title}</strong> : '无'}
        </div>

        <Space>
          <Popconfirm
            title="开始回填存量？"
            description="将队列化下载全部微信文章，游客限速约 1 篇/分钟"
            onConfirm={handleBackfill}
          >
            <Button type="primary" loading={backfillMutation.isPending}>
              开始回填存量
            </Button>
          </Popconfirm>
          <Button onClick={handleRetry} loading={retryMutation.isPending}>
            重试失败
          </Button>
        </Space>
      </Card>
    </div>
  );
};

export default WeChatSettings;
