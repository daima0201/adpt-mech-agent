"""
规划求解Agent实现
基于BaseAgent的支持复杂任务分解和分步执行的智能体
"""

import asyncio
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional, Iterator

from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.base.base_agent import BaseAgent
from src.agents.base.base_llm import BaseLLM
from src.agents.base.base_message import Message, MessageBuilder


class PlanAndSolveAgent(BaseAgent):
    """规划求解Agent - 支持复杂任务分解和分步执行"""

    async def _process(self, input_data: Any, *, stream: bool, **kwargs):
        pass

    def customized_initialize(self):
        pass

    def __init__(self, instance_id: str, config: AgentFullConfig, llm: Optional[BaseLLM] = None):
        super().__init__(config, llm)
        self.plans_history = []

    async def process_message(self, message: Message) -> Message:
        """处理消息的核心方法（异步）"""
        self.set_state(self.state.THINKING)

        try:
            # 调试信息：打印接收到的消息
            self.logger.debug(f"PlanAndSolveAgent收到消息: {message.content}")

            result = await self._run_with_planning_async(message.content)
            response_message = MessageBuilder.create_assistant_message(result['final_answer'])

            # 保存到历史记录
            self.add_message_to_history(message)
            self.add_message_to_history(response_message)

            self.logger.info(f"规划求解完成，步骤数: {result['total_steps']}, 成功率: {result['success_rate']:.2f}")
            return response_message

        except Exception as e:
            self.set_state(self.state.ERROR)
            self.logger.error(f"规划求解失败: {str(e)}")
            error_message = MessageBuilder.create_error_message(f"规划求解失败: {str(e)}")
            return error_message
        finally:
            self.set_state(self.state.IDLE)

    def run(self, input_text: str, **kwargs) -> str:
        """同步运行方法"""
        user_message = MessageBuilder.create_user_message(input_text)
        response_message = asyncio.run(self.process_message(user_message))

        return response_message.content

    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """流式规划处理"""
        result = self.run(input_text, **kwargs)
        for char in result:
            yield char

    async def _run_with_planning_async(self, input_text: str) -> Dict[str, Any]:
        """异步规划推理"""
        # 生成计划
        plan = await self._generate_plan_async(input_text)

        # 执行计划
        execution_result = await self._execute_plan_async(plan, input_text)

        # 整合结果
        final_answer = await self._integrate_results_async(execution_result)

        result = {
            'original_query': input_text,
            'generated_plan': plan,
            'execution_steps': execution_result['steps'],
            'final_answer': final_answer,
            'success_rate': execution_result['success_rate'],
            'total_steps': len(plan['steps'])
        }

        # 记录计划历史
        self.plans_history.append({
            'query': input_text,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })

        return result

    async def run_with_planning_async(self, input_text: str, **kwargs) -> Dict[str, Any]:
        """带详细规划的异步运行方法"""

        # 生成计划
        plan = await self._generate_plan_async(input_text)

        # 执行计划
        execution_result = await self._execute_plan_async(plan, input_text)

        # 整合结果
        final_answer = self._integrate_results(execution_result)

        result = {
            'original_query': input_text,
            'generated_plan': plan,
            'execution_steps': execution_result['steps'],
            'final_answer': final_answer,
            'success_rate': execution_result['success_rate'],
            'total_steps': len(plan['steps'])
        }

        # 记录计划历史
        self.plans_history.append({
            'query': input_text,
            'result': result,
            'timestamp': datetime.now().isoformat()
        })

        return result

    async def _generate_plan_async(self, query: str) -> Dict[str, Any]:
        """异步生成任务执行计划"""
        # 使用智能体的角色定义作为基础prompt
        if hasattr(self.config, 'role_definition') and self.config.role_definition:
            base_prompt = self.config.role_definition.template
        else:
            base_prompt = "你是一个专业的AI助手，擅长规划和解决问题"

        planning_prompt = f"""{base_prompt}

请为以下问题制定一个详细的执行计划：

问题：{query}

请将任务分解为具体的步骤，并为每个步骤指定：
1. 步骤描述
2. 预期输出
3. 依赖关系（如果有）
4. 预计难度（简单/中等/困难）

请以JSON格式回复：
{{
    "goal": "总体目标",
    "steps": [
        {{
            "step_number": 1,
            "description": "步骤描述",
            "expected_output": "预期输出",
            "dependencies": [],
            "difficulty": "简单"
        }}
    ]
}}"""

        # 调试信息：打印发送给LLM的规划提示
        self.logger.debug(f"PlanAndSolveAgent发送规划提示:\n{planning_prompt}")

        plan_response = await self._call_llm_safe(planning_prompt)

        try:
            # 尝试解析JSON
            json_match = re.search(r'\{.*?\}', plan_response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                # 如果JSON解析失败，使用默认结构
                plan_data = self._parse_text_plan(plan_response, query)
        except:
            plan_data = self._parse_text_plan(plan_response, query)

        return plan_data

    async def _generate_plan_async(self, query: str) -> Dict[str, Any]:
        """异步生成任务执行计划"""

        planning_prompt = f"""请为以下问题制定一个详细的执行计划：

问题：{query}

请将任务分解为具体的步骤，并为每个步骤指定：
1. 步骤描述
2. 预期输出
3. 依赖关系（如果有）
4. 预计难度（简单/中等/困难）

请以JSON格式回复：
{{
    "goal": "总体目标",
    "steps": [
        {{
            "step_number": 1,
            "description": "步骤描述",
            "expected_output": "预期输出",
            "dependencies": [],
            "difficulty": "简单"
        }}
    ]
}}"""

        plan_response = await self._call_llm_safe(planning_prompt)

        try:
            # 尝试解析JSON
            json_match = re.search(r'\{.*?\}', plan_response, re.DOTALL)
            if json_match:
                plan_data = json.loads(json_match.group())
            else:
                # 如果JSON解析失败，使用默认结构
                plan_data = self._parse_text_plan(plan_response, query)
        except:
            plan_data = self._parse_text_plan(plan_response, query)

        return plan_data

    @staticmethod
    def _parse_text_plan(plan_text: str, query: str) -> Dict[str, Any]:
        """解析文本格式的计划"""

        steps = []
        lines = plan_text.split('\n')
        current_step = None

        for line in lines:
            line = line.strip()

            # 检测步骤开始
            step_match = re.match(r'(\d+)[\.、:]\s*(.*)', line)
            if step_match:
                if current_step:
                    steps.append(current_step)

                step_num = int(step_match.group(1))
                description = step_match.group(2)

                current_step = {
                    'step_number': step_num,
                    'description': description,
                    'expected_output': '',
                    'dependencies': [],
                    'difficulty': '中等'
                }
            elif current_step and line:
                # 添加到当前步骤的描述中
                current_step['description'] += ' ' + line

        if current_step:
            steps.append(current_step)

        return {
            'goal': query,
            'steps': steps
        }

    async def _execute_plan_async(self, plan: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """异步执行计划"""

        steps_result = []
        successful_steps = 0

        for step in plan['steps']:
            step_result = await self._execute_step_async(step, original_query, steps_result)
            steps_result.append(step_result)

            if step_result['success']:
                successful_steps += 1

        success_rate = successful_steps / len(plan['steps']) if plan['steps'] else 1.0

        return {
            'steps': steps_result,
            'success_rate': success_rate,
            'total_steps': len(plan['steps']),
            'successful_steps': successful_steps
        }

    def _execute_plan(self, plan: Dict[str, Any], original_query: str) -> Dict[str, Any]:
        """执行计划"""

        steps_result = []
        successful_steps = 0

        for step in plan['steps']:
            step_result = self._execute_step(step, original_query, steps_result)
            steps_result.append(step_result)

            if step_result['success']:
                successful_steps += 1

        success_rate = successful_steps / len(plan['steps']) if plan['steps'] else 1.0

        return {
            'steps': steps_result,
            'success_rate': success_rate,
            'total_steps': len(plan['steps']),
            'successful_steps': successful_steps
        }

    async def _execute_step_async(self, step: Dict[str, Any], original_query: str, previous_results: List) -> Dict[
        str, Any]:
        """异步执行单个步骤"""

        # 构建上下文
        context = f"原始问题：{original_query}\n"
        context += f"当前步骤：{step['description']}\n"

        # 添加之前步骤的结果作为上下文
        if previous_results:
            context += "之前的步骤结果：\n"
            for i, result in enumerate(previous_results):
                if result['success']:
                    context += f"步骤 {i + 1}: {result['output'][:100]}...\n"

        step_prompt = f"""{context}

请完成这个步骤。请提供清晰、准确的回答。"""

        try:
            # 调试信息：打印步骤执行提示
            self.logger.debug(f"PlanAndSolveAgent执行步骤 {step['step_number']} 提示:\n{step_prompt}")

            response = await self._call_llm_safe(step_prompt)

            return {
                'step_number': step['step_number'],
                'description': step['description'],
                'input': step_prompt,
                'output': response,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'step_number': step['step_number'],
                'description': step['description'],
                'input': step_prompt,
                'output': '',
                'success': False,
                'error': str(e)
            }

    def _execute_step(self, step: Dict[str, Any], original_query: str, previous_results: List) -> Dict[str, Any]:
        """执行单个步骤（同步版本）"""
        import asyncio

        # 构建上下文
        context = f"原始问题：{original_query}\n"
        context += f"当前步骤：{step['description']}\n"

        # 添加之前步骤的结果作为上下文
        if previous_results:
            context += "之前的步骤结果：\n"
            for i, result in enumerate(previous_results):
                if result['success']:
                    context += f"步骤 {i + 1}: {result['output'][:100]}...\n"

        step_prompt = f"""{context}

请完成这个步骤。请提供清晰、准确的回答。"""

        try:
            response = asyncio.run(self._call_llm_safe(step_prompt))

            return {
                'step_number': step['step_number'],
                'description': step['description'],
                'input': step_prompt,
                'output': response,
                'success': True,
                'error': None
            }
        except Exception as e:
            return {
                'step_number': step['step_number'],
                'description': step['description'],
                'input': step_prompt,
                'output': '',
                'success': False,
                'error': str(e)
            }

    async def _integrate_results_async(self, execution_result: Dict[str, Any]) -> str:
        """异步整合各步骤结果"""

        integration_prompt = """请基于以下步骤的执行结果，给出最终的完整回答：

"""

        for step in execution_result['steps']:
            if step['success']:
                integration_prompt += f"步骤 {step['step_number']} ({step['description']}):\n{step['output']}\n\n"

        integration_prompt += "请将这些步骤的结果整合成一个连贯、完整的最终回答。"

        # 调试信息：打印结果整合提示
        self.logger.debug(f"PlanAndSolveAgent结果整合提示:\n{integration_prompt}")

        final_answer = await self._call_llm_safe(integration_prompt)
        return final_answer

    def _integrate_results(self, execution_result: Dict[str, Any]) -> str:
        """整合各步骤结果（同步版本）"""
        import asyncio

        integration_prompt = """请基于以下步骤的执行结果，给出最终的完整回答：

"""

        for step in execution_result['steps']:
            if step['success']:
                integration_prompt += f"步骤 {step['step_number']} ({step['description']}):\n{step['output']}\n\n"

        integration_prompt += "请将这些步骤的结果整合成一个连贯、完整的最终回答。"

        final_answer = asyncio.run(self._call_llm_safe(integration_prompt))
        return final_answer

    def get_planning_stats(self) -> Dict[str, Any]:
        """获取规划统计信息"""

        if not self.plans_history:
            return {'total_plans': 0, 'average_steps': 0.0, 'average_success_rate': 0.0}

        total_plans = len(self.plans_history)
        total_steps = sum(len(record['result']['generated_plan']['steps']) for record in self.plans_history)
        total_success_rate = sum(record['result']['success_rate'] for record in self.plans_history)

        return {
            'total_plans': total_plans,
            'average_steps': total_steps / total_plans,
            'average_success_rate': total_success_rate / total_plans,
            'most_complex_plan': max(len(record['result']['generated_plan']['steps']) for record in self.plans_history)
        }

    def export_plan(self, plan_id: int = -1) -> Dict[str, Any]:
        """导出特定计划"""

        if not self.plans_history:
            return {'error': '没有可导出的计划'}

        if plan_id < 0:
            plan_id = len(self.plans_history) + plan_id

        if plan_id < 0 or plan_id >= len(self.plans_history):
            return {'error': '无效的计划ID'}

        plan_record = self.plans_history[plan_id]

        return {
            'plan_id': plan_id,
            'query': plan_record['query'],
            'plan': plan_record['result']['generated_plan'],
            'execution_results': plan_record['result']['execution_steps'],
            'final_answer': plan_record['result']['final_answer'],
            'timestamp': plan_record['timestamp']
        }

    def add_tool(self, tool_name: str, tool_func: callable):
        """添加工具到Agent"""
        if not hasattr(self, '_tools'):
            self._tools = {}
        self._tools[tool_name] = tool_func
        self.logger.info(f"工具 '{tool_name}' 已添加到规划求解Agent")

    async def _execute_step_with_tools_async(self, step: Dict[str, Any], original_query: str, previous_results: List) -> \
            Dict[str, Any]:
        """异步执行单个步骤（支持工具调用）"""

        # 检查是否需要使用工具
        if hasattr(self, '_tools') and self._tools:
            # 分析步骤描述，判断是否需要工具
            step_description = step['description'].lower()

            # 简单的工具匹配逻辑
            for tool_name, tool_func in self._tools.items():
                if tool_name.lower() in step_description:
                    try:
                        # 构建工具调用上下文
                        context = f"原始问题：{original_query}\n当前步骤：{step['description']}"

                        # 调用工具
                        if asyncio.iscoroutinefunction(tool_func):
                            tool_result = await tool_func(context)
                        else:
                            tool_result = tool_func(context)

                        return {
                            'step_number': step['step_number'],
                            'description': step['description'],
                            'input': context,
                            'output': str(tool_result),
                            'success': True,
                            'error': None,
                            'tool_used': tool_name
                        }
                    except Exception as e:
                        self.logger.error(f"工具 '{tool_name}' 执行失败: {str(e)}")
                        # 回退到LLM执行
                        return await self._execute_step_async(step, original_query, previous_results)

        # 如果没有匹配的工具或工具执行失败，使用LLM执行
        return await self._execute_step_async(step, original_query, previous_results)

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
