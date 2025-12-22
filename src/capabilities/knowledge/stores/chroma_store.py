"""
Chroma向量存储实现
基于ChromaDB的向量数据库封装
"""

import asyncio
from typing import List, Dict, Any, Optional
import logging
from pathlib import Path

import chromadb
from chromadb.config import Settings

from .store_base import BaseVectorStore
from ...core.schema.chunk import Chunk

logger = logging.getLogger(__name__)


class ChromaStore(BaseVectorStore):
    """Chroma向量存储实现"""
    
    def __init__(self, persist_directory: str = "./data/vector_stores/chroma",
                 collection_name: str = "documents"):
        """
        初始化Chroma存储
        
        Args:
            persist_directory: 持久化目录路径
            collection_name: 集合名称
        """
        self.persist_directory = Path(persist_directory)
        self.collection_name = collection_name
        self.client = None
        self.collection = None
        
        # 确保目录存在
        self.persist_directory.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ChromaStore initialized with directory: {persist_directory}")
    
    async def initialize(self) -> None:
        """异步初始化Chroma客户端和集合"""
        try:
            # 创建Chroma客户端
            self.client = chromadb.PersistentClient(
                path=str(self.persist_directory),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # 获取或创建集合
            try:
                self.collection = self.client.get_collection(self.collection_name)
                logger.info(f"Loaded existing collection: {self.collection_name}")
            except Exception:
                self.collection = self.client.create_collection(
                    name=self.collection_name,
                    metadata={"description": "Document chunks for RAG system"}
                )
                logger.info(f"Created new collection: {self.collection_name}")
            
            logger.info("ChromaStore initialization completed")
            
        except Exception as e:
            logger.error(f"ChromaStore initialization failed: {e}")
            raise
    
    async def add_chunk(self, chunk: Chunk) -> bool:
        """添加块到向量存储"""
        try:
            if not chunk.embedding:
                logger.warning(f"Chunk {chunk.id} has no embedding, skipping")
                return False
            
            # 准备元数据
            metadata = chunk.metadata.copy()
            metadata.update({
                "document_id": chunk.document_id,
                "start_position": chunk.start_position,
                "end_position": chunk.end_position,
                "chunk_size": len(chunk.content)
            })
            
            # 添加到集合
            self.collection.add(
                ids=[chunk.id],
                embeddings=[chunk.embedding],
                metadatas=[metadata],
                documents=[chunk.content]
            )
            
            logger.debug(f"Chunk added successfully: {chunk.id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add chunk {chunk.id}: {e}")
            return False
    
    async def add_chunks(self, chunks: List[Chunk]) -> List[bool]:
        """批量添加块"""
        results = []
        for chunk in chunks:
            try:
                success = await self.add_chunk(chunk)
                results.append(success)
            except Exception as e:
                logger.error(f"Failed to add chunk {chunk.id}: {e}")
                results.append(False)
        
        return results
    
    async def search(self, query_embedding: List[float], top_k: int = 5) -> List[Chunk]:
        """搜索相似块"""
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )
            
            chunks = []
            if results['ids'] and results['ids'][0]:
                for i, chunk_id in enumerate(results['ids'][0]):
                    content = results['documents'][0][i] if results['documents'] else ""
                    metadata = results['metadatas'][0][i] if results['metadatas'] else {}
                    distance = results['distances'][0][i] if results['distances'] else 0.0
                    
                    chunk = Chunk(
                        id=chunk_id,
                        content=content,
                        document_id=metadata.get("document_id", ""),
                        metadata=metadata,
                        embedding=None,  # 不返回嵌入以节省内存
                        similarity_score=1.0 - distance  # 转换为相似度分数
                    )
                    chunks.append(chunk)
            
            logger.debug(f"Search completed: found {len(chunks)} chunks")
            return chunks
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def delete_by_document_id(self, document_id: str) -> bool:
        """根据文档ID删除所有相关块"""
        try:
            # 查询该文档的所有块
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            if results['ids']:
                # 删除这些块
                self.collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for document {document_id}")
                return True
            else:
                logger.warning(f"No chunks found for document {document_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to delete chunks for document {document_id}: {e}")
            return False
    
    async def get_chunks_by_document_id(self, document_id: str) -> List[Chunk]:
        """根据文档ID获取所有块"""
        try:
            results = self.collection.get(
                where={"document_id": document_id}
            )
            
            chunks = []
            if results['ids']:
                for i, chunk_id in enumerate(results['ids']):
                    content = results['documents'][i] if results['documents'] else ""
                    metadata = results['metadatas'][i] if results['metadatas'] else {}
                    
                    chunk = Chunk(
                        id=chunk_id,
                        content=content,
                        document_id=document_id,
                        metadata=metadata,
                        embedding=None
                    )
                    chunks.append(chunk)
            
            return chunks
            
        except Exception as e:
            logger.error(f"Failed to get chunks for document {document_id}: {e}")
            return []
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取存储统计信息"""
        try:
            # 获取集合信息
            count = self.collection.count()
            
            # 估算大小（简化版）
            size_bytes = await self._estimate_size()
            
            return {
                'chunks_count': count,
                'size_bytes': size_bytes,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory)
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'chunks_count': 0,
                'size_bytes': 0,
                'collection_name': self.collection_name,
                'persist_directory': str(self.persist_directory)
            }
    
    async def _estimate_size(self) -> int:
        """估算存储大小"""
        try:
            # 简化的估算逻辑
            # 实际应该检查磁盘文件大小
            if self.persist_directory.exists():
                total_size = sum(f.stat().st_size for f in self.persist_directory.rglob('*') if f.is_file())
                return total_size
            return 0
        except Exception:
            return 0
    
    async def close(self) -> None:
        """关闭连接"""
        try:
            # Chroma持久化客户端不需要显式关闭
            logger.info("ChromaStore closed")
        except Exception as e:
            logger.error(f"Error closing ChromaStore: {e}")


class AsyncChromaStore(ChromaStore):
    """异步Chroma存储包装器"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._semaphore = asyncio.Semaphore(5)  # 限制并发操作
    
    async def add_chunks_concurrent(self, chunks: List[Chunk]) -> List[bool]:
        """并发添加块"""
        async def add_single_chunk(chunk):
            async with self._semaphore:
                return await self.add_chunk(chunk)
        
        tasks = [add_single_chunk(chunk) for chunk in chunks]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def search_batch(self, query_embeddings: List[List[float]], top_k: int = 5) -> List[List[Chunk]]:
        """批量搜索"""
        async def search_single_query(query_embedding):
            async with self._semaphore:
                return await self.search(query_embedding, top_k)
        
        tasks = [search_single_query(embedding) for embedding in query_embeddings]
        return await asyncio.gather(*tasks, return_exceptions=True)