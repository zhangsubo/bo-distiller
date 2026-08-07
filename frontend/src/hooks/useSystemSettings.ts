import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSyncStatus, saveSyncConfig } from '../api/sync';
import { fetchPrompts, savePrompts } from '../api/prompts';
import type { SyncConfigPayload, PromptsConfig } from '../api/types';

// 定时同步配置（只包含 enabled/interval/incremental/last_sync/next_run_time）
export function useSyncConfig() {
  return useQuery({
    queryKey: ['sync', 'config'],
    queryFn: fetchSyncStatus,
  });
}

export function useSaveSyncConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: SyncConfigPayload) => saveSyncConfig(config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sync', 'config'] }),
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
