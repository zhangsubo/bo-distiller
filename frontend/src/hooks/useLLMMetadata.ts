/**
 * LLM 元数据管理 Hooks
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  getProviders,
  getProviderMetadata,
  getProviderModels,
  refreshProviderMetadata,
  refreshAllProviders,
  clearProviderCache,
  clearAllCache,
  getCacheStats,
  addProvider,
  deleteProvider,
  type ProviderMetadata,
  type ProviderModel,
  type CacheStats,
} from '../api/llmMetadata';

/**
 * 获取支持的提供商列表
 */
export function useProviders() {
  return useQuery({
    queryKey: ['llm', 'providers'],
    queryFn: getProviders,
    staleTime: 1000 * 60 * 60, // 1 小时
  });
}

/**
 * 获取提供商元数据
 */
export function useProviderMetadata(providerId: string, enabled = true) {
  return useQuery({
    queryKey: ['llm', 'metadata', providerId],
    queryFn: () => getProviderMetadata(providerId),
    enabled: enabled && !!providerId,
    staleTime: 1000 * 60 * 60, // 1 小时
  });
}

/**
 * 获取提供商模型列表
 */
export function useProviderModels(
  providerId: string,
  apiBase?: string,
  apiKey?: string,
  enabled = true
) {
  return useQuery({
    queryKey: ['llm', 'models', providerId, apiBase, apiKey],
    queryFn: () => getProviderModels(providerId, apiBase, apiKey),
    enabled: enabled && !!providerId,
    staleTime: 1000 * 60 * 60, // 1 小时
  });
}

/**
 * 刷新提供商元数据
 */
export function useRefreshProviderMetadata() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: string) => refreshProviderMetadata(providerId),
    onSuccess: (_, providerId) => {
      // 刷新该提供商的元数据
      queryClient.invalidateQueries({ queryKey: ['llm', 'metadata', providerId] });
      queryClient.invalidateQueries({ queryKey: ['llm', 'cache'] });
    },
  });
}

/**
 * 刷新所有提供商元数据
 */
export function useRefreshAllProviders() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: refreshAllProviders,
    onSuccess: () => {
      // 刷新所有元数据
      queryClient.invalidateQueries({ queryKey: ['llm', 'metadata'] });
      queryClient.invalidateQueries({ queryKey: ['llm', 'cache'] });
    },
  });
}

/**
 * 清除提供商缓存
 */
export function useClearProviderCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: string) => clearProviderCache(providerId),
    onSuccess: (_, providerId) => {
      queryClient.invalidateQueries({ queryKey: ['llm', 'metadata', providerId] });
      queryClient.invalidateQueries({ queryKey: ['llm', 'models', providerId] });
      queryClient.invalidateQueries({ queryKey: ['llm', 'cache'] });
    },
  });
}

/**
 * 清除所有缓存
 */
export function useClearAllCache() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: clearAllCache,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['llm'] });
    },
  });
}

/**
 * 获取缓存统计
 */
export function useCacheStats() {
  return useQuery({
    queryKey: ['llm', 'cache', 'stats'],
    queryFn: getCacheStats,
    refetchInterval: 30000, // 每 30 秒刷新
  });
}

/**
 * 测试连通性
 */
export function useTestConnectivity() {
  return useMutation({
    mutationFn: async ({
      apiKey,
      apiBase,
      model,
    }: {
      apiKey: string;
      apiBase: string;
      model: string;
    }) => {
      const response = await fetch('/api/llm/test-connectivity', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          api_key: apiKey,
          api_base: apiBase,
          model: model,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || '测试失败');
      }

      return response.json();
    },
  });
}

/**
 * 添加提供商
 */
export function useAddProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: string) => addProvider(providerId),
    onSuccess: () => {
      // 刷新提供商列表
      queryClient.invalidateQueries({ queryKey: ['llm', 'providers'] });
      // 刷新缓存统计
      queryClient.invalidateQueries({ queryKey: ['llm', 'cache', 'stats'] });
    },
  });
}

/**
 * 删除提供商
 */
export function useDeleteProvider() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (providerId: string) => deleteProvider(providerId),
    onSuccess: () => {
      // 刷新提供商列表
      queryClient.invalidateQueries({ queryKey: ['llm', 'providers'] });
      // 刷新缓存统计
      queryClient.invalidateQueries({ queryKey: ['llm', 'cache', 'stats'] });
    },
  });
}
