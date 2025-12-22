"""
知识库核心实现
提供文档管理、检索和向量化功能
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import logging

from .interface import AbstractKnowledgeBase
from .schema.document import Document
from .schema.chunk import Chunk
from .schema.query import Query
from ..embedders.embedder_base import BaseEmbedder
from ..stores.store_base import BaseVectorStore
from ..processors.processor_base import BaseProcessor
from ..retrievers.retriever_base import BaseRetriever

logger = logging.getLogger(__name__)


class KnowledgeBase(AbstractKnowledgeBase):
    """知识库主类 - 集成文档处理、嵌入和检索功能"""
    
    def __init__(self,
                 vector_store: BaseVectorStore,
                 embedder: BaseEmbedder,
                 processors: Optional[List[BaseProcessor]] = None,
                 retriever: Optional[BaseRetriever] = None):
        """
        初始化知识库
        
        Args:
            vector_store: 向量存储实例
            embedder: 嵌入模型实例
            processors: 文档处理器列表
            retriever: 检索器实例
        """
        self.vector_store = vector_store
        self.embedder = embedder
        self.processors = processors or []
        self.retriever = retriever
        
        # 统计信息
        self._document_count = 0
        self._chunk_count = 0
        
        logger.info("KnowledgeBase initialized")
    
    async def initialize(self) -> None:
        """异步初始化知识库"""
        try:
            await self.vector_store.initialize()
            logger.info("KnowledgeBase initialization completed")
        except Exception as e:
            logger.error(f"KnowledgeBase initialization failed: {e}")
            raise
    
    async def add_document(self, document: Document) -> str:
        """添加文档到知识库"""
        try:
            # 1. 预处理文档
            processed_doc = document
            for processor in self.processors:
                processed_doc = await processor.process(processed_doc)
            
            # 2. 切分文档
            chunks = await self._split_document(processed_doc)
            
            # 3. 生成嵌入
            chunk_texts = [chunk.content for chunk in chunks]
            embeddings = await self.embedder.embed_batch(chunk_texts)
            
            # 4. 存储到向量数据库
            for i, chunk in enumerate(chunks):
                chunk.embedding = embeddings[i]
                await self.vector_store.add_chunk(chunk)
            
            # 5. 更新统计
            self._document_count += 1
            self._chunk_count += len(chunks)
            
            logger.info(f"Document added successfully: {len(chunks)} chunks created")
            return document.id
            
        except Exception as e:
            logger.error(f"Failed to add document: {e}")
            raise
    
    async def add_documents(self, documents: List[Document]) -> List[str]:
        """批量添加文档"""
        results = []
        for doc in documents:
            try:
                doc_id = await self.add_document(doc)
                results.append(doc_id)
            except Exception as e:
                logger.error(f"Failed to add document {doc.id}: {e}")
                results.append(None)
        
        return results
    
    async def search(self, query: Query, top_k: int = 5) -> List[Chunk]:
        """搜索知识库"""
        try:
            if self.retriever:
                # 使用配置的检索器
                return await self.retriever.search(query, top_k=top_k)
            else:
                # 默认向量检索
                query_embedding = await self.embedder.embed(query.text)
                return await self.vector_store.search(query_embedding, top_k=top_k)
                
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    async def delete_document(self, document_id: str) -> bool:
        """删除文档"""
        try:
            success = await self.vector_store.delete_by_document_id(document_id)
            if success:
                # 更新统计（需要重新计算）
                stats = await self.get_statistics()
                self._document_count = stats['documents_count']
                self._chunk_count = stats['chunks_count']
            
            return success
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            return False
    
    async def get_document(self, document_id: str) -> Optional[Document]:
        """获取文档"""
        try:
            chunks = await self.vector_store.get_chunks_by_document_id(document_id)
            if not chunks:
                return None
            
            # 重建文档内容
            content = "\n".join([chunk.content for chunk in chunks])
            metadata = chunks[0].metadata.copy() if chunks else {}
            
            return Document(
                id=document_id,
                content=content,
                metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
            return None
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        try:
            store_stats = await self.vector_store.get_statistics()
            
            return {
                'documents_count': store_stats.get('documents_count', self._document_count),
                'chunks_count': store_stats.get('chunks_count', self._chunk_count),
                'vector_db_size': store_stats.get('size_bytes', 0),
                'embedding_model': self.embedder.model_name,
                'vector_store_type': type(self.vector_store).__name__
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                'documents_count': self._document_count,
                'chunks_count': self._chunk_count,
                'vector_db_size': 0,
                'embedding_model': self.embedder.model_name,
                'vector_store_type': type(self.vector_store).__name__
            }
    
    async def _split_document(self, document: Document) -> List[Chunk]:
        """切分文档为块"""
        # 简化的文本切分逻辑
        # 实际应该使用专门的文本切分器
        
        content = document.content
        chunk_size = 500  # 字符数
        overlap = 50      # 重叠字符数
        
        chunks = []
        start = 0
        
        while start < len(content):
            end = min(start + chunk_size, len(content))
            
            # 尝试在句子边界处切分
            if end < len(content):
                # 向后查找句子结束符
                sentence_endings = ['.', '!', '?', '。', '！', '？', '\n']
                for i in range(end, min(end + 100, len(content))):
                    if content[i] in sentence_endings:
                        end = i + 1
                        break
            
            chunk_content = content[start:end].strip()
            if chunk_content:
                chunk = Chunk(
                    content=chunk_content,
                    document_id=document.id,
                    metadata=document.metadata.copy(),
                    start_position=start,
                    end_position=end
                )
                chunks.append(chunk)
            
            start = end - overlap
            if start <= end - overlap:  # 防止无限循环
                break
        
        return chunks
    
    async def close(self) -> None:
        """关闭知识库资源"""
        try:
            await self.vector_store.close()
            logger.info("KnowledgeBase closed successfully")
        except Exception as e:
            logger.error(f"Error closing KnowledgeBase: {e}")


class AsyncKnowledgeBase(KnowledgeBase):
    """异步知识库实现 - 支持并发操作"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._semaphore = asyncio.Semaphore(10)  # 限制并发数
    
    async def add_documents_concurrent(self, documents: List[Document]) -> List[str]:
        """并发添加文档"""
        async def add_single_doc(doc):
            async with self._semaphore:
                return await self.add_document(doc)
        
        tasks = [add_single_doc(doc) for doc in documents]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    async def search_batch(self, queries: List[Query], top_k: int = 5) -> List[List[Chunk]]:
        """批量搜索"""
        async def search_single_query(query):
            async with self._semaphore:
                return await self.search(query, top_k)
        
        tasks = [search_single_query(query) for query in queries]
        return await asyncio.gather(*tasks, return_exceptions=True)