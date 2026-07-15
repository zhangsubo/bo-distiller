import { useQuery } from '@tanstack/react-query';
import { fetchKnowledgeDocs, fetchKnowledgeDoc, searchKnowledge } from '../api/knowledge';

export function useKnowledgeDocs() {
  return useQuery({
    queryKey: ['knowledgeDocs'],
    queryFn: fetchKnowledgeDocs,
  });
}

export function useKnowledgeDoc(name: string | null) {
  return useQuery({
    queryKey: ['knowledgeDoc', name],
    queryFn: () => fetchKnowledgeDoc(name!),
    enabled: !!name,
  });
}

export function useKnowledgeSearch(query: string) {
  return useQuery({
    queryKey: ['knowledgeSearch', query],
    queryFn: () => searchKnowledge(query),
    enabled: query.length >= 2,
  });
}
