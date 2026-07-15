import client from './client';
import type { DistillStatus } from './types';

export async function startDistill(params: {
  model?: string;
  incremental?: boolean;
}): Promise<void> {
  return client.post('/distill/start', params);
}

export async function stopDistill(): Promise<void> {
  return client.post('/distill/stop');
}

export async function fetchDistillStatus(): Promise<{ data: DistillStatus }> {
  return client.get('/distill/status');
}
