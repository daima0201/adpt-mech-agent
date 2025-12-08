"""
HelloAgents - 智能体开发框架

一个模块化、可扩展的智能体系统框架，支持多种智能体模式和工具集成。

主要组件：
- core: 核心框架层（Agent基类、LLM接口、消息系统等）
- impls: 智能体实现层（SimpleAgent、ReActAgent等）
- tools: 工具系统层（工具注册、异步执行器等）

快速开始：
```python
from impls import SimpleAgent, HelloAgentsLLM

# 创建LLM实例
llm = HelloAgentsLLM()

# 创建简单智能体
agent = SimpleAgent("助手", llm)

# 运行对话
response = agent.run("你好！")
print(response)
```
"""

from src.agents.core import (
    Agent, SimpleAgent, ReActAgent, ReflectionAgent, PlanAndSolveAgent,
    HelloAgentsLLM, Message, ConversationHistory, Config
)
from src.agents.tools import ToolRegistry, CalculatorTool, SearchTool

__version__ = "1.0.0"
__author__ = "HelloAgents Team"

__all__ = [
    # Core components
    'Agent',
    'SimpleAgent', 
    'ReActAgent',
    'ReflectionAgent',
    'PlanAndSolveAgent',
    'HelloAgentsLLM',
    'Message',
    'ConversationHistory',
    'Config',
    
    # Tools
    'ToolRegistry',
    'CalculatorTool',
    'SearchTool'
]