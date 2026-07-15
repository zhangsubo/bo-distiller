import client from './client';
import type { AppConfig, TopicsConfig, SourceConfig } from './types';

export async function fetchConfig(): Promise<{ config: AppConfig }> {
  return client.get('/config');
}

export async function saveConfig(config: AppConfig): Promise<void> {
  return client.post('/config', config);
}

export async function fetchSources(): Promise<{ sources: SourceConfig[] }> {
  return client.get('/sources');
}

export async function saveSources(sources: SourceConfig[]): Promise<void> {
  return client.post('/sources', { sources });
}

export async function fetchTopicsConfig(): Promise<{ config: TopicsConfig }> {
  return client.get('/topics/config');
}

export async function saveTopicsConfig(config: TopicsConfig): Promise<void> {
  return client.post('/topics/config', config);
}
