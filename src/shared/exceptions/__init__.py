"""
统一异常体系
定义项目使用的所有异常类型
"""

from .base import BaseError, ConfigError, ValidationError
from .agent_errors import (
    AgentError,
    AgentExecutionError,
    AgentInitializationError,
    ToolNotFoundError,
    ToolExecutionError
)
from .knowledge_errors import (
    KnowledgeBaseError,
    DocumentLoadError,
    EmbeddingError,
    RetrievalError,
    VectorStoreError
)
from .tool_errors import (
    ToolError,
    ToolValidationError,
    ToolTimeoutError,
    ToolPermissionError
)

__all__ = [
    'BaseError',
    'ConfigError', 
    'ValidationError',
    'AgentError',
    'AgentExecutionError',
    'AgentInitializationError',
    'ToolNotFoundError',
    'ToolExecutionError',
    'KnowledgeBaseError',
    'DocumentLoadError',
    'EmbeddingError',
    'RetrievalError',
    'VectorStoreError',
    'ToolError',
    'ToolValidationError',
    'ToolTimeoutError',
    'ToolPermissionError'
]