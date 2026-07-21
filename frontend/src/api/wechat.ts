import client from './client';
import type { WeChatConfig, WeChatStatus, WeChatStats } from './types';

export async function fetchWeChatStatus(): Promise<WeChatStatus> {
  return client.get('/wechat/status');
}

export async function fetchWeChatConfig(): Promise<{ config: WeChatConfig }> {
  return client.get('/wechat/config');
}

export async function saveWeChatConfig(
  config: WeChatConfig,
): Promise<{ status: string }> {
  return client.post('/wechat/config', config);
}

export async function backfillWeChat(): Promise<{ enqueued: number; stats: WeChatStats }> {
  return client.post('/wechat/backfill');
}

export async function retryFailedWeChat(): Promise<{ reset: number }> {
  return client.post('/wechat/retry-failed');
}
