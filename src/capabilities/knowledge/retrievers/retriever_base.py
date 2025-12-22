"""
检索器基础抽象类定义
提供知识检索功能
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from ..core.schema.chunk import Chunk
from ..core.schema.query import Query

logger = logging.getLogger(__name__)


class BaseRetriever(ABC):
    """检索器基类"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
    
    @abstractmethod
    async def retrieve(self, query: Query, top_k: int = 5) -> List[Chunk]:
        """检索相关文档"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """获取检索器配置"""
        pass