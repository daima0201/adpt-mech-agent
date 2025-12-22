"""
HelloAgents 核心框架模块
提供智能体系统的基础组件和接口定义
"""

from src.agents.base.base_agent import BaseAgent
from src.agents.base.base_llm import BaseLLM
from src.agents.base.base_message import Message, MessageType, ConversationHistory
from src.agents.enum.agent_state import AgentState
from src.shared.exceptions import (
    AgentError,
    ToolExecutionError,
    LLMError,
    ConfigurationError,
    ValidationError
)

# 具体的Agent实现在impls模块中，这里只提供基类和接口

__all__ = [
    # Agent基类和接口
    'BaseAgent', 'AgentState',

    # LLM相关
    'BaseLLM',

    # 消息系统
    'Message', 'MessageType', 'ConversationHistory',

    # 智能体状态
    'AgentState',

    # 异常体系
    'AgentError', 'ToolExecutionError', 'LLMError', 'ConfigurationError', 'ValidationError'
]
