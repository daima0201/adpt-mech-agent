"""
嵌入器基础抽象类定义
提供文本向量化功能
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BaseEmbedder(ABC):
    """嵌入器基类"""
    
    def __init__(self, model_name: str, **kwargs):
        self.model_name = model_name
        self.config = kwargs
        self._initialized = False
    
    @abstractmethod
    async def initialize(self) -> None:
        """异步初始化嵌入器"""
        pass
    
    @abstractmethod
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """批量嵌入文本"""
        pass
    
    @abstractmethod
    async def embed_query(self, query: str) -> List[float]:
        """嵌入查询文本"""
        pass
    
    @abstractmethod
    def get_dimension(self) -> int:
        """获取嵌入维度"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass