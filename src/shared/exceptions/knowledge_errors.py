"""
知识库相关异常
定义知识库操作过程中的异常类型
"""

from typing import Optional, Dict, Any
from .base import BaseError


class KnowledgeBaseError(BaseError):
    """知识库基础异常"""
    
    def __init__(
        self, 
        message: str, 
        knowledge_base: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if knowledge_base:
            details['knowledge_base'] = knowledge_base
        if operation:
            details['operation'] = operation
        
        super().__init__(message, code="KNOWLEDGE_BASE_ERROR", details=details, **kwargs)


class DocumentLoadError(KnowledgeBaseError):
    """文档加载异常"""
    
    def __init__(
        self, 
        message: str, 
        document_path: Optional[str] = None,
        document_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if document_path:
            details['document_path'] = document_path
        if document_type:
            details['document_type'] = document_type
        
        super().__init__(message, code="DOCUMENT_LOAD_ERROR", details=details, **kwargs)


class EmbeddingError(KnowledgeBaseError):
    """嵌入异常"""
    
    def __init__(
        self, 
        message: str, 
        embedder_type: Optional[str] = None,
        text_length: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if embedder_type:
            details['embedder_type'] = embedder_type
        if text_length is not None:
            details['text_length'] = text_length
        
        super().__init__(message, code="EMBEDDING_ERROR", details=details, **kwargs)


class RetrievalError(KnowledgeBaseError):
    """检索异常"""
    
    def __init__(
        self, 
        message: str, 
        query: Optional[str] = None,
        similarity_threshold: Optional[float] = None,
        retrieved_count: Optional[int] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if query:
            details['query'] = query
        if similarity_threshold is not None:
            details['similarity_threshold'] = similarity_threshold
        if retrieved_count is not None:
            details['retrieved_count'] = retrieved_count
        
        super().__init__(message, code="RETRIEVAL_ERROR", details=details, **kwargs)


class VectorStoreError(KnowledgeBaseError):
    """向量存储异常"""
    
    def __init__(
        self, 
        message: str, 
        vector_store_type: Optional[str] = None,
        collection_name: Optional[str] = None,
        operation: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if vector_store_type:
            details['vector_store_type'] = vector_store_type
        if collection_name:
            details['collection_name'] = collection_name
        if operation:
            details['operation'] = operation
        
        super().__init__(message, code="VECTOR_STORE_ERROR", details=details, **kwargs)