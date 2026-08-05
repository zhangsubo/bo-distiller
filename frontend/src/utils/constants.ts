export const SOURCE_TYPES = [
  { label: 'Cubox', value: 'cubox' },
  { label: '本地 Markdown', value: 'local_markdown' },
  { label: '本地文件', value: 'local_file' },
  { label: 'RSS', value: 'rss' },
  { label: '书签', value: 'bookmark' },
  { label: 'URL 列表', value: 'url_list' },
];

// 支持的 LLM 提供商（与后端保持一致）
export const LLM_MODELS = [
  'deepseek',
  'xiaomi',
  'xiaomi-token-plan-cn',
  'minimax',
  'moonshotai',
  'kimi-for-coding',
  'opencode-go',
] as const;

export const PAGE_SIZE = 20;
