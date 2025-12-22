import logging
from typing import List, Iterable, Optional

from .base import BaseMemory
from .memory_item import MemoryItem
from .memory_type import MemoryType

logger = logging.getLogger(__name__)


class SessionMemory(BaseMemory):
    """
    SessionMemory = 会话级唯一记忆容器
    - 所有 AgentMemory 的事实来源
    - 不做 IO
    - 不自动触发总结 / flush
    """

    def __init__(self, session_id: str) -> None:
        super().__init__()
        self.session_id = session_id

    # =========================
    # 会话级写入（user / system / agent）
    # =========================

    def remember(
            self,
            *,
            role: str,
            content,
            memory_type: MemoryType = MemoryType.SHORT_TERM,
            metadata: Optional[dict] = None,
    ) -> MemoryItem:
        """
        会话级写入入口（user / system / agent 都可用）
        """
        item = MemoryItem(
            session_id=self.session_id,
            role=role,
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )
        self.add(item)
        return item

    # =========================
    # 会话级查询
    # =========================

    def by_role(self, role: str) -> List[MemoryItem]:
        return self.filter(role=role)

    def short_term(self) -> List[MemoryItem]:
        return self.get_short_term()

    def long_term(self) -> List[MemoryItem]:
        return self.get_long_term()

    # =========================
    # 短期 → 长期 机制（不自动触发）
    # =========================

    def promote(
            self,
            items: Iterable[MemoryItem],
            *,
            reason: Optional[str] = None,
    ) -> None:
        """
        将指定 MemoryItem 提升为长期记忆
        """
        for item in items:
            if item.memory_type == MemoryType.LONG_TERM:
                continue

            item.memory_type = MemoryType.LONG_TERM
            if reason:
                item.metadata.setdefault("promotion_reason", reason)

    def promote_by_ids(
            self,
            ids: Iterable[str],
            *,
            reason: Optional[str] = None,
    ) -> None:
        id_set = set(ids)
        self.promote(
            (m for m in self._items if m.id in id_set),
            reason=reason,
        )

    # =========================
    # 清理策略（供 Manager 调用）
    # =========================

    def drop_short_term(
            self,
            *,
            keep_last_n: Optional[int] = None,
    ) -> None:
        """
        清理短期记忆
        - keep_last_n: 保留最近 N 条短期记忆
        """
        if keep_last_n is None:
            super().drop_short_term()
            return

        short_terms = sorted(
            self.get_short_term(),
            key=lambda m: m.timestamp,
        )

        to_keep = set(m.id for m in short_terms[-keep_last_n:])

        before = len(self._items)
        self._items = [
            m for m in self._items
            if m.memory_type == MemoryType.LONG_TERM or m.id in to_keep
        ]
        after = len(self._items)

        logger.debug(
            "SessionMemory %s dropped %s short-term memories",
            self.session_id,
            before - after,
        )

    # =========================
    # 可观测性
    # =========================

    def stats(self) -> dict:
        """
        会话记忆统计（给调试 / dashboard）
        """
        return {
            "session_id": self.session_id,
            "total": len(self),
            "short_term": len(self.get_short_term()),
            "long_term": len(self.get_long_term()),
        }

    def __repr__(self) -> str:
        return (
            f"<SessionMemory "
            f"session_id={self.session_id} "
            f"size={len(self)}>"
        )
