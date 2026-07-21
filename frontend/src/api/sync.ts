import client from './client';
import type { SyncStatus, SyncConfigPayload } from './types';

export async function fetchSyncStatus(): Promise<SyncStatus> {
  return client.get('/sync/status');
}

export async function saveSyncConfig(
  config: SyncConfigPayload,
): Promise<{ status: string; message: string }> {
  return client.post('/sync/config', config);
}
