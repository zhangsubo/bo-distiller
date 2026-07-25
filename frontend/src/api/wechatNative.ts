/**
 * 微信本地化下载 API 客户端
 */

import axios from './client';

export interface LoginStatus {
  authenticated: boolean;
  message: string;
  cookie_file?: string;
}

export interface AccountInfo {
  fakeid: string;
  nickname: string;
  alias: string;
  signature: string;
}

export interface DownloadStats {
  total: number;
  pending: number;
  downloading: number;
  done: number;
  failed: number;
}

/**
 * 获取登录状态
 */
export const getLoginStatus = async (): Promise<LoginStatus> => {
  const { data } = await axios.get('/api/wechat-native/status');
  return data;
};

/**
 * 搜索公众号
 */
export const searchAccounts = async (keyword: string): Promise<AccountInfo[]> => {
  const { data } = await axios.post('/api/wechat-native/search', { keyword });
  return data.accounts;
};

/**
 * 同步公众号文章列表
 */
export const syncArticles = async (
  fakeid: string,
  nickname: string,
  maxArticles?: number
): Promise<{ synced: number; message: string }> => {
  const { data } = await axios.post('/api/wechat-native/sync', {
    fakeid,
    nickname,
    max_articles: maxArticles,
  });
  return data;
};

/**
 * 开始下载文章
 */
export const startDownload = async (limit?: number): Promise<{ status: string; message: string }> => {
  const { data } = await axios.post('/api/wechat-native/download', { limit });
  return data;
};

/**
 * 获取下载统计
 */
export const getDownloadStats = async (): Promise<DownloadStats> => {
  const { data } = await axios.get('/api/wechat-native/stats');
  return data;
};

/**
 * 重试失败的下载
 */
export const retryFailed = async (): Promise<{ reset: number; message: string }> => {
  const { data } = await axios.post('/api/wechat-native/retry-failed');
  return data;
};

/**
 * 获取配置
 */
export const getConfig = async (): Promise<any> => {
  const { data } = await axios.get('/api/wechat-native/config');
  return data.config;
};

/**
 * 更新配置
 */
export const updateConfig = async (config: any): Promise<{ status: string; message: string }> => {
  const { data } = await axios.post('/api/wechat-native/config', config);
  return data;
};
