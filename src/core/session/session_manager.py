import asyncio
import logging
from typing import Dict, Optional

from src.agents.base.base_agent import BaseAgent
from .session_context import SessionContext  # 引入 SessionContext

logger = logging.getLogger(__name__)


class SessionManager:
    """
    会话编排器 - 管理多个智能体在同一会话中的行为
    """

    def __init__(self, session_id: str, context: Optional[SessionContext] = None):
        self.session_id = session_id
        self.context = context or SessionContext(session_id=session_id)  # 使用 SessionContext
        self.agents: Dict[str, BaseAgent] = {}  # 会话内所有智能体
        self._lock = asyncio.Lock()

    # ==================== Agent 管理 ====================

    async def add_agent(self, agent: BaseAgent):
        """将 Agent 拉入会话"""
        self.agents[agent.agent_id] = agent
        agent.session_id = self.session_id
        logger.info(f"Agent {agent.agent_id} 已加入 session {self.session_id}")

    async def remove_agent(self, agent_id: str):
        """移除 Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            logger.info(f"Agent {agent_id} 已从 session {self.session_id} 移除")

    # ==================== 发言权控制 ====================

    async def acquire_speaking(self, agent_id: str):
        """申请发言权"""
        async with self._lock:
            if self.context.speaking_agent_id:
                raise RuntimeError(f"已有 Agent 正在发言: {self.context.speaking_agent_id}")
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} 不在会话中")
            self.context.speaking_agent_id = agent_id
            logger.info(f"Agent {agent_id} 获得发言权")

    async def release_speaking(self, agent_id: str):
        """释放发言权"""
        async with self._lock:
            if self.context.speaking_agent_id != agent_id:
                return
            self.context.speaking_agent_id = None
            logger.info(f"Agent {agent_id} 释放发言权")

    # ==================== 用户打断 ====================

    async def interrupt(self):
        """用户打断当前发言 Agent"""
        async with self._lock:
            if not self.context.speaking_agent_id:
                logger.info("当前没有 Agent 正在发言，无需打断")
                return
            agent_id = self.context.speaking_agent_id
            agent = self.agents.get(agent_id)
            if agent and hasattr(agent, "stop"):
                agent.stop()
            self.context.speaking_agent_id = None
            logger.info(f"Agent {agent_id} 被用户打断")

    # ==================== 消息处理 ====================

    async def handle_user_message(self, message: str):
        """
        处理用户消息
        - 如果 @AgentX 格式 → 切换 active
        - 普通消息 → 默认 active Agent 回答
        """
        async with self._lock:
            if self.context.speaking_agent_id:
                raise RuntimeError("请先打断当前发言 Agent")

            # 检查 @AgentX 指令
            if message.startswith("@"):
                agent_id, content = self._parse_mention(message)
                await self.activate_agent(agent_id)
                return await self._dispatch(agent_id, content)

            # 默认 active Agent
            if not self.context.active_agent_id:
                raise RuntimeError("当前没有 active Agent")
            return await self._dispatch(self.context.active_agent_id, message)

    async def _dispatch(self, agent_id: str, content: str):
        """统一消息派发"""
        agent = self.agents[agent_id]
        await self.acquire_speaking(agent_id)
        try:
            # 调用 Agent 流式或非流式接口
            if hasattr(agent, "process_stream"):
                async for chunk in agent.process_stream(content):
                    yield chunk
            elif hasattr(agent, "process"):
                result = await agent.process(content)
                yield result
            else:
                raise RuntimeError(f"Agent {agent_id} 不支持处理接口")
        finally:
            await self.release_speaking(agent_id)

    @staticmethod
    def _parse_mention(message: str) -> tuple[str, str]:
        """
        解析 @AgentID 消息格式
        例: "@AgentX 你好" -> ("AgentX", "你好")
        """
        parts = message.split(maxsplit=1)
        agent_id = parts[0][1:]  # 去掉 @
        content = parts[1] if len(parts) > 1 else ""
        return agent_id, content
