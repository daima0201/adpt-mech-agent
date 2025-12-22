"""
ReAct Agent实现
基于BaseAgent的支持推理和工具调用的智能体
"""

import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncGenerator

from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.base.base_agent import BaseAgent
from src.agents.base.base_llm import BaseLLM
from src.agents.base.base_message import Message, MessageBuilder
from src.capabilities.tools.base import Tool
from src.capabilities.tools.registry import ToolRegistry


class ReActAgent(BaseAgent):
    """ReAct (Reasoning + Acting) Agent - 支持推理和工具调用"""

    async def _process(self, input_data: Any, *, stream: bool, **kwargs):
        pass

    def customized_initialize(self):
        pass

    def __init__(self, instance_id: str, config: AgentFullConfig, llm: Optional[BaseLLM] = None,
                 tool_registry: Optional[ToolRegistry] = None, max_iterations: int = 5):
        super().__init__(config, llm)
        self.tool_registry = tool_registry
        self.max_iterations = max_iterations
        self.thoughts_history = []
        self._initialized = False

    async def initialize(self):
        """异步初始化"""
        if not self._initialized:
            # 确保LLM已初始化
            if self.llm and hasattr(self.llm, 'initialize'):
                await self.llm.initialize()
            self._initialized = True

    async def process_message(self, message: Message) -> Message:
        """处理消息的核心方法（异步）"""
        # 确保已初始化
        await self.initialize()

        self.set_state(self.state.THINKING)

        try:
            # 调试信息：打印接收到的消息
            self.logger.debug(f"ReActAgent收到消息: {message.content[:100]}...")

            result = await self._run_react_async(message.content)
            response_message = MessageBuilder.create_assistant_message(result)

            # 保存到历史记录
            self.add_message_to_history(message)
            self.add_message_to_history(response_message)

            self.logger.info(f"ReAct处理完成，迭代次数: {len(self.thoughts_history)}")
            return response_message

        except Exception as e:
            self.set_state(self.state.ERROR)
            self.logger.error(f"ReAct处理失败: {str(e)}", exc_info=True)
            error_message = MessageBuilder.create_error_message(
                f"处理过程中出现错误: {str(e)}。请稍后重试或简化问题。"
            )
            return error_message
        finally:
            self.set_state(self.state.IDLE)

    async def run(self, input_text: str, **kwargs) -> str:
        """异步运行方法"""
        await self.initialize()

        user_message = MessageBuilder.create_user_message(input_text)
        response_message = await self.process_message(user_message)

        return response_message.content

    async def stream_process_message(self, message: Message) -> AsyncGenerator[str, None]:
        """流式处理消息 - ReAct智能体的流式实现"""
        # 确保已初始化
        await self.initialize()

        self.set_state(self.state.THINKING)

        try:
            # 调试信息：打印接收到的消息
            self.logger.debug(f"ReActAgent收到消息(流式): {message.content[:100]}...")

            # 使用流式ReAct处理
            result = ""
            thoughts = []
            current_iteration = 0

            while current_iteration < self.max_iterations:
                prompt = self._build_react_prompt(message.content, thoughts)

                # 检查LLM是否支持流式调用
                if hasattr(self.llm, 'stream_invoke'):
                    # 流式调用LLM
                    response_text = ""

                    # 构建正确的消息格式
                    messages = [{"role": "user", "content": prompt}]

                    # 检查stream_invoke返回的是异步生成器还是普通生成器
                    stream_result = self.llm.stream_invoke(messages)

                    if hasattr(stream_result, '__aiter__'):
                        # 异步生成器
                        async for chunk in stream_result:
                            response_text += chunk
                            yield chunk
                            await asyncio.sleep(0.01)  # 小延迟让流式效果更明显
                    else:
                        # 普通生成器
                        for chunk in stream_result:
                            response_text += chunk
                            yield chunk
                            await asyncio.sleep(0.01)  # 小延迟让流式效果更明显

                    # 解析响应并执行工具
                    thought, action, observation = self._parse_react_response(response_text)

                    if action == "FINISH":
                        break
                    elif action in ["knowledge_base", "calculator", "search", "validator"]:
                        # 执行工具
                        tool_result = await self.execute_tool(action, parameters)
                        thoughts.append({
                            "thought": response_text,
                            "action": action,
                            "parameters": parameters,
                            "result": tool_result
                        })

                        # 流式输出工具执行结果
                        tool_output = f"\n🔧 执行工具 '{action}': {tool_result}\n"
                        for char in tool_output:
                            yield char
                            await asyncio.sleep(0.01)
                    else:
                        # 无效动作
                        error_msg = f"无效动作: {action}"
                        for char in error_msg:
                            yield char
                            await asyncio.sleep(0.01)
                        break
                else:
                    # LLM不支持流式，使用普通方式
                    response = await self.llm.invoke(prompt)
                    yield response

                    # 解析响应并执行工具
                    action, parameters = self._parse_action(response)

                    if action == "FINISH":
                        break
                    elif action in ["knowledge_base", "calculator", "search", "validator"]:
                        # 执行工具
                        tool_result = await self.execute_tool(action, parameters)
                        thoughts.append({
                            "thought": response,
                            "action": action,
                            "parameters": parameters,
                            "result": tool_result
                        })
                    else:
                        # 无效动作
                        yield f"无效动作: {action}"
                        break

                current_iteration += 1

            # 保存到历史记录
            self.add_message_to_history(message)
            response_message = MessageBuilder.create_assistant_message(result)
            self.add_message_to_history(response_message)

            self.logger.info(f"ReAct流式处理完成，迭代次数: {len(thoughts)}")

        except Exception as e:
            self.set_state(self.state.ERROR)
            self.logger.error(f"ReAct流式处理失败: {str(e)}", exc_info=True)
            error_msg = f"处理过程中出现错误: {str(e)}。请稍后重试或简化问题。"
            for char in error_msg:
                yield char
                await asyncio.sleep(0.01)
        finally:
            self.set_state(self.state.IDLE)

    async def _run_react_async(self, input_text: str) -> str:
        """异步ReAct推理循环"""
        thoughts = []
        current_iteration = 0

        while current_iteration < self.max_iterations:
            prompt = self._build_react_prompt(input_text, thoughts)

            # 调试信息：打印ReAct迭代提示
            print(f"DEBUG: ReActAgent第{current_iteration + 1}次迭代提示:\n{prompt}")

            # 安全调用LLM，处理异步/同步差异
            response = await self._call_llm_safe(prompt)

            thought, action, observation = self._parse_react_response(response)
            thoughts.append((thought, action, observation))

            if not action or action == "FINISH":
                break

            # 如果是最终回答，结束循环
            if not action or action.upper() == "FINISH":
                self.logger.debug("推理完成")
                break

            # 执行工具调用
            if action and self.tool_registry:
                try:
                    observation = await self._execute_action_async(action)
                    thoughts[-1] = (thought, action, observation)  # 更新观察结果
                except Exception as e:
                    observation = f"工具执行失败: {str(e)}"
                    thoughts[-1] = (thought, action, observation)

                    # 工具失败时是否继续？这里可以选择停止
                    if "找不到工具" in observation:
                        break

            current_iteration += 1

        # 保存思考历史
        self.thoughts_history.extend(thoughts)

        return self._extract_final_answer(thoughts)

    async def _call_llm_safe(self, prompt: str) -> str:
        """安全调用LLM，处理异步/同步差异"""
        if not self.llm:
            raise ValueError("LLM未设置")

        messages = [{"role": "user", "content": prompt}]

        # 检查是否是异步方法
        if hasattr(self.llm, 'async_invoke'):
            return await self.llm.async_invoke(messages)
        elif asyncio.iscoroutinefunction(getattr(self.llm, 'invoke', None)):
            return await self.llm.invoke(messages)
        elif hasattr(self.llm, 'invoke'):
            # 同步调用
            return self.llm.invoke(messages)
        else:
            # 尝试通用调用
            return await self.llm(messages)

    async def _execute_action_async(self, action: str) -> str:
        """异步执行动作（工具调用）"""
        if not self.tool_registry:
            return "错误：未配置工具注册表"

        # 解析动作格式：工具名:参数JSON
        parts = action.split(':', 1)
        if len(parts) != 2:
            return f"错误：动作格式不正确，应为 '工具名:{{参数}}'，收到: {action}"

        tool_name, params_str = parts
        tool_name = tool_name.strip()

        # 获取工具
        tool = self.tool_registry.get_tool(tool_name)
        if not tool:
            available_tools = []
            try:
                available_tools = self.tool_registry.list_tools()
            except AttributeError:
                if hasattr(self.tool_registry, 'tools'):
                    available_tools = list(self.tool_registry.tools.keys())
                elif hasattr(self.tool_registry, '_tools'):
                    available_tools = list(self.tool_registry._tools.keys())

            return f"错误：找不到工具 '{tool_name}'，可用工具: {', '.join(available_tools)}"

        # 解析参数
        params = self._parse_tool_params(params_str)

        # 执行工具
        try:
            if hasattr(tool, 'async_execute'):
                result = await tool.async_execute(**params)
            elif hasattr(tool, 'execute'):
                result = tool.execute(**params)
                if asyncio.iscoroutine(result):
                    result = await result
            else:
                # 如果工具不可调用，使用execute方法
                if hasattr(tool, 'execute'):
                    result = tool.execute(**params)
                    if asyncio.iscoroutine(result):
                        result = await result
                else:
                    result = f"工具 {tool_name} 无法执行"

            return str(result)[:500]  # 限制长度

        except Exception as e:
            self.logger.error(f"工具执行失败 {tool_name}: {e}")
            return f"工具执行失败: {str(e)}"

    def _build_react_prompt(self, query: str, thoughts: List) -> str:
        """构建ReAct提示词"""
        # 使用智能体的角色定义作为基础prompt
        base_prompt = "你是一个专业的AI助手，擅长推理和工具使用"

        # 优先从config的role_definition获取
        if hasattr(self.config, 'role_definition') and self.config.role_definition:
            base_prompt = self.config.role_definition.template
        # 其次从extra_params获取
        elif hasattr(self.config, 'extra_params') and self.config.extra_params:
            if 'role_definition' in self.config.extra_params:
                base_prompt = self.config.extra_params['role_definition']

        # 添加ReAct格式说明和可用工具列表
        available_tools = []
        if self.tool_registry:
            try:
                available_tools = self.tool_registry.list_tools()
            except AttributeError:
                # 如果list_tools不存在，尝试其他方式获取工具列表
                if hasattr(self.tool_registry, 'tools'):
                    available_tools = list(self.tool_registry.tools.keys())
                elif hasattr(self.tool_registry, '_tools'):
                    available_tools = list(self.tool_registry._tools.keys())

        tools_info = ""
        if available_tools:
            tools_info = f"\n可用工具: {', '.join(available_tools)} - 只能使用这些具体的工具名称，不能自己发明动作名称"

        react_format = f"""
请按照以下格式进行思考和回答：
思考：[你的思考过程]
行动：[要执行的动作名称{tools_info}，如果没有动作则写FINISH]
观察：[动作执行的结果或观察到的信息]

重要规则：
1. 行动部分只能写FINISH或可用的工具名称
2. 不要发明新的动作名称
3. 如果不需要工具，直接写FINISH
4. 在思考部分给出完整的最终答案
"""

        prompt = f"{base_prompt}{react_format}\n\n问题：{query}\n\n"

        if thoughts:
            prompt += "之前的思考过程：\n"
            for i, (thought, action, observation) in enumerate(thoughts):
                prompt += f"第{i + 1}轮:\n"
                if thought:
                    prompt += f"思考：{thought}\n"
                if action:
                    prompt += f"行动：{action}\n"
                if observation:
                    prompt += f"观察：{observation}\n"
                prompt += "\n"
            prompt += "请继续思考：\n"
        else:
            prompt += "请开始思考这个问题：\n"

        return prompt

    def _parse_react_response(self, response: str) -> tuple:
        """解析ReAct响应"""
        lines = response.split('\n')
        thought = ""
        action = ""
        observation = ""

        current_section = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 检测新的部分开始
            if line.startswith('思考：') or '思考:' in line:
                current_section = 'thought'
                thought = line.replace('思考：', '').replace('思考:', '').strip()
            elif line.startswith('行动：') or '行动:' in line or '动作:' in line:
                current_section = 'action'
                action = line.replace('行动：', '').replace('行动:', '').replace('动作：', '').replace('动作:',
                                                                                                     '').strip()
            elif line.startswith('观察：') or '观察:' in line:
                current_section = 'observation'
                observation = line.replace('观察：', '').replace('观察:', '').strip()
            elif current_section == 'thought':
                thought += " " + line
            elif current_section == 'action':
                action += " " + line
            elif current_section == 'observation':
                observation += " " + line

        # 清理多余空格
        thought = thought.strip()
        action = action.strip()
        observation = observation.strip()

        # 如果没有明确格式，尝试智能解析
        if not thought and not action and not observation:
            # 如果响应很短，可能是直接回答
            if len(response.strip()) < 100:
                thought = response.strip()
                action = "FINISH"
            else:
                # 否则将整个响应作为思考
                thought = response.strip()

        return thought, action, observation

    def _parse_tool_params(self, params_str: str) -> Dict[str, Any]:
        """安全解析工具参数"""
        params_str = params_str.strip()

        if not params_str:
            return {}

        # 尝试解析为JSON
        if params_str.startswith('{') and params_str.endswith('}'):
            try:
                return json.loads(params_str)
            except json.JSONDecodeError:
                pass

        # 如果不是有效JSON，作为单个参数
        return {"input": params_str}

    def _extract_final_answer(self, thoughts: List) -> str:
        """从思考过程中提取最终答案"""
        if not thoughts:
            return "未能生成有效回答"

        last_thought, last_action, last_observation = thoughts[-1]

        # 添加检查
        if last_action and last_action != "FINISH" and last_observation:
            # 如果最后一次有工具调用但未完成，说明可能中断了
            return f"推理未完成。最后执行了：{last_action}，结果：{last_observation}"

        if last_observation:
            return last_observation
        elif last_thought:
            return last_thought
        else:
            return "思考过程不完整"

    def run_with_tools(self, input_text: str, available_tools: List[Tool], **kwargs) -> Dict[str, Any]:
        """使用指定工具集运行"""

        # 临时设置工具注册表
        original_registry = self.tool_registry
        if hasattr(self, '_temp_tool_registry'):
            self.tool_registry = self._temp_tool_registry

        try:
            response = self.run(input_text, **kwargs)

            return {
                'final_answer': response,
                'thought_process': self.thoughts_history,
                'tools_used': [thought[1] for thought in self.thoughts_history if thought[1]],
                'iterations': len(self.thoughts_history)
            }
        finally:
            # 恢复原始工具注册表
            self.tool_registry = original_registry

    def get_reasoning_trace(self) -> List[Dict[str, Any]]:
        """获取完整的推理轨迹"""
        trace = []

        for i, (thought, action, observation) in enumerate(self.thoughts_history):
            trace.append({
                'step': i + 1,
                'thought': thought,
                'action': action,
                'observation': observation,
                'has_tool_call': bool(action and action != 'FINISH')
            })

        return trace

    def reset_reasoning(self) -> None:
        """重置推理状态"""
        self.thoughts_history.clear()

    def set_tools(self, tools: List[Tool]) -> None:
        """动态设置工具"""
        if not hasattr(self, '_temp_tool_registry'):
            self._temp_tool_registry = ToolRegistry()

        for tool in tools:
            self._temp_tool_registry.register_tool(tool)
