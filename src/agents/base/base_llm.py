"""
LLM统一接口定义 - 基类模块
支持多种后端模型和调用方式
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterable

from src.agents.repositories.models import LLMConfig


class BaseLLM(ABC):
    """LLM统一接口抽象基类"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
    
    @abstractmethod
    async def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """异步调用LLM"""
        pass
    
    @abstractmethod
    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterable[str]:
        """流式调用LLM"""
        pass
    
    @abstractmethod
    def get_model_info(self) -> Dict[str, Any]:
        """获取模型信息"""
        pass
    
    def update_config(self, **kwargs) -> None:
        """更新配置参数"""
        for key, value in kwargs.items():
            if hasattr(self.config, key):
                setattr(self.config, key, value)