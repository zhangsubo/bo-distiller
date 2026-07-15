import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchDistillStatus, startDistill, stopDistill } from '../api/distill';

export function useDistillStatus() {
  return useQuery({
    queryKey: ['distillStatus'],
    queryFn: fetchDistillStatus,
    refetchInterval: (query) => {
      // 正在运行时每 3 秒刷新，否则 30 秒
      const data = query.state.data?.data;
      return data?.running ? 3000 : 30000;
    },
  });
}

export function useStartDistill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: startDistill,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['distillStatus'] }),
  });
}

export function useStopDistill() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: stopDistill,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['distillStatus'] }),
  });
}
