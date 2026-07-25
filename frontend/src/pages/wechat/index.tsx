import React, { useState, useEffect } from 'react';
import {
  Card,
  Input,
  Button,
  Table,
  Space,
  message,
  Statistic,
  Row,
  Col,
  Alert,
  Tag,
  Modal,
  InputNumber,
  Divider,
} from 'antd';
import {
  SearchOutlined,
  DownloadOutlined,
  SyncOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  ReloadOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';
import {
  getLoginStatus,
  searchAccounts,
  syncArticles,
  startDownload,
  getDownloadStats,
  retryFailed,
  AccountInfo,
  DownloadStats,
  LoginStatus,
} from '../../api/wechatNative';

const { Search } = Input;

const WechatNativePage: React.FC = () => {
  const [loginStatus, setLoginStatus] = useState<LoginStatus | null>(null);
  const [loading, setLoading] = useState(false);
  const [searchLoading, setSearchLoading] = useState(false);
  const [syncLoading, setSyncLoading] = useState(false);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const [accounts, setAccounts] = useState<AccountInfo[]>([]);
  const [stats, setStats] = useState<DownloadStats | null>(null);
  const [selectedAccount, setSelectedAccount] = useState<AccountInfo | null>(null);
  const [maxArticles, setMaxArticles] = useState<number | undefined>(undefined);
  const [downloadLimit, setDownloadLimit] = useState<number | undefined>(undefined);

  // 加载登录状态
  const loadLoginStatus = async () => {
    try {
      const status = await getLoginStatus();
      setLoginStatus(status);
    } catch (error) {
      console.error('Failed to load login status:', error);
    }
  };

  // 加载下载统计
  const loadStats = async () => {
    try {
      const data = await getDownloadStats();
      setStats(data);
    } catch (error) {
      console.error('Failed to load stats:', error);
    }
  };

  useEffect(() => {
    loadLoginStatus();
    loadStats();

    // 定期刷新统计
    const interval = setInterval(loadStats, 5000);
    return () => clearInterval(interval);
  }, []);

  // 搜索公众号
  const handleSearch = async (keyword: string) => {
    if (!keyword.trim()) {
      message.warning('请输入公众号名称');
      return;
    }

    setSearchLoading(true);
    try {
      const results = await searchAccounts(keyword);
      setAccounts(results);
      if (results.length === 0) {
        message.info('未找到匹配的公众号');
      } else {
        message.success(`找到 ${results.length} 个公众号`);
      }
    } catch (error: any) {
      message.error(error.response?.data?.detail || '搜索失败');
    } finally {
      setSearchLoading(false);
    }
  };

  // 同步文章列表
  const handleSync = async (account: AccountInfo) => {
    setSelectedAccount(account);
    setSyncLoading(true);
    try {
      const result = await syncArticles(account.fakeid, account.nickname, maxArticles);
      message.success(result.message);
      await loadStats();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '同步失败');
    } finally {
      setSyncLoading(false);
      setSelectedAccount(null);
    }
  };

  // 开始下载
  const handleDownload = async () => {
    setDownloadLoading(true);
    try {
      const result = await startDownload(downloadLimit);
      message.success(result.message);
      setTimeout(loadStats, 2000);
    } catch (error: any) {
      message.error(error.response?.data?.detail || '下载失败');
    } finally {
      setDownloadLoading(false);
    }
  };

  // 重试失败
  const handleRetryFailed = async () => {
    try {
      const result = await retryFailed();
      message.success(result.message);
      await loadStats();
    } catch (error: any) {
      message.error(error.response?.data?.detail || '重试失败');
    }
  };

  // 公众号列表列定义
  const columns = [
    {
      title: '公众号',
      dataIndex: 'nickname',
      key: 'nickname',
      render: (text: string, record: AccountInfo) => (
        <div>
          <div style={{ fontWeight: 500 }}>{text}</div>
          {record.alias && <div style={{ fontSize: 12, color: '#999' }}>@{record.alias}</div>}
        </div>
      ),
    },
    {
      title: '简介',
      dataIndex: 'signature',
      key: 'signature',
      ellipsis: true,
    },
    {
      title: '操作',
      key: 'action',
      width: 120,
      render: (_: any, record: AccountInfo) => (
        <Button
          type="primary"
          size="small"
          icon={<SyncOutlined />}
          loading={syncLoading && selectedAccount?.fakeid === record.fakeid}
          onClick={() => handleSync(record)}
        >
          同步
        </Button>
      ),
    },
  ];

  return (
    <div style={{ padding: '24px' }}>
      <Card title="微信公众号本地化下载工具" style={{ marginBottom: 16 }}>
        {/* 登录状态 */}
        {loginStatus && (
          <Alert
            message={
              loginStatus.authenticated ? (
                <span>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  已登录
                </span>
              ) : (
                <span>
                  <CloseCircleOutlined style={{ color: '#ff4d4f', marginRight: 8 }} />
                  {loginStatus.message}
                </span>
              )
            }
            type={loginStatus.authenticated ? 'success' : 'warning'}
            description={
              loginStatus.authenticated ? (
                '认证有效，可以使用所有功能'
              ) : (
                <div>
                  <p>请使用 CLI 命令登录：</p>
                  <code>./venv/bin/python cli/wechat_native.py login</code>
                </div>
              )
            }
            style={{ marginBottom: 16 }}
          />
        )}

        {/* 下载统计 */}
        {stats && (
          <Row gutter={16} style={{ marginBottom: 24 }}>
            <Col span={6}>
              <Card>
                <Statistic title="总数" value={stats.total} />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="待下载"
                  value={stats.pending}
                  valueStyle={{ color: '#1890ff' }}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="已完成"
                  value={stats.done}
                  valueStyle={{ color: '#52c41a' }}
                  prefix={<CheckCircleOutlined />}
                />
              </Card>
            </Col>
            <Col span={6}>
              <Card>
                <Statistic
                  title="失败"
                  value={stats.failed}
                  valueStyle={{ color: '#ff4d4f' }}
                  prefix={<CloseCircleOutlined />}
                />
              </Card>
            </Col>
          </Row>
        )}

        <Divider />

        {/* 搜索公众号 */}
        <div style={{ marginBottom: 16 }}>
          <Search
            placeholder="输入公众号名称搜索"
            enterButton={<><SearchOutlined /> 搜索</>}
            size="large"
            onSearch={handleSearch}
            loading={searchLoading}
            disabled={!loginStatus?.authenticated}
          />
          <div style={{ marginTop: 8, fontSize: 12, color: '#999' }}>
            <InfoCircleOutlined /> 搜索前请确保已通过 CLI 登录
          </div>
        </div>

        {/* 同步选项 */}
        {accounts.length > 0 && (
          <div style={{ marginBottom: 16 }}>
            <Space>
              <span>同步限制：</span>
              <InputNumber
                min={1}
                max={1000}
                placeholder="不限制"
                value={maxArticles}
                onChange={(value) => setMaxArticles(value || undefined)}
                style={{ width: 150 }}
              />
              <span>篇</span>
            </Space>
          </div>
        )}

        {/* 公众号列表 */}
        {accounts.length > 0 && (
          <Table
            columns={columns}
            dataSource={accounts}
            rowKey="fakeid"
            pagination={false}
            style={{ marginBottom: 16 }}
          />
        )}

        <Divider />

        {/* 下载操作 */}
        <Space size="large">
          <Space>
            <Button
              type="primary"
              icon={<DownloadOutlined />}
              size="large"
              loading={downloadLoading}
              disabled={!loginStatus?.authenticated || !stats || stats.pending === 0}
              onClick={handleDownload}
            >
              开始下载
            </Button>
            <InputNumber
              min={1}
              max={1000}
              placeholder="不限制"
              value={downloadLimit}
              onChange={(value) => setDownloadLimit(value || undefined)}
              style={{ width: 150 }}
              addonBefore="限制"
              addonAfter="篇"
            />
          </Space>

          <Button
            icon={<ReloadOutlined />}
            size="large"
            disabled={!stats || stats.failed === 0}
            onClick={handleRetryFailed}
          >
            重试失败 ({stats?.failed || 0})
          </Button>

          <Button icon={<SyncOutlined />} size="large" onClick={loadStats}>
            刷新统计
          </Button>
        </Space>
      </Card>

      {/* 使用说明 */}
      <Card title="使用说明" style={{ marginTop: 16 }}>
        <div style={{ lineHeight: 2 }}>
          <h4>1. 首次使用</h4>
          <p>请先在终端运行登录命令（一次性，7天有效）：</p>
          <code style={{ background: '#f5f5f5', padding: '4px 8px', borderRadius: 4 }}>
            ./venv/bin/python cli/wechat_native.py login
          </code>

          <h4 style={{ marginTop: 16 }}>2. 同步文章列表</h4>
          <p>在搜索框输入公众号名称，选择目标公众号点击"同步"按钮</p>

          <h4 style={{ marginTop: 16 }}>3. 下载文章</h4>
          <p>点击"开始下载"按钮，系统会自动下载待处理的文章</p>

          <h4 style={{ marginTop: 16 }}>核心优势</h4>
          <ul>
            <li>✅ 完全本地化，无需第三方 API</li>
            <li>✅ 更高限速（60+次/分钟）</li>
            <li>✅ 功能完整（搜索+列表+下载）</li>
            <li>✅ 断点续传，自动限速</li>
          </ul>
        </div>
      </Card>
    </div>
  );
};

export default WechatNativePage;
