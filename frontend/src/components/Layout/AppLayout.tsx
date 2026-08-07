import React from 'react';
import { Layout, Menu, Segmented } from 'antd';
import {
  DatabaseOutlined,
  ImportOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAppStore, THEME_OPTIONS } from '../../stores/appStore';
import type { AppTheme } from '../../stores/appStore';

const { Sider, Content, Header } = Layout;

const menuItems = [
  {
    key: 'input',
    icon: <ImportOutlined />,
    label: '输入采集',
    children: [
      { key: '/articles', label: 'Cubox' },
    ],
  },
  { key: '/distill', icon: <ThunderboltOutlined />, label: '蒸馏进度' },
  { key: '/knowledge', icon: <BookOutlined />, label: '知识库' },
  { key: '/settings', icon: <SettingOutlined />, label: '设置' },
];

const allLeafKeys = ['/articles', '/distill', '/knowledge', '/settings'];

const AppLayout: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const collapsed = useAppStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useAppStore((s) => s.toggleSidebar);
  const theme = useAppStore((s) => s.theme);
  const setTheme = useAppStore((s) => s.setTheme);

  const selectedKey = allLeafKeys.find((key) =>
    location.pathname.startsWith(key),
  ) || '/articles';

  const openKeys = location.pathname.startsWith('/articles') ? ['input'] : [];

  const menuTheme = theme === 'editorial' ? 'light' : 'dark';

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={toggleSidebar}
        theme={menuTheme}
        width={200}
        className="app-sider"
      >
        <div
          className="app-logo"
          style={{
            height: 48,
            margin: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontWeight: 600,
            fontSize: collapsed ? 14 : 16,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? 'BD' : 'Bo-Distiller'}
        </div>
        <Menu
          theme={menuTheme}
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={({ key }) => {
            if (allLeafKeys.includes(key)) {
              navigate(key);
            }
          }}
        />
      </Sider>
      <Layout>
        <Header
          className="app-header"
          style={{
            padding: '0 24px',
            display: 'flex',
            alignItems: 'center',
            height: 48,
          }}
        >
          <span style={{ fontSize: 14, color: 'var(--theme-text-secondary)' }}>
            智能内容蒸馏工具
          </span>
          <Segmented
            style={{ marginLeft: 'auto' }}
            options={THEME_OPTIONS}
            value={theme}
            onChange={(v) => setTheme(v as AppTheme)}
          />
        </Header>
        <Content
          className="app-content"
          style={{ margin: 16, padding: 24, overflow: 'auto' }}
        >
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
