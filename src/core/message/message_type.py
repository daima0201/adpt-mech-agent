# src/core/message/message_type.py
from enum import Enum


class MessageType(str, Enum):
    """
    消息发送者 / 语义类型（“谁发的/大概语义”）

    说明：
    - USER/AGENT/SYSTEM：自然语言或系统输出的来源
    - CONTROL：控制指令（非自然语言的命令，例如 CANCEL/HANDOVER）
    - EVENT：内部事件/状态变更（用于观测、指标、状态广播）
    """
    USER = "user"
    AGENT = "agent"
    SYSTEM = "system"
    SESSION = "session"  # 会话编排器（SessionRuntime）

    CONTROL = "control"  # 非自然语言指令
    EVENT = "event"  # 内部事件 / 状态变更
