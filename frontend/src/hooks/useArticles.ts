import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { fetchArticles, fetchArticle, deleteArticle, fetchArticleStats, syncCubox } from '../api/articles';

export function useArticles(params: {
  page?: number;
  page_size?: number;
  search?: string;
  source_type?: string;
}) {
  return useQuery({
    queryKey: ['articles', params],
    queryFn: () => fetchArticles(params),
    placeholderData: (prev) => prev,
  });
}

export function useArticle(id: string | null) {
  return useQuery({
    queryKey: ['article', id],
    queryFn: () => fetchArticle(id!),
    enabled: !!id,
  });
}

export function useDeleteArticle() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: deleteArticle,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['articleStats'] });
    },
  });
}

export function useArticleStats() {
  return useQuery({
    queryKey: ['articleStats'],
    queryFn: fetchArticleStats,
  });
}

export function useSyncCubox() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: syncCubox,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['articles'] });
      queryClient.invalidateQueries({ queryKey: ['articleStats'] });
    },
  });
}
