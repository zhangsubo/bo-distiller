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

export async function syncCubox(): Promise<{ status: string; message: string; count: number }> {
  return client.post('/articles/sync');
}
