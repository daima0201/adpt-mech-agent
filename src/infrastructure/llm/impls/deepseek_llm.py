"""
DeepSeek LLM实现
"""

from typing import List, Dict, Any, Optional, Iterator, AsyncIterator
from src.agents.base.base_llm import BaseLLM, LLMConfig


class DeepSeekClient(BaseLLM):
    """DeepSeek客户端实现"""
    
    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config)
        self._client = None
    
    async def _get_client(self):
        """获取DeepSeek客户端实例"""
        if self._client is None:
            try:
                import openai
                # DeepSeek使用OpenAI兼容的API格式
                client_config = {
                    'api_key': self.config.api_key,
                    'base_url': 'https://api.deepseek.com'
                }
                self._client = openai.AsyncOpenAI(**client_config)
            except ImportError:
                raise ImportError("请安装openai包: pip install openai")
        return self._client
    
    async def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """异步调用DeepSeek API"""
        client = await self._get_client()
        
        # 合并配置参数
        params = {
            'model': self.config.model_name or 'deepseek-chat',
            'messages': messages,
            'temperature': float(self.config.temperature) if self.config.temperature else 0.7,
            'max_tokens': self.config.max_tokens,
            'timeout': self.config.timeout
        }
        params.update(kwargs)
        
        try:
            response = await client.chat.completions.create(**params)
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"DeepSeek调用失败: {str(e)}")
    
    async def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterator[str]:
        """异步流式调用DeepSeek API"""
        from typing import AsyncIterator
        
        client = await self._get_client()
        
        params = {
            'model': self.config.model_name or 'deepseek-chat',
            'messages': messages,
            'temperature': float(self.config.temperature) if self.config.temperature else 0.7,
            'max_tokens': self.config.max_tokens,
            'stream': True,
            'timeout': self.config.timeout
        }
        params.update(kwargs)
        
        try:
            response = await client.chat.completions.create(**params)
            async for chunk in response:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            raise Exception(f"DeepSeek流式调用失败: {str(e)}")
    
    def get_model_info(self) -> Dict[str, Any]:
        """获取DeepSeek模型信息"""
        return {
            'provider': 'DeepSeek',
            'model': self.config.model_name or 'deepseek-chat',
            'capabilities': ['chat', 'completion', 'streaming']
        }