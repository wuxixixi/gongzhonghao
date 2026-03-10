import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import MainLayout from './layouts/MainLayout';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import ArticleList from './pages/articles/ArticleList';
import ArticleDetail from './pages/articles/ArticleDetail';
import ArticleEditor from './pages/articles/ArticleEditor';
import DeepAnalysisList from './pages/articles/DeepAnalysisList';
import ConfigPanel from './pages/config/ConfigPanel';
import SystemStatus from './pages/monitor/SystemStatus';
import LogViewer from './pages/monitor/LogViewer';
import TaskHistory from './pages/monitor/TaskHistory';
import DraftManager from './pages/publish/DraftManager';
import PublishHistory from './pages/publish/PublishHistory';
import { useAuthStore } from './stores/authStore';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  if (!isAuthenticated) return <Navigate to="/login" replace />;
  return <>{children}</>;
};

const App: React.FC = () => {
  const checkAuth = useAuthStore((s) => s.checkAuth);

  useEffect(() => {
    checkAuth();
  }, []);

  return (
    <ConfigProvider locale={zhCN} theme={{ token: { colorPrimary: '#1677ff' } }}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/" element={<ProtectedRoute><MainLayout /></ProtectedRoute>}>
            <Route index element={<Dashboard />} />
            <Route path="articles" element={<ArticleList />} />
            <Route path="articles/deep" element={<DeepAnalysisList />} />
            <Route path="articles/:date" element={<ArticleDetail />} />
            <Route path="articles/:date/edit" element={<ArticleEditor />} />
            <Route path="config" element={<ConfigPanel />} />
            <Route path="monitor" element={<SystemStatus />} />
            <Route path="monitor/logs" element={<LogViewer />} />
            <Route path="monitor/history" element={<TaskHistory />} />
            <Route path="publish" element={<DraftManager />} />
            <Route path="publish/history" element={<PublishHistory />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ConfigProvider>
  );
};

export default App;
