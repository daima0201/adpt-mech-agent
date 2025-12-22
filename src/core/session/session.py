import asyncio
import logging
from typing import Dict, Optional, Any, List, AsyncGenerator

from src.agents.base.base_agent import BaseAgent

logger = logging.getLogger(__name__)


class Session:
    """
    Session 实体类 - 管理多个智能体在同一会话中的行为

    功能：
    1. 管理会话内多个智能体实例
    2. 控制 active 与 speaking 状态
    3. 支持用户打断 / @Agent 指定发言
    4. 共享记忆库
    5. Agent 间消息传递通过 Session 中转
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.agents: Dict[str, BaseAgent] = {}  # 会话内所有 Agent
        self.active_agent_id: Optional[str] = None  # 当前 active Agent
        self.speaking_agent_id: Optional[str] = None  # 当前发言 Agent
        self.shared_memory: List[Dict[str, Any]] = []  # 会话共享记忆
        self._lock = asyncio.Lock()  # 并发控制锁
        self.user_interruptible: bool = False  # 是否允许用户打断

    # ==================== Agent 管理 ====================

    def add_agent(self, agent: BaseAgent):
        """将 Agent 拉入会话"""
        self.agents[agent.agent_id] = agent
        agent.session_id = self.session_id
        logger.info(f"Agent {agent.agent_id} 已加入 session {self.session_id}")

    def remove_agent(self, agent_id: str):
        """移除 Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            if self.active_agent_id == agent_id:
                self.active_agent_id = None
            if self.speaking_agent_id == agent_id:
                self.speaking_agent_id = None
            logger.info(f"Agent {agent_id} 已从 session {self.session_id} 移除")

    async def activate_agent(self, agent_id: str):
        """切换 active Agent"""
        async with self._lock:
            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} 不在 session 中")

            # 关闭旧 active
            if self.active_agent_id and self.active_agent_id != agent_id:
                old_agent = self.agents[self.active_agent_id]
                old_agent.switch_active(False)

            # 设置新 active
            self.active_agent_id = agent_id
            self.agents[agent_id].switch_active(True)
            logger.info(f"Agent {agent_id} 被设为 active")

    # ==================== 发言权控制 ====================

    async def acquire_speaking(self, agent_id: str):
        """申请发言权"""
        async with self._lock:
            if self.speaking_agent_id:
                raise RuntimeError(f"已有 Agent 正在发言: {self.speaking_agent_id}")

            if agent_id not in self.agents:
                raise ValueError(f"Agent {agent_id} 不在 session 中")

            self.speaking_agent_id = agent_id
            self.user_interruptible = True
            agent = self.agents[agent_id]
            agent.speaking = True
            logger.info(f"Agent {agent_id} 获得发言权")

    async def release_speaking(self, agent_id: str):
        """释放发言权"""
        async with self._lock:
            if self.speaking_agent_id != agent_id:
                return

            agent = self.agents[agent_id]
            agent.speaking = False
            self.speaking_agent_id = None
            self.user_interruptible = False
            logger.info(f"Agent {agent_id} 释放发言权")

    # ==================== 用户打断 ====================

    async def interrupt(self):
        """用户打断当前发言 Agent"""
        async with self._lock:
            if not self.speaking_agent_id:
                logger.info("当前没有 Agent 正在发言，无需打断")
                return

            agent = self.agents[self.speaking_agent_id]
            if hasattr(agent, "stop"):
                agent.stop()
            if hasattr(agent, "release_speaking"):
                await agent.release_speaking()

            logger.info(f"Agent {self.speaking_agent_id} 被用户打断")
            self.speaking_agent_id = None
            self.user_interruptible = False

    # ==================== 消息处理 ====================

    async def handle_user_message(self, message: str):
        """
        处理用户消息
        - 如果 @AgentX 格式 → 切换 active
        - 普通消息 → 默认 active Agent 回答
        """
        async with self._lock:
            if self.speaking_agent_id:
                raise RuntimeError("请先打断当前发言 Agent")

            # 检查 @AgentX 指令
            if message.startswith("@"):
                agent_id, content = self._parse_mention(message)
                await self.activate_agent(agent_id)
                return await self._dispatch(agent_id, content)

            # 默认 active Agent
            if not self.active_agent_id:
                raise RuntimeError("当前没有 active Agent")
            return await self._dispatch(self.active_agent_id, message)

    async def _dispatch(self, agent_id: str, content: str) -> AsyncGenerator[str, None]:
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

    # ==================== 工具方法 ====================

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

    async def broadcast_message(self, message: str):
        """Agent 间广播消息"""
        async with self._lock:
            for agent_id, agent in self.agents.items():
                # 可以添加一个 message 接口
                if hasattr(agent, "process"):
                    await agent.process(f"[广播] {message}")

    async def add_shared_memory(self, entry: Dict[str, Any]):
        """添加共享记忆"""
        async with self._lock:
            self.shared_memory.append(entry)

    async def get_shared_memory(self) -> List[Dict[str, Any]]:
        """获取共享记忆"""
        async with self._lock:
            return list(self.shared_memory)
