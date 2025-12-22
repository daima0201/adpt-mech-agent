import asyncio
import logging
import time
from typing import Optional, Any, AsyncGenerator

from src.agents import BaseLLM
from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.base.prompt_agent import PromptAgent
from src.agents.enum.cognitive_state import CognitiveState
from src.shared.exceptions.agent_errors import AgentProcessingError

logger = logging.getLogger(__name__)


# ==================== SimpleAgent ====================

class SimpleAgent(PromptAgent):
    """
    SimpleAgent = 最小可用 Agent
    - session_id: 实例级属性
    - 支持流式和非流式
    - 支持 stop / interrupt
    """

    def __init__(self, agent_id: str, config: AgentFullConfig, llm: BaseLLM, max_history: int = 10):
        super().__init__(agent_id, config, max_history)
        self.llm = llm
        self.session_id: Optional[str] = None
        self._stop_event = asyncio.Event()
        self._enter_cognitive_state(CognitiveState.NONE)

        logger.info(f"SimpleAgent实例创建: {agent_id} ({config.agent_config.name}), 最大历史: {max_history}")

    # ========= 发言权调度 =========

    def release_speaking(self):
        """主动释放会话发言权"""
        self._enter_cognitive_state(CognitiveState.NONE)
        self.speaking = False
        self._stop_event.set()
        logger.info(f"{self.agent_id} 已释放发言权")

    async def on_session_switch(self, next_agent: PromptAgent):
        """当前 Agent 发言完毕，通知下一个 Agent 可以发言"""
        self.release_speaking()
        next_agent.speaking = True
        next_agent._enter_cognitive_state(CognitiveState.THINKING)

    # ========= Stop / Interrupt =========

    def stop(self):
        self._stop_event.set()

    # ========= 核心业务处理 =========

    async def _do_process(self, input_data: Any, *, stream: bool, **kwargs):
        # === 会话开始，申请发言权 ===
        self._enter_cognitive_state(CognitiveState.THINKING)
        self.speaking = True  # 明确申请发言权
        logger.info(f"{self.agent_id} 当前发言状态: {self.speaking}, CognitiveState: {self.cognitive_state}")

        try:
            # === 构建完整提示 ===
            prompt = self.build_full_prompt(str(input_data))

            # === 真正进入生成阶段 ===
            self._enter_cognitive_state(CognitiveState.PROCESSING)

            if stream:
                # ⚠️ 流式生成的状态恢复在 _stream_generate 内部处理
                return self._stream_generate(prompt)

            start_time = time.time()
            system_prompt = self._build_system_prompt()
            messages = self._build_messages(system_prompt, prompt)
            llm_kwargs = self._extract_llm_kwargs(kwargs)
            result = await self.llm.invoke(messages, **llm_kwargs)

            # 更新对话历史
            self._update_conversation_history(prompt, result)

            # 记录处理统计
            processing_time = time.time() - start_time
            logger.info(
                f"处理完成 - 实例: {self.agent_id}, "
                f"输入长度: {len(prompt)}, 输出长度: {len(result)}, "
                f"耗时: {processing_time:.2f}s"
            )
            return result

        except Exception:
            # 会话级错误
            self._enter_cognitive_state(CognitiveState.ERROR)
            raise

        finally:
            # === 结束会话，释放发言权（非流式） ===
            if not stream:
                self._enter_cognitive_state(CognitiveState.NONE)
                self.speaking = False

    async def _stream_generate(self, prompt: str, **kwargs) -> AsyncGenerator[str, None]:
        self._stop_event.clear()

        if not prompt or not prompt.strip():
            logger.warning("接收到空输入")
            yield "请输入有效的内容"
            return

        full_response = ""

        # === 流式生成开始 ===
        self._enter_cognitive_state(CognitiveState.PROCESSING)

        try:
            start_time = time.time()
            system_prompt = self._build_system_prompt()
            messages = self._build_messages(system_prompt, prompt)
            llm_kwargs = self._extract_llm_kwargs(kwargs)
            llm_kwargs['stream'] = True

            logger.debug(f"开始流式处理，输入长度: {len(prompt)}")

            # 获取流式响应
            stream_result = self.llm.stream_invoke(messages, **llm_kwargs)

            # 异步迭代
            async for chunk in stream_result:
                if self._stop_event.is_set():
                    logger.info(f"{self.agent_id} 流式生成被用户中断")
                    self._enter_cognitive_state(CognitiveState.NONE)  # 确保状态恢复
                    self.speaking = False
                    break

                chunk_str = str(chunk)
                if chunk_str:
                    full_response += chunk_str
                    yield chunk_str

            if not full_response.strip():
                logger.warning("LLM返回空响应")
                yield "抱歉，我没有收到有效的响应。"
                full_response = "抱歉，我没有收到有效的响应。"

            # 更新对话历史
            self._update_conversation_history(prompt, full_response)

            # 记录处理统计
            processing_time = time.time() - start_time
            logger.info(
                f"流式处理完成 - 实例: {self.agent_id}, "
                f"输入长度: {len(prompt)}, 输出长度: {len(full_response)}, "
                f"耗时: {processing_time:.2f}s"
            )

            # 流结束后（正常或中断）确保状态恢复
            if not self._stop_event.is_set():
                self._enter_cognitive_state(CognitiveState.NONE)

        except Exception as e:
            self._enter_cognitive_state(CognitiveState.ERROR)
            logger.error(f"流式处理失败 - 实例: {self.agent_id}, 错误: {str(e)}", exc_info=True)
            raise AgentProcessingError(f"流式处理失败: {str(e)}") from e

        finally:
            # 流结束后释放发言权
            self._enter_cognitive_state(CognitiveState.NONE)

    # ========= TODO:以下待重构 =========

    def _update_conversation_history(self, user_input: str, assistant_response: str):
        """
        更新对话历史

        Args:
            user_input: 用户输入
            assistant_response: 助手响应

        设计说明:
            1. 维护固定长度的对话历史
            2. 确保user和assistant消息成对出现
            3. 避免历史过长导致token超限
        """
        # 添加新的对话对
        self.conversation_history.append({"role": "user", "content": user_input, "agent_id": "USER-INPUT"})
        self.conversation_history.append(
            {"role": "assistant", "content": assistant_response, "agent_id": self.agent_id})

        # 限制历史长度
        if len(self.conversation_history) > self.max_history * 2:
            # 移除最旧的消息对
            removed_count = 0
            while len(self.conversation_history) > self.max_history * 2:
                self.conversation_history.pop(0)
                removed_count += 1
            if removed_count > 0:
                logger.debug(f"对话历史已修剪，移除了 {removed_count // 2} 对消息")

        logger.debug(f"对话历史更新，当前长度: {len(self.conversation_history)}")
