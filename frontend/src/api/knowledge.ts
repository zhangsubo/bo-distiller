import client from './client';
import type { KnowledgeDocInfo } from './types';

export async function fetchKnowledgeDocs(): Promise<{ documents: KnowledgeDocInfo[] }> {
  return client.get('/knowledge');
}

export async function fetchKnowledgeDoc(name: string): Promise<{ name: string; content: string }> {
  return client.get(`/knowledge/${name}`);
}

export async function searchKnowledge(query: string): Promise<{ results: Array<{ name: string; title: string; snippet: string }> }> {
  return client.get('/knowledge/search', { params: { q: query } });
}
