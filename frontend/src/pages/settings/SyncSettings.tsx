import React, { useEffect } from 'react';
import { Form, Switch, InputNumber, Button, Descriptions, Space, message, Spin } from 'antd';
import { SyncOutlined } from '@ant-design/icons';
import { useMutation } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useSyncStatus, useSaveSyncConfig } from '../../hooks/useSystemSettings';
import { syncCubox } from '../../api/articles';

function formatTime(value: string | null | undefined): string {
  if (!value) return '从未';
  const d = dayjs(value);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : String(value);
}

const SyncSettings: React.FC = () => {
  const [form] = Form.useForm();
  const { data, isLoading } = useSyncStatus();
  const saveMutation = useSaveSyncConfig();

  const syncNowMutation = useMutation({
    mutationFn: syncCubox,
    onSuccess: (res) => {
      message.success(res?.message || `同步完成，新增 ${res?.count ?? 0} 篇文章`);
    },
    onError: () => {
      message.error('同步失败');
    },
  });

  useEffect(() => {
    if (data) {
      form.setFieldsValue({
        enabled: data.enabled,
        interval_minutes: data.interval_minutes,
        incremental: data.incremental,
      });
    }
  }, [data, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      await saveMutation.mutateAsync({
        enabled: values.enabled,
        interval_minutes: values.interval_minutes,
        incremental: values.incremental,
      });
      message.success('同步配置已保存');
    } catch {
      message.error('保存失败');
    }
  };

  if (isLoading) return <Spin />;

  return (
    <div>
      <Form form={form} layout="vertical" style={{ maxWidth: 400 }}>
        <Form.Item name="enabled" label="启用定时同步" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item
          name="interval_minutes"
          label="同步间隔（分钟）"
          rules={[{ required: true, message: '请设置同步间隔' }]}
        >
          <InputNumber min={5} step={5} style={{ width: 150 }} />
        </Form.Item>
        <Form.Item
          name="incremental"
          label="增量同步（仅拉取新增收藏）"
          valuePropName="checked"
        >
          <Switch />
        </Form.Item>
        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
              保存配置
            </Button>
            <Button
              icon={<SyncOutlined />}
              onClick={() => syncNowMutation.mutate()}
              loading={syncNowMutation.isPending}
            >
              立即同步
            </Button>
          </Space>
        </Form.Item>
      </Form>

      <Descriptions title="同步状态" bordered size="small" column={1} style={{ maxWidth: 500 }}>
        <Descriptions.Item label="上次同步时间">
          {formatTime(data?.last_sync)}
        </Descriptions.Item>
        <Descriptions.Item label="下次执行时间">
          {formatTime(data?.next_run_time)}
        </Descriptions.Item>
      </Descriptions>
    </div>
  );
};

export default SyncSettings;
