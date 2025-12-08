"""
知识库基础抽象类定义
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from .schema.document import Document
from .schema.chunk import Chunk
from .schema.query import Query

logger = logging.getLogger(__name__)


class BaseKnowledgeBase(ABC):
    """知识库基类"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化知识库"""
        pass
    
    @abstractmethod
    async def add_document(self, document: Document) -> str:
        """添加文档到知识库"""
        pass
    
    @abstractmethod
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """批量添加文档"""
        pass
    
    @abstractmethod
    async def search(self, query: Query, top_k: int = 5) -> List[Chunk]:
        """搜索知识库"""
        pass
    
    @abstractmethod
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        pass
    
    @abstractmethod
    async def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档"""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭知识库资源"""
        pass


class BaseVectorStore(ABC):
    """向量存储基类"""
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化向量存储"""
        pass
    
    @abstractmethod
    async def add_chunk(self, chunk: Chunk) -> bool:
        """添加块到向量存储"""
        pass
    
    @abstractmethod
    async def add_chunks(self, chunks: List[Chunk]) -> List[bool]:
        """批量添加块"""
        pass
    
    @abstractmethod
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Chunk]:
        """搜索相似块"""
        pass
    
    @abstractmethod
    async def delete_by_document_id(self, document_id: str) -> bool:
        """根据文档ID删除所有相关块"""
        pass
    
    @abstractmethod
    async def get_chunks_by_document_id(self, document_id: str) -> List[Chunk]:
        """根据文档ID获取所有块"""
        pass
    
    @abstractmethod
    async def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭连接"""
        pass


class BaseEmbedder(ABC):
    """嵌入模型基类"""
    
    @property
    @abstractmethod
    def model_name(self) -> str:
        """获取模型名称"""
        pass
    
    @abstractmethod
    async def embed(self, text: str) -> List[float]:
        """生成单个文本的嵌入向量"""
        pass
    
    @abstractmethod
    async def embed_batch(self, texts: List[str]) -> List[List[float]]:
        """批量生成嵌入向量"""
        pass
    
    @abstractmethod
    async def get_dimension(self) -> int:
        """获取嵌入维度"""
        pass
    
    @abstractmethod
    async def close(self) -> None:
        """关闭模型资源"""
        pass


class BaseProcessor(ABC):
    """文档处理器基类"""
    
    @abstractmethod
    async def process(self, document: Document) -> Document:
        """处理文档"""
        pass
    
    @abstractmethod
    async def process_batch(self, documents: List[Document]) -> List[Document]:
        """批量处理文档"""
        pass


class BaseRetriever(ABC):
    """检索器基类"""
    
    @abstractmethod
    async def search(self, query: Query, top_k: int = 5) -> List[Chunk]:
        """搜索知识库"""
        pass
    
    @abstractmethod
    async def search_batch(self, queries: List[Query], top_k: int = 5) -> List[List[Chunk]]:
        """批量搜索"""
        pass