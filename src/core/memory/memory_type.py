from enum import Enum


class MemoryType(str, Enum):
    """
    记忆生命周期类型
    """

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"

    @classmethod
    def from_value(cls, value: str) -> "MemoryType":
        """
        从字符串安全反序列化（用于文件加载）
        """
        try:
            return cls(value)
        except ValueError:
            raise ValueError(f"Unknown MemoryType: {value}")
