# src/core/message/message_target.py
from enum import Enum


class MessageTarget(str, Enum):
    """
    消息路由目标（“发给谁”）

    BROADCAST：
      - 发给 session 内所有 subscriber_id（你的 MessageBus 会遍历 _subscribers.values()）
      - 也会先发给所有 broadcast_subscribers（旁路监听）

    AGENT：
      - 定向发给某个 agent（MessageItem.target_id 必填）

    SYSTEM：
      - 发给 session/orchestrator（你约定 subscriber_id 为 "system"/"session"）

    FRONTEND（可选）：
      - 仅给前端订阅者（用于减少前端不关心的内部消息）
      - 推荐约定 subscriber_id 为 "frontend"

    LOGGER（可选）：
      - 仅给日志/观测订阅者（用于隔离内部观测流）
      - 推荐约定 subscriber_id 为 "logger"
    """
    BROADCAST = "broadcast"  # session 内所有 subscriber
    AGENT = "agent"  # 指定 agent
    SYSTEM = "system"  # 系统级服务（SessionManager/ToolRunner/全局编排）

    SESSION = "session"  # 会话编排器（SessionRuntime）
    FRONTEND = "frontend"  # 只给前端订阅者（可选）
    LOGGER = "logger"  # 只给日志/观测订阅者（可选）
