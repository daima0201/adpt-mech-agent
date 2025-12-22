"""
向量存储基础抽象类定义
提供向量数据的存储和检索功能
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Tuple
import logging

from ..core.schema.chunk import Chunk

logger = logging.getLogger(__name__)


class BaseVectorStore(ABC):
    """向量存储基类"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化向量存储"""
        pass
    
    @abstractmethod
    async def add_chunks(self, chunks: List[Chunk]) -> None:
        """添加分块到向量存储"""
        pass
    
    @abstractmethod
    async def search_similar(self, vector: List[float], top_k: int = 5) -> List[Tuple[Chunk, float]]:
        """相似性搜索"""
        pass
    
    @abstractmethod
    async def delete_chunks(self, chunk_ids: List[str]) -> None:
        """删除分块"""
        pass
    
    @abstractmethod
    async def get_chunk_count(self) -> int:
        """获取分块数量"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空向量存储"""
        pass