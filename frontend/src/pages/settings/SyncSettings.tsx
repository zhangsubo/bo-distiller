import React, { useEffect, useState } from 'react';
import { Form, Switch, InputNumber, Button, Descriptions, Space, message, Spin, Progress, Alert, Radio } from 'antd';
import { SyncOutlined, StopOutlined } from '@ant-design/icons';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import dayjs from 'dayjs';
import { useSyncStatus as useSystemSyncConfig, useSaveSyncConfig } from '../../hooks/useSystemSettings';
import { useSyncStatus } from '../../hooks/useArticles';
import { syncCubox, cancelSyncCubox } from '../../api/articles';

function formatTime(value: string | null | undefined): string {
  if (!value) return '从未';
  const d = dayjs(value);
  return d.isValid() ? d.format('YYYY-MM-DD HH:mm:ss') : String(value);
}

const SyncSettings: React.FC = () => {
  const [form] = Form.useForm();
  const queryClient = useQueryClient();
  const { data, isLoading } = useSystemSyncConfig();
  const saveMutation = useSaveSyncConfig();
  const [syncMode, setSyncMode] = useState<'full' | 'incremental'>('incremental');

  // 监控同步状态
  const { data: syncStatus } = useSyncStatus(true);

  const syncNowMutation = useMutation({
    mutationFn: (incremental: boolean) => syncCubox(incremental),
    onSuccess: (res) => {
      message.success(res?.message || '同步任务已启动');
      // 立即刷新同步状态
      queryClient.invalidateQueries({ queryKey: ['syncStatus'] });
    },
    onError: (error: any) => {
      message.error(error?.message || '同步失败');
    },
  });

  const cancelSyncMutation = useMutation({
    mutationFn: cancelSyncCubox,
    onSuccess: (res) => {
      message.info(res?.message || '正在取消同步...');
      // 立即刷新同步状态
      queryClient.invalidateQueries({ queryKey: ['syncStatus'] });
    },
    onError: (error: any) => {
      message.error(error?.message || '取消失败');
    },
  });

  // 当同步完成时刷新文章列表
  useEffect(() => {
    if (syncStatus && !syncStatus.running && syncStatus.last_sync_time) {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['articleStats'] });

      // 显示完成消息
      if (syncStatus.error) {
        message.error(`同步失败: ${syncStatus.error}`);
      } else if (syncStatus.progress) {
        message.success(syncStatus.progress);
      }
    }
  }, [syncStatus?.running, syncStatus?.last_sync_time, queryClient]);

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

  const isSyncing = syncNowMutation.isPending || syncStatus?.running;
  const progress = syncStatus?.total > 0 ? Math.round((syncStatus.processed / syncStatus.total) * 100) : 0;

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

        <Form.Item label="立即同步模式">
          <Radio.Group value={syncMode} onChange={(e) => setSyncMode(e.target.value)} disabled={isSyncing}>
            <Radio.Button value="incremental">增量同步</Radio.Button>
            <Radio.Button value="full">全量同步</Radio.Button>
          </Radio.Group>
          <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
            {syncMode === 'incremental'
              ? '• 只同步新收藏的文章 + 补抓空标签文章'
              : '• 重新同步所有文章（耗时较长）'}
          </div>
        </Form.Item>

        <Form.Item>
          <Space>
            <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
              保存配置
            </Button>
            <Button
              icon={<SyncOutlined spin={isSyncing} />}
              onClick={() => syncNowMutation.mutate(syncMode === 'incremental')}
              loading={isSyncing}
              disabled={isSyncing}
            >
              {isSyncing ? '同步中...' : '立即同步'}
            </Button>
            {isSyncing && (
              <Button
                danger
                icon={<StopOutlined />}
                onClick={() => cancelSyncMutation.mutate()}
                loading={cancelSyncMutation.isPending}
              >
                取消同步
              </Button>
            )}
          </Space>
        </Form.Item>
      </Form>

      {/* 同步进度提示 */}
      {syncStatus?.running && (
        <Alert
          message="正在同步"
          description={
            <div>
              <div>{syncStatus.progress}</div>
              {syncStatus.total > 0 && (
                <Progress
                  percent={progress}
                  status="active"
                  format={() => `${syncStatus.processed} / ${syncStatus.total}`}
                />
              )}
            </div>
          }
          type="info"
          showIcon
          style={{ marginBottom: 16, maxWidth: 500 }}
        />
      )}

      {/* 同步错误提示 */}
      {syncStatus?.error && !syncStatus.running && (
        <Alert
          message="同步失败"
          description={syncStatus.error}
          type="error"
          closable
          style={{ marginBottom: 16, maxWidth: 500 }}
        />
      )}

      <Descriptions title="同步状态" bordered size="small" column={1} style={{ maxWidth: 500 }}>
        <Descriptions.Item label="上次同步时间">
          {formatTime(syncStatus?.last_sync_time || data?.last_sync)}
        </Descriptions.Item>
        <Descriptions.Item label="下次执行时间">
          {formatTime(data?.next_run_time)}
        </Descriptions.Item>
      </Descriptions>
    </div>
  );
};

export default SyncSettings;
