import client from './client';
import type { ArticleListResponse, Article, ArticleStats } from './types';

export async function fetchArticles(params: {
  page?: number;
  page_size?: number;
  search?: string;
  source_type?: string;
}): Promise<ArticleListResponse> {
  return client.get('/articles', { params });
}

export async function fetchArticle(id: string): Promise<{ data: Article }> {
  return client.get(`/articles/${id}`);
}

export async function deleteArticle(id: string): Promise<void> {
  return client.delete(`/articles/${id}`);
}

export async function fetchArticleStats(): Promise<{ data: ArticleStats }> {
  return client.get('/articles/stats');
}

export async function syncCubox(incremental: boolean = false): Promise<{ status: string; message: string }> {
  return client.post('/articles/sync', null, { params: { incremental } });
}

export async function cancelSyncCubox(): Promise<{ status: string; message: string }> {
  return client.post('/articles/sync/cancel');
}

export async function getSyncStatus(): Promise<{
  running: boolean;
  progress: string;
  total: number;
  processed: number;
  error: string | null;
  last_sync_time: string | null;
}> {
  return client.get('/articles/sync/status');
}
