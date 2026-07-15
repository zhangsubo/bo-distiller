"""
内容源适配器基类

定义所有内容源适配器必须实现的接口。
"""

from abc import ABC, abstractmethod
from typing import List

from ..models import Article, SourceConfig


class SourceAdapter(ABC):
    """内容源适配器基类

    所有内容源适配器（RSS、书签、本地文件、Cubox 等）
    都必须继承此基类并实现抽象方法。
    """

    @abstractmethod
    def fetch(self, source_config: SourceConfig) -> List[Article]:
        """抓取内容

        Args:
            source_config: 内容源配置

        Returns:
            文章列表
        """
        pass

    @abstractmethod
    def validate(self, source_config: SourceConfig) -> bool:
        """验证源配置

        Args:
            source_config: 内容源配置

        Returns:
            配置是否有效
        """
        pass

    def fetch_incremental(
        self, source_config: SourceConfig, since: float = 0
    ) -> List[Article]:
        """增量抓取内容

        Args:
            source_config: 内容源配置
            since: 上次抓取的时间戳（Unix timestamp）

        Returns:
            新增的文章列表
        """
        # 默认实现：全量抓取
        return self.fetch(source_config)
