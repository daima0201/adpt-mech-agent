# src/core/message/message_factory.py
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional

from .message_item import MessageItem
from .message_target import MessageTarget
from .message_type import MessageType


# =========================
# 事件类型 & 子类型（可集中维护）
# =========================

@dataclass(frozen=True)
class MessageEvents:
    """
    高层事件类型（metadata["event"]）
    """
    USER_INPUT: str = "USER_INPUT"  # 用户输入
    AGENT_OUTPUT: str = "AGENT_OUTPUT"  # 智能体输出
    CONTROL: str = "CONTROL"  # 控制消息
    TOOL_CALL: str = "TOOL_CALL"  # 工具调用
    TOOL_RESULT: str = "TOOL_RESULT"  # 调用结果
    ERROR: str = "ERROR"  # 报错
    EVENT: str = "EVENT"  # 观测/通知事件（不驱动状态机）


@dataclass(frozen=True)
class OutputSubtypes:
    """AGENT_OUTPUT 子类型（metadata["subtype"]）"""
    TEXT: str = "TEXT"
    JSON: str = "JSON"


@dataclass(frozen=True)
class ControlSubtypes:
    # ---- user/runtime control ----
    CANCEL: str = "CANCEL"
    INTERRUPT: str = "INTERRUPT"
    RETRY: str = "RETRY"
    SWITCH_AGENT: str = "SWITCH_AGENT"
    SET_PERSONA: str = "SET_PERSONA"
    CLEAR_CONTEXT: str = "CLEAR_CONTEXT"

    # ---- handover transaction ----
    HANDOVER_REQUEST: str = "HANDOVER_REQUEST"  # 发起交接请求
    HANDOVER_UI_PROMPT: str = "HANDOVER_UI_PROMPT"
    HANDOVER_CONFIRM: str = "HANDOVER_CONFIRM"  # 用户同意交接
    HANDOVER_REJECT: str = "HANDOVER_REJECT"  # 用户拒绝交接
    HANDOVER_CONTEXT: str = "HANDOVER_CONTEXT"

    # ---- ack (required for orchestration) ----
    INPUT_ACK: str = "INPUT_ACK"
    CANCEL_ACK: str = "CANCEL_ACK"

    # ---- session lifecycle (request/done) ----
    REQUEST_SESSION_OPEN: str = "REQUEST_SESSION_OPEN"
    SESSION_OPENED: str = "SESSION_OPENED"
    REQUEST_SESSION_CLOSE: str = "REQUEST_SESSION_CLOSE"
    SESSION_CLOSED: str = "SESSION_CLOSED"

    # ---- agent resource management (request/done) ----
    REQUEST_ADD_AGENT: str = "REQUEST_ADD_AGENT"
    ADD_AGENT_DONE: str = "ADD_AGENT_DONE"
    ADD_AGENT_FAILED: str = "ADD_AGENT_FAILED"

    REQUEST_REMOVE_AGENT: str = "REQUEST_REMOVE_AGENT"
    REMOVE_AGENT_DONE: str = "REMOVE_AGENT_DONE"
    REMOVE_AGENT_FAILED: str = "REMOVE_AGENT_FAILED"


@dataclass(frozen=True)
class ErrorCodes:
    """ERROR 子类型/错误码（metadata["subtype"]）"""
    MODEL_ERROR: str = "MODEL_ERROR"
    TOOL_ERROR: str = "TOOL_ERROR"
    VALIDATION_ERROR: str = "VALIDATION_ERROR"
    INTERNAL_ERROR: str = "INTERNAL_ERROR"


# =========================
# MessageFactory
# =========================

