import React, { Suspense, lazy } from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { Spin } from 'antd';
import AppLayout from './components/Layout/AppLayout';

const ArticlesPage = lazy(() => import('./pages/articles/index'));
const ArticleDetail = lazy(() => import('./pages/articles/ArticleDetail'));
const SettingsPage = lazy(() => import('./pages/settings/index'));
const DistillPage = lazy(() => import('./pages/distill/index'));
const KnowledgePage = lazy(() => import('./pages/knowledge/index'));
const KnowledgeViewer = lazy(() => import('./pages/knowledge/KnowledgeViewer'));

const Loading = (
  <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
    <Spin size="large" />
  </div>
);

const App: React.FC = () => {
  return (
    <Suspense fallback={Loading}>
      <Routes>
        <Route element={<AppLayout />}>
          <Route path="/" element={<Navigate to="/articles" replace />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/articles/:id" element={<ArticleDetail />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="/distill" element={<DistillPage />} />
          <Route path="/knowledge" element={<KnowledgePage />} />
          <Route path="/knowledge/:name" element={<KnowledgeViewer />} />
        </Route>
      </Routes>
    </Suspense>
  );
};

export default App;
