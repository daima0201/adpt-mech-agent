import asyncio
import logging
import time
from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List, Dict

from src.agents.enum.run_time_state import RuntimeState

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

    def __init__(self, agent_id: str, max_history: int = 10):
        self.agent_id = agent_id
        self.run_time_state: RuntimeState = RuntimeState.IDLE
        self._closed = False
        self.metrics = AgentMetrics()
        self.is_initialized = False
        self.conversation_history: List[Dict[str, str]] = []  # 格式: [{"role": "user/assistant", "content": "..."}]
        self.max_history = max(max_history, 1)  # 至少保留1条历史

        # ========= 新增 active和speaking 支持 =========
        self.active: bool = False  # 当前实例是否 active（可发言/处理任务）
        self.speaking: bool = False  # 当前会话是否正在发言

        # ========= 并发控制锁 =========
        # initialization_lock: 只保护 initialize
        # _lock: 保护 process 全流程
        self._initialization_lock = asyncio.Lock()
        self._lock = asyncio.Lock()

    async def initialize(self) -> bool:
        """初始化入口（全局只执行一次）"""
        async with self._initialization_lock:
            if self.is_initialized:
                logger.warning(f"Agent {self.agent_id} 已经初始化过")
                return True
            await self.customized_initialize()
            self.is_initialized = True
            return True

    # ========= Active 管理 =========

    def switch_active(self, value: bool):
        """切换 active 状态"""
        old = self.active
        self.active = value
        logger.info(f"{self.agent_id} active: {old} -> {self.active}")

    def is_active(self) -> bool:
        """检查当前实例是否 active"""
        return self.active

    # ========= 对外统一入口（不可 override） =========

    async def process(self, input_data: Any, **kwargs) -> Any:
        """
        执行 Agent 处理逻辑并统一统计运行指标。

        指标口径说明：
        - total_calls：每次进入 process 记一次
        - total_latency：本次 process 的整体耗时
        - total_errors：process 过程中发生异常的次数
        """
        start_time = time.time()
        has_error = False

        try:
            result = await self._run(input_data, stream=False, **kwargs)
            return result

        except Exception:
            has_error = True
            logger.error(
                f"Agent {self.agent_id} processing failed, input_type={type(input_data)}",
                exc_info=True
            )
            raise

        finally:
            elapsed = time.time() - start_time
            async with self._lock:
                self.metrics.total_calls += 1
                self.metrics.total_latency += elapsed
                if has_error:
                    self.metrics.total_errors += 1

    async def process_stream(self, input_data: Any, **kwargs) -> AsyncGenerator[Any, None]:
        """
        执行 Agent 流式处理逻辑并统一统计运行指标。

        指标口径说明：
        - total_calls：每次进入 process_stream 记一次
        - total_latency：从调用开始到流结束/异常的整体耗时
        - total_errors：流式处理过程中发生异常的次数
        """
        start_time = time.time()
        has_error = False

        try:
            result = await self._run(input_data, stream=True, **kwargs)

            if not hasattr(result, "__aiter__"):
                raise TypeError("process_stream 必须返回 AsyncGenerator")

            async for chunk in result:
                yield chunk

        except Exception:
            has_error = True
            logger.error(
                f"Agent {self.agent_id} stream processing failed, input_type={type(input_data)}",
                exc_info=True
            )
            raise

        finally:
            elapsed = time.time() - start_time
            async with self._lock:
                self.metrics.total_calls += 1
                self.metrics.total_latency += elapsed
                if has_error:
                    self.metrics.total_errors += 1

    # ========= 核心调度逻辑 =========

    async def _run(self, input_data: Any, *, stream: bool, **kwargs):
        if self._closed:
            raise RuntimeError(f"Agent {self.agent_id} is closed")

        # 🔹 新增：发言权检查
        if not self.active:
            raise RuntimeError(f"Agent {self.agent_id} 当前没有发言权")

        await self.initialize()
        self._enter_running()
        start_time = time.monotonic()

        try:
            self.metrics.total_calls += 1
            result = await self._process(input_data, stream=stream, **kwargs)
            return result

        except Exception as e:
            self.metrics.total_errors += 1
            self.run_time_state = RuntimeState.ERROR
            logger.exception(f"Agent {self.agent_id} processing failed")
            raise

        finally:
            elapsed = time.monotonic() - start_time
            self.metrics.total_latency += elapsed
            if self.run_time_state != RuntimeState.CLOSED:
                self.run_time_state = RuntimeState.IDLE

    # ========= 子类需要实现的方法 =========

    @abstractmethod
    async def _process(self, input_data: Any, *, stream: bool, **kwargs):
        raise NotImplementedError

    @abstractmethod
    def customized_initialize(self):
        pass

    # ========= 生命周期 =========

    async def close(self):
        if self._closed:
            return
        self._closed = True
        self.run_time_state = RuntimeState.CLOSED
        await self._on_close()

    async def _on_close(self):
        pass

    # ========= 状态辅助 =========

    def _enter_running(self):
        if self.run_time_state == RuntimeState.CLOSED:
            raise RuntimeError("Agent already closed")
        self.run_time_state = RuntimeState.RUNNING

    # ========= 健康检查 =========

    def health_check(self) -> dict:
        return self._status()

    def _status(self) -> dict:
        """返回 Agent 当前状态（实例级 + 会话级 + 指标）"""
        return {
            "agent_id": self.agent_id,
            "active": self.active,  # 实例级 active
            "speaking": getattr(self, "_speaking", False),  # 会话级 active
            "cognitive_state": getattr(self, "cognitive_state", None).value
            if hasattr(self, "cognitive_state") and self.cognitive_state else None,
            "run_time_state": self.run_time_state.value,
            "total_calls": self.metrics.total_calls,
            "total_errors": self.metrics.total_errors,
            "total_latency": round(self.metrics.total_latency, 4),
            "conversation_history_len": len(self.conversation_history),
        }
