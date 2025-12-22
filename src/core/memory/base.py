import logging
from typing import List, Iterable, Optional, Callable

from .memory_item import MemoryItem
from .memory_type import MemoryType

logger = logging.getLogger(__name__)


class BaseMemory:
    """
    BaseMemory = 内存态记忆容器（无 IO）
    - 以 MemoryItem 为唯一数据单元
    - 不负责加载 / 持久化
    """

    def __init__(self) -> None:
        self._items: List[MemoryItem] = []

    # =========================
    # 基础操作
    # =========================

    def add(self, item: MemoryItem) -> None:
        """添加一条记忆"""
        self._items.append(item)

    def extend(self, items: Iterable[MemoryItem]) -> None:
        """批量添加记忆"""
        self._items.extend(items)

    def all(self) -> List[MemoryItem]:
        """返回全部记忆（引用拷贝）"""
        return list(self._items)

    def clear(self) -> None:
        """清空所有记忆（慎用）"""
        self._items.clear()

    # =========================
    # 查询能力
    # =========================

    def filter(
            self,
            *,
            role: Optional[str] = None,
            memory_type: Optional[MemoryType] = None,
            predicate: Optional[Callable[[MemoryItem], bool]] = None,
    ) -> List[MemoryItem]:
        """
        通用过滤接口
        """
        result = self._items

        if role is not None:
            result = [m for m in result if m.role == role]

        if memory_type is not None:
            result = [m for m in result if m.memory_type == memory_type]

        if predicate is not None:
            result = [m for m in result if predicate(m)]

        return result

    # =========================
    # 短期 / 长期操作
    # =========================

    def get_short_term(self) -> List[MemoryItem]:
        return self.filter(memory_type=MemoryType.SHORT_TERM)

    def get_long_term(self) -> List[MemoryItem]:
        return self.filter(memory_type=MemoryType.LONG_TERM)

    def drop_short_term(self) -> None:
        """清除所有短期记忆"""
        before = len(self._items)
        self._items = [
            m for m in self._items
            if m.memory_type != MemoryType.SHORT_TERM
        ]
        after = len(self._items)
        logger.debug("Dropped %s short-term memories", before - after)

    # =========================
    # 高级能力（给 Manager / Session 用）
    # =========================

    def snapshot(self) -> List[MemoryItem]:
        """
        获取当前内存快照（用于 flush）
        """
        return list(self._items)

    def load_snapshot(self, items: Iterable[MemoryItem]) -> None:
        """
        从外部加载一组 MemoryItem（Manager 使用）
        """
        self.clear()
        self.extend(items)

    # =========================
    # 调试 / 可视化
    # =========================

    def __len__(self) -> int:
        return len(self._items)

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} size={len(self._items)}>"
