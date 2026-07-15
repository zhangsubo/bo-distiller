"""
测试数据模型
"""

import sys
from datetime import datetime
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import Article, SourceInfo, SourceType, SystemConfig


def test_article_creation():
    """测试文章模型创建"""
    source = SourceInfo(
        type=SourceType.LOCAL_FILE,
        name="测试来源",
        identifier="/path/to/file",
    )

    article = Article(
        id="test-001",
        title="测试文章标题",
        content="这是一篇测试文章的内容。",
        url="https://example.com/article/1",
        source=source,
        author="测试作者",
        published_date=datetime.now(),
    )

    assert article.id == "test-001"
    assert article.title == "测试文章标题"
    assert article.content_length == len("这是一篇测试文章的内容。")
    assert article.short_title == "测试文章标题"
    print("✅ Article 创建测试通过")


def test_system_config():
    """测试系统配置模型"""
    config = SystemConfig()

    assert config.project_name == "bo-distiller"
    assert config.output_dir == "./output"
    assert config.cache_dir == ".cache"
    assert config.llm.default_provider == "deepseek"
    assert config.processing.batch_temperature == 0.3
    print("✅ SystemConfig 创建测试通过")


def test_source_types():
    """测试源类型枚举"""
    assert SourceType.RSS == "rss"
    assert SourceType.BOOKMARK == "bookmark"
    assert SourceType.LOCAL_FILE == "local_file"
    assert SourceType.CUBOX == "cubox"
    print("✅ SourceType 枚举测试通过")


if __name__ == "__main__":
    test_article_creation()
    test_system_config()
    test_source_types()
    print("\n🎉 所有测试通过！")
