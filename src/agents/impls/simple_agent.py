"""
简单对话Agent实现
基于BaseAgent的基础问答模式智能体
"""

from typing import List, Dict, Any, Optional, Iterator
from src.agents.core.agent import Agent, AgentConfig
from src.agents.core.message import Message, MessageBuilder
from src.agents.core import HelloAgentsLLM


class SimpleAgent(Agent):
    """简单对话Agent - 基础的问答模式"""
    
    def __init__(self, config: AgentConfig, llm: Optional[HelloAgentsLLM] = None):
        super().__init__(config, llm)
    
    async def process_message(self, message: Message) -> Message:
        """处理消息的核心方法（异步）"""
        self.set_state(self.state.THINKING)
        
        try:
            # 构建消息列表
            messages = []
            
            # 添加系统消息
            messages.append({"role": "system", "content": self.config.system_prompt})
            
            # 添加历史消息
            for msg in self.get_message_history():
                messages.append({"role": msg.role, "content": msg.content})
            
            # 添加当前用户消息
            messages.append({"role": "user", "content": message.content})
            
            # 调用LLM
            response = await self.llm.invoke(messages)
            
            # 创建响应消息
            response_message = MessageBuilder.create_assistant_message(response)
            
            # 保存到历史记录
            self.add_message_to_history(message)
            self.add_message_to_history(response_message)
            
            self.logger.info(f"成功处理消息，生成长度: {len(response)}")
            return response_message
            
        except Exception as e:
            self.set_state(self.state.ERROR)
            self.logger.error(f"处理消息失败: {str(e)}")
            error_message = MessageBuilder.create_error_message(f"处理失败: {str(e)}")
            return error_message
        finally:
            self.set_state(self.state.IDLE)
    
    def run(self, input_text: str, **kwargs) -> str:
        """同步运行方法"""
        import asyncio
        
        # 创建用户消息
        user_message = MessageBuilder.create_user_message(input_text)
        
        # 异步处理消息
        response_message = asyncio.run(self.process_message(user_message))
        
        return response_message.content
    
    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """流式运行方法"""
        # 构建消息列表
        messages = []
        
        # 添加系统消息
        messages.append({"role": "system", "content": self.config.system_prompt})
        
        # 添加历史消息
        for msg in self.get_message_history():
            messages.append({"role": msg.role, "content": msg.content})
        
        # 添加当前用户消息
        messages.append({"role": "user", "content": input_text})
        
        # 流式调用LLM
        full_response = ""
        for chunk in self.llm.stream_invoke(messages, **kwargs):
            full_response += chunk
            yield chunk
        
        # 保存完整对话到历史记录
        user_message = MessageBuilder.create_user_message(input_text)
        response_message = MessageBuilder.create_assistant_message(full_response)
        self.add_message_to_history(user_message)
        self.add_message_to_history(response_message)
    
    def run_with_metadata(self, input_text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """带元数据的运行方法"""
        response = self.run(input_text)
        
        return {
            'response': response,
            'input_metadata': metadata or {},
            'history_length': len(self.get_message_history()),
            'agent_name': self.config.name
        }
    
    def batch_run(self, inputs: List[str], **kwargs) -> List[str]:
        """批量处理输入"""
        results = []
        
        for input_text in inputs:
            result = self.run(input_text, **kwargs)
            results.append(result)
        
        return results
    
    def get_conversation_stats(self) -> Dict[str, Any]:
        """获取对话统计信息"""
        history = self.get_message_history()
        user_messages = [msg for msg in history if msg.role == 'user']
        assistant_messages = [msg for msg in history if msg.role == 'assistant']
        
        return {
            'total_messages': len(history),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'average_user_length': sum(len(msg.content) for msg in user_messages) / max(len(user_messages), 1),
            'average_assistant_length': sum(len(msg.content) for msg in assistant_messages) / max(len(assistant_messages), 1)
        }