import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchSyncStatus, saveSyncConfig } from '../api/sync';
import { fetchPrompts, savePrompts } from '../api/prompts';
import type { SyncConfigPayload, PromptsConfig } from '../api/types';

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
