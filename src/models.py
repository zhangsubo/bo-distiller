"""
Bo-Distiller 数据模型定义

使用 Pydantic v2 定义核心数据结构，确保类型安全和数据验证。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

try:
    from pydantic import BaseModel, Field, computed_field
    PYDANTIC_V2 = True
except ImportError:
    from pydantic import BaseModel, Field
    PYDANTIC_V2 = False


class SourceType(str, Enum):
    """内容源类型枚举"""
    RSS = "rss"
    BOOKMARK = "bookmark"
    URL_LIST = "url_list"
    LOCAL_FILE = "local_file"
    LOCAL_MARKDOWN = "local_markdown"
    CUBOX = "cubox"


class SourceInfo(BaseModel):
    """来源信息"""
    type: SourceType
    name: str = Field(..., description="来源名称（RSS 标题/书签文件名等）")
    identifier: str = Field(..., description="唯一标识（RSS URL/文件路径等）")


class SourceConfig(BaseModel):
    """内容源配置"""
    type: SourceType
    name: str
    identifier: str = Field("", description="唯一标识（URL/文件路径/CLI命令）")
    url: Optional[str] = None
    file: Optional[str] = None
    enabled: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Article(BaseModel):
    """统一文章模型

    所有内容源的输入都会被转换为这个统一模型。
    """
    id: str = Field(..., description="唯一标识（基于 URL 或内容 hash）")
    title: str = Field(..., description="文章标题")
    content: str = Field(..., description="正文内容")
    url: Optional[str] = Field(None, description="原文链接")
    source: SourceInfo = Field(..., description="来源信息")
    author: Optional[str] = Field(None, description="作者")
    published_date: Optional[datetime] = Field(None, description="发布时间")
    fetched_date: datetime = Field(default_factory=datetime.now, description="抓取时间")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据（标签、分类等）")

    if PYDANTIC_V2:
        @computed_field
        @property
        def content_length(self) -> int:
            """内容长度（字符数）"""
            return len(self.content)

        @computed_field
        @property
        def short_title(self) -> str:
            """截断标题（用于显示）"""
            return self.title[:50] + "..." if len(self.title) > 50 else self.title
    else:
        @property
        def content_length(self) -> int:
            """内容长度（字符数）"""
            return len(self.content)

        @property
        def short_title(self) -> str:
            """截断标题（用于显示）"""
            return self.title[:50] + "..." if len(self.title) > 50 else self.title


class TopicConfig(BaseModel):
    """主题配置"""
    name: str = Field(..., description="主题名称")
    keywords: List[str] = Field(default_factory=list, description="关键词列表")
    prompt_key: str = Field(..., description="对应的提示词键")
    parent: Optional[str] = Field(None, description="父主题（用于层次化）")
    discovery_method: str = Field("hybrid", description="发现方法：keyword/embedding/hybrid")


class PromptTemplate(BaseModel):
    """提示词模板"""
    system: str = Field(..., description="系统提示词")
    user_template: Optional[str] = Field(None, description="用户提示词模板")


class ProviderConfig(BaseModel):
    """单个 LLM 提供商配置"""
    api_key: str = Field(..., description="API Key（支持 ${ENV_VAR} 格式）")
    api_base: str = Field(..., description="API Base URL")
    model: str = Field(..., description="模型名称")
    max_context: int = Field(128000, description="最大上下文窗口")
    max_output: int = Field(8000, description="单次输出最大 token 数")


class LLMConfig(BaseModel):
    """LLM 配置"""
    call_mode: str = Field("direct", description="调用方式：direct / agent_cli")
    default_provider: str = Field("deepseek", description="默认提供商")
    providers: Dict[str, ProviderConfig] = Field(default_factory=dict)


class ProcessingConfig(BaseModel):
    """处理参数配置"""
    max_context: int = Field(128000, description="最大上下文窗口")
    max_output: int = Field(8000, description="单次输出最大 token 数")
    reserved_tokens: int = Field(2000, description="系统提示词预留 token")
    safety_margin: float = Field(0.9, ge=0.5, le=1.0, description="安全系数")
    batch_temperature: float = Field(0.3, ge=0.0, le=1.0, description="批次提取温度")
    synthesis_temperature: float = Field(0.2, ge=0.0, le=1.0, description="知识整合温度")
    max_article_length: int = Field(0, ge=0, description="文章截取长度（0=不截断）")


class TopicDiscoveryConfig(BaseModel):
    """主题发现配置"""
    method: str = Field("hybrid", description="发现方法")
    min_articles_per_topic: int = Field(3, ge=1, description="每个主题最少文章数")
    max_topics: int = Field(20, ge=1, description="最大主题数")
    enable_hierarchical: bool = Field(False, description="是否启用层次化主题")


class OutputConfig(BaseModel):
    """输出配置"""
    feishu_enabled: bool = Field(False, description="是否启用飞书输出")
    feishu_space_id: Optional[str] = Field(None, description="飞书知识库空间 ID")
    local_enabled: bool = Field(True, description="是否启用本地输出")
    local_dir: str = Field("./output", description="本地输出目录")
    include_sources: bool = Field(True, description="是否生成原文合集")


class SystemConfig(BaseModel):
    """系统总配置"""
    project_name: str = Field("bo-distiller", description="项目名称")
    output_dir: str = Field("./output", description="输出目录")
    cache_dir: str = Field(".cache", description="缓存目录")
    llm: LLMConfig = Field(default_factory=LLMConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    topic_discovery: TopicDiscoveryConfig = Field(default_factory=TopicDiscoveryConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)


class KnowledgeDoc(BaseModel):
    """知识文档"""
    topic: str = Field(..., description="主题名称")
    content: str = Field(..., description="文档内容")
    article_count: int = Field(0, description="来源文章数")
    batch_count: int = Field(0, description="批次数")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    metadata: Dict[str, Any] = Field(default_factory=dict)


class BatchResult(BaseModel):
    """批次处理结果"""
    topic: str
    batch_index: int
    content: str
    article_ids: List[str]
    created_at: datetime = Field(default_factory=datetime.now)


class CacheProgress(BaseModel):
    """缓存进度"""
    current_step: str = Field("init", description="当前步骤")
    completed_steps: List[str] = Field(default_factory=list)
    topic_progress: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    last_updated: datetime = Field(default_factory=datetime.now)
