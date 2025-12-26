# src/core/message/message_bus.py
import asyncio
import inspect
import logging
from typing import Callable, Dict, List, Optional, Awaitable, Union

from .message_item import MessageItem
from .message_target import MessageTarget

logger = logging.getLogger(__name__)

SyncSubscriber = Callable[[MessageItem], None]
AsyncSubscriber = Callable[[MessageItem], Awaitable[None]]
Subscriber = Union[SyncSubscriber, AsyncSubscriber]


class MessageBus:
    """
    MessageBus = Session 内消息路由与分发器（升级版）

    目标：
    - publish 不直接调用 subscriber，统一进队列，避免重入
    - 支持同步/异步 subscriber
    - 保留你现有 subscribe/unsubscribe/broadcast 语义
    - 分发顺序稳定，适配流式 chunk + HANDOVER 控制流
    """

    def __init__(self, session_id: str, *, max_queue: int = 10000) -> None:
        self.session_id = session_id

        # subscriber_id -> callbacks
        self._subscribers: Dict[str, List[Subscriber]] = {}
        self._broadcast_subscribers: List[Subscriber] = []

        self._queue: asyncio.Queue[MessageItem] = asyncio.Queue(maxsize=max_queue)
        self._task: Optional[asyncio.Task] = None
        self._closed: bool = False

    # =========================
    # 生命周期
    # =========================

    async def start(self) -> None:
        if self._task:
            return
        self._task = asyncio.create_task(self._loop(), name=f"messagebus[{self.session_id}]")
        logger.info("MessageBus started: session=%s", self.session_id)

    async def close(self) -> None:
        self._closed = True
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass
        logger.info("MessageBus closed: session=%s", self.session_id)

    # =========================
    # 订阅管理
    # =========================

    def subscribe(
            self,
            *,
            subscriber_id: str,
            callback: Subscriber,
            broadcast: bool = False,
    ) -> None:
        """
        注册订阅者
        - broadcast=True：永远收到所有消息（旁路监听：Memory/FE/Logger）
        - broadcast=False：按 subscriber_id 定向接收（agent_id / "system" / "session"）
        """
        if broadcast:
            self._broadcast_subscribers.append(callback)
            logger.debug("Subscriber %s registered for broadcast", subscriber_id)
            return

        self._subscribers.setdefault(subscriber_id, []).append(callback)
        logger.debug("Subscriber %s registered", subscriber_id)

    def unsubscribe(self, *, subscriber_id: str) -> None:
        self._subscribers.pop(subscriber_id, None)
        logger.debug("Subscriber %s removed", subscriber_id)

    # =========================
    # 消息发布
    # =========================

    async def publish(self, message: MessageItem) -> None:
        """
        发布一条消息：只入队，不在调用栈内分发
        """
        self._validate_message(message)

        if self._closed:
            raise RuntimeError("MessageBus is closed")

        # 若未 start，允许直接 start（防止忘记启动）
        if not self._task:
            await self.start()

        await self._queue.put(message)

    # =========================
    # 分发循环
    # =========================

    async def _loop(self) -> None:
        while not self._closed:
            msg = await self._queue.get()
            try:
                await self._dispatch(msg)
            except Exception:
                logger.exception("Dispatch failed: msg=%s", msg)
            finally:
                self._queue.task_done()

    async def _dispatch(self, message: MessageItem) -> None:
        """
        分发顺序：
        1) broadcast_subscribers（旁路监听，保证都能看到）
        2) target 路由（AGENT / SYSTEM / BROADCAST）
        """
        # 1) 旁路广播（永远先发，便于记录日志/记忆/前端）
        for cb in list(self._broadcast_subscribers):
            await self._safe_dispatch(cb, message)

        # 2) target 路由
        if message.target == MessageTarget.BROADCAST:
            # BROADCAST：发给所有 subscriber_id（包括 system/session/agents）
            for callbacks in list(self._subscribers.values()):
                for cb in list(callbacks):
                    await self._safe_dispatch(cb, message)
            return

        if message.target == MessageTarget.AGENT:
            if not message.target_id:
                logger.warning("Message %s missing target_id", message.id)
                return
            callbacks = self._subscribers.get(message.target_id, [])
            for cb in list(callbacks):
                await self._safe_dispatch(cb, message)
            return

        if message.target == MessageTarget.SYSTEM:
            # SYSTEM：约定系统订阅者 id 为 "system"
            callbacks = self._subscribers.get("system", [])
            for cb in list(callbacks):
                await self._safe_dispatch(cb, message)
            return

        if message.target == MessageTarget.SESSION:
            callbacks = self._subscribers.get("session", [])
            for cb in list(callbacks):
                await self._safe_dispatch(cb, message)
            return

        if message.target == MessageTarget.FRONTEND:
            # FRONTEND：仅前端订阅者
            callbacks = self._subscribers.get("frontend", [])
            for cb in list(callbacks):
                await self._safe_dispatch(cb, message)
            return

        if message.target == MessageTarget.LOGGER:
            # LOGGER：仅日志订阅者
            callbacks = self._subscribers.get("logger", [])
            for cb in list(callbacks):
                await self._safe_dispatch(cb, message)
            return

        logger.warning("Unknown target: %s", message.target)

    # =========================
    # 内部工具
    # =========================

    def _validate_message(self, message: MessageItem) -> None:
        if message.session_id != self.session_id:
            raise ValueError(
                f"Message session_id mismatch: {message.session_id} != {self.session_id}"
            )

    @staticmethod
    async def _safe_dispatch(callback: Subscriber, message: MessageItem) -> None:
        try:
            if inspect.iscoroutinefunction(callback):
                await callback(message)  # type: ignore[misc]
            else:
                # 同步 callback 放到线程池也行；这里先直接调用（简单）
                callback(message)  # type: ignore[misc]
        except Exception:
            logger.exception("Error dispatching message %s", message.id)

    # =========================
    # 可观测性
    # =========================

    def stats(self) -> dict:
        return {
            "session_id": self.session_id,
            "subscribers": list(self._subscribers.keys()),
            "broadcast_subscribers": len(self._broadcast_subscribers),
            "queue_size": self._queue.qsize(),
            "running": self._task is not None and not self._task.done(),
        }

    def __repr__(self) -> str:
        return (
            f"<MessageBus session_id={self.session_id} "
            f"subscribers={len(self._subscribers)} "
            f"queue={self._queue.qsize()}>"
        )
