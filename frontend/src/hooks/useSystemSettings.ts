import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSyncStatus, saveSyncConfig } from '../api/sync';
import {
  fetchWeChatStatus,
  fetchWeChatConfig,
  saveWeChatConfig,
  backfillWeChat,
  retryFailedWeChat,
} from '../api/wechat';
import { fetchPrompts, savePrompts } from '../api/prompts';
import type { SyncConfigPayload, WeChatConfig, PromptsConfig } from '../api/types';

// 定时同步
export function useSyncStatus() {
  return useQuery({
    queryKey: ['syncStatus'],
    queryFn: fetchSyncStatus,
  });
}

export function useSaveSyncConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: SyncConfigPayload) => saveSyncConfig(config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['syncStatus'] }),
  });
}

// 微信下载
export function useWeChatStatus() {
  return useQuery({
    queryKey: ['wechatStatus'],
    queryFn: fetchWeChatStatus,
    refetchInterval: 5000,
  });
}

export function useWeChatConfig() {
  return useQuery({
    queryKey: ['wechatConfig'],
    queryFn: fetchWeChatConfig,
  });
}

export function useSaveWeChatConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: WeChatConfig) => saveWeChatConfig(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['wechatConfig'] });
      queryClient.invalidateQueries({ queryKey: ['wechatStatus'] });
    },
  });
}

export function useBackfillWeChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: backfillWeChat,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wechatStatus'] }),
  });
}

export function useRetryFailedWeChat() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: retryFailedWeChat,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['wechatStatus'] }),
  });
}

// 提示词
export function usePrompts() {
  return useQuery({
    queryKey: ['prompts'],
    queryFn: fetchPrompts,
  });
}

export function useSavePrompts() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (prompts: PromptsConfig) => savePrompts(prompts),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['prompts'] }),
  });
}
