import logging
from typing import List, Optional, Callable

from .base import BaseMemory
from .memory_item import MemoryItem
from .memory_type import MemoryType

logger = logging.getLogger(__name__)


class AgentMemory:
    """
    AgentMemory = 以某个 agent_id 为中心的记忆视图
    - 不直接持久化
    - 所有 MemoryItem 实际存储在 SessionMemory 中
    """

    def __init__(
            self,
            *,
            agent_id: str,
            session_id: str,
            session_memory: BaseMemory,
    ) -> None:
        self.agent_id = agent_id
        self.session_id = session_id
        self._session_memory = session_memory

    # =========================
    # 写入接口
    # =========================

    def remember(
            self,
            content,
            *,
            memory_type: MemoryType = MemoryType.SHORT_TERM,
            metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        写入一条记忆（默认短期）
        """
        item = MemoryItem(
            session_id=self.session_id,
            role=self.agent_id,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )
        self._session_memory.add(item)
        return item

    def remember_long_term(
            self,
            content,
            *,
            metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        明确写入长期记忆
        """
        return self.remember(
            content,
            memory_type=MemoryType.LONG_TERM,
            metadata=metadata,
        )

    # =========================
    # 读取接口（核心）
    # =========================

    def memories(self) -> List[MemoryItem]:
        """
        获取与该 agent 相关的所有记忆
        """
        return self._session_memory.filter(role=self.agent_id)

    def short_term(self) -> List[MemoryItem]:
        return self._session_memory.filter(
            role=self.agent_id,
            memory_type=MemoryType.SHORT_TERM,
        )

    def long_term(self) -> List[MemoryItem]:
        return self._session_memory.filter(
            role=self.agent_id,
            memory_type=MemoryType.LONG_TERM,
        )

    def recent(
            self,
            limit: int = 10,
            *,
            predicate: Optional[Callable[[MemoryItem], bool]] = None,
    ) -> List[MemoryItem]:
        """
        获取最近 N 条记忆（可选条件过滤）
        """
        items = self.memories()
        if predicate:
            items = [m for m in items if predicate(m)]
        return sorted(items, key=lambda m: m.timestamp)[-limit:]

    # =========================
    # 行为辅助接口（给 Agent 用）
    # =========================

    def context_for_llm(
            self,
            *,
            short_term_limit: int = 10,
            include_long_term: bool = True,
    ) -> List[MemoryItem]:
        """
        构建用于 LLM 推理的上下文记忆集合
        """
        context: List[MemoryItem] = []

        if include_long_term:
            context.extend(self.long_term())

        context.extend(self.recent(limit=short_term_limit))

        # 按时间排序，保证上下文自然
        return sorted(context, key=lambda m: m.timestamp)

    # =========================
    # 维护性接口
    # =========================

    def __repr__(self) -> str:
        return f"<AgentMemory agent_id={self.agent_id}>"
