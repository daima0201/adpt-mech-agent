import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List, Dict, Optional, AsyncIterator, Tuple

from src.agents.enum.run_time_state import RuntimeState
from src.core.message.message_factory import MessageFactory
from src.core.message.message_item import MessageItem
from src.core.message.message_target import MessageTarget
from src.core.message.message_type import MessageType
from src.core.persona.persona_matrix import PersonaMatrix

logger = logging.getLogger(__name__)


class AgentMetrics:
    """Agent 级统一指标（协议级，不掺业务）"""
    __slots__ = ("total_calls", "total_errors", "total_latency")

    def __init__(self):
        self.total_calls: int = 0
        self.total_errors: int = 0
        self.total_latency: float = 0.0


class BaseAgent(ABC):
    """
    BaseAgent = Agent 的宪法层

    功能：
    - 生命周期管理
    - 状态机管理
    - 并发安全
    - 统一执行入口
    - 指标采集
    - active 属性 & 切换
    """

    def __init__(self, agent_id: str):
        self.agent_id = agent_id

        # ===== Persona（由 Session 注入）=====
        self._persona: Optional["PersonaMatrix"] = None

        # ===== 会话相关（由 Session 注入）=====
        self.session_id: Optional[str] = None
        self.memory_manager = None  # MemoryManager 实例，由 Session 注入
        self.message_bus = None  # MessageBus 实例，由 Session 注入

        # ===== 状态 =====
        self.run_time_state: RuntimeState = RuntimeState.IDLE
        self.active: bool = False  # 当前实例是否 active（可允许被 Session 调度发言/处理任务）
        self.speaking: bool = False  # 当前会话是否正在生成输出
        self._closed = False

        # ===== 指标 =====
        self.metrics = AgentMetrics()
        # 心跳统计数据
        self.heartbeat_stats: Dict[str, Any] = {
            "total_heartbeats": 0,
            "missed_heartbeats": 0,
            "last_missed_at": None,
            "avg_interval": 0.0,
            "min_interval": float('inf'),
            "max_interval": 0.0,
        }

        # ===== 心跳机制 =====
        self._creation_time: float = time.monotonic()
        self._last_heartbeat: float = self._creation_time
        self._heartbeat_interval: float = 30.0  # 秒，可配置

        # ===== 控制 =====
        # initialization_lock: 只保护 initialize
        # _metrix_lock: 保护指标写入流程
        # _process_lock：保护运行全流程
        self._cancel_event = asyncio.Event()
        self.is_initialized = False
        self._initialization_lock = asyncio.Lock()
        self._metrics_lock = asyncio.Lock()
        self._process_lock = asyncio.Lock()

        # ===== @deprecated 历史记忆（新的记忆统一交由session保管，此属性废除） =====
        self.conversation_history: List[Dict[str, str]] = []  # 格式: [{"role": "user/assistant", "content": "..."}]

    async def initialize(self) -> bool:
        """初始化入口（全局只执行一次）"""
        async with self._initialization_lock:
            if self.is_initialized:
                logger.warning(f"Agent {self.agent_id} has already been initialized")
                return True
            await self._customized_initialize()
            self.is_initialized = True
            return True

    # ========= 子类需要实现的方法 =========

    @abstractmethod
    async def _customized_initialize(self):
        """子类初始化"""
        raise NotImplementedError

    # ========= 截断输出 管理 =========

    def _stop(self):
        # 手动截断输出
        self._cancel_event.set()

    def _clear_cancel(self):
        # 清除截断标志
        self._cancel_event.clear()

    def is_canceled(self) -> bool:
        # 是否取消输出
        return self._cancel_event.is_set()

    # ========= Active 管理 =========

    def switch_active(self, value: bool):
        """切换 active 状态"""
        if self.speaking:
            raise RuntimeError("Cannot switch active state while speaking")

        old = self.active
        self.active = value
        logger.info(f"{self.agent_id} active: {old} -> {self.active}")

    def is_active(self) -> bool:
        """检查当前实例是否 active"""
        return self.active

    # ==================== Persona 管理（关键） ====================

    @property
    def persona(self) -> PersonaMatrix:
        if not self._persona:
            raise RuntimeError(f"Agent {self.agent_id} has no PersonaMatrix")
        return self._persona

    def has_persona(self) -> bool:
        return self._persona is not None

    def attach_persona(self, persona: PersonaMatrix):
        """
        Session 注入人格的唯一入口：
        - 校验 persona
        - 绑定 persona
        - 切换 memory scope（人格隔离关键）
        """
        if persona is None:
            raise ValueError("persona cannot be None")
        if self.speaking:
            raise RuntimeError("cannot switch persona while speaking")
        if not self.session_id:
            raise RuntimeError("attach_persona requires agent to be in a Session")
        persona.validate()
        old_id = self._persona.persona_id if self._persona else None
        self._persona = persona

        # 人格切换 = 记忆视角切换（强约束）
        if self.memory_manager is not None:
            if not hasattr(self.memory_manager, "switch_scope"):
                raise AttributeError("memory_manager must implement switch_scope(scope_id: str)")
            self.memory_manager.switch_scope(persona.memory_scope_id)

        logger.info(
            f"{self.agent_id} persona: {old_id} -> {persona.persona_id} (scope={persona.memory_scope_id})"
        )

    def detach_persona(self):
        if self.speaking:
            raise RuntimeError("cannot switch persona while speaking")
        self._persona = None

    # ==================== Persona 消费入口 ====================

    def build_system_prompt(self, context: Optional[dict] = None) -> str:
        """
        BaseAgent 不做策略决策，只负责把 persona 的 prompt 作为“可消费输出”提供给子类。
        依赖 PersonaMatrix.build_system_prompt(context)（建议你在 PersonaMatrix 中提供该纯函数）
        """
        if not hasattr(self.persona, "build_system_prompt"):
            raise AttributeError(
                "PersonaMatrix must have build_system_prompt(context) method"
            )
        return self.persona.build_system_prompt(context or {})

    def get_memories(self, **kwargs):
        """
        统一从 memory_manager 获取记忆，但 scope 永远来自 persona.memory_scope_id
        依赖 memory_manager.get_memories(scope_id=..., **kwargs)
        """
        if self.memory_manager is None:
            return []
        if not hasattr(self.memory_manager, "get_memories"):
            raise AttributeError("memory_manager must implement get_memories(scope_id: str, **kwargs)")
        return self.memory_manager.get_memories(scope_id=self.persona.memory_scope_id, **kwargs)

    # ===== 总线入口 =====

    async def on_message(self, msg: MessageItem) -> None:
        """
        Agent 在 session 内消费消息的唯一入口：
        - 只消费 target=AGENT & target_id==self.agent_id 的消息
        - USER_INPUT：先 INPUT_ACK，再生成输出（emit AGENT_OUTPUT）
        - CONTROL:CANCEL：stop + CANCEL_ACK
        """
        if msg.session_id != self.session_id:
            return
        if msg.target != MessageTarget.AGENT or msg.target_id != self.agent_id:
            return

        trace_id = msg.metadata.get("trace_id")
        turn_id = msg.metadata.get("turn_id")

        try:
            ev = msg.event
            st = msg.subtype

            # 1) CANCEL
            if ev == "CONTROL" and st in ("CANCEL", "INTERRUPT"):
                self._stop()
                await self.emit_message(
                    MessageFactory.cancel_ack(
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        trace_id=trace_id,
                        turn_id=turn_id,
                        target=MessageTarget.SESSION,
                        visibility="internal",
                        origin="agent",
                        extra_meta=None
                    )
                )
                return

            # 2) USER_INPUT
            if ev == "USER_INPUT":
                self._clear_cancel()
                has_stream = hasattr(self, "_handle_stream") and callable(self._handle_stream)
                # 2.1 先 ACK
                await self.emit_message(
                    MessageFactory.input_ack(
                        session_id=self.session_id,
                        agent_id=self.agent_id,
                        trace_id=trace_id,
                        turn_id=turn_id,
                        target=MessageTarget.SESSION,
                        visibility="internal",
                        origin="agent",
                        extra_meta=None
                    )
                )

                # 2.2 再“说话”（你子类实现 process/process_stream）
                # 默认流式
                if has_stream:
                    seq = 0
                    output = ""
                    async for chunk in self.process_stream(msg):
                        if self.is_canceled():
                            break
                        seq += 1
                        await self.emit_message(
                            MessageFactory.agent_chunk(
                                session_id=self.session_id,
                                agent_id=self.agent_id,
                                text=chunk,
                                seq=seq,
                                trace_id=trace_id,
                                turn_id=turn_id,
                                target=MessageTarget.SESSION,
                                visibility="internal",
                                origin="agent",
                                extra_meta=None
                            )
                        )
                        output += str(chunk)
                    # final（如果没取消）
                    if not self.is_canceled():
                        await self.emit_message(
                            MessageFactory.agent_final(
                                session_id=self.session_id,
                                agent_id=self.agent_id,
                                text=output,
                                trace_id=trace_id,
                                turn_id=turn_id,
                                target=MessageTarget.SESSION,
                                visibility="internal",
                                persist=True,
                                origin="agent",
                                extra_meta=None
                            )
                        )
                else:
                    seq = 1
                    result = await self.process(msg)
                    if not self.is_canceled():
                        await self.emit_message(
                            MessageFactory.agent_chunk(
                                session_id=self.session_id,
                                agent_id=self.agent_id,
                                text=result,
                                seq=seq,
                                trace_id=trace_id,
                                turn_id=turn_id,
                                target=MessageTarget.SESSION,
                                visibility="internal",
                                origin="agent",
                                extra_meta=None
                            )
                        )
                        # final（如果没取消）
                        if not self.is_canceled():
                            await self.emit_message(
                                MessageFactory.agent_final(
                                    session_id=self.session_id,
                                    agent_id=self.agent_id,
                                    text=result,
                                    trace_id=trace_id,
                                    turn_id=turn_id,
                                    target=MessageTarget.SESSION,
                                    visibility="internal",
                                    persist=True,
                                    origin="agent",
                                    extra_meta=None
                                )
                            )
                return

        except Exception as e:
            # 不要让异常炸到 bus dispatch 层：统一 emit ERROR
            await self.emit_message(
                MessageFactory.error(
                    session_id=self.session_id,
                    code="AGENT_ON_MESSAGE_ERROR",
                    message=repr(e),
                    sender_id=self.agent_id,
                    sender_type=MessageType.AGENT,
                    target=MessageTarget.SYSTEM,
                    target_id=None,
                    trace_id=None,
                    turn_id=None,
                    visibility="internal",
                    origin="agent",
                    extra_meta=None
                )
            )

    # ==================== Message 能力（唯一入口） ====================

    async def emit_message(
            self,
            message: MessageItem
    ) -> MessageItem:
        """
        Agent 在 session 内发送消息的唯一入口
        emit_message 负责“让系统发生变化”
        """
        if not self.session_id:
            raise RuntimeError("Agent not in Session")

        # 1️⃣ 发布到 MessageBus
        if self.message_bus is not None:
            if not hasattr(self.message_bus, "publish"):
                raise AttributeError("message_bus must implement publish(message: MessageItem)")
            await self.message_bus.publish(message)

        # # 2️⃣ 是否进入 Memory，由 MemoryManager 决定（不是 Message 决定）
        # if self.memory_manager:
        #     self.memory_manager.on_message(message)

        return message

    async def handover_to(self, agent_id: str, reason: str, *, next_persona_id: Optional[str] = None):
        """
        @TODO :智能体在判断自己的能力不满足当前用户的需求的时候，会发起交接请求，判断标准暂定为在当前的全部人格矩阵中，有更适合的人格矩阵，后期这个能力可能会被移到session中判断，引入辅助智能体
        Agent 发起交接（注意：是否允许、是否切换人格，由 SessionPolicyExecutor/Session 决策）
        """
        payload = {"type": "HANDOVER", "reason": reason}
        if next_persona_id:
            payload["next_persona_id"] = next_persona_id
        return await self.emit_message(
            MessageFactory.handover_request(
                session_id=self.session_id,
                from_agent_id=self.agent_id,
                reason=reason,
                to_agent_id=agent_id,
                next_persona_id=next_persona_id,
                trace_id=None,
                turn_id=None,
                visibility="internal",
                origin="agent",
                extra_meta=None
            )
        )

    # ==================== 心跳机制 ====================

    async def heartbeat(self):
        """线程安全的心跳实现"""
        now = time.monotonic()
        old_last_heartbeat = self._last_heartbeat

        # 原子更新最后心跳时间
        self._last_heartbeat = now

        # 只有在不是第一次心跳时才计算
        if old_last_heartbeat != self._creation_time:
            elapsed = now - old_last_heartbeat

            # 使用本地变量避免竞态
            missed = elapsed > self._heartbeat_interval * 1.5

            # 原子更新统计数据
            self.heartbeat_stats["total_heartbeats"] = self.heartbeat_stats.get("total_heartbeats", 0) + 1

            if missed:
                self.heartbeat_stats["missed_heartbeats"] = self.heartbeat_stats.get("missed_heartbeats", 0) + 1
                self.heartbeat_stats["last_missed_at"] = now

                # 异步记录警告
                asyncio.create_task(
                    self._async_log_heartbeat_warning(elapsed)
                )

            # 更新统计信息（竞态可接受）
            self._update_heartbeat_stats(elapsed)

    async def _async_log_heartbeat_warning(self, elapsed: float):
        """异步记录心跳警告"""
        try:
            logger.warning(
                f"Agent {self.agent_id} missed heartbeat: "
                f"elapsed={elapsed:.2f}s > interval={self._heartbeat_interval}s"
            )
        except Exception:
            pass  # 日志失败不影响心跳功能

    def is_alive(self) -> bool:
        """原子检查Agent是否存活"""
        if self._closed:
            return False

        # 原子读取最后心跳时间
        last_heartbeat = self._last_heartbeat

        if last_heartbeat == self._creation_time:
            return True

        elapsed = time.monotonic() - last_heartbeat
        return elapsed < self._heartbeat_interval * 2.0

    def get_heartbeat_status(self) -> Dict[str, Any]:
        """获取心跳状态信息"""
        now = time.monotonic()
        elapsed = now - self._last_heartbeat

        return {
            "agent_id": self.agent_id,
            "is_alive": self.is_alive(),
            "last_heartbeat": self._last_heartbeat,
            "elapsed_since_last": round(elapsed, 2),
            "heartbeat_interval": self._heartbeat_interval,
            "heartbeat_stats": self.heartbeat_stats.copy(),
            "status": "healthy" if elapsed < self._heartbeat_interval else (
                "warning" if elapsed < self._heartbeat_interval * 2 else "critical"
            ),
        }

    def _update_heartbeat_stats(self, elapsed: float):
        """更新心跳统计（处理第一次心跳的特殊情况）"""
        if self.heartbeat_stats["total_heartbeats"] == 1:
            # 第一次心跳，直接设置
            self.heartbeat_stats["min_interval"] = elapsed
            self.heartbeat_stats["max_interval"] = elapsed
            self.heartbeat_stats["avg_interval"] = elapsed
        else:
            # 后续心跳，正常更新
            self.heartbeat_stats["min_interval"] = min(
                self.heartbeat_stats["min_interval"], elapsed
            )
            self.heartbeat_stats["max_interval"] = max(
                self.heartbeat_stats["max_interval"], elapsed
            )
            # avg_interval 可以在 get_heartbeat_status() 中计算

    @staticmethod
    def _calculate_health_score(status: dict) -> float:
        """计算健康评分（0-100），私有方法"""
        score = 100.0

        # 1. 检查运行状态
        if status.get("run_time_state") == RuntimeState.ERROR.value:
            score -= 30
        elif status.get("run_time_state") == RuntimeState.CLOSED.value:
            return 0.0

        # 2. 检查心跳
        if not status.get("is_alive", True):
            score -= 40

        # 3. 检查错误率
        total_calls = status.get("total_calls", 0)
        total_errors = status.get("total_errors", 0)
        if total_calls > 0:
            error_rate = total_errors / total_calls
            if error_rate > 0.1:  # 10%错误率
                score -= 20 * error_rate

        # 4. 检查延迟
        if total_calls > 0:
            avg_latency = status.get("total_latency", 0) / total_calls
            if avg_latency > 5.0:  # 平均延迟超过5秒
                score -= 10

        return max(0.0, min(100.0, score))

    # ========= 统一执行入口（不可 override） =========

    async def process(self, message: MessageItem, **kwargs) -> Any:
        """
        执行 Agent 处理逻辑并统一统计运行指标。
        process / process_stream 负责“说话”

        指标口径说明：
        - total_calls：每次进入 process 记一次
        - total_latency：本次 process 的整体耗时
        - total_errors：process 过程中发生异常的次数
        """
        start_time = time.monotonic()
        has_error = False
        try:
            self._preflight_checks(message)
            await self.initialize()
            self._enter_running()
            self.speaking = True
            async with self._process_lock:
                result, started = await self._run(message, **kwargs)
            return result
        except Exception as e:
            has_error = True
            self.run_time_state = RuntimeState.ERROR
            logger.error(
                f"Agent {self.agent_id} processing failed, input_type={type(message)}",
                exc_info=True
            )
            error = repr(e)
            raise

        finally:
            self.speaking = False
            if self.run_time_state != RuntimeState.CLOSED and not has_error:
                self.run_time_state = RuntimeState.IDLE
            elapsed = time.monotonic() - start_time
            async with self._metrics_lock:
                self.metrics.total_calls += 1
                self.metrics.total_latency += elapsed
                if has_error:
                    self.metrics.total_errors += 1

    async def process_stream(self, message: MessageItem, **kwargs) -> AsyncGenerator[Any, None]:
        """
        执行 Agent 流式处理逻辑并统一统计运行指标。
        process / process_stream 负责“说话”

        指标口径说明：
        - total_calls：每次进入 process_stream 记一次
        - total_latency：从调用开始到流结束/异常的整体耗时
        - total_errors：流式处理过程中发生异常的次数
        """
        start_time = time.monotonic()
        has_error = False
        try:
            self._preflight_checks(message)
            await self.initialize()
            self._enter_running()
            self.speaking = True
            async with self._process_lock:
                result, started = await self._run_stream(message, **kwargs)

            if not hasattr(result, "__aiter__"):
                raise TypeError("process_stream must return AsyncGenerator")

            async for chunk in result:
                yield chunk
        except Exception as e:
            has_error = True
            self.run_time_state = RuntimeState.ERROR
            logger.error(
                f"Agent {self.agent_id} stream processing failed, input_type={type(message)}",
                exc_info=True
            )
            error = repr(e)
            raise
        finally:
            self.speaking = False
            if self.run_time_state != RuntimeState.CLOSED and not has_error:
                self.run_time_state = RuntimeState.IDLE
            elapsed = time.monotonic() - start_time
            async with self._metrics_lock:
                self.metrics.total_calls += 1
                self.metrics.total_latency += elapsed
                if has_error:
                    self.metrics.total_errors += 1

    # ==================== 核心调度（分流） ====================

    async def _run(self, input_data: MessageItem, **kwargs) -> Tuple[Any, bool]:
        error: Optional[str] = None
        # 系统事件：START_PROCESS（带 persona/scope，便于调试隔离）
        await self.emit_message(
            MessageFactory.event(
                session_id=self.session_id,
                name="START_PROCESS",
                payload={
                    "event": "START_PROCESS",
                    "persona_id": self._persona.persona_id,  # type: ignore[union-attr]
                    "memory_scope_id": self._persona.memory_scope_id,  # type: ignore[union-attr]
                    "stream": False,
                },
                sender_id=self.agent_id,
                target=MessageTarget.SYSTEM,
                trace_id=None,
                turn_id=None,
                visibility="internal",
                persist=False,
                origin="agent",
                extra_meta=None
            )
        )
        started = True
        try:
            return await self._handle(input_data, **kwargs), started
        except Exception as e:
            error = repr(e)
            logger.exception(f"Agent {self.agent_id} processing failed")
            raise
        finally:
            if started:
                try:
                    p = self._persona
                    await self.emit_message(
                        MessageFactory.event(
                            session_id=self.session_id,
                            name="END_PROCESS",
                            payload={
                                "event": "END_PROCESS",
                                "persona_id": p.persona_id if p else None,
                                "memory_scope_id": p.memory_scope_id if p else None,
                                "stream": False,
                                "error": error,
                            },
                            sender_id=self.agent_id,
                            target=MessageTarget.SYSTEM,
                            trace_id=None,
                            turn_id=None,
                            visibility="internal",
                            persist=False,
                            origin="agent",
                            extra_meta=None
                        )
                    )
                except AttributeError as e:
                    logger.warning(f"END_PROCESS failed due to missing Persona attributes: {e}", exc_info=True)
                except TypeError as e:
                    logger.warning(f"END_PROCESS failed due to incorrect message type: {e}", exc_info=True)
                except asyncio.TimeoutError as e:
                    logger.warning(f"END_PROCESS failed due to timeout: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"END_PROCESS failed due to unexpected error: {e}", exc_info=True)

    async def _run_stream(self, input_data: MessageItem, **kwargs) -> Tuple[AsyncIterator[Any], bool]:
        error: Optional[str] = None
        # 系统事件：START_PROCESS（带 persona/scope，便于调试隔离）
        await self.emit_message(
            MessageFactory.event(
                session_id=self.session_id,
                name="START_PROCESS",
                payload={
                    "event": "START_PROCESS",
                    "persona_id": self._persona.persona_id,  # type: ignore[union-attr]
                    "memory_scope_id": self._persona.memory_scope_id,  # type: ignore[union-attr]
                    "stream": True,
                },
                sender_id=self.agent_id,
                target=MessageTarget.SYSTEM,
                trace_id=None,
                turn_id=None,
                visibility="internal",
                persist=False,
                origin="agent",
                extra_meta=None
            )
        )
        started = True
        try:
            result = self._handle_stream(input_data, **kwargs)
            return result, started
        except Exception as e:
            error = repr(e)
            logger.exception(f"Agent {self.agent_id} processing failed")
            raise
        finally:
            if started:
                try:
                    p = self._persona
                    await self.emit_message(
                        MessageFactory.event(
                            session_id=self.session_id,
                            name="END_PROCESS",
                            payload={
                                "event": "END_PROCESS",
                                "persona_id": p.persona_id if p else None,
                                "memory_scope_id": p.memory_scope_id if p else None,
                                "stream": True,
                                "error": error,
                            },
                            sender_id=self.agent_id,
                            target=MessageTarget.SYSTEM,
                            trace_id=None,
                            turn_id=None,
                            visibility="internal",
                            persist=False,
                            origin="agent",
                            extra_meta=None
                        )
                    )
                except AttributeError as e:
                    logger.warning(f"END_PROCESS failed due to missing Persona attributes: {e}", exc_info=True)
                except TypeError as e:
                    logger.warning(f"END_PROCESS failed due to incorrect message type: {e}", exc_info=True)
                except asyncio.TimeoutError as e:
                    logger.warning(f"END_PROCESS failed due to timeout: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"END_PROCESS failed due to unexpected error: {e}", exc_info=True)

    def _preflight_checks(self, input_data: Any):
        # 生命周期检查
        if self._closed:
            raise RuntimeError(f"Agent {self.agent_id} is closed")
        # 发言权检查
        if not self.active:
            raise RuntimeError(f"Agent {self.agent_id} has no right to speak")
        # 类型检查
        if not isinstance(input_data, MessageItem):
            raise TypeError("Agent only accepts MessageItem")
        # Persona 检查（强约束）
        if not self._persona:
            raise RuntimeError(f"Agent {self.agent_id} has no PersonaMatrix，can not execute")

    # ========= 子类需要实现的方法 =========

    @abstractmethod
    async def _handle(self, message: MessageItem, **kwargs) -> Any:
        """非流式处理"""
        raise NotImplementedError

    @abstractmethod
    def _handle_stream(self, message: MessageItem, **kwargs) -> AsyncGenerator[Any, None]:
        """
        流式处理：
        - 必须是 async generator function（内部 yield）
        - 或返回一个 AsyncGenerator
        """
        raise NotImplementedError

    # ========= 生命周期 =========

    async def close(self):
        async with self._process_lock:
            if self._closed:
                return
            self._closed = True
            self.run_time_state = RuntimeState.CLOSED
            await self._on_close()

    @abstractmethod
    async def _on_close(self):
        pass

    # ========= 状态辅助 =========

    def _enter_running(self):
        if self.run_time_state == RuntimeState.CLOSED:
            raise RuntimeError("Agent already closed")
        self.run_time_state = RuntimeState.RUNNING

    # ========= 健康检查 =========

    def health_check(self) -> dict:
        """增强的健康检查，包含心跳信息"""
        base_status = self._status()

        # 获取心跳状态
        heartbeat_status = self.get_heartbeat_status()

        # 合并状态
        full_status = {**base_status, **heartbeat_status}

        # 添加总体健康评分
        health_score = self._calculate_health_score(full_status)
        full_status["health_score"] = round(health_score, 1)
        full_status["health_status"] = (
            "healthy" if health_score >= 80 else
            "degraded" if health_score >= 60 else
            "critical"
        )

        return full_status

    def _status(self) -> dict:
        """返回 Agent 当前状态（实例级 + 会话级 + 指标）"""
        return {
            "agent_id": self.agent_id,
            "active": self.active,  # 实例级 active
            "speaking": self.speaking,  # 会话级 active
            "cognitive_state": getattr(self, "cognitive_state", None).value
            if hasattr(self, "cognitive_state") and self.cognitive_state else None,
            "run_time_state": self.run_time_state.value,
            "total_calls": self.metrics.total_calls,
            "total_errors": self.metrics.total_errors,
            "total_latency": round(self.metrics.total_latency, 4),
            "conversation_history_len": len(self.conversation_history),
        }
