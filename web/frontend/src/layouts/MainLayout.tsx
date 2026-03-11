import React, { useEffect, useState } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { Layout, Menu, theme, Dropdown, Button, Space, Avatar } from 'antd';
import {
  DashboardOutlined,
  FileTextOutlined,
  SettingOutlined,
  MonitorOutlined,
  SendOutlined,
  UserOutlined,
  LogoutOutlined,
  ExperimentOutlined,
  HistoryOutlined,
  FileSearchOutlined,
  CloudUploadOutlined,
} from '@ant-design/icons';
import { useAuthStore } from '../stores/authStore';
import type { MenuProps } from 'antd';

const { Header, Sider, Content } = Layout;

const menuItems: MenuProps['items'] = [
  { key: '/', icon: <DashboardOutlined />, label: '工作台' },
  {
    key: 'content', icon: <FileTextOutlined />, label: '内容管理',
    children: [
      { key: '/articles', icon: <FileTextOutlined />, label: '每日文章' },
      { key: '/articles/deep', icon: <ExperimentOutlined />, label: '深度分析' },
    ],
  },
  { key: '/config', icon: <SettingOutlined />, label: '系统配置' },
  {
    key: 'monitor', icon: <MonitorOutlined />, label: '系统监控',
    children: [
      { key: '/monitor', icon: <MonitorOutlined />, label: '运行状态' },
      { key: '/monitor/logs', icon: <FileSearchOutlined />, label: '实时日志' },
      { key: '/monitor/history', icon: <HistoryOutlined />, label: '任务历史' },
    ],
  },
  {
    key: 'publish', icon: <SendOutlined />, label: '发布管理',
    children: [
      { key: '/publish', icon: <CloudUploadOutlined />, label: '草稿管理' },
      { key: '/publish/history', icon: <HistoryOutlined />, label: '发布历史' },
    ],
  },
];

const MainLayout: React.FC = () => {
  const [collapsed, setCollapsed] = useState(false);
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout } = useAuthStore();
  const { token: { colorBgContainer, borderRadiusLG } } = theme.useToken();

  const handleMenuClick: MenuProps['onClick'] = ({ key }) => {
    navigate(key);
  };

  const userMenuItems: MenuProps['items'] = [
    { key: 'user', icon: <UserOutlined />, label: user?.username || '用户', disabled: true },
    { type: 'divider' },
    {
      key: 'logout', icon: <LogoutOutlined />, label: '退出登录',
      onClick: async () => { await logout(); navigate('/login'); },
    },
  ];

  // 计算当前选中的菜单
  const selectedKey = location.pathname === '/' ? '/' : location.pathname;

  // 计算展开的子菜单
  const openKeys = [];
  if (location.pathname.startsWith('/articles')) openKeys.push('content');
  if (location.pathname.startsWith('/monitor')) openKeys.push('monitor');
  if (location.pathname.startsWith('/publish')) openKeys.push('publish');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider collapsible collapsed={collapsed} onCollapse={setCollapsed} theme="dark">
        <div style={{
          height: 64, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: '#fff', fontWeight: 'bold', fontSize: collapsed ? 14 : 16,
        }}>
          {collapsed ? 'AI' : 'AI 日报管理'}
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          defaultOpenKeys={openKeys}
          items={menuItems}
          onClick={handleMenuClick}
        />
      </Sider>
      <Layout>
        <Header style={{
          padding: '0 24px', background: colorBgContainer,
          display: 'flex', justifyContent: 'flex-end', alignItems: 'center',
        }}>
          <Dropdown menu={{ items: userMenuItems }} placement="bottomRight">
            <Space style={{ cursor: 'pointer' }}>
              <Avatar icon={<UserOutlined />} size="small" />
              <span>{user?.username}</span>
            </Space>
          </Dropdown>
        </Header>
        <Content style={{ margin: 16 }}>
          <div style={{
            padding: 24, minHeight: 360,
            background: colorBgContainer, borderRadius: borderRadiusLG,
          }}>
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
};

export default MainLayout;
