import React, { useEffect, useState } from 'react';
import {
  Form,
  Input,
  Select,
  InputNumber,
  Card,
  Button,
  Space,
  Divider,
  message,
  Spin,
  Alert,
  Tabs,
  Typography,
  Row,
  Col,
  Statistic,
  Popconfirm,
  Tooltip,
} from 'antd';
import {
  ReloadOutlined,
  ClearOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
} from '@ant-design/icons';
import { useConfig, useSaveConfig } from '../../hooks/useConfig';
import { LLM_MODELS } from '../../utils/constants';
import type { AppConfig, LLMProvider } from '../../api/types';
import {
  useProviders,
  useCacheStats,
  useRefreshAllProviders,
  useClearAllCache,
  useTestConnectivity,
} from '../../hooks/useLLMMetadata';
import ProviderMetadataCard from '../../components/ProviderMetadataCard';
import ProviderConfigCard from '../../components/ProviderConfigCard';

const { Text, Title } = Typography;

const LLMSettings: React.FC = () => {
  const [form] = Form.useForm();
  const [activeTab, setActiveTab] = useState('config');
  const [selectedProvider, setSelectedProvider] = useState<string>(''); // 当前选中的提供商
  const [isCustomConnected, setIsCustomConnected] = useState(false); // 自定义提供商连通性状态
  const { data, isLoading } = useConfig();
  const saveMutation = useSaveConfig();

  // LLM 元数据相关
  const { data: providers } = useProviders();
  const { data: cacheStats, isLoading: cacheLoading } = useCacheStats();
  const refreshAllMutation = useRefreshAllProviders();
  const clearAllCacheMutation = useClearAllCache();
  const testConnectivityMutation = useTestConnectivity();

  // 测试自定义提供商连通性
  const handleTestCustomConnectivity = async () => {
    try {
      const providerConfig = form.getFieldValue(['providers', 'custom']) || {};
      const { api_key, api_base, model } = providerConfig;

      if (!api_key || !api_base || !model) {
        message.warning('请先填写 API Key、Base URL 和模型');
        return;
      }

      const result = await testConnectivityMutation.mutateAsync({
        apiKey: api_key,
        apiBase: api_base,
        model: model,
      });

      if (result.success) {
        message.success('连通性测试成功！API 配置正常');
        setIsCustomConnected(true); // 设置为已连通
      } else {
        message.error(result.message || '连通性测试失败');
        setIsCustomConnected(false);
      }
    } catch (error: any) {
      message.error(error.message || '连通性测试失败');
      setIsCustomConnected(false);
    }
  };

  useEffect(() => {
    if (data?.config) {
      const defaultProvider = data.config.llm.default_provider;
      setSelectedProvider(defaultProvider); // 设置选中的提供商

      form.setFieldsValue({
        default_provider: defaultProvider,
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
      // 先获取所有表单值（不验证）
      const values = form.getFieldsValue();
      if (!data?.config) return;

      // 只验证选中的提供商配置
      const providerConfig = values.providers?.[selectedProvider];
      if (!providerConfig) {
        message.error(`请配置 ${selectedProvider} 提供商`);
        return;
      }

      // 验证必填字段
      const requiredFields = ['api_key', 'api_base', 'model', 'max_context', 'max_output'];
      const missingFields = requiredFields.filter((field) => !providerConfig[field]);

      if (missingFields.length > 0) {
        message.error(`${selectedProvider} 配置不完整，请填写: ${missingFields.join(', ')}`);
        return;
      }

      const updated: AppConfig = {
        ...data.config,
        llm: {
          ...data.config.llm,
          call_mode: 'direct', // 默认使用直接 API 调用
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
    } catch (error) {
      message.error(`保存失败: ${error}`);
    }
  };

  const handleRefreshAll = async () => {
    try {
      const results = await refreshAllMutation.mutateAsync();
      const successCount = Object.values(results).filter(Boolean).length;
      const totalCount = Object.keys(results).length;
      message.success(`已刷新 ${successCount}/${totalCount} 个提供商`);
    } catch (error) {
      message.error(`刷新失败: ${error}`);
    }
  };

  const handleClearAllCache = async () => {
    try {
      await clearAllCacheMutation.mutateAsync();
      message.success('已清除所有缓存');
    } catch (error) {
      message.error(`清除缓存失败: ${error}`);
    }
  };

  if (isLoading) return <Spin />;

  // 计算缓存统计
  const cachedCount = cacheStats
    ? Object.values(cacheStats).filter((s) => s.metadata_cached).length
    : 0;
  const totalCount = providers?.length || 0;

  return (
    <div>
      <Tabs
        activeKey={activeTab}
        onChange={setActiveTab}
        items={[
          {
            key: 'config',
            label: '提供商配置',
            children: (
              <Form form={form} layout="vertical">
                <Alert
                  message="提示"
                  description='提供商元数据（Base URL、上下文窗口等）可在"元数据管理"标签页中查看和更新'
                  type="info"
                  icon={<InfoCircleOutlined />}
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                <Form.Item name="default_provider" label="默认 LLM 提供商">
                  <Select
                    options={[
                      ...LLM_MODELS.map((m) => ({ label: m, value: m })),
                      { label: '自定义', value: 'custom' },
                    ]}
                    style={{ width: 200 }}
                    onChange={(value) => setSelectedProvider(value)}
                  />
                </Form.Item>

                <Divider>提供商配置</Divider>

                {selectedProvider && (
                  selectedProvider === 'custom' ? (
                    // 自定义提供商配置（手动输入模型）
                    <Card
                      title={
                        <Space>
                          <span>自定义</span>
                          <Tooltip title="自定义提供商，需手动填写所有配置">
                            <InfoCircleOutlined style={{ color: '#1890ff' }} />
                          </Tooltip>
                        </Space>
                      }
                      extra={
                        <Button
                          type="default"
                          size="small"
                          icon={<ApiOutlined />}
                          onClick={handleTestCustomConnectivity}
                          loading={testConnectivityMutation.isPending}
                          style={isCustomConnected ? { color: '#52c41a' } : {}}
                        >
                          {isCustomConnected ? '可连通' : '连通性测试'}
                        </Button>
                      }
                      size="small"
                      style={{ marginBottom: 16 }}
                    >
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Form.Item
                          name={['providers', 'custom', 'api_key']}
                          label="API Key"
                          style={{ marginBottom: 8 }}
                        >
                          <Input.Password placeholder="输入 API Key" />
                        </Form.Item>

                        <Form.Item
                          name={['providers', 'custom', 'api_base']}
                          label="Base URL"
                          style={{ marginBottom: 8 }}
                        >
                          <Input placeholder="输入 API Base URL" />
                        </Form.Item>

                        <Space wrap>
                          <Form.Item
                            name={['providers', 'custom', 'model']}
                            label="模型"
                            style={{ marginBottom: 8, width: 250 }}
                          >
                            <Input placeholder="输入模型名称" />
                          </Form.Item>

                          <Form.Item
                            name={['providers', 'custom', 'max_context']}
                            label="上下文窗口"
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
                            name={['providers', 'custom', 'max_output']}
                            label="最大输出"
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
                  ) : (
                    // 标准提供商配置（使用 ProviderConfigCard）
                    <ProviderConfigCard
                      key={selectedProvider}
                      providerId={selectedProvider}
                      providerName={selectedProvider}
                    />
                  )
                )}

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
            ),
          },
          {
            key: 'metadata',
            label: '元数据管理',
            children: (
              <div>
                <Card size="small" style={{ marginBottom: 16 }}>
                  <Row gutter={16}>
                    <Col span={8}>
                      <Statistic
                        title="支持的提供商"
                        value={totalCount}
                        suffix="个"
                        prefix={<InfoCircleOutlined />}
                      />
                    </Col>
                    <Col span={8}>
                      <Statistic
                        title="已缓存"
                        value={cachedCount}
                        suffix={`/ ${totalCount}`}
                        prefix={<CheckCircleOutlined style={{ color: '#52c41a' }} />}
                        valueStyle={{ color: cachedCount > 0 ? '#52c41a' : undefined }}
                      />
                    </Col>
                    <Col span={8}>
                      <Space>
                        <Button
                          icon={<ReloadOutlined />}
                          onClick={handleRefreshAll}
                          loading={refreshAllMutation.isPending}
                        >
                          刷新所有
                        </Button>
                        <Popconfirm
                          title="确定清除所有缓存？"
                          description="清除后需要重新获取元数据"
                          onConfirm={handleClearAllCache}
                          okText="确定"
                          cancelText="取消"
                        >
                          <Button
                            icon={<ClearOutlined />}
                            loading={clearAllCacheMutation.isPending}
                            danger
                          >
                            清除所有缓存
                          </Button>
                        </Popconfirm>
                      </Space>
                    </Col>
                  </Row>
                </Card>

                <Alert
                  message="关于元数据"
                  description={
                    <>
                      <p>
                        元数据包含提供商的 Base URL、上下文窗口、最大输出等配置信息。
                      </p>
                      <p>
                        数据来源：
                        <a
                          href="https://models.dev"
                          target="_blank"
                          rel="noopener noreferrer"
                        >
                          https://models.dev
                        </a>
                        （MIT License）
                      </p>
                      <p>元数据会自动缓存 30 天，可手动刷新或清除缓存。</p>
                    </>
                  }
                  type="info"
                  showIcon
                  style={{ marginBottom: 16 }}
                />

                {cacheLoading ? (
                  <Spin />
                ) : (
                  <>
                    {providers?.map((providerId) => (
                      <ProviderMetadataCard
                        key={providerId}
                        providerId={providerId}
                        isCached={cacheStats?.[providerId]?.metadata_cached}
                      />
                    ))}
                  </>
                )}
              </div>
            ),
          },
        ]}
      />
    </div>
  );
};

export default LLMSettings;
