"""
多向量库管理器
支持多种向量存储的统一管理
"""

from typing import Dict, List, Optional, Type, Any
import logging
from .base import BaseVectorStore
from ..core.schema.chunk import Chunk

logger = logging.getLogger(__name__)


class VectorStoreManager:
    """向量存储管理器"""
    
    def __init__(self):
        self._stores: Dict[str, BaseVectorStore] = {}
        self._default_store: Optional[str] = None
    
    def register_store(self, name: str, store: BaseVectorStore) -> None:
        """注册向量存储"""
        if name in self._stores:
            logger.warning(f"向量存储 '{name}' 已存在，将被覆盖")
        
        self._stores[name] = store
        logger.info(f"向量存储 '{name}' 注册成功")
    
    def set_default_store(self, name: str) -> None:
        """设置默认向量存储"""
        if name not in self._stores:
            raise ValueError(f"向量存储 '{name}' 未注册")
        
        self._default_store = name
        logger.info(f"默认向量存储设置为: {name}")
    
    async def initialize_all(self) -> None:
        """初始化所有向量存储"""
        for name, store in self._stores.items():
            try:
                await store.initialize()
                logger.info(f"向量存储 '{name}' 初始化成功")
            except Exception as e:
                logger.error(f"向量存储 '{name}' 初始化失败: {e}")
                raise
    
    async def add_chunk(self, chunk: Chunk, store_name: Optional[str] = None) -> bool:
        """添加块到指定向量存储"""
        store = self._get_store(store_name)
        return await store.add_chunk(chunk)
    
    async def add_chunks(self, chunks: List[Chunk], store_name: Optional[str] = None) -> List[bool]:
        """批量添加块到指定向量存储"""
        store = self._get_store(store_name)
        return await store.add_chunks(chunks)
    
    async def search(self, query_embedding: List[float], top_k: int = 5, 
                    store_name: Optional[str] = None) -> List[Chunk]:
        """在指定向量存储中搜索"""
        store = self._get_store(store_name)
        return await store.search(query_embedding, top_k)
    
    async def delete_by_document_id(self, document_id: str, store_name: Optional[str] = None) -> bool:
        """根据文档ID删除块"""
        store = self._get_store(store_name)
        return await store.delete_by_document_id(document_id)
    
    async def get_statistics(self, store_name: Optional[str] = None) -> Dict[str, Any]:
        """获取存储统计信息"""
        store = self._get_store(store_name)
        return await store.get_statistics()
    
    def list_stores(self) -> List[str]:
        """列出所有已注册的向量存储"""
        return list(self._stores.keys())
    
    def get_store(self, name: str) -> BaseVectorStore:
        """获取指定的向量存储"""
        if name not in self._stores:
            raise ValueError(f"向量存储 '{name}' 未注册")
        return self._stores[name]
    
    def _get_store(self, store_name: Optional[str]) -> BaseVectorStore:
        """获取向量存储实例"""
        if store_name is None:
            if self._default_store is None:
                raise ValueError("未设置默认向量存储")
            store_name = self._default_store
        
        if store_name not in self._stores:
            raise ValueError(f"向量存储 '{store_name}' 未注册")
        
        return self._stores[store_name]
    
    async def close_all(self) -> None:
        """关闭所有向量存储连接"""
        for name, store in self._stores.items():
            try:
                await store.close()
                logger.info(f"向量存储 '{name}' 已关闭")
            except Exception as e:
                logger.error(f"关闭向量存储 '{name}' 失败: {e}")


# 全局向量存储管理器实例
_vector_store_manager = VectorStoreManager()


def get_vector_store_manager() -> VectorStoreManager:
    """获取全局向量存储管理器实例"""
    return _vector_store_manager