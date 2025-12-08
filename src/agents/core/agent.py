"""
Agent基类定义
提供智能体的基础功能和生命周期管理
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from enum import Enum

from src.agents.core.message import Message
from src.agents.core.llm import HelloAgentsLLM
from src.agents.tools import Tool


class AgentState(Enum):
    """Agent状态枚举"""
    IDLE = "idle"           # 空闲状态
    THINKING = "thinking"   # 思考中
    EXECUTING = "executing" # 执行中
    WAITING = "waiting"     # 等待输入
    ERROR = "error"         # 错误状态


@dataclass
class AgentConfig:
    """Agent配置类"""
    name: str
    description: str
    system_prompt: str
    temperature: float = 0.7
    max_tokens: int = 2048
    timeout: int = 60
    retry_count: int = 3
    tools_enabled: bool = True
    memory_enabled: bool = True


class Agent(ABC):
    """
    智能体基类
    所有具体Agent实现的父类
    """
    
    def __init__(self, config: AgentConfig, llm: Optional[HelloAgentsLLM] = None):
        self.config = config
        self.llm = llm or HelloAgentsLLM()
        self.state = AgentState.IDLE
        self.logger = logging.getLogger(f"agent.{config.name}")
        self.message_history: List[Message] = []
        self.available_tools: Dict[str, Tool] = {}
        self._current_task: Optional[str] = None
        self._error_count = 0

    @abstractmethod
    async def process_message(self, message: Message) -> Message:
        """处理消息的抽象方法"""
        pass

    async def add_tool(self, tool: Tool) -> None:
        """添加工具到智能体"""
        self.available_tools[tool.name] = tool
        self.logger.info(f"工具 '{tool.name}' 已添加到智能体")

    async def remove_tool(self, tool_name: str) -> None:
        """从智能体中移除工具"""
        if tool_name in self.available_tools:
            del self.available_tools[tool_name]
            self.logger.info(f"工具 '{tool_name}' 已从智能体移除")

    def get_state(self) -> AgentState:
        """获取当前状态"""
        return self.state

    def set_state(self, state: AgentState) -> None:
        """设置状态"""
        old_state = self.state
        self.state = state
        self.logger.debug(f"状态变更: {old_state.value} -> {state.value}")

    async def reset(self) -> None:
        """重置智能体状态"""
        self.state = AgentState.IDLE
        self.message_history.clear()
        self._current_task = None
        self._error_count = 0
        self.logger.info("智能体已重置")

    def get_message_history(self, limit: Optional[int] = None) -> List[Message]:
        """获取消息历史"""
        if limit:
            return self.message_history[-limit:]
        return self.message_history.copy()

    def add_message_to_history(self, message: Message) -> None:
        """添加消息到历史记录"""
        self.message_history.append(message)
        # 限制历史记录大小
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-50:]

    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具"""
        if not self.config.tools_enabled:
            raise RuntimeError("工具功能未启用")
        
        if tool_name not in self.available_tools:
            raise ValueError(f"工具 '{tool_name}' 不可用")
        
        self.set_state(AgentState.EXECUTING)
        
        try:
            tool = self.available_tools[tool_name]
            result = await tool.execute(**parameters)
            self.logger.info(f"工具 '{tool_name}' 执行成功")
            return result
        except Exception as e:
            self._error_count += 1
            self.logger.error(f"工具 '{tool_name}' 执行失败: {str(e)}")
            raise
        finally:
            self.set_state(AgentState.IDLE)

    def should_retry(self) -> bool:
        """判断是否应该重试"""
        return self._error_count < self.config.retry_count

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "name": self.config.name,
            "state": self.state.value,
            "message_count": len(self.message_history),
            "tool_count": len(self.available_tools),
            "error_count": self._error_count,
            "current_task": self._current_task
        }

    async def close(self) -> None:
        """关闭智能体，释放资源"""
        self.state = AgentState.IDLE
        self.message_history.clear()
        self.available_tools.clear()
        self.logger.info("智能体已关闭")

