"""
知识库模块
提供文档管理、向量化和检索功能
"""

from .core.config import KnowledgeConfig
from .core.knowledge_base import KnowledgeBase

__all__ = [
    'KnowledgeConfig',
    'KnowledgeBase'
]