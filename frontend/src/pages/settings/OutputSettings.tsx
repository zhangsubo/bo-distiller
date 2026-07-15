import React, { useEffect } from 'react';
import { Form, Switch, Input, Button, Card, message, Spin } from 'antd';
import { useConfig, useSaveConfig } from '../../hooks/useConfig';
import type { AppConfig } from '../../api/types';

const OutputSettings: React.FC = () => {
  const [form] = Form.useForm();
  const { data, isLoading } = useConfig();
  const saveMutation = useSaveConfig();

  useEffect(() => {
    if (data?.config) {
      form.setFieldsValue({
        local_enabled: data.config.output.local.enabled,
        local_dir: data.config.output.local.dir,
        include_sources: data.config.output.local.include_sources,
        feishu_enabled: data.config.output.feishu.enabled,
        feishu_space_id: data.config.output.feishu.space_id,
      });
    }
  }, [data, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!data?.config) return;

      const updated: AppConfig = {
        ...data.config,
        output: {
          local: {
            enabled: values.local_enabled,
            dir: values.local_dir,
            include_sources: values.include_sources,
          },
          feishu: {
            enabled: values.feishu_enabled,
            space_id: values.feishu_space_id || null,
          },
        },
      };

      await saveMutation.mutateAsync(updated);
      message.success('输出配置已保存');
    } catch {
      message.error('保存失败');
    }
  };

  if (isLoading) return <Spin />;

  return (
    <Form form={form} layout="vertical">
      <Card title="本地输出" size="small" style={{ marginBottom: 16 }}>
        <Form.Item name="local_enabled" label="启用本地输出" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="local_dir" label="输出目录">
          <Input placeholder="./output" />
        </Form.Item>
        <Form.Item name="include_sources" label="生成原文合集" valuePropName="checked">
          <Switch />
        </Form.Item>
      </Card>

      <Card title="飞书知识库" size="small" style={{ marginBottom: 16 }}>
        <Form.Item name="feishu_enabled" label="启用飞书输出" valuePropName="checked">
          <Switch />
        </Form.Item>
        <Form.Item name="feishu_space_id" label="飞书空间 ID">
          <Input placeholder="飞书知识库空间 ID" />
        </Form.Item>
      </Card>

      <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
        保存输出配置
      </Button>
    </Form>
  );
};

export default OutputSettings;
