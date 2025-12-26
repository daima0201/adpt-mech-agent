# src/core/session/session_runtime.py
import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Callable, Awaitable, re

from src.agents.base.base_agent import BaseAgent
from src.core.message.message_bus import MessageBus
from src.core.message.message_factory import MessageFactory, MessageEvents, ControlSubtypes, ErrorCodes
from src.core.message.message_item import MessageItem
from src.core.message.message_target import MessageTarget
from src.core.message.message_type import MessageType
from .session_context import SessionContext

logger = logging.getLogger(__name__)


# -------------------------
# 内部：inflight/事务记录
# -------------------------

@dataclass
class InflightTurn:
    turn_id: str
    trace_id: str
    created_at: float = field(default_factory=time.time)
    target_agent_id: Optional[str] = None
    status: str = "ROUTING"  # ROUTING | RUNNING | COMPLETED | FAILED | CANCELED
    last_output_at: float = 0.0
    # 用于 handover 附带“切换前输出”（可选）
    last_agent_output_final: Optional[str] = None


# -------------------------
# SessionRuntime
# -------------------------

class SessionRuntime:
    """
    SessionRuntime = 会话编排器（强编排）

    核心铁律：
    1) 前端不和 agent 交互：所有 agent 输出必须由 SessionRuntime 转发给 FRONTEND
    2) 输入路由必须 ACK：USER_INPUT -> AGENT 后必须等 INPUT_ACK（超时给前端 ERROR）
    3) SessionRuntime 不直接调用 agent.process/process_stream：只通过总线发消息
    4) SessionRuntime 不做 IO/不创建 agent：创建/移除交给 SessionManager（通过 REQUEST_* + *_DONE 回执）
    """

    # 你可以调参
    INPUT_ACK_TIMEOUT_SEC = 2.0
    CANCEL_ACK_TIMEOUT_SEC = 2.0
    MAX_INFLIGHT_HISTORY = 2000

    # （可选）只在终态回收时保留最近 N 秒的，想要 TTL 可以再加：
    # INFIGHT_TTL_SEC = 15 * 60

    def __init__(
            self,
            session_id: str,
            bus: MessageBus,
            context: Optional[SessionContext] = None,
    ):
        self.session_id = session_id
        self.bus = bus
        self.context = context or SessionContext(session_id=session_id)

        self.agents: Dict[str, BaseAgent] = {}
        self._lock = asyncio.Lock()

        # inflight: turn_id -> InflightTurn
        self._inflight: Dict[str, InflightTurn] = {}

        # ack 等待表：turn_id -> asyncio.Event
        self._wait_input_ack: Dict[str, asyncio.Event] = {}
        self._wait_cancel_ack: Dict[str, asyncio.Event] = {}

        # 订阅：
        # 1) SYSTEM 入口（前端来的 USER_INPUT / CONTROL、SessionManager 回执等）
        self.bus.subscribe(subscriber_id="system", callback=self.on_message)
        # 1) SYSTEM 入口（前端来的 USER_INPUT / CONTROL、SessionManager 回执等）
        self.bus.subscribe(subscriber_id="session", callback=self.on_message)

        logger.info("SessionRuntime subscribed: session_id=%s", self.session_id)

    # =========================
    # Agent 管理：只做注册/解绑，不做创建
    # =========================

    async def register_agent(self, agent: BaseAgent, *, make_active: bool = False) -> None:
        """
        注册一个已经创建好的 agent 进入当前 session。
        注意：创建/装配应由 SessionManager 完成，然后回 *_DONE 再调用这里。
        """
        async with self._lock:
            if agent.agent_id in self.agents:
                return

            self.agents[agent.agent_id] = agent
            agent.session_id = self.session_id

            # 让 agent 能收到定向消息：target=AGENT,target_id=agent_id
            # bus 会根据 subscriber_id=agent_id 路由给 agent
            self.bus.subscribe(subscriber_id=agent.agent_id, callback=self._make_agent_callback(agent))

            if make_active or not getattr(self.context, "active_agent_id", None):
                await self._switch_active(agent.agent_id, reason="register_agent")

            logger.info("Agent registered: %s in session %s", agent.agent_id, self.session_id)

    async def unregister_agent(self, agent_id: str) -> None:
        """
        仅做本地解绑 + 取消订阅。真正的持久化/销毁由 SessionManager 处理。
        """
        async with self._lock:
            if agent_id not in self.agents:
                return
            self.bus.unsubscribe(subscriber_id=agent_id)
            del self.agents[agent_id]

            if getattr(self.context, "active_agent_id", None) == agent_id:
                self.context.active_agent_id = None
            if getattr(self.context, "speaking_agent_id", None) == agent_id:
                self.context.speaking_agent_id = None

            logger.info("Agent unregistered: %s in session %s", agent_id, self.session_id)

    @staticmethod
    def _make_agent_callback(agent: BaseAgent) -> Callable[[MessageItem], Awaitable[None]]:
        """
        适配 agent 的消费接口。强烈建议你的 BaseAgent 提供 on_message(msg)。
        """

        async def _cb(msg: MessageItem) -> None:
            # 仅处理发给该 agent 的定向消息

            try:
                fn = getattr(agent, "on_message", None)
                if callable(fn):
                    ret = fn(msg)
                    if asyncio.iscoroutine(ret):
                        await ret
                    return
                # 不支持未实现on_message的agent
                # # fallback（不推荐）：没有 on_message 的情况下，你可以临时用 process/process_stream
                # if msg.event == MessageEvents.USER_INPUT and isinstance(msg.payload, str):
                #     if hasattr(agent, "process"):
                #         ret = agent.process(msg)
                #         if asyncio.iscoroutine(ret):
                #             await ret
                #         return
                #     if hasattr(agent, "process_stream"):
                #         # process_stream 可能是 async generator；这里不消费（避免 runtime 直接拉流）
                #         # 正确做法：agent 自己消费 msg 后自行 publish chunk/final 到总线
                #         logger.warning("Agent %s has process_stream but no on_message; please implement on_message",
                #                        agent.agent_id)
                #         return
                logger.warning("Agent %s has no on_message/process handler for msg=%s", agent.agent_id, msg)
            except Exception as e:
                error = repr(e)
                logger.exception("Agent callback failed: agent=%s msg=%s error=%s", agent.agent_id, msg, error)

        return _cb

    # =========================
    # 总线入口：统一 on_message
    # =========================

    async def on_message(self, msg: MessageItem) -> None:
        """
        SessionRuntime 的唯一入口：消费消息 -> 状态机 -> publish 新消息
        """
        # 只处理本 session 消息
        if msg.session_id != self.session_id:
            return

        # 防止自己转发给 FRONTEND 的消息再次被处理（避免循环）
        if msg.metadata.get("routed_by") == "session_runtime":
            return

        ev = msg.event
        st = msg.subtype

        if ev == MessageEvents.USER_INPUT:
            await self._handle_user_input(msg)
            return

        if ev == MessageEvents.AGENT_OUTPUT:
            await self._handle_agent_output(msg)
            return

        if ev == MessageEvents.CONTROL:
            await self._handle_control(msg)
            return

        if ev == MessageEvents.ERROR:
            # 统一转发给前端（也可按 visibility 控制）
            await self._forward_to_frontend(msg)
            return

        # EVENT/其他：如果需要观测也可转发或记录
        # 默认不处理
        return

    # =========================
    # USER_INPUT：强编排路由 + ACK
    # =========================

    async def _handle_user_input(self, msg: MessageItem) -> None:
        """
        用户输入只能先进 Session，再由 SessionRuntime 路由到 AGENT。
        """
        # _handle_user_input 一开始加
        if msg.target not in (MessageTarget.SESSION, MessageTarget.SYSTEM):
            # 可选：直接丢弃，或发 ERROR 给前端/日志
            return

        payload = msg.payload
        if not isinstance(payload, str):
            # @TODO 这里面以后需要明确payload的格式，再回来确定
            # 结构化输入也允许，但至少要能解析出文本/意图
            # 这里先简单转 str
            payload = str(payload)

        # 解析 mention：既支持 "@xxx ..." 也支持 metadata/payload 结构化字段
        mentioned = SessionRuntime._extract_mentioned_agent_id(msg)

        # turn/trace
        trace_id = msg.metadata.get("trace_id") or MessageFactory.new_trace_id()
        turn_id = msg.metadata.get("turn_id") or MessageFactory.new_turn_id()

        # 确定目标 agent
        target_agent = mentioned or getattr(self.context, "active_agent_id", None) or self._default_agent_id()
        if not target_agent:
            await self._publish_frontend_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message="当前没有可用的 active agent",
                trace_id=trace_id,
                turn_id=turn_id,
            )
            return

        # 若 mention，执行 active 切换（本地 + 总线）
        if mentioned and mentioned != getattr(self.context, "active_agent_id", None):
            if target_agent not in self.agents:
                await self._publish_frontend_error(
                    code=ErrorCodes.VALIDATION_ERROR,
                    message=f"目标智能体不存在或未加入会话: {target_agent}",
                    trace_id=trace_id,
                    turn_id=turn_id,
                )
                return
            await self._switch_active(mentioned, reason="mention_user_input", trace_id=trace_id, turn_id=turn_id)

        # inflight 登记 + 等 ACK
        inflight = InflightTurn(turn_id=turn_id, trace_id=trace_id, target_agent_id=target_agent, status="ROUTING")
        self._inflight[turn_id] = inflight
        ack_ev = asyncio.Event()
        self._wait_input_ack[turn_id] = ack_ev

        # 每次新 turn 进入时做一次回收
        self._gc_inflight()

        # 先通知前端：已受理
        await self.bus.publish(
            MessageFactory.event(
                session_id=self.session_id,
                name="TURN_ACCEPTED",
                payload={"turn_id": turn_id, "trace_id": trace_id, "target_agent_id": target_agent},
                target=MessageTarget.FRONTEND,
                visibility="frontend",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

        # 真正路由到 agent（定向）
        routed = MessageFactory.user_input(
            session_id=self.session_id,
            user_id=msg.sender_id or "user",
            text=payload,
            target=MessageTarget.AGENT,
            target_id=target_agent,
            trace_id=trace_id,
            turn_id=turn_id,
            persist=bool(msg.metadata.get("persist", True)),
            visibility="internal",  # 输入内容前端已知，不需要再展示
            extra_meta={"routed_by": "session_runtime"},
        )
        await self.bus.publish(routed)

        # 启动 ACK 超时监督（异步，不阻塞 on_message）
        asyncio.create_task(self._wait_input_ack_timeout(turn_id, trace_id), name=f"wait_input_ack[{turn_id}]")

    @staticmethod
    def _extract_mentioned_agent_id(self, msg: MessageItem) -> Optional[str]:
        """
        强编排风格的mention提取器

        设计原则：
        1. 只接受明确的mention信号
        2. 宁可漏判，不可误判
        3. 格式必须严格规范

        支持的格式（按优先级）：
        1. metadata.mentioned_agent_id（最明确）
        2. payload.mentioned_agent_id（结构化数据）
        3. 严格的前缀@格式（@开头，后面跟着有效标识符）
        """
        # ========== 1. metadata（最明确的指令）==========
        mid = msg.metadata.get("mentioned_agent_id")
        if isinstance(mid, str):
            agent_id = mid.strip()
            if agent_id and self._is_valid_agent_id(agent_id):
                logger.debug(f"Extracted from metadata: {agent_id}")
                return agent_id

        # ========== 2. payload（结构化数据）==========
        if isinstance(msg.payload, dict):
            v = msg.payload.get("mentioned_agent_id")
            if isinstance(v, str):
                agent_id = v.strip()
                if agent_id and self._is_valid_agent_id(agent_id):
                    logger.debug(f"Extracted from payload: {agent_id}")
                    return agent_id

        # ========== 3. 严格的@前缀语法 ==========
        # 情况B：payload是字符串（用户输入文本）
        if isinstance(msg.payload, str):
            text = msg.payload.strip()
            if not text:
                return None

            # 必须是@开头，且@后紧跟着有效标识符
            if text.startswith("@"):
                # 更严格的正则：必须以@开头，后跟字母/数字/下划线/连字符/中文
                match = re.match(r'^@([a-zA-Z0-9_\-\u4e00-\u9fa5]+)(?:\s|$)', text)
                if match:
                    agent_id = match.group(1)
                    if self._is_valid_agent_id(agent_id):
                        logger.debug(f"Extracted from @prefix in payload: {agent_id}")
                        return agent_id

            # 情况C：payload是字符串但不是以@开头
            # 绝对不尝试"宽松匹配"，直接返回None
            return None

        # ========== 4. 其他payload类型 ==========
        # 情况D：payload是其他类型（数字、列表等）
        # 不尝试解析，直接返回None
        return None

    @staticmethod
    def _is_valid_agent_id(agent_id: str) -> bool:
        """
        验证agent_id的基本格式
        @TODO 验证是否合法的agent_id，需要以后明确agent的ID的固定格式（方便管理），再回到此处进行更改
        这只是基本验证，真正的存在性检查在路由时做
        这里只检查格式是否合理
        """
        if not agent_id or not agent_id.strip():
            return False

        # 不允许的特殊字符
        invalid_chars = set(' @#$%^&*()+=|\\<>?/.,;:\'"`~[]{}')
        if any(c in invalid_chars for c in agent_id):
            logger.debug(f"Invalid agent_id contains special chars: {agent_id}")
            return False

        # 长度限制（根据你的系统设定）
        if len(agent_id) > 50:
            logger.debug(f"Agent_id too long: {agent_id}")
            return False

        return True

    def _default_agent_id(self) -> Optional[str]:
        # 你可以改成更聪明的策略：最早注册的、最近可用的等
        if self.agents:
            return next(iter(self.agents.keys()))
        return None

    async def _wait_input_ack_timeout(self, turn_id: str, trace_id: str) -> None:
        ev = self._wait_input_ack.get(turn_id)
        if not ev:
            return
        try:
            ok = await asyncio.wait_for(ev.wait(), timeout=self.INPUT_ACK_TIMEOUT_SEC)
            if not ok:
                return
        except asyncio.TimeoutError:
            inflight = self._inflight.get(turn_id)
            if inflight and inflight.status == "ROUTING":
                inflight.status = "FAILED"
            await self._publish_frontend_error(
                code="ROUTE_TIMEOUT",
                message="目标智能体未在超时内确认接收输入（INPUT_ACK）",
                trace_id=trace_id,
                turn_id=turn_id,
            )
        finally:
            # 清理等待器（避免泄漏）
            self._wait_input_ack.pop(turn_id, None)
            # 失败也回收一次
            self._gc_inflight()

    def _gc_inflight(self) -> None:
        """
        回收 inflight：只保留最近 MAX_INFLIGHT_HISTORY 条
        （暂时不引入时间判断）
        """
        if len(self._inflight) <= self.MAX_INFLIGHT_HISTORY:
            return

        items = sorted(
            self._inflight.items(),
            key=lambda kv: kv[1].created_at,
            reverse=True,
        )
        self._inflight = dict(items[: self.MAX_INFLIGHT_HISTORY])

    # =========================
    # CONTROL：ACK / CANCEL / INVITE / REMOVE / HANDOVER / SWITCH 等
    # =========================

    async def _handle_control(self, msg: MessageItem) -> None:
        st = msg.subtype or ""

        # ---- 来自 agent 的 INPUT_ACK ----
        if st == "INPUT_ACK":
            turn_id = msg.metadata.get("turn_id")
            if isinstance(turn_id, str) and turn_id in self._wait_input_ack:
                inflight = self._inflight.get(turn_id)
                if inflight:
                    inflight.status = "RUNNING"
                self._wait_input_ack[turn_id].set()

                # 可选：通知前端“agent 已开始”
                await self.bus.publish(
                    MessageFactory.event(
                        session_id=self.session_id,
                        name="AGENT_STARTED",
                        payload={"turn_id": turn_id, "trace_id": msg.metadata.get("trace_id"),
                                 "agent_id": msg.sender_id},
                        target=MessageTarget.FRONTEND,
                        visibility="frontend",
                        extra_meta={"routed_by": "session_runtime"},
                    )
                )
            return

        # ---- 来自前端：CANCEL/INTERRUPT ----
        if st in ("CANCEL", "INTERRUPT"):
            await self._do_cancel_current(msg)
            return

        # ---- 来自 agent：CANCEL_ACK ----
        if st == "CANCEL_ACK":
            turn_id = msg.metadata.get("turn_id")
            if isinstance(turn_id, str) and turn_id in self._wait_cancel_ack:
                self._wait_cancel_ack[turn_id].set()
            # speaking 清理交给 cancel 流程的 finally
            return

        # ---- 前端/系统：SWITCH_AGENT ----
        if st == ControlSubtypes.SWITCH_AGENT:
            payload = msg.payload if isinstance(msg.payload, dict) else {}
            to_agent = payload.get("to") or payload.get("agent_id") or msg.metadata.get("to_agent_id")
            if isinstance(to_agent, str) and to_agent:
                await self._switch_active(to_agent, reason="external_switch", trace_id=msg.metadata.get("trace_id"),
                                          turn_id=msg.metadata.get("turn_id"))
            return

        # ---- 前端：INVITE_AGENT / REMOVE_AGENT 等（转给 SessionManager）----
        if st in ("INVITE_AGENT", "REQUEST_ADD_AGENT"):
            # SessionRuntime 不创建，转交 SessionManager
            await self.bus.publish(
                MessageFactory.control(
                    session_id=self.session_id,
                    subtype="REQUEST_ADD_AGENT",
                    sender_id="session_runtime",
                    target=MessageTarget.SYSTEM,
                    payload=msg.payload,
                    visibility="internal",
                    extra_meta={"routed_by": "session_runtime"},
                )
            )
            return

        if st in ("REMOVE_AGENT", "REQUEST_REMOVE_AGENT"):
            await self._request_remove_agent(msg)
            return

        # ---- HANDOVER 流程（agent->prompt->frontend confirm）----
        if st == "HANDOVER_REQUEST":
            await self._handover_prompt_frontend(msg)
            return

        if st in ("HANDOVER_CONFIRM", "HANDOVER_REJECT"):
            await self._handover_apply(msg)
            return

        # 其他 CONTROL：默认不处理
        return

    async def _do_cancel_current(self, msg: MessageItem) -> None:
        speaking = getattr(self.context, "speaking_agent_id", None)
        if not speaking:
            await self.bus.publish(
                MessageFactory.event(
                    session_id=self.session_id,
                    name="NO_SPEAKING_AGENT",
                    payload={"reason": "no agent is speaking"},
                    target=MessageTarget.FRONTEND,
                    visibility="frontend",
                    extra_meta={"routed_by": "session_runtime"},
                )
            )
            return

        # 找当前 turn：简单做法是“最近 RUNNING 的 turn”
        turn_id = self._find_running_turn_for_agent(speaking)
        if not turn_id:
            # 没有关联 turn 也允许 cancel：用临时 turn_id 表示取消事务
            turn_id = MessageFactory.new_turn_id()
            trace_id = msg.metadata.get("trace_id") or MessageFactory.new_trace_id()
            self._inflight[turn_id] = InflightTurn(turn_id=turn_id, trace_id=trace_id, target_agent_id=speaking,
                                                   status="RUNNING")

        trace_id = self._inflight[turn_id].trace_id

        ev = asyncio.Event()
        self._wait_cancel_ack[turn_id] = ev

        # 发 CANCEL 给 speaking agent（定向）
        await self.bus.publish(
            MessageFactory.control(
                session_id=self.session_id,
                subtype="CANCEL",
                sender_id="frontend" if msg.sender_id else "session_runtime",
                target=MessageTarget.AGENT,
                target_id=speaking,
                payload={"reason": "user_interrupt", "turn_id": turn_id},
                trace_id=trace_id,
                turn_id=turn_id,
                visibility="internal",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

        # 等 ACK（异步监督）
        asyncio.create_task(self._wait_cancel_ack_timeout(turn_id, trace_id, speaking),
                            name=f"wait_cancel_ack[{turn_id}]")

    def _find_running_turn_for_agent(self, agent_id: str) -> Optional[str]:
        # 取最新的 RUNNING turn
        candidates = [t for t in self._inflight.values() if
                      t.target_agent_id == agent_id and t.status in ("ROUTING", "RUNNING")]
        if not candidates:
            return None
        candidates.sort(key=lambda x: x.created_at, reverse=True)
        return candidates[0].turn_id

    async def _wait_cancel_ack_timeout(self, turn_id: str, trace_id: str, agent_id: str) -> None:
        ev = self._wait_cancel_ack.get(turn_id)
        if not ev:
            return
        try:
            await asyncio.wait_for(ev.wait(), timeout=self.CANCEL_ACK_TIMEOUT_SEC)
        except asyncio.TimeoutError:
            await self._publish_frontend_error(
                code="CANCEL_TIMEOUT",
                message=f"智能体 {agent_id} 未在超时内确认取消（CANCEL_ACK）",
                trace_id=trace_id,
                turn_id=turn_id,
            )
        finally:
            # 结束 speaking（无论 ACK 是否到来，UI 都不应继续等；是否强制停止由 agent 实现）
            if getattr(self.context, "speaking_agent_id", None) == agent_id:
                self.context.speaking_agent_id = None
            inflight = self._inflight.get(turn_id)
            if inflight and inflight.status in ("ROUTING", "RUNNING"):
                inflight.status = "CANCELED"
            self._wait_cancel_ack.pop(turn_id, None)

            self._gc_inflight()

            await self.bus.publish(
                MessageFactory.event(
                    session_id=self.session_id,
                    name="TURN_CANCELED",
                    payload={"turn_id": turn_id, "trace_id": trace_id},
                    target=MessageTarget.FRONTEND,
                    visibility="frontend",
                    extra_meta={"routed_by": "session_runtime"},
                )
            )

    async def _request_remove_agent(self, msg: MessageItem) -> None:
        payload = msg.payload if isinstance(msg.payload, dict) else {}
        agent_id = payload.get("agent_id") or payload.get("id")
        if not isinstance(agent_id, str) or not agent_id:
            await self._publish_frontend_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message="REMOVE_AGENT 缺少 agent_id",
                trace_id=msg.metadata.get("trace_id"),
                turn_id=msg.metadata.get("turn_id"),
            )
            return

        # 如果该 agent 正在说话：先 cancel（并等待 ACK/DONE 由上层事务做，这里先发起 cancel）
        if getattr(self.context, "speaking_agent_id", None) == agent_id:
            await self._do_cancel_current(
                MessageFactory.control(
                    session_id=self.session_id,
                    subtype="CANCEL",
                    sender_id="session_runtime",
                    target=MessageTarget.SYSTEM,
                    payload={"reason": "remove_agent_pre_cancel"},
                    visibility="internal",
                )
            )

        # 请求 SessionManager 做持久化/销毁
        await self.bus.publish(
            MessageFactory.control(
                session_id=self.session_id,
                subtype="REQUEST_REMOVE_AGENT",
                sender_id="session_runtime",
                target=MessageTarget.SYSTEM,
                payload={"agent_id": agent_id, "reason": payload.get("reason", "user_remove")},
                visibility="internal",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

        # 本地先解绑（你之前也倾向“先本地清理 + 等 DONE 最终确认”）
        await self.unregister_agent(agent_id)

        await self.bus.publish(
            MessageFactory.event(
                session_id=self.session_id,
                name="AGENT_REMOVED_LOCAL",
                payload={"agent_id": agent_id},
                target=MessageTarget.FRONTEND,
                visibility="frontend",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

    async def _handover_prompt_frontend(self, msg: MessageItem) -> None:
        # agent 发起切换请求 -> 前端弹窗
        await self.bus.publish(
            MessageFactory.control(
                session_id=self.session_id,
                subtype="HANDOVER_UI_PROMPT",
                sender_id="session_runtime",
                target=MessageTarget.FRONTEND,
                payload={
                    "from_agent": msg.sender_id,
                    "request": msg.payload,
                    "trace_id": msg.metadata.get("trace_id"),
                    "turn_id": msg.metadata.get("turn_id"),
                },
                visibility="frontend",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

    async def _handover_apply(self, msg: MessageItem) -> None:
        # 前端确认后执行：切 active + 把上下文发给新 agent
        if msg.subtype == "HANDOVER_REJECT":
            await self.bus.publish(
                MessageFactory.event(
                    session_id=self.session_id,
                    name="HANDOVER_REJECTED",
                    payload=msg.payload,
                    target=MessageTarget.LOGGER,
                    visibility="internal",
                    extra_meta={"routed_by": "session_runtime"},
                )
            )
            return

        payload = msg.payload if isinstance(msg.payload, dict) else {}
        to_agent = payload.get("to_agent") or payload.get("to")
        from_agent = payload.get("from_agent")

        if not isinstance(to_agent, str) or not to_agent:
            await self._publish_frontend_error(
                code=ErrorCodes.VALIDATION_ERROR,
                message="HANDOVER_CONFIRM 缺少 to_agent",
                trace_id=msg.metadata.get("trace_id"),
                turn_id=msg.metadata.get("turn_id"),
            )
            return

        trace_id = msg.metadata.get("trace_id") or MessageFactory.new_trace_id()
        turn_id = msg.metadata.get("turn_id") or MessageFactory.new_turn_id()

        await self._switch_active(to_agent, reason="handover_confirmed", trace_id=trace_id, turn_id=turn_id)

        # 附带切换前输出（如果传了就用传的；否则用 inflight 里记的）
        prev_output = payload.get("prev_output")
        if not prev_output and isinstance(from_agent, str):
            # 找 from_agent 最近一次 final 输出
            prev_output = self._find_last_final_output(from_agent)

        await self.bus.publish(
            MessageFactory.control(
                session_id=self.session_id,
                subtype="HANDOVER_CONTEXT",
                sender_id="session_runtime",
                target=MessageTarget.AGENT,
                target_id=to_agent,
                payload={
                    "from_agent": from_agent,
                    "prev_output": prev_output,
                    "reason": payload.get("reason"),
                },
                trace_id=trace_id,
                turn_id=turn_id,
                visibility="internal",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

    def _find_last_final_output(self, agent_id: str) -> Optional[str]:
        # 在 inflight 里找最近完成且记录了 final 输出的
        done = [t for t in self._inflight.values() if t.target_agent_id == agent_id and t.last_agent_output_final]
        if not done:
            return None
        done.sort(key=lambda x: x.last_output_at, reverse=True)
        return done[0].last_agent_output_final

    async def _switch_active(self, agent_id: str, *, reason: str, trace_id: Optional[str] = None,
                             turn_id: Optional[str] = None) -> None:
        # 本地立即生效
        self.context.active_agent_id = agent_id

        # 再发总线可观测事件
        await self.bus.publish(
            MessageFactory.control(
                session_id=self.session_id,
                subtype=ControlSubtypes.SWITCH_AGENT,
                sender_id="session_runtime",
                target=MessageTarget.SYSTEM,  # 或 BROADCAST
                payload={
                    "from": None,  # 你也可以记录旧值
                    "to": agent_id,
                    "reason": reason,
                },
                trace_id=trace_id,
                turn_id=turn_id,
                visibility="internal",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

        # 前端刷新 active 状态
        await self.bus.publish(
            MessageFactory.event(
                session_id=self.session_id,
                name="ACTIVE_AGENT_CHANGED",
                payload={"active_agent_id": agent_id, "reason": reason},
                target=MessageTarget.FRONTEND,
                visibility="frontend",
                extra_meta={"routed_by": "session_runtime"},
            )
        )

    # =========================
    # AGENT_OUTPUT：只要收到，就由 SessionRuntime 转发给 FRONTEND
    # =========================

    async def _handle_agent_output(self, msg: MessageItem) -> None:
        # 记录 speaking 状态机
        sender = msg.sender_id
        stream = msg.stream
        is_chunk = bool(stream.get("is_chunk", False))
        is_final = msg.is_final()

        # 推断 turn_id
        turn_id = msg.metadata.get("turn_id")
        if isinstance(turn_id, str) and turn_id in self._inflight:
            inflight = self._inflight[turn_id]
            inflight.last_output_at = time.time()
            if is_final and isinstance(msg.payload, str):
                inflight.last_agent_output_final = msg.payload
            if inflight.status in ("ROUTING", "RUNNING"):
                inflight.status = "RUNNING"

        # speaking 归属
        if is_chunk:
            if not getattr(self.context, "speaking_agent_id", None):
                self.context.speaking_agent_id = sender
            elif self.context.speaking_agent_id != sender:
                # 并发异常：可以丢弃或报错，这里报错给前端
                await self._publish_frontend_error(
                    code="SPEAKING_CONFLICT",
                    message=f"speaking 冲突：{self.context.speaking_agent_id} 正在发言，但 {sender} 输出了 chunk",
                    trace_id=msg.metadata.get("trace_id"),
                    turn_id=turn_id,
                )
                return

        if is_final:
            # final 结束发言权
            if getattr(self.context, "speaking_agent_id", None) == sender:
                self.context.speaking_agent_id = None
            # inflight 结束
            if isinstance(turn_id, str) and turn_id in self._inflight:
                self._inflight[turn_id].status = "COMPLETED"

        # 统一转发给前端
        await self._forward_to_frontend(msg)

    async def _forward_to_frontend(self, msg: MessageItem) -> None:
        # 不改变 payload，只改 target + 打标 routed_by
        forwarded = MessageItem(
            session_id=self.session_id,
            sender_id=msg.sender_id,
            sender_type=msg.sender_type,
            target=MessageTarget.FRONTEND,
            target_id=None,
            payload=msg.payload,
            timestamp=msg.timestamp,
            metadata=dict(msg.metadata),
        )
        forwarded.metadata["routed_by"] = "session_runtime"
        forwarded.metadata["visibility"] = "frontend"  # 前端可见

        await self.bus.publish(forwarded)

    async def _publish_frontend_error(self, *, code: str, message: str, trace_id: Optional[str],
                                      turn_id: Optional[str]) -> None:
        await self.bus.publish(
            MessageFactory.error(
                session_id=self.session_id,
                code=code,
                message=message,
                sender_id="session_runtime",
                sender_type=MessageType.SYSTEM,
                target=MessageTarget.FRONTEND,
                trace_id=trace_id,
                turn_id=turn_id,
                visibility="frontend",
                extra_meta={"routed_by": "session_runtime"},
            )
        )