class MessageFactory:
    """
    统一产消息的工厂（建议：系统内所有 publish 都使用它）

    目的：
    - 让消息“长什么样”统一（metadata 字段统一）
    - 让“有哪些消息”一眼可见（工厂方法即清单）
    - 减少各模块手写 metadata 导致的混乱

    metadata 规范字段：
    - event: MessageEvents.*
    - subtype: 各事件子类型（ControlSubtypes/OutputSubtypes/ErrorCodes 或 tool name）
    - stream: {"is_chunk": bool, "seq": int, "final": bool}
    - persist: bool（默认 False）
    - visibility: "frontend" | "internal" | "both"（默认 both）
    - trace_id: str（同一次请求链路一致）
    - turn_id: str（同一轮对话一致）
    """

    # ---------- ID helpers ----------

    @staticmethod
    def new_trace_id() -> str:
        """生成一次请求链路 trace_id（建议每次 user_input 生成一次）"""
        return str(uuid.uuid4())

    @staticmethod
    def new_turn_id() -> str:
        """生成一轮对话 turn_id（建议每轮 user->assistant 生成一次）"""
        return str(uuid.uuid4())

    # ---------- metadata helper ----------

    @staticmethod
    def _meta(
            *,
            event: str,
            subtype: Optional[str] = None,
            persist: bool = False,
            visibility: str = "both",
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            stream: Optional[Dict[str, Any]] = None,
            origin: str = "system",
            routed_by: Optional[str] = None,
            extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta: Dict[str, Any] = {
            "event": event,
            "persist": persist,
            "visibility": visibility,
            "origin": origin,
        }
        if subtype is not None:
            meta["subtype"] = subtype
        if trace_id is not None:
            meta["trace_id"] = trace_id
        if turn_id is not None:
            meta["turn_id"] = turn_id
        if stream is not None:
            meta["stream"] = stream
        if routed_by:
            meta["routed_by"] = routed_by
        if extra:
            meta.update(extra)
        return meta

    # =========================================================
    # 1) USER_INPUT（用户输入）
    # =========================================================

    @staticmethod
    def user_input(
            *,
            session_id: str,
            user_id: str = "user",
            text: str,
            target: MessageTarget = MessageTarget.SYSTEM,  # ✅ 强编排：先到 SYSTEM
            target_id: Optional[str] = None,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            persist: bool = True,
            visibility: str = "both",
            origin: str = "frontend",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        if target == MessageTarget.AGENT and not target_id:
            raise ValueError("user_input: target_id required when target=AGENT")

        return MessageItem(
            session_id=session_id,
            sender_id=user_id,
            sender_type=MessageType.USER,
            target=target,
            target_id=target_id,
            payload=text,
            metadata=MessageFactory._meta(
                event=MessageEvents.USER_INPUT,
                subtype=None,
                persist=persist,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    # =========================================================
    # 2) AGENT_OUTPUT（强编排：默认不直达前端）
    # =========================================================

    @staticmethod
    def agent_chunk(
            *,
            session_id: str,
            agent_id: str,
            text: str,
            seq: int,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            # ✅ 强编排：先给 SessionRuntime
            target: MessageTarget = MessageTarget.SESSION,
            visibility: str = "internal",
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
            stream: Optional[bool] = True,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=agent_id,
            sender_type=MessageType.AGENT,
            target=target,
            payload=text,
            metadata=MessageFactory._meta(
                event=MessageEvents.AGENT_OUTPUT,
                subtype=OutputSubtypes.TEXT,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                stream={"is_chunk": True, "seq": seq, "final": False},
                origin=origin,
                extra=extra_meta,
            ),
        )

    @staticmethod
    def agent_final(
            *,
            session_id: str,
            agent_id: str,
            text: str,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            # ✅ 强编排：final 也先给 SessionRuntime（让它决定转发/持久化）
            target: MessageTarget = MessageTarget.SESSION,
            visibility: str = "internal",
            persist: bool = True,
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=agent_id,
            sender_type=MessageType.AGENT,
            target=target,
            payload=text,
            metadata=MessageFactory._meta(
                event=MessageEvents.AGENT_OUTPUT,
                subtype=OutputSubtypes.TEXT,
                persist=persist,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                stream={"is_chunk": False, "seq": None, "final": True},
                origin=origin,
                extra=extra_meta,
            ),
        )

    # =========================================================
    # 3) CONTROL
    # =========================================================

    @staticmethod
    def control(
            *,
            session_id: str,
            subtype: str,
            sender_id: str = "system",
            target: MessageTarget = MessageTarget.SYSTEM,
            target_id: Optional[str] = None,
            payload: Any = None,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            persist: bool = False,
            visibility: str = "internal",
            origin: str = "system",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        if target == MessageTarget.AGENT and not target_id:
            raise ValueError("control: target_id required when target=AGENT")

        return MessageItem(
            session_id=session_id,
            sender_id=sender_id,
            sender_type=MessageType.CONTROL,
            target=target,
            target_id=target_id,
            payload=payload,
            metadata=MessageFactory._meta(
                event=MessageEvents.CONTROL,
                subtype=subtype,
                persist=persist,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    @staticmethod
    def handover_request(
            *,
            session_id: str,
            from_agent_id: str,
            reason: str,
            # 可选：建议目标 agent（不是强制）
            to_agent_id: Optional[str] = None,
            # 可选：建议切换到的人格
            next_persona_id: Optional[str] = None,
            trace_id: Optional[str],
            turn_id: Optional[str],
            visibility: str = "internal",
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        """
        HANDOVER_REQUEST：
        - agent → session 的交接请求
        - 不直接生效，必须由 SessionRuntime + Frontend 确认
        """

        payload: Dict[str, Any] = {
            "from_agent": from_agent_id,
            "reason": reason,
        }

        if to_agent_id:
            payload["to_agent"] = to_agent_id
        if next_persona_id:
            payload["next_persona_id"] = next_persona_id

        return MessageItem(
            session_id=session_id,
            sender_id=from_agent_id,
            sender_type=MessageType.CONTROL,
            target=MessageTarget.SESSION,  # ✅ 关键
            payload=payload,
            metadata=MessageFactory._meta(
                event=MessageEvents.CONTROL,
                subtype=ControlSubtypes.HANDOVER_REQUEST,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    # ---- 常用 ACK 工具（避免各处手写 metadata）----

    @staticmethod
    def input_ack(
            *,
            session_id: str,
            agent_id: str,
            trace_id: Optional[str],
            turn_id: Optional[str],
            target: MessageTarget = MessageTarget.SESSION,
            visibility: str = "internal",
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=agent_id,
            sender_type=MessageType.CONTROL,
            target=target,
            payload={"ok": True},
            metadata=MessageFactory._meta(
                event=MessageEvents.CONTROL,
                subtype=ControlSubtypes.INPUT_ACK,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    @staticmethod
    def cancel_ack(
            *,
            session_id: str,
            agent_id: str,
            trace_id: Optional[str],
            turn_id: Optional[str],
            target: MessageTarget = MessageTarget.SESSION,
            visibility: str = "internal",
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=agent_id,
            sender_type=MessageType.CONTROL,
            target=target,
            payload={"ok": True},
            metadata=MessageFactory._meta(
                event=MessageEvents.CONTROL,
                subtype=ControlSubtypes.CANCEL_ACK,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    # =========================================================
    # 4) TOOL_CALL / TOOL_RESULT
    # =========================================================

    @staticmethod
    def tool_call(
            *,
            session_id: str,
            agent_id: str,
            name: str,
            arguments: Dict[str, Any],
            target: MessageTarget = MessageTarget.SYSTEM,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            visibility: str = "internal",
            origin: str = "agent",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=agent_id,
            sender_type=MessageType.AGENT,
            target=target,
            payload={"name": name, "arguments": arguments},
            metadata=MessageFactory._meta(
                event=MessageEvents.TOOL_CALL,
                subtype=name,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    @staticmethod
    def tool_result(
            *,
            session_id: str,
            tool_name: str,
            result: Any,
            sender_id: str = "tool_runner",
            target: MessageTarget = MessageTarget.SYSTEM,
            target_id: Optional[str] = None,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            persist: bool = False,
            visibility: str = "internal",
            origin: str = "tool_runner",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        if target == MessageTarget.AGENT and not target_id:
            raise ValueError("tool_result: target_id required when target=AGENT")

        return MessageItem(
            session_id=session_id,
            sender_id=sender_id,
            sender_type=MessageType.EVENT,
            target=target,
            target_id=target_id,
            payload={"name": tool_name, "result": result},
            metadata=MessageFactory._meta(
                event=MessageEvents.TOOL_RESULT,
                subtype=tool_name,
                persist=persist,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    # =========================================================
    # 5) ERROR
    # =========================================================

    @staticmethod
    def error(
            *,
            session_id: str,
            code: str,
            message: str,
            sender_id: str = "system",
            sender_type: MessageType = MessageType.SYSTEM,
            target: MessageTarget = MessageTarget.SYSTEM,
            target_id: Optional[str] = None,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            visibility: str = "internal",
            origin: str = "system",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        if target == MessageTarget.AGENT and not target_id:
            raise ValueError("error: target_id required when target=AGENT")

        return MessageItem(
            session_id=session_id,
            sender_id=sender_id,
            sender_type=sender_type,
            target=target,
            target_id=target_id,
            payload={"code": code, "message": message},
            metadata=MessageFactory._meta(
                event=MessageEvents.ERROR,
                subtype=code,
                persist=False,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )

    # =========================================================
    # 6) EVENT（观测/通知）
    # =========================================================

    @staticmethod
    def event(
            *,
            session_id: str,
            name: str,
            payload: Any = None,
            sender_id: str = "system",
            target: MessageTarget = MessageTarget.LOGGER,
            trace_id: Optional[str] = None,
            turn_id: Optional[str] = None,
            visibility: str = "internal",
            persist: bool = False,
            origin: str = "system",
            extra_meta: Optional[Dict[str, Any]] = None,
    ) -> MessageItem:
        return MessageItem(
            session_id=session_id,
            sender_id=sender_id,
            sender_type=MessageType.EVENT,
            target=target,
            payload=payload,
            metadata=MessageFactory._meta(
                event=MessageEvents.EVENT,
                subtype=name,
                persist=persist,
                visibility=visibility,
                trace_id=trace_id,
                turn_id=turn_id,
                origin=origin,
                extra=extra_meta,
            ),
        )
