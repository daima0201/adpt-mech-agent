"""
知识库基础抽象类定义
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Protocol
import logging

from .schema.document import Document
from .schema.chunk import Chunk
from .schema.query import Query

logger = logging.getLogger(__name__)


class KnowledgeBaseInterface(Protocol):
    """知识库接口定义 - 支持不同实现替换"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化知识库"""
        pass


class AbstractKnowledgeBase(ABC):
    """知识库抽象基类"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化知识库"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> None:
        """添加文档到知识库"""
        pass
    
    @abstractmethod
    async def search(self, query: Query, top_k: int = 5) -> List[Chunk]:
        """搜索知识库"""
        pass
    
    @abstractmethod
    async def delete_documents(self, document_ids: List[str]) -> None:
        """删除文档"""
        pass
    
    @abstractmethod
    async def get_document_count(self) -> int:
        """获取文档数量"""
        pass
    
    @abstractmethod
    async def clear(self) -> None:
        """清空知识库"""
        pass