import json
import logging
import time
from pathlib import Path
from typing import List

from .agent_memory import AgentMemory
from .memory_item import MemoryItem
from .session_memory import SessionMemory

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    MemoryManager = 记忆系统唯一中控
    - 唯一负责 IO
    - 唯一负责 session 生命周期
    """

    def __init__(
            self,
            *,
            base_dir: str,
            auto_flush: bool = True,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

        self.auto_flush = auto_flush
        self._sessions: dict[str, SessionMemory] = {}

    # =========================
    # Session 生命周期
    # =========================

    def load_session(self, session_id: str) -> SessionMemory:
        """
        加载或创建 SessionMemory
        """
        if session_id in self._sessions:
            return self._sessions[session_id]

        session_memory = SessionMemory(session_id=session_id)

        file_path = self._session_file(session_id)
        if file_path.exists():
            items = self._load_from_file(file_path)
            session_memory.load_snapshot(items)
            logger.info("Loaded session %s with %s memories", session_id, len(items))
        else:
            logger.info("Created new session %s", session_id)

        self._sessions[session_id] = session_memory
        return session_memory

    def flush_session(self, session_id: str) -> None:
        """
        将 session 的所有记忆写回文件
        """
        session_memory = self._sessions.get(session_id)
        if not session_memory:
            return

        file_path = self._session_file(session_id)
        self._save_to_file(
            file_path,
            session_id=session_id,
            items=session_memory.snapshot(),
        )
        logger.info(
            "Flushed session %s (%s memories)",
            session_id,
            len(session_memory),
        )

    def close_session(self, session_id: str) -> None:
        """
        关闭 session（flush + 释放内存）
        """
        if self.auto_flush:
            self.flush_session(session_id)
        self._sessions.pop(session_id, None)

    # =========================
    # Agent 生命周期
    # =========================

    def agent_enter(
            self,
            *,
            session_id: str,
            agent_id: str,
    ) -> AgentMemory:
        """
        Agent 进入 session
        """
        session_memory = self.load_session(session_id)
        return AgentMemory(
            agent_id=agent_id,
            session_id=session_id,
            session_memory=session_memory,
        )

    def agent_leave(
            self,
            *,
            session_id: str,
            agent_id: str,
    ) -> None:
        """
        Agent 离开 session
        - 不做 agent 级写入
        - 是否 flush 由 session 决定
        """
        logger.debug("Agent %s left session %s", agent_id, session_id)

    # =========================
    # 短期 → 长期 策略（默认）
    # =========================

    def promote_short_term(
            self,
            session_id: str,
            *,
            min_short_term: int = 20,
            promote_last_n: int = 5,
            reason: str = "auto_promote",
    ) -> None:
        """
        默认短期 → 长期策略
        """
        session_memory = self._sessions.get(session_id)
        if not session_memory:
            return

        short_terms = session_memory.short_term()
        if len(short_terms) < min_short_term:
            return

        to_promote = sorted(
            short_terms,
            key=lambda m: m.timestamp,
        )[-promote_last_n:]

        session_memory.promote(to_promote, reason=reason)

        logger.info(
            "Promoted %s memories to long-term in session %s",
            len(to_promote),
            session_id,
        )

    # =========================
    # 内部：文件 IO
    # =========================

    def _session_file(self, session_id: str) -> Path:
        return self.base_dir / f"{session_id}.json"

    def _load_from_file(self, path: Path) -> List[MemoryItem]:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)

        items = []
        for raw in data.get("memories", []):
            items.append(MemoryItem(**raw))
        return items

    def _save_to_file(
            self,
            path: Path,
            *,
            session_id: str,
            items: List[MemoryItem],
    ) -> None:
        payload = {
            "session_id": session_id,
            "version": 1,
            "updated_at": time.time(),
            "memories": [self._serialize_item(m) for m in items],
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def _serialize_item(self, item: MemoryItem) -> dict:
        return {
            "id": item.id,
            "session_id": item.session_id,
            "role": item.role,
            "content": item.content,
            "memory_type": item.memory_type.value,
            "timestamp": item.timestamp,
            "metadata": item.metadata,
        }
