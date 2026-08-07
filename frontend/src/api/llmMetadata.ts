/**
 * LLM 元数据管理 API
 */

const API_BASE = '';

export interface ProviderMetadata {
  provider_id: string;
  name: string;
  base_url: string | null;
  models: Record<string, any> | any[];
  description?: string;
  full_metadata?: any;
}

export interface ProviderModel {
  id: string;
  object?: string;
  created?: number;
  owned_by?: string;
}

export interface CacheStats {
  [providerId: string]: {
    metadata_cached: boolean;
    models_cached: boolean;
  };
}

/**
 * 获取支持的提供商列表
 */
export async function getProviders(): Promise<string[]> {
  const response = await fetch(`${API_BASE}/api/llm/providers`);
  if (!response.ok) throw new Error('获取提供商列表失败');
  const data = await response.json();
  return data.providers;
}

/**
 * 获取提供商元数据
 */
export async function getProviderMetadata(
  providerId: string,
  forceRefresh = false
): Promise<ProviderMetadata> {
  const url = `${API_BASE}/api/llm/providers/${providerId}/metadata?force_refresh=${forceRefresh}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`获取 ${providerId} 元数据失败`);
  const result = await response.json();
  return result.data;
}

/**
 * 获取提供商模型列表（API Key 由后端从 system_config 读取，不通过 URL 传递）
 */
export async function getProviderModels(
  providerId: string,
  forceRefresh = false
): Promise<ProviderModel[]> {
  const url = `${API_BASE}/api/llm/providers/${providerId}/models?force_refresh=${forceRefresh}`;
  const response = await fetch(url);
  if (!response.ok) throw new Error(`获取 ${providerId} 模型列表失败`);
  const result = await response.json();
  return result.data.models;
}

/**
 * 刷新指定提供商元数据
 */
export async function refreshProviderMetadata(providerId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/llm/providers/${providerId}/refresh`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error(`刷新 ${providerId} 元数据失败`);
}

/**
 * 刷新所有提供商元数据
 */
export async function refreshAllProviders(): Promise<Record<string, boolean>> {
  const response = await fetch(`${API_BASE}/api/llm/providers/refresh-all`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('刷新所有提供商失败');
  const result = await response.json();
  return result.results;
}

/**
 * 清除指定提供商缓存
 */
export async function clearProviderCache(providerId: string): Promise<void> {
  const response = await fetch(`${API_BASE}/api/llm/providers/${providerId}/cache`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error(`清除 ${providerId} 缓存失败`);
}

/**
 * 清除所有缓存
 */
export async function clearAllCache(): Promise<void> {
  const response = await fetch(`${API_BASE}/api/llm/cache`, {
    method: 'DELETE',
  });
  if (!response.ok) throw new Error('清除所有缓存失败');
}

/**
 * 获取缓存统计
 */
export async function getCacheStats(): Promise<CacheStats> {
  const response = await fetch(`${API_BASE}/api/llm/cache/stats`);
  if (!response.ok) throw new Error('获取缓存统计失败');
  const result = await response.json();
  return result.data;
}

/**
 * 添加新的提供商
 */
export async function addProvider(providerId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE}/api/llm/providers`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ provider_id: providerId }),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '添加提供商失败');
  }
  return response.json();
}

/**
 * 删除提供商
 */
export async function deleteProvider(providerId: string): Promise<{ status: string; message: string }> {
  const response = await fetch(`${API_BASE}/api/llm/providers/${providerId}`, {
    method: 'DELETE',
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || '删除提供商失败');
  }
  return response.json();
}
