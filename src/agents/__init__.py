"""
HelloAgents - 智能体开发框架

一个模块化、可扩展的智能体系统框架，支持多种智能体模式和工具集成。

主要组件：
- base: 核心框架层（Agent基类、LLM接口、消息系统等）
- impls: 智能体实现层（SimpleAgent、ReActAgent等）
- tools: 工具系统层（工具注册、异步执行器等）

快速开始：
```python
from impls import SimpleAgent, BaseLLM

# 创建LLM实例
llm = BaseLLM()

# 创建简单智能体
agent = SimpleAgent("助手", llm)

# 运行对话
response = agent.run("你好！")
print(response)
```
"""

from src.agents.base import (
    BaseAgent, AgentState,
    BaseLLM, Message, ConversationHistory
)
from src.agents.impls import (
    SimpleAgent, ReActAgent, ReflectionAgent, PlanAndSolveAgent,
)

__version__ = "1.0.0"
__author__ = "HelloAgents Team"

__all__ = [
    # Core components
    'BaseAgent',
    'AgentState',
    'BaseLLM',
    'Message',
    'ConversationHistory',

    # Agent实现和工厂
    'SimpleAgent',
    'ReActAgent',
    'ReflectionAgent',
    'PlanAndSolveAgent'

    # Tools
    'ToolRegistry'
]
