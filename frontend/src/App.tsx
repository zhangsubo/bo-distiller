import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider, Spin } from 'antd';
import type { ThemeConfig } from 'antd';
import AppLayout from './components/Layout/AppLayout';
import { useAppStore } from './stores/appStore';
import type { AppTheme } from './stores/appStore';

const THEME_TOKENS: Record<AppTheme, ThemeConfig> = {
  classic: {},
  neubrutalism: {
    token: {
      colorPrimary: '#2196f3',
      borderRadius: 0,
      fontFamily: "'Helvetica Neue', Arial, sans-serif",
    },
  },
  editorial: {
    token: {
      colorPrimary: '#b03a2e',
      borderRadius: 2,
      fontFamily: "Georgia, 'Times New Roman', 'Songti SC', serif",
    },
  },
};

const ArticlesPage = lazy(() => import('./pages/articles/index'));
const ArticleDetail = lazy(() => import('./pages/articles/ArticleDetail'));
const SettingsPage = lazy(() => import('./pages/settings/index'));
const DistillPage = lazy(() => import('./pages/distill/index'));
const KnowledgePage = lazy(() => import('./pages/knowledge/index'));

const Loading = (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <Spin size="large" />
  </div>
);

const App: React.FC = () => {
  const theme = useAppStore((s) => s.theme);
  return (
    <ConfigProvider theme={THEME_TOKENS[theme]}>
      <Suspense fallback={Loading}>
        <Routes>
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/articles" replace />} />
            <Route path="/articles" element={<ArticlesPage />} />
            <Route path="/articles/:id" element={<ArticleDetail />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/distill" element={<DistillPage />} />
            <Route path="/knowledge" element={<KnowledgePage />} />
            <Route path="/knowledge/:name" element={<KnowledgePage />} />
          </Route>
        </Routes>
      </Suspense>
    </ConfigProvider>
  );
};

export default App;
