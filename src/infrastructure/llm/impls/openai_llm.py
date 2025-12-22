"""
OpenAI LLM实现
"""

from typing import List, Dict, Any, Optional, AsyncIterable

from src.agents.base.base_llm import BaseLLM, LLMConfig


class OpenAIClient(BaseLLM):
    """OpenAI客户端实现"""

    def __init__(self, config: Optional[LLMConfig] = None):
        super().__init__(config)
        self._client = None

    async def _get_client(self):
        """获取OpenAI客户端实例"""
        if self._client is None:
            try:
                import openai
                client_config = {}
                if self.config.api_key:
                    client_config['api_key'] = self.config.api_key
                if self.config.base_url:
                    client_config['base_url'] = self.config.base_url
                self._client = openai.AsyncOpenAI(**client_config)
            except ImportError:
                raise ImportError("请安装openai包: pip install openai")
        return self._client

    async def invoke(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """异步调用OpenAI API"""
        client = await self._get_client()

        # 合并配置参数
        params = {
            'model': self.config.model_name,
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
            raise Exception(f"OpenAI调用失败: {str(e)}")

    def stream_invoke(self, messages: List[Dict[str, str]], **kwargs) -> AsyncIterable[str]:
        """流式调用OpenAI API"""
        import asyncio

        # 创建一个新的事件循环来运行异步代码
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            # 获取同步客户端
            client = loop.run_until_complete(self._get_client())

            params = {
                'model': self.config.model_name,
                'messages': messages,
                'temperature': float(self.config.temperature) if self.config.temperature else 0.7,
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
        finally:
            loop.close()

    def get_model_info(self) -> Dict[str, Any]:
        """获取OpenAI模型信息"""
        return {
            'provider': 'OpenAI',
            'model': self.config.model_name,
            'capabilities': ['chat', 'completion', 'streaming']
        }
