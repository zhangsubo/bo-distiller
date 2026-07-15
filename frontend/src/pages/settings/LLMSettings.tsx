import React, { useEffect } from 'react';
import { Form, Input, Select, InputNumber, Card, Button, Space, Divider, message, Spin } from 'antd';
import { useConfig, useSaveConfig } from '../../hooks/useConfig';
import { LLM_MODELS } from '../../utils/constants';
import type { AppConfig, LLMProvider } from '../../api/types';

const LLMSettings: React.FC = () => {
  const [form] = Form.useForm();
  const { data, isLoading } = useConfig();
  const saveMutation = useSaveConfig();

  useEffect(() => {
    if (data?.config) {
      form.setFieldsValue({
        default_provider: data.config.llm.default_provider,
        call_mode: data.config.llm.call_mode,
        batch_temperature: data.config.processing.batch_temperature,
        synthesis_temperature: data.config.processing.synthesis_temperature,
        safety_margin: data.config.processing.safety_margin,
        max_article_length: data.config.processing.max_article_length,
        providers: data.config.llm.providers,
      });
    }
  }, [data, form]);

  const handleSave = async () => {
    try {
      const values = await form.validateFields();
      if (!data?.config) return;

      const updated: AppConfig = {
        ...data.config,
        llm: {
          ...data.config.llm,
          call_mode: values.call_mode,
          default_provider: values.default_provider,
          providers: values.providers,
        },
        processing: {
          ...data.config.processing,
          batch_temperature: values.batch_temperature,
          synthesis_temperature: values.synthesis_temperature,
          safety_margin: values.safety_margin,
          max_article_length: values.max_article_length,
        },
      };

      await saveMutation.mutateAsync(updated);
      message.success('配置已保存');
    } catch {
      message.error('保存失败');
    }
  };

  if (isLoading) return <Spin />;

  return (
    <Form form={form} layout="vertical">
      <Form.Item name="default_provider" label="默认 LLM 提供商">
        <Select options={LLM_MODELS.map((m) => ({ label: m, value: m }))} style={{ width: 200 }} />
      </Form.Item>

      <Form.Item name="call_mode" label="调用方式">
        <Select
          options={[
            { label: '直接 API 调用', value: 'direct' },
            { label: '通过 Agent CLI', value: 'agent_cli' },
          ]}
          style={{ width: 200 }}
        />
      </Form.Item>

      <Divider>提供商配置</Divider>

      {LLM_MODELS.map((model) => (
        <Card key={model} title={model} size="small" style={{ marginBottom: 16 }}>
          <Space wrap>
            <Form.Item name={['providers', model, 'api_key']} label="API Key" style={{ marginBottom: 8, width: 300 }}>
              <Input.Password />
            </Form.Item>
            <Form.Item name={['providers', model, 'api_base']} label="API Base" style={{ marginBottom: 8, width: 300 }}>
              <Input />
            </Form.Item>
            <Form.Item name={['providers', model, 'model']} label="模型" style={{ marginBottom: 8, width: 200 }}>
              <Input />
            </Form.Item>
            <Form.Item name={['providers', model, 'max_context']} label="上下文窗口" style={{ marginBottom: 8, width: 150 }}>
              <InputNumber min={1000} step={1000} style={{ width: '100%' }} />
            </Form.Item>
            <Form.Item name={['providers', model, 'max_output']} label="最大输出" style={{ marginBottom: 8, width: 150 }}>
              <InputNumber min={1000} step={1000} style={{ width: '100%' }} />
            </Form.Item>
          </Space>
        </Card>
      ))}

      <Divider>处理参数</Divider>

      <Space wrap>
        <Form.Item name="batch_temperature" label="批次提取温度">
          <InputNumber min={0} max={1} step={0.1} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="synthesis_temperature" label="整合温度">
          <InputNumber min={0} max={1} step={0.1} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="safety_margin" label="安全系数">
          <InputNumber min={0.5} max={1} step={0.05} style={{ width: 120 }} />
        </Form.Item>
        <Form.Item name="max_article_length" label="文章截取长度 (0=不截断)">
          <InputNumber min={0} step={500} style={{ width: 150 }} />
        </Form.Item>
      </Space>

      <Form.Item>
        <Button type="primary" onClick={handleSave} loading={saveMutation.isPending}>
          保存配置
        </Button>
      </Form.Item>
    </Form>
  );
};

export default LLMSettings;
