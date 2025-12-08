"""
LLM统一接口定义
支持多种后端模型和调用方式
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Iterator
from dataclasses import dataclass


@dataclass
class LLMConfig:
    """LLM配置类"""
    model_name: str = "gpt-3.5-turbo"
    temperature: float = 0.7
    max_tokens: int = 2048
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    timeout: int = 30
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'model_name': self.model_name,
            'temperature': self.temperature,
            'max_tokens': self.max_tokens,
            'api_key': self.api_key,
            'base_url': self.base_url,
            'timeout': self.timeout
        }


class HelloAgentsLLM(ABC):
    """LLM统一接口抽象基类"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        self.config = config or LLMConfig()
    
    @abstractmethod
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """同步调用LLM"""
        pass
    
    @abstractmethod
    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
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


class OpenAIClient(HelloAgentsLLM):
    """OpenAI客户端实现"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config)
        self._client = None
    
    def _get_client(self):
        """获取OpenAI客户端实例"""
        if self._client is None:
            try:
                import openai
                if self.config.api_key:
                    openai.api_key = self.config.api_key
                if self.config.base_url:
                    openai.base_url = self.config.base_url
                self._client = openai
            except ImportError:
                raise ImportError("请安装openai包: pip install openai")
        return self._client
    
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """调用OpenAI API"""
        client = self._get_client()
        
        # 合并配置参数
        params = {
            'model': self.config.model_name,
            'messages': messages,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'timeout': self.config.timeout
        }
        params.update(kwargs)
        
        try:
            response = client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI调用失败: {str(e)}")
    
    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """流式调用OpenAI API"""
        client = self._get_client()
        
        params = {
            'model': self.config.model_name,
            'messages': messages,
            'temperature': self.config.temperature,
            'max_tokens': self.config.max_tokens,
            'stream': True,
            'timeout': self.config.timeout
        }
        params.update(kwargs)
        
        try:
            response = client.chat.completions.create(**params)
            for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"OpenAI流式调用失败: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取OpenAI模型信息"""
        return {
            'provider': 'OpenAI',
            'model': self.config.model_name,
            'capabilities': ['chat', 'completion', 'streaming']
        }


class MockLLM(HelloAgentsLLM):
    """模拟LLM - 用于测试和开发"""
    
    def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """模拟调用"""
        last_message = messages[-1]['content'] if messages else ""
        return f"这是对'{last_message}'的模拟回答。"
    
    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> Iterator[str]:
        """模拟流式调用"""
        last_message = messages[-1]['content'] if messages else ""
        response = f"这是对'{last_message}'的模拟流式回答。"
        for char in response:
            yield char
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取模拟模型信息"""
        return {
            'provider': 'Mock',
            'model': 'mock-model',
            'capabilities': ['chat', 'completion', 'streaming']
        }


class LLMFactory:
    """LLM工厂类"""
    
    @staticmethod
    def create_llm(llm_type: str = "openai", config: Optional[LLMConfig] = None) -> HelloAgentsLLM:
        """创建LLM实例"""
        
        if llm_type.lower() == "openai":
            return OpenAIClient(config)
        elif llm_type.lower() == "mock":
            return MockLLM(config)
        else:
            raise ValueError(f"不支持的LLM类型: {llm_type}")
    
    @staticmethod
    def from_config(config_dict: Dict[str, Any]) -> HelloAgentsLLM:
        """从配置字典创建LLM实例"""
        llm_type = config_dict.get('type', 'openai')
        llm_config = LLMConfig(**{k: v for k, v in config_dict.items() if k != 'type'})
        return LLMFactory.create_llm(llm_type, llm_config)