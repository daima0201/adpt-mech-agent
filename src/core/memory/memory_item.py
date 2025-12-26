import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional


@dataclass
class MemoryItem:
    """
    记忆原子（唯一事实单元）

    设计原则：
    - 一个 MemoryItem = 一个不可再分的记忆事实
    - 长期 / 短期是 MemoryItem 的属性，而不是容器属性
    - persona 通过 memory_scope_id 绑定记忆视角
    """

    # ========= 身份 =========
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # ========= 语义归属 =========
    role: str = "unknown"  # agent_id / user / system
    scope: str = "session"  # session / agent
    """
    memory_scope_id:
    - persona / agent / special purpose 的记忆命名空间
    - 例：
        - persona:quantum_consultant_XXX
        - persona:planner_XXX
        - agent:tool_agent_XXX
    """
    scope_id : str = ""  # session_id / agent_id
    term: str = "short"  # short / long

    # ========= 内容 =========
    content: str = ""
    summary: Optional[str] = None

    # ========= 时间 =========
    timestamp: str = field(
        default_factory=lambda: datetime.utcnow().isoformat() + "Z"
    )

    # ========= 扩展 =========
    metadata: Dict[str, Any] = field(default_factory=dict)

    # ========= 行为 =========

    def promote_to_long(self, summary: Optional[str] = None) -> None:
        """
        将记忆标记为长期记忆（状态变更）
        """
        self.term = "long"
        if summary:
            self.summary = summary

        self.metadata["promoted_at"] = datetime.utcnow().isoformat() + "Z"
        self.metadata["promoted_from"] = "short"

    # ========= 序列化 =========

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "role": self.role,
            "scope": self.scope,
            "term": self.term,
            "content": self.content,
            "summary": self.summary,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "MemoryItem":
        return MemoryItem(
            id=data.get("id", str(uuid.uuid4())),
            role=data.get("role", "unknown"),
            scope=data.get("scope", "session"),
            term=data.get("term", "short"),
            content=data.get("content", ""),
            summary=data.get("summary"),
            timestamp=data.get("timestamp"),
            metadata=data.get("metadata", {}),
        )
