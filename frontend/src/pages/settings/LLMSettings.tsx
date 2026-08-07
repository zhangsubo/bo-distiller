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
  Modal,
} from 'antd';
import {
  ReloadOutlined,
  ClearOutlined,
  InfoCircleOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ApiOutlined,
  PlusOutlined,
  QuestionCircleOutlined,
} from '@ant-design/icons';
import { useConfig, useSaveConfig } from '../../hooks/useConfig';
import type { AppConfig, LLMProvider } from '../../api/types';
import {
  useProviders,
  useCacheStats,
  useRefreshAllProviders,
  useClearAllCache,
  useTestConnectivity,
  useAddProvider,
  useDeleteProvider,
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
  const addProviderMutation = useAddProvider();
  const deleteProviderMutation = useDeleteProvider();

  // 添加提供商弹窗状态
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newProviderId, setNewProviderId] = useState('');

  // 处理参数说明弹窗状态
  const [isParamsHelpOpen, setIsParamsHelpOpen] = useState(false);

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
        max_concurrent: data.config.processing.max_concurrent,
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
          max_concurrent: values.max_concurrent,
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

  // 添加提供商
  const handleAddProvider = async () => {
    if (!newProviderId.trim()) {
      message.warning('请输入 Provider ID');
      return;
    }

    try {
      const result = await addProviderMutation.mutateAsync(newProviderId.trim());
      message.success(result.message || '添加成功');
      setIsAddModalOpen(false);
      setNewProviderId('');
    } catch (error: any) {
      message.error(error.message || '添加失败');
    }
  };

  // 删除提供商
  const handleDeleteProvider = async (providerId: string) => {
    try {
      const result = await deleteProviderMutation.mutateAsync(providerId);
      message.success(result.message || '删除成功');
    } catch (error: any) {
      message.error(error.message || '删除失败');
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
                      ...(providers || []).map((p) => ({ label: p, value: p })),
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

                <Divider>
                  处理参数
                  <Tooltip title="查看参数详细说明">
                    <Button
                      type="link"
                      icon={<QuestionCircleOutlined />}
                      onClick={() => setIsParamsHelpOpen(true)}
                      style={{ marginLeft: 8 }}
                    />
                  </Tooltip>
                </Divider>

                <Space wrap style={{ alignItems: 'flex-start' }}>
                  <Form.Item name="batch_temperature" label="批次提取温度">
                    <InputNumber min={0} max={1} step={0.1} style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item name="synthesis_temperature" label="整合温度">
                    <InputNumber min={0} max={1} step={0.1} style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item name="safety_margin" label="安全系数">
                    <InputNumber min={0.5} max={1} step={0.05} style={{ width: 120 }} />
                  </Form.Item>
                  <Form.Item name="max_article_length" label="文章截取长度" extra="0=不截断">
                    <InputNumber min={0} step={500} style={{ width: 150 }} />
                  </Form.Item>
                  <Form.Item name="max_concurrent" label="并发处理批次数" extra="同时处理的批次数量（1-10）">
                    <InputNumber min={1} max={10} step={1} style={{ width: 120 }} />
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
                      <Space direction="vertical" style={{ width: '100%' }}>
                        <Button
                          type="primary"
                          icon={<PlusOutlined />}
                          onClick={() => setIsAddModalOpen(true)}
                          block
                        >
                          添加提供商
                        </Button>
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
                        defaultProvider={data?.config?.llm?.default_provider}
                        onDelete={handleDeleteProvider}
                      />
                    ))}
                  </>
                )}

                {/* 添加提供商弹窗 */}
                <Modal
                  title="添加提供商"
                  open={isAddModalOpen}
                  onOk={handleAddProvider}
                  onCancel={() => {
                    setIsAddModalOpen(false);
                    setNewProviderId('');
                  }}
                  confirmLoading={addProviderMutation.isPending}
                  okText="添加"
                  cancelText="取消"
                >
                  <Form layout="vertical" style={{ marginTop: 16 }}>
                    <Form.Item
                      label="Provider ID"
                      required
                      extra={
                        <span>
                          请输入 <a href="https://models.dev" target="_blank" rel="noopener noreferrer">models.dev</a> 中的 Provider ID
                        </span>
                      }
                    >
                      <Input
                        placeholder="例如: openai, anthropic, google"
                        value={newProviderId}
                        onChange={(e) => setNewProviderId(e.target.value)}
                        onPressEnter={handleAddProvider}
                      />
                    </Form.Item>
                  </Form>
                </Modal>
              </div>
            ),
          },
        ]}
      />

      {/* 处理参数说明弹窗 - 移到 Tabs 外部 */}
      <Modal
        title="处理参数详细说明"
        open={isParamsHelpOpen}
        onCancel={() => setIsParamsHelpOpen(false)}
        footer={[
          <Button key="close" type="primary" onClick={() => setIsParamsHelpOpen(false)}>
            关闭
          </Button>
        ]}
        width={800}
      >
        <div style={{ maxHeight: '70vh', overflow: 'auto' }}>
          <Title level={4}>1. 批次提取温度 (batch_temperature)</Title>
          <Text>
            <ul>
              <li><strong>默认值</strong>: 0.3</li>
              <li><strong>范围</strong>: 0.0 - 1.0</li>
              <li><strong>作用</strong>: 控制从文章批次中提取核心观点时的随机性</li>
            </ul>
            <p><strong>含义</strong>:</p>
            <ul>
              <li>温度 = 0: 完全确定性，每次提取的内容几乎一致</li>
              <li>温度较低 (0.1-0.3): 提取结果稳定、聚焦，更倾向于提取明确的核心观点</li>
              <li>温度较高 (0.7-1.0): 提取结果更有创造性和多样性，但可能不够聚焦</li>
            </ul>
            <p><strong>推荐设置</strong>: 0.3（默认）- 保证提取的观点准确且聚焦</p>
          </Text>

          <Divider />

          <Title level={4}>2. 整合温度 (synthesis_temperature)</Title>
          <Text>
            <ul>
              <li><strong>默认值</strong>: 0.2</li>
              <li><strong>范围</strong>: 0.0 - 1.0</li>
              <li><strong>作用</strong>: 控制整合多个批次结果时的随机性</li>
            </ul>
            <p><strong>含义</strong>:</p>
            <ul>
              <li>温度 = 0: 整合结果高度一致，严格按照原文归纳</li>
              <li>温度较低 (0.1-0.3): 整合结果稳定、严谨，更忠实于原文</li>
              <li>温度较高 (0.7-1.0): 整合时有更多创造性，可能产生新的见解</li>
            </ul>
            <p><strong>为什么比批次提取温度更低？</strong></p>
            <p>批次提取是从原文提取观点（允许一定灵活性），整合是汇总已提取的观点（需要更高准确性）。</p>
            <p><strong>推荐设置</strong>: 0.2（默认）- 确保最终文档的一致性和准确性</p>
          </Text>

          <Divider />

          <Title level={4}>3. 安全系数 (safety_margin)</Title>
          <Text>
            <ul>
              <li><strong>默认值</strong>: 0.9</li>
              <li><strong>范围</strong>: 0.5 - 1.0</li>
              <li><strong>作用</strong>: 控制上下文窗口的使用率，防止超出 token 限制</li>
            </ul>
            <p><strong>计算公式</strong>:</p>
            <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
              可用 tokens = (最大上下文 - 最大输出 - 预留 tokens) × 安全系数
            </pre>
            <p><strong>不同设置的影响</strong>:</p>
            <ul>
              <li>0.9 (推荐): 留 10% 余量，非常安全，适合大多数场景</li>
              <li>0.95: 留 5% 余量，更充分利用上下文，但风险略高</li>
              <li>0.8: 留 20% 余量，非常保守，适合不稳定的 API</li>
            </ul>
            <p><strong>为什么需要安全系数？</strong></p>
            <p>Token 计数可能不完全准确，不同模型的 token 化方式有差异，避免因超出限制导致 API 调用失败。</p>
          </Text>

          <Divider />

          <Title level={4}>4. 文章截取长度 (max_article_length)</Title>
          <Text>
            <ul>
              <li><strong>默认值</strong>: 0</li>
              <li><strong>范围</strong>: 0 或任意正整数</li>
              <li><strong>作用</strong>: 限制每篇文章的最大字符数，0 表示不截断</li>
            </ul>
            <p><strong>使用场景</strong>:</p>
            <ul>
              <li><strong>0 (不截断)</strong>: 使用文章完整内容，不丢失任何信息</li>
              <li><strong>3000</strong>: 只使用文章前 3000 个字符，快速处理</li>
              <li><strong>5000</strong>: 只使用文章前 5000 个字符，平衡完整性和速度</li>
            </ul>
            <p><strong>推荐设置</strong>: 0（默认）- 除非遇到超长文章问题</p>
          </Text>

          <Divider />

          <Title level={4}>5. 并发处理批次数 (max_concurrent)</Title>
          <Text>
            <ul>
              <li><strong>默认值</strong>: 3</li>
              <li><strong>范围</strong>: 1 - 10</li>
              <li><strong>作用</strong>: 同时处理的批次数量</li>
            </ul>
            <p><strong>速度对比</strong>（假设 30 个批次，每批次 10 秒）:</p>
            <ul>
              <li>并发数 = 1: 300 秒 (5 分钟) - 串行处理</li>
              <li>并发数 = 3: 100 秒 (1.6 分钟) - 默认推荐</li>
              <li>并发数 = 5: 60 秒 (1 分钟) - 高速处理</li>
              <li>并发数 = 10: 30 秒 - 最高并发</li>
            </ul>
            <p><strong>不同场景建议</strong>:</p>
            <ul>
              <li><strong>1</strong>: API 有严格速率限制</li>
              <li><strong>3</strong>: 默认推荐，适合大多数场景</li>
              <li><strong>5-10</strong>: 本地模型或无限制 API</li>
            </ul>
            <p><strong>注意</strong>: 并发数过高可能触发 API 速率限制（429 错误）</p>
          </Text>

          <Divider />

          <Title level={4}>参数组合建议</Title>
          <Text>
            <p><strong>追求准确性（默认推荐）</strong>:</p>
            <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
              批次提取温度: 0.3{'\n'}
              整合温度: 0.2{'\n'}
              安全系数: 0.9{'\n'}
              文章截取长度: 0{'\n'}
              并发处理批次数: 3
            </pre>

            <p><strong>追求速度</strong>:</p>
            <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
              批次提取温度: 0.3{'\n'}
              整合温度: 0.2{'\n'}
              安全系数: 0.9{'\n'}
              文章截取长度: 3000 (截取文章){'\n'}
              并发处理批次数: 5 (提高并发)
            </pre>

            <p><strong>API 限制严格</strong>:</p>
            <pre style={{ background: '#f5f5f5', padding: 8, borderRadius: 4 }}>
              批次提取温度: 0.3{'\n'}
              整合温度: 0.2{'\n'}
              安全系数: 0.8 (更保守){'\n'}
              文章截取长度: 0{'\n'}
              并发处理批次数: 1 (串行处理)
            </pre>
          </Text>
        </div>
      </Modal>
    </div>
  );
};

export default LLMSettings;
