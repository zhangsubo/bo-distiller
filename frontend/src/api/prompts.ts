import client from './client';
import type { PromptsConfig } from './types';

export async function fetchPrompts(): Promise<{ prompts: PromptsConfig }> {
  return client.get('/prompts');
}

export async function savePrompts(prompts: PromptsConfig): Promise<{ status: string }> {
  return client.post('/prompts', { prompts });
}
