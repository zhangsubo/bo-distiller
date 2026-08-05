/**
 * LLM 提供商元数据展示组件
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Button,
  Space,
  Tag,
  Descriptions,
  Modal,
  List,
  Spin,
  message,
  Typography,
  Tooltip,
  Popconfirm,
  Checkbox,
  Alert,
} from 'antd';
import {
  ReloadOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  InfoCircleOutlined,
  ClearOutlined,
  SaveOutlined,
} from '@ant-design/icons';
import {
  useProviderMetadata,
  useRefreshProviderMetadata,
  useClearProviderCache,
} from '../hooks/useLLMMetadata';
import { useConfig, useSaveConfig } from '../hooks/useConfig';

const { Text, Paragraph } = Typography;

interface ProviderMetadataCardProps {
  providerId: string;
  isCached?: boolean;
}

const ProviderMetadataCard: React.FC<ProviderMetadataCardProps> = ({
  providerId,
  isCached = false,
}) => {
  const [showModels, setShowModels] = useState(false);
  const [selectedModels, setSelectedModels] = useState<string[]>([]);
  const [hasChanges, setHasChanges] = useState(false);

  const { data: metadata, isLoading, refetch } = useProviderMetadata(providerId);
  const { data: configData } = useConfig();
  const saveMutation = useSaveConfig();
  const refreshMutation = useRefreshProviderMetadata();
  const clearCacheMutation = useClearProviderCache();

  // 当打开模型列表时，加载已保存的启用模型
  useEffect(() => {
    if (showModels && configData?.config) {
      const providerConfig = configData.config.llm.providers[providerId];
      const enabledModels = providerConfig?.enabled_models || [];

      // 如果没有保存过，默认全选
      if (enabledModels.length === 0 && metadata?.models) {
        const allModelIds = Object.keys(metadata.models);
        setSelectedModels(allModelIds);
      } else {
        setSelectedModels(enabledModels);
      }
      setHasChanges(false);
    }
  }, [showModels, configData, providerId, metadata]);

  // 获取已启用的模型数量
  const getEnabledModelsCount = () => {
    if (!configData?.config || !metadata?.models) return 0;

    const providerConfig = configData.config.llm.providers[providerId];
    const enabledModels = providerConfig?.enabled_models || [];

    // 如果没有配置，默认全部启用
    if (enabledModels.length === 0) {
      return Object.keys(metadata.models).length;
    }

    return enabledModels.length;
  };

  const handleRefresh = async () => {
    try {
      await refreshMutation.mutateAsync(providerId);
      message.success(`已刷新 ${providerId} 元数据`);
      refetch();
    } catch (error) {
      message.error(`刷新失败: ${error}`);
    }
  };

  const handleClearCache = async () => {
    try {
      await clearCacheMutation.mutateAsync(providerId);
      message.success(`已清除 ${providerId} 缓存`);
      refetch();
    } catch (error) {
      message.error(`清除缓存失败: ${error}`);
    }
  };

  // 处理模型选择变化
  const handleModelToggle = (modelId: string, checked: boolean) => {
    setSelectedModels((prev) => {
      const newSelected = checked
        ? [...prev, modelId]
        : prev.filter((id) => id !== modelId);
      setHasChanges(true);
      return newSelected;
    });
  };

  // 全选/取消全选
  const handleSelectAll = (checked: boolean) => {
    if (checked && metadata?.models) {
      setSelectedModels(Object.keys(metadata.models));
    } else {
      setSelectedModels([]);
    }
    setHasChanges(true);
  };

  // 保存启用的模型列表
  const handleSaveEnabledModels = async () => {
    if (!configData?.config) return;

    if (selectedModels.length === 0) {
      message.warning('至少需要选择一个模型');
      return;
    }

    try {
      const updatedConfig = {
        ...configData.config,
        llm: {
          ...configData.config.llm,
          providers: {
            ...configData.config.llm.providers,
            [providerId]: {
              ...(configData.config.llm.providers[providerId] || {}),
              enabled_models: selectedModels,
            },
          },
        },
      };

      await saveMutation.mutateAsync(updatedConfig);
      message.success('已保存模型选择');
      setHasChanges(false);
      setShowModels(false); // 保存成功后自动关闭弹窗
    } catch (error) {
      message.error(`保存失败: ${error}`);
    }
  };

  if (isLoading) {
    return (
      <Card size="small" style={{ marginBottom: 16 }}>
        <Spin />
      </Card>
    );
  }

  if (!metadata) {
    return (
      <Card
        size="small"
        title={providerId}
        style={{ marginBottom: 16 }}
        extra={
          <Tooltip title="刷新元数据">
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={handleRefresh}
              loading={refreshMutation.isPending}
            />
          </Tooltip>
        }
      >
        <Text type="secondary">无法加载元数据</Text>
      </Card>
    );
  }

  const models = metadata.models
    ? Object.entries(metadata.models as Record<string, any>).map(([id, model]) => ({
        id,
        ...model,
      }))
    : [];

  return (
    <>
      <Card
        size="small"
        title={
          <Space>
            <Text strong>{metadata.name}</Text>
            {isCached ? (
              <Tag icon={<CheckCircleOutlined />} color="success">
                已缓存
              </Tag>
            ) : (
              <Tag icon={<CloseCircleOutlined />} color="default">
                未缓存
              </Tag>
            )}
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="刷新元数据">
              <Button
                size="small"
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
                loading={refreshMutation.isPending}
              />
            </Tooltip>
            <Popconfirm
              title="确定清除缓存？"
              onConfirm={handleClearCache}
              okText="确定"
              cancelText="取消"
            >
              <Tooltip title="清除缓存">
                <Button
                  size="small"
                  icon={<ClearOutlined />}
                  loading={clearCacheMutation.isPending}
                />
              </Tooltip>
            </Popconfirm>
          </Space>
        }
        style={{ marginBottom: 16 }}
      >
        <Descriptions size="small" column={2}>
          <Descriptions.Item label="提供商 ID">{metadata.provider_id}</Descriptions.Item>
          <Descriptions.Item label="Base URL">{metadata.base_url || '未配置'}</Descriptions.Item>
          <Descriptions.Item label="可用模型数">
            {getEnabledModelsCount()}/{models.length}
          </Descriptions.Item>
          <Descriptions.Item label="操作">
            <Button type="link" size="small" onClick={() => setShowModels(true)}>
              选择可用模型
            </Button>
          </Descriptions.Item>
        </Descriptions>

        {metadata.description && (
          <Paragraph
            type="secondary"
            ellipsis={{ rows: 2, expandable: true }}
            style={{ marginTop: 8, marginBottom: 0 }}
          >
            {metadata.description}
          </Paragraph>
        )}
      </Card>

      {/* 模型列表对话框 */}
      <Modal
        title={`${metadata.name} - 支持的模型`}
        open={showModels}
        onCancel={() => setShowModels(false)}
        width={800}
        footer={
          <Space>
            <Button onClick={() => setShowModels(false)}>关闭</Button>
            <Button
              type="primary"
              icon={<SaveOutlined />}
              onClick={handleSaveEnabledModels}
              loading={saveMutation.isPending}
              disabled={!hasChanges}
            >
              保存选择
            </Button>
          </Space>
        }
      >
        <Space direction="vertical" style={{ width: '100%' }} size="middle">
          <Alert
            message="模型启用说明"
            description="勾选的模型将在「提供商配置」页面中显示为可选项。至少需要选择一个模型。"
            type="info"
            showIcon
          />

          <Space>
            <Checkbox
              checked={selectedModels.length === models.length && models.length > 0}
              indeterminate={selectedModels.length > 0 && selectedModels.length < models.length}
              onChange={(e) => handleSelectAll(e.target.checked)}
            >
              全选 ({selectedModels.length}/{models.length})
            </Checkbox>
          </Space>

          <List
            dataSource={models}
            renderItem={(model: any) => (
              <List.Item
                extra={
                  <Checkbox
                    checked={selectedModels.includes(model.id)}
                    onChange={(e) => handleModelToggle(model.id, e.target.checked)}
                  />
                }
              >
                <List.Item.Meta
                  title={model.name || model.id}
                  description={
                    <Space direction="vertical" size="small" style={{ width: '100%' }}>
                      {model.description && <Text type="secondary">{model.description}</Text>}
                      <Space wrap>
                        {model.limit?.context && (
                          <Tag>上下文: {model.limit.context.toLocaleString()}</Tag>
                        )}
                        {model.limit?.output && (
                          <Tag>最大输出: {model.limit.output.toLocaleString()}</Tag>
                        )}
                        {model.family && <Tag color="blue">{model.family}</Tag>}
                        {model.knowledge && <Tag color="green">知识截止: {model.knowledge}</Tag>}
                      </Space>
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Space>
      </Modal>
    </>
  );
};

export default ProviderMetadataCard;
