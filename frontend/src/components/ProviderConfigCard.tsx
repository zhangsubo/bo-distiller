/**
 * LLM 提供商配置卡片组件
 *
 * 从元数据自动填充 Base URL、上下文窗口、最大输出等字段
 */

import React, { useEffect, useState } from 'react';
import { Card, Form, Input, Select, InputNumber, Space, Spin, Alert, Tooltip, Button, message } from 'antd';
import { ExclamationCircleOutlined, ApiOutlined } from '@ant-design/icons';
import { useProviderMetadata, useTestConnectivity } from '../hooks/useLLMMetadata';
import { useConfig } from '../hooks/useConfig';

interface ProviderConfigCardProps {
  providerId: string;
  providerName: string;
}

const ProviderConfigCard: React.FC<ProviderConfigCardProps> = ({
  providerId,
  providerName,
}) => {
  const form = Form.useFormInstance();
  const { data: metadata, isLoading } = useProviderMetadata(providerId);
  const { data: configData } = useConfig();
  const testConnectivityMutation = useTestConnectivity();
  const [isConnected, setIsConnected] = useState(false); // 连通性状态

  // 测试连通性
  const handleTestConnectivity = async () => {
    try {
      // 获取当前表单值
      const providerConfig = form.getFieldValue(['providers', providerId]) || {};
      const { api_key, api_base, model } = providerConfig;

      // 验证必填字段
      if (!api_key || !api_base || !model) {
        message.warning('请先填写 API Key、Base URL 和模型');
        return;
      }

      // 调用测试接口
      const result = await testConnectivityMutation.mutateAsync({
        apiKey: api_key,
        apiBase: api_base,
        model: model,
      });

      if (result.success) {
        message.success('连通性测试成功！API 配置正常');
        setIsConnected(true); // 设置为已连通
      } else {
        message.error(result.message || '连通性测试失败');
        setIsConnected(false);
      }
    } catch (error: any) {
      message.error(error.message || '连通性测试失败');
      setIsConnected(false);
    }
  };

  // 当元数据加载完成时，设置默认值
  useEffect(() => {
    if (metadata && metadata.base_url) {
      const currentValues = form.getFieldValue(['providers', providerId]) || {};

      // 只在字段为空时设置默认值
      if (!currentValues.api_base) {
        form.setFieldValue(['providers', providerId, 'api_base'], metadata.base_url);
      }

      // 如果有模型数据，设置默认的上下文窗口和最大输出
      const models = metadata.models as Record<string, any> || {};
      const firstModelId = Object.keys(models)[0];

      if (firstModelId && models[firstModelId]) {
        const firstModel = models[firstModelId];
        const limit = firstModel.limit || {};

        if (!currentValues.max_context && limit.context) {
          form.setFieldValue(['providers', providerId, 'max_context'], limit.context);
        }

        if (!currentValues.max_output && limit.output) {
          form.setFieldValue(['providers', providerId, 'max_output'], limit.output);
        }

        // 如果模型字段为空，设置第一个模型
        if (!currentValues.model) {
          form.setFieldValue(['providers', providerId, 'model'], firstModelId);
        }
      }
    }
  }, [metadata, form, providerId]);

  // 获取模型选项（只显示已启用的模型）
  const getModelOptions = () => {
    if (!metadata?.models) return [];

    const models = metadata.models as Record<string, any>;
    const providerConfig = configData?.config?.llm?.providers?.[providerId];
    const enabledModels = providerConfig?.enabled_models;

    // 如果没有配置 enabled_models，默认显示所有模型
    const modelIds = enabledModels && enabledModels.length > 0
      ? enabledModels
      : Object.keys(models);

    return modelIds
      .filter((modelId) => models[modelId]) // 确保模型存在
      .map((modelId) => ({
        label: models[modelId]?.name || modelId,
        value: modelId,
      }));
  };

  // 当模型改变时，更新上下文窗口和最大输出
  const handleModelChange = (modelId: string) => {
    if (!metadata?.models) return;

    const models = metadata.models as Record<string, any>;
    const model = models[modelId];
    if (model?.limit) {
      if (model.limit.context) {
        form.setFieldValue(['providers', providerId, 'max_context'], model.limit.context);
      }
      if (model.limit.output) {
        form.setFieldValue(['providers', providerId, 'max_output'], model.limit.output);
      }
    }
  };

  return (
    <Card
      title={
        <Space>
          <span>{providerName}</span>
          {providerId === 'kimi-for-coding' && (
            <Tooltip
              title="必须使用 Kimi Code CLI 或部分第三方 Code Agent 使用（Claude Code、Codex、opencode 等）"
              placement="right"
            >
              <ExclamationCircleOutlined style={{ color: '#ff4d4f', fontSize: '14px' }} />
            </Tooltip>
          )}
        </Space>
      }
      extra={
        <Button
          type="default"
          size="small"
          icon={<ApiOutlined />}
          onClick={handleTestConnectivity}
          loading={testConnectivityMutation.isPending}
          style={isConnected ? { color: '#52c41a' } : {}}
        >
          {isConnected ? '可连通' : '连通性测试'}
        </Button>
      }
      size="small"
      style={{ marginBottom: 16 }}
    >
      {isLoading && (
        <div style={{ textAlign: 'center', padding: '20px 0' }}>
          <Spin tip="加载元数据中...">
            <div style={{ minHeight: '40px' }} />
          </Spin>
        </div>
      )}

      {!isLoading && !metadata && (
        <Alert
          message="无法加载元数据"
          description="将使用手动配置"
          type="warning"
          showIcon
          style={{ marginBottom: 16 }}
        />
      )}

      <Space direction="vertical" style={{ width: '100%' }}>
        <Form.Item
          name={['providers', providerId, 'api_key']}
          label="API Key"
          rules={[{ required: true, message: '请输入 API Key' }]}
          style={{ marginBottom: 8 }}
        >
          <Input.Password placeholder="输入 API Key" />
        </Form.Item>

        <Form.Item
          name={['providers', providerId, 'api_base']}
          label="Base URL"
          tooltip="从元数据自动获取，也可以手动修改"
          style={{ marginBottom: 8 }}
        >
          <Input placeholder="API Base URL" />
        </Form.Item>

        <Space wrap>
          <Form.Item
            name={['providers', providerId, 'model']}
            label="模型"
            rules={[{ required: true, message: '请选择模型' }]}
            style={{ marginBottom: 8, width: 250 }}
          >
            <Select
              placeholder="选择模型"
              options={getModelOptions()}
              onChange={handleModelChange}
              showSearch
              filterOption={(input, option) =>
                (option?.label ?? '').toLowerCase().includes(input.toLowerCase())
              }
            />
          </Form.Item>

          <Form.Item
            name={['providers', providerId, 'max_context']}
            label="上下文窗口"
            tooltip="从元数据自动获取，也可以手动修改"
            style={{ marginBottom: 8, width: 150 }}
          >
            <InputNumber
              min={1000}
              step={1000}
              style={{ width: '100%' }}
              placeholder="上下文"
            />
          </Form.Item>

          <Form.Item
            name={['providers', providerId, 'max_output']}
            label="最大输出"
            tooltip="从元数据自动获取，也可以手动修改"
            style={{ marginBottom: 8, width: 150 }}
          >
            <InputNumber
              min={1000}
              step={1000}
              style={{ width: '100%' }}
              placeholder="最大输出"
            />
          </Form.Item>
        </Space>
      </Space>
    </Card>
  );
};

export default ProviderConfigCard;
