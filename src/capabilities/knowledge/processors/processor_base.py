"""
文档处理器基础抽象类定义
提供文档预处理和分块功能
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import logging

from ..core.schema.document import Document
from ..core.schema.chunk import Chunk

logger = logging.getLogger(__name__)


class BaseProcessor(ABC):
    """处理器基类"""
    
    def __init__(self, name: str, **kwargs):
        self.name = name
        self.config = kwargs
    
    @abstractmethod
    async def process_documents(self, documents: List[Document]) -> List[Chunk]:
        """处理文档列表"""
        pass
    
    @abstractmethod
    def get_config(self) -> Dict[str, Any]:
        """获取处理器配置"""
        pass