import React from 'react';
import { Layout, Menu } from 'antd';
import {
  DatabaseOutlined,
  ImportOutlined,
  SettingOutlined,
  ThunderboltOutlined,
  BookOutlined,
} from '@ant-design/icons';
import { useNavigate, useLocation, Outlet } from 'react-router-dom';
import { useAppStore } from '../../stores/appStore';

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

  const selectedKey = allLeafKeys.find((key) =>
    location.pathname.startsWith(key),
  ) || '/articles';

  const openKeys = location.pathname.startsWith('/articles') ? ['input'] : [];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        collapsible
        collapsed={collapsed}
        onCollapse={toggleSidebar}
        theme="dark"
        width={200}
      >
        <div
          style={{
            height: 48,
            margin: 12,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontWeight: 600,
            fontSize: collapsed ? 14 : 16,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
          }}
        >
          {collapsed ? 'BD' : 'Bo-Distiller'}
        </div>
        <Menu
          theme="dark"
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
          style={{
            padding: '0 24px',
            background: '#fff',
            display: 'flex',
            alignItems: 'center',
            borderBottom: '1px solid #f0f0f0',
            height: 48,
          }}
        >
          <span style={{ fontSize: 14, color: '#666' }}>
            智能内容蒸馏工具
          </span>
        </Header>
        <Content style={{ margin: 16, padding: 24, background: '#fff', borderRadius: 8, overflow: 'auto' }}>
          <Outlet />
        </Content>
      </Layout>
    </Layout>
  );
};

export default AppLayout;
