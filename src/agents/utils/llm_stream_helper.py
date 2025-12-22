"""
LLM流式调用助手
提供统一的流式调用接口，支持实时展示AI响应
"""

from typing import List, Dict, Iterator, Optional
from src.agents.base.base_llm import BaseLLM


class LLMStreamHelper:
    """LLM流式调用助手"""
    
    @staticmethod
    def think(llm: BaseLLM, messages: List[Dict[str, str]], temperature: float = 0) -> str:
        """
        调用大语言模型进行思考，并返回其响应。
        支持流式输出展示效果。
        
        Args:
            llm: LLM实例
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            完整的响应内容
        """
        print(f"🧠 正在调用 {type(llm).__name__} 模型...")
        
        # 准备调用参数
        kwargs = {}
        if temperature != 0:
            kwargs['temperature'] = temperature
        
        try:
            # 优先使用流式调用
            if hasattr(llm, 'stream_invoke'):
                print("✅ 大语言模型响应成功:")
                collected_content = []
                
                for chunk in llm.stream_invoke(messages, **kwargs):
                    print(chunk, end="", flush=True)
                    collected_content.append(chunk)
                
                print()  # 在流式输出结束后换行
                return "".join(collected_content)
            else:
                # 回退到普通调用
                response = llm.invoke(messages, **kwargs)
                print(f"✅ LLM调用成功: {response}")
                return response
                
        except Exception as e:
            print(f"❌ 调用LLM API时发生错误: {e}")
            return None
    
    @staticmethod
    def stream_think(llm: BaseLLM, messages: List[Dict[str, str]], temperature: float = 0) -> Iterator[str]:
        """
        流式调用大语言模型，返回生成器。
        
        Args:
            llm: LLM实例
            messages: 消息列表
            temperature: 温度参数
            
        Returns:
            响应内容的生成器
        """
        # 准备调用参数
        kwargs = {}
        if temperature != 0:
            kwargs['temperature'] = temperature
        
        try:
            if hasattr(llm, 'stream_invoke'):
                yield from llm.stream_invoke(messages, **kwargs)
            else:
                # 如果LLM不支持流式调用，将完整响应作为单个块返回
                response = llm.invoke(messages, **kwargs)
                yield response
        except Exception as e:
            yield f"❌ 调用LLM API时发生错误: {e}"


# 便捷函数
def think_with_llm(llm: BaseLLM, messages: List[Dict[str, str]], temperature: float = 0) -> str:
    """便捷函数：使用LLM进行思考"""
    return LLMStreamHelper.think(llm, messages, temperature)


def stream_think_with_llm(llm: BaseLLM, messages: List[Dict[str, str]], temperature: float = 0) -> Iterator[str]:
    """便捷函数：流式调用LLM进行思考"""
    return LLMStreamHelper.stream_think(llm, messages, temperature)