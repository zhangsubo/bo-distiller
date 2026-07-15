import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchConfig, saveConfig, fetchSources, saveSources, fetchTopicsConfig, saveTopicsConfig } from '../api/config';
import type { AppConfig, TopicsConfig, SourceConfig } from '../api/types';

export function useConfig() {
  return useQuery({
    queryKey: ['config'],
    queryFn: fetchConfig,
  });
}

export function useSaveConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: AppConfig) => saveConfig(config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['config'] }),
  });
}

export function useSources() {
  return useQuery({
    queryKey: ['sources'],
    queryFn: fetchSources,
  });
}

export function useSaveSources() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (sources: SourceConfig[]) => saveSources(sources),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sources'] }),
  });
}

export function useTopicsConfig() {
  return useQuery({
    queryKey: ['topicsConfig'],
    queryFn: fetchTopicsConfig,
  });
}

export function useSaveTopicsConfig() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (config: TopicsConfig) => saveTopicsConfig(config),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['topicsConfig'] }),
  });
}
