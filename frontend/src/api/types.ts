// 文章
export interface Article {
  id: string;
  title: string;
  content: string;
  url: string | null;
  source_type: string;
  source_name: string;
  source_identifier: string;
  author: string | null;
  published_date: string | null;
  fetched_date: string;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface Pagination {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface ArticleListResponse {
  data: Article[];
  pagination: Pagination;
}

// 统计
export interface ArticleStats {
  total_articles: number;
  sources: Array<{
    source_type: string;
    source_name: string;
    count: number;
  }>;
  db_path: string;
  db_size: number;
}

// 同步状态
export interface SyncState {
  source_type: string;
  source_name: string;
  last_sync: string | null;
  total_articles: number;
  metadata: Record<string, unknown>;
}

// 主题
export interface Topic {
  name: string;
  keywords: string[];
  description: string;
  priority: number;
  parent: string | null;
  article_count: number;
}

// 知识库文档
export interface KnowledgeDocInfo {
  name: string;
  title: string;
  size: number;
  modified: string;
}

// 蒸馏状态
export interface DistillStatus {
  running: boolean;
  step: string;
  started_at: string | null;
  error: string | null;
  cache: {
    articles_cached: boolean;
    cleaned_cached: boolean;
    topics_cached: boolean;
    batch_count: number;
    final_count: number;
  };
  topics_done: string[];
}

// 配置
export interface LLMProvider {
  api_key: string;
  api_base: string;
  model: string;
  max_context: number;
  max_output: number;
}

export interface AppConfig {
  project: {
    name: string;
    output_dir: string;
    cache_dir: string;
  };
  llm: {
    call_mode: string;
    default_provider: string;
    providers: Record<string, LLMProvider>;
  };
  processing: {
    max_context: number;
    max_output: number;
    reserved_tokens: number;
    safety_margin: number;
    batch_temperature: number;
    synthesis_temperature: number;
    max_article_length: number;
  };
  topic_discovery: {
    method: string;
    min_articles_per_topic: number;
    max_topics: number;
    enable_hierarchical: boolean;
  };
  output: {
    feishu: { enabled: boolean; space_id: string | null };
    local: { enabled: boolean; dir: string; include_sources: boolean };
  };
}

// 内容源
export interface SourceConfig {
  type: string;
  name: string;
  identifier: string;
  enabled: boolean;
}

// 定时同步
export interface SyncStatus {
  enabled: boolean;
  interval_minutes: number;
  incremental: boolean;
  last_sync: string | null;
  next_run_time: string | null;
}

export interface SyncConfigPayload {
  enabled: boolean;
  interval_minutes: number;
  incremental: boolean;
}

// 微信下载
export interface WeChatConfig {
  enabled: boolean;
  api_base: string;
  api_token: string;
  storage_dir: string;
  formats: string[];
  requests_per_minute: number;
  download_on_sync: boolean;
  write_back_content: boolean;
  localize_images: boolean;
}

export interface WeChatStats {
  pending: number;
  downloading: number;
  done: number;
  failed: number;
}

export interface WeChatCurrent {
  article_id: string | null;
  title: string | null;
  worker_alive: boolean;
}

export interface WeChatStatus {
  stats: WeChatStats;
  current: WeChatCurrent;
  enabled: boolean;
}

// 提示词
export interface PromptTemplate {
  system?: string;
  user_template?: string;
}

export type PromptsConfig = Record<string, PromptTemplate | Record<string, unknown>>;

// Topics 配置 (YAML 结构)
export interface TopicsConfig {
  predefined_topics: Record<string, {
    keywords: string[];
    prompt_key: string;
    parent: string | null;
    description: string;
    priority: number;
  }>;
  hierarchy: Record<string, unknown>;
  discovery: Record<string, unknown>;
  deduplication: Record<string, unknown>;
  classification_priority: string[];
}
