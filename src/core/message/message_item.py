# src/core/message/message_item.py
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

from .message_target import MessageTarget
from .message_type import MessageType


@dataclass
class MessageItem:
    """
    会话内通信的最小事实单元（瞬时，不默认持久化）

    核心原则：
    - MessageBus 只负责：入队 + 分发（不解析 payload，不关心业务语义）
    - 业务语义统一放 metadata（event/subtype/stream/persist/visibility/...）
    - payload 允许任何类型（str/dict/command/object），由消费者解释
    - 默认不持久化：是否持久化由 metadata["persist"] 决定（默认 False）

    字段概览：
    1) 标识：
      - id: 消息唯一 ID
      - session_id: 会话 ID（MessageBus 会校验一致性）
    2) 发送方：
      - sender_id: user / agent_id / system / tool / frontend ...
      - sender_type: MessageType（粗粒度来源/语义类型）
    3) 接收方（路由）：
      - target: MessageTarget（BROADCAST / AGENT / SYSTEM / FRONTEND / LOGGER）
      - target_id: target=AGENT 时必填
    4) 内容：
      - payload: 任意（str/dict/对象）
    5) 元信息：
      - timestamp: 产生时间
      - metadata: 高层语义与控制信息（推荐规范见下）

    推荐 metadata 规范（统一字段）：
    - event: 高层事件类型（USER_INPUT / AGENT_OUTPUT / CONTROL / TOOL_CALL / TOOL_RESULT / ERROR）
    - subtype: 子类型（例如 CONTROL:CANCEL，AGENT_OUTPUT:TEXT，ERROR:MODEL_ERROR）
    - stream: dict（用于流式：is_chunk/seq/final）
    - persist: bool（是否持久化；默认 False）
    - visibility: "frontend" | "internal" | "both"（默认 both）
    - trace_id: 一次请求链路 ID
    - turn_id: 一轮对话 ID
    - tags/debug/extra/...：按需扩展
    """

    # ========= 1) 标识 =========

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    """消息唯一 ID（用于日志/追踪/去重/关联）"""

    session_id: str = ""
    """所属会话 ID（MessageBus 会校验 message.session_id == bus.session_id）"""

    # ========= 2) 发送方 =========

    sender_id: str = ""
    """发送者 ID：user / agent_id / system / frontend / tool 等"""

    sender_type: MessageType = MessageType.AGENT
    """
    发送者类型（粗粒度来源/语义类型）：
    - USER / AGENT / SYSTEM
    - CONTROL：非自然语言控制指令
    - EVENT：内部事件/状态变更/观测信息
    """

    # ========= 3) 接收方（路由） =========

    target: MessageTarget = MessageTarget.BROADCAST
    """
    路由目标：
    - BROADCAST：广播（所有 subscriber_id；同时 broadcast_subscribers 永远会先收到）
    - AGENT：定向 agent（target_id 必填）
    - SYSTEM：session/orchestrator（约定 subscriber_id 为 "system"/"session"）
    - FRONTEND：仅前端订阅者（建议 subscriber_id="frontend"）
    - LOGGER：仅日志/观测订阅者（建议 subscriber_id="logger"）
    """

    target_id: Optional[str] = None
    """当 target == AGENT 时必填，表示目标 agent_id"""

    # ========= 4) 内容 =========

    payload: Any = None
    """
    消息载荷：
    - str：文本/提示
    - dict：结构化数据（tool call/result、错误、状态等）
    - object：自定义对象/命令（慎用，注意可序列化与日志可读性）
    """

    # ========= 5) 元信息 =========

    timestamp: float = field(default_factory=time.time)
    """消息生成时间（epoch seconds）"""

    metadata: Dict[str, Any] = field(default_factory=dict)
    """高层语义与控制信息（见类注释推荐规范）"""

    # =========================
    # 路由/语义辅助（基础）
    # =========================

    def is_broadcast(self) -> bool:
        """是否广播消息（target=BROADCAST）"""
        return self.target == MessageTarget.BROADCAST

    def is_direct(self) -> bool:
        """是否定向消息（target=AGENT 且 target_id 不为空）"""
        return self.target == MessageTarget.AGENT and self.target_id is not None

    def is_system_sender(self) -> bool:
        """发送方是否系统（sender_type=SYSTEM）"""
        return self.sender_type == MessageType.SYSTEM

    def is_control_sender(self) -> bool:
        """发送方是否控制/系统类（sender_type in {SYSTEM, CONTROL}）"""
        return self.sender_type in {MessageType.SYSTEM, MessageType.CONTROL}

    # =========================
    # 事件语义 helpers（推荐）
    # =========================

    @property
    def event(self) -> Optional[str]:
        """
        高层事件类型（metadata["event"]）：
        USER_INPUT / AGENT_OUTPUT / CONTROL / TOOL_CALL / TOOL_RESULT / ERROR
        """
        v = self.metadata.get("event")
        return str(v) if v is not None else None

    @property
    def subtype(self) -> Optional[str]:
        """
        子类型（metadata["subtype"]）：
        - CONTROL: CANCEL / RETRY / HANDOVER / SWITCH_AGENT / SET_PERSONA / CLEAR_CONTEXT ...
        - AGENT_OUTPUT: TEXT / JSON / ...
        - ERROR: MODEL_ERROR / TOOL_ERROR / VALIDATION_ERROR ...
        """
        v = self.metadata.get("subtype")
        return str(v) if v is not None else None

    @property
    def stream(self) -> Dict[str, Any]:
        """
        流式控制信息（metadata["stream"]，dict）：
        - is_chunk: bool 是否为流式分片
        - seq: int 分片序号
        - final: bool 是否最终包（可选）
        """
        v = self.metadata.get("stream")
        return v if isinstance(v, dict) else {}

    def is_chunk(self) -> bool:
        """是否为流式分片（stream.is_chunk=True）"""
        return bool(self.stream.get("is_chunk", False))

    def is_final(self) -> bool:
        """
        是否为最终输出：
        - 若 stream 明确给 final，则以 final 为准
        - 否则默认：非 chunk 即 final
        """
        if "final" in self.stream:
            return bool(self.stream["final"])
        return not self.is_chunk()

    def should_persist(self) -> bool:
        """
        是否需要持久化（metadata["persist"]）：
        - 默认 False（与“瞬时，不默认持久化”一致）
        - SessionRecorder/MemoryRecorder 可只处理 persist=True 的消息
        """
        return bool(self.metadata.get("persist", False))

    def visibility(self) -> str:
        """
        可见性（metadata["visibility"]）：
        - frontend：仅前端可见
        - internal：仅内部可见
        - both：两者都可见（默认）
        """
        return str(self.metadata.get("visibility", "both"))

    def is_frontend_visible(self) -> bool:
        """前端是否应渲染此消息（visibility=frontend/both）"""
        return self.visibility() in ("frontend", "both")

    def with_meta(self, **kwargs) -> "MessageItem":
        """
        便捷补充 metadata（浅合并，会覆盖同名 key）
        """
        self.metadata.update(kwargs)
        return self

    # =========================
    # 调试输出
    # =========================

    def __repr__(self) -> str:
        return (
            f"<MessageItem id={self.id} "
            f"sender={self.sender_id}/{self.sender_type.value} "
            f"target={self.target.value} "
            f"event={self.event} "
            f"payload_type={type(self.payload).__name__}>"
        )
