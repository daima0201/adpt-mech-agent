# """
# 反思Agent实现
# 基于BaseAgent的支持自我反思和改进的智能体
# """
#
# import asyncio
#
# from datetime import datetime
# from typing import List, Dict, Any, Optional, Iterator
#
# from src.agents.DTO.agent_full_config import AgentFullConfig
# from src.agents.base.base_agent import BaseAgent
# from src.agents.base.base_llm import BaseLLM
# from src.agents.base.base_message import Message, MessageBuilder
#
#
# class ReflectionAgent(BaseAgent):
#     """反思Agent - 支持自我评估和改进"""
#
#     def __init__(self, instance_id: str, config: AgentFullConfig, llm: Optional[BaseLLM] = None,
#                  reflection_threshold: float = 0.7):
#         super().__init__(config, llm)
#         self.reflection_threshold = reflection_threshold
#         self.reflection_history = []
#
#     async def process_message(self, message: Message) -> Message:
#         """处理消息的核心方法（异步）"""
#         self.set_state(self.state.THINKING)
#
#         try:
#             # 调试信息：打印接收到的消息
#             self.logger.debug(f"ReflectionAgent收到消息: {message.content}")
#
#             result = await self._run_with_reflection_async(message.content)
#             response_message = MessageBuilder.create_assistant_message(result['final_response'])
#
#             # 保存到历史记录
#             self.add_message_to_history(message)
#             self.add_message_to_history(response_message)
#
#             self.logger.info(f"反思处理完成，反思次数: {len(self.reflection_history)}")
#             return response_message
#
#         except Exception as e:
#             self.set_state(self.state.ERROR)
#             self.logger.error(f"反思处理失败: {str(e)}")
#             error_message = MessageBuilder.create_error_message(f"反思处理失败: {str(e)}")
#             return error_message
#         finally:
#             self.set_state(self.state.IDLE)
#
#     def run(self, input_text: str, **kwargs) -> str:
#         """同步运行方法"""
#         import asyncio
#
#         user_message = MessageBuilder.create_user_message(input_text)
#         response_message = asyncio.run(self.process_message(user_message))
#
#         return response_message.content
#
#     def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
#         """流式反思处理"""
#         result = self.run(input_text, **kwargs)
#         for char in result:
#             yield char
#
#     async def _run_with_reflection_async(self, input_text: str) -> Dict[str, Any]:
#         """异步反思推理"""
#         # 构建消息列表，包含系统提示
#         messages = []
#
#         # 添加系统消息 - 使用role_definition作为system_prompt
#         if hasattr(self.config, 'role_definition') and self.config.role_definition:
#             system_prompt = self.config.role_definition.template
#         else:
#             # 回退到默认系统提示
#             system_prompt = "你是一个善于反思和改进的AI助手"
#
#         messages.append({"role": "system", "content": system_prompt})
#         messages.append({"role": "user", "content": input_text})
#
#         # 调试信息：打印初始响应消息
#         self.logger.debug(f"ReflectionAgent发送给LLM的初始消息:\n系统提示: {system_prompt}\n用户消息: {input_text}")
#
#         initial_response = await self._call_llm_safe(messages)
#
#         # 评估是否需要反思
#         needs_reflection = await self._should_reflect_async(initial_response, input_text)
#
#         if needs_reflection:
#             # 进行反思
#             reflection_result = await self._perform_reflection_async(initial_response, input_text)
#
#             # 基于反思改进回答
#             improved_response = await self._improve_response_async(initial_response, reflection_result)
#
#             result = {
#                 'initial_response': initial_response,
#                 'final_response': improved_response,
#                 'needed_reflection': True,
#                 'reflection_result': reflection_result,
#                 'improvement_score': self._calculate_improvement_score(initial_response, improved_response)
#             }
#         else:
#             result = {
#                 'initial_response': initial_response,
#                 'final_response': initial_response,
#                 'needed_reflection': False,
#                 'reflection_result': None,
#                 'improvement_score': 0.0
#             }
#
#         # 记录反思历史
#         self.reflection_history.append({
#             'input': input_text,
#             'result': result,
#             'timestamp': datetime.now().isoformat()
#         })
#
#         return result
#
#     async def run_with_reflection_async(self, input_text: str, **kwargs) -> Dict[str, Any]:
#         """带反思的异步运行方法"""
#
#         # 初始响应
#         messages = [{"role": "user", "content": input_text}]
#         initial_response = await self._call_llm_safe(messages)
#
#         # 评估是否需要反思
#         needs_reflection = await self._should_reflect_async(initial_response, input_text)
#
#         if needs_reflection:
#             # 进行反思
#             reflection_result = await self._perform_reflection_async(initial_response, input_text)
#
#             # 基于反思改进回答
#             improved_response = await self._improve_response_async(initial_response, reflection_result)
#
#             result = {
#                 'initial_response': initial_response,
#                 'final_response': improved_response,
#                 'needed_reflection': True,
#                 'reflection_result': reflection_result,
#                 'improvement_score': self._calculate_improvement_score(initial_response, improved_response)
#             }
#         else:
#             result = {
#                 'initial_response': initial_response,
#                 'final_response': initial_response,
#                 'needed_reflection': False,
#                 'reflection_result': None,
#                 'improvement_score': 0.0
#             }
#
#         # 记录反思历史
#         self.reflection_history.append({
#             'input': input_text,
#             'result': result,
#             'timestamp': datetime.now().isoformat()
#         })
#
#         return result
#
#     async def _should_reflect_async(self, response: str, query: str) -> bool:
#         """异步判断是否需要反思"""
#         confidence_score = await self._assess_confidence_async(response, query)
#         return confidence_score < self.reflection_threshold
#
#     def _should_reflect(self, response: str, query: str) -> bool:
#         """判断是否需要反思"""
#         confidence_score = self._assess_confidence(response, query)
#         return confidence_score < self.reflection_threshold
#
#     async def _assess_confidence_async(self, response: str, query: str) -> float:
#         """异步评估回答置信度"""
#         # 简化的置信度评估
#         return self._assess_confidence(response, query)
#
#     def _assess_confidence(self, response: str, query: str) -> float:
#         """评估回答置信度"""
#
#         # 基于长度的简单置信度评估
#         response_length = len(response.strip())
#         query_length = len(query.strip())
#
#         if response_length == 0:
#             return 0.0
#
#         # 如果回答太短或包含不确定词汇，降低置信度
#         uncertainty_words = ['可能', '大概', '也许', '不确定', '不清楚', '不知道']
#         has_uncertainty = any(word in response for word in uncertainty_words)
#
#         length_ratio = min(response_length / max(query_length, 1), 2.0) / 2.0
#         certainty_bonus = 0.3 if not has_uncertainty else 0.0
#
#         return min(length_ratio + certainty_bonus, 1.0)
#
#     async def _perform_reflection_async(self, response: str, query: str) -> Dict[str, Any]:
#         """异步执行反思过程"""
#         reflection_prompt = f"""请对以下回答进行反思和评估：
#
# 问题：{query}
# 当前回答：{response}
#
# 请从以下角度进行评估：
# 1. 准确性：回答是否准确反映了问题？
# 2. 完整性：是否遗漏了重要信息？
# 3. 清晰度：表达是否清晰易懂？
# 4. 改进建议：如何改进这个回答？
#
# 请提供详细的反思意见。"""
#
#         # 调试信息：打印反思提示
#         self.logger.debug(f"ReflectionAgent反思提示:\n{reflection_prompt}")
#
#         reflection_result = await self._call_llm_safe(reflection_prompt)
#
#         return {
#             'reflection_text': reflection_result,
#             'assessment_criteria': ['accuracy', 'completeness', 'clarity'],
#             'suggestions': self._extract_suggestions(reflection_result)
#         }
#
#     def _perform_reflection(self, response: str, query: str) -> Dict[str, Any]:
#         """执行反思过程（同步版本）"""
#         import asyncio
#
#         reflection_prompt = f"""请对以下回答进行反思和评估：
#
# 问题：{query}
# 当前回答：{response}
#
# 请从以下角度进行评估：
# 1. 准确性：回答是否准确反映了问题？
# 2. 完整性：是否遗漏了重要信息？
# 3. 清晰度：表达是否清晰易懂？
# 4. 改进建议：如何改进这个回答？
#
# 请提供详细的反思意见。"""
#
#         reflection_result = asyncio.run(self._call_llm_safe(reflection_prompt))
#
#         return {
#             'reflection_text': reflection_result,
#             'assessment_criteria': ['accuracy', 'completeness', 'clarity'],
#             'suggestions': self._extract_suggestions(reflection_result)
#         }
#
#     def _extract_suggestions(self, reflection_text: str) -> List[str]:
#         """从反思文本中提取改进建议"""
#         suggestions = []
#         lines = reflection_text.split('\n')
#
#         for line in lines:
#             line = line.strip()
#             if any(keyword in line for keyword in ['建议', '应该', '可以', '需要']):
#                 suggestions.append(line)
#
#         return suggestions[:5]  # 最多返回5条建议
#
#     async def _improve_response_async(self, original_response: str, reflection_result: Dict[str, Any]) -> str:
#         """异步基于反思改进回答"""
#         improvement_prompt = f"""原始回答：{original_response}
#
# 反思意见：{reflection_result['reflection_text']}
#
# 请基于上述反思意见，改进原始回答，使其更加准确、完整和清晰。"""
#
#         # 调试信息：打印改进提示
#         self.logger.debug(f"ReflectionAgent改进提示:\n{improvement_prompt}")
#
#         improved_response = await self._call_llm_safe(improvement_prompt)
#         return improved_response
#
#     def _improve_response(self, original_response: str, reflection_result: Dict[str, Any]) -> str:
#         """基于反思改进回答（同步版本）"""
#         import asyncio
#
#         improvement_prompt = f"""原始回答：{original_response}
#
# 反思意见：{reflection_result['reflection_text']}
#
# 请基于上述反思意见，改进原始回答，使其更加准确、完整和清晰。"""
#
#         improved_response = asyncio.run(self._call_llm_safe(improvement_prompt))
#         return improved_response
#
#     def _calculate_improvement_score(self, original: str, improved: str) -> float:
#         """计算改进程度评分"""
#
#         # 简单的改进评分（基于长度变化和内容差异）
#         original_len = len(original)
#         improved_len = len(improved)
#
#         if original_len == 0:
#             return 1.0 if improved_len > 0 else 0.0
#
#         length_improvement = min((improved_len - original_len) / original_len, 1.0)
#
#         # 简单的相似度检查（避免完全重复）
#         similarity = self._calculate_similarity(original, improved)
#         content_improvement = 1.0 - similarity
#
#         return (length_improvement + content_improvement) / 2.0
#
#     @staticmethod
#     def _calculate_similarity(text1: str, text2: str) -> float:
#         """计算文本相似度"""
#
#         words1 = set(text1.split())
#         words2 = set(text2.split())
#
#         if not words1 or not words2:
#             return 0.0
#
#         intersection = words1 & words2
#         union = words1 | words2
#
#         return len(intersection) / len(union)
#
#     def get_reflection_stats(self) -> Dict[str, Any]:
#         """获取反思统计信息"""
#
#         if not self.reflection_history:
#             return {'total_reflections': 0, 'average_improvement': 0.0}
#
#         total_reflections = len(self.reflection_history)
#         reflections_needed = sum(1 for record in self.reflection_history if record['result']['needed_reflection'])
#         avg_improvement = sum(
#             record['result']['improvement_score'] for record in self.reflection_history) / total_reflections
#
#         return {
#             'total_reflections': total_reflections,
#             'reflections_needed': reflections_needed,
#             'reflection_rate': reflections_needed / total_reflections,
#             'average_improvement': avg_improvement
#         }
#
#     async def _call_llm_safe(self, prompt_or_messages) -> str:
#         """安全调用LLM，处理异步/同步差异"""
#         if not self.llm:
#             raise ValueError("LLM未设置")
#
#         # 统一消息格式
#         if isinstance(prompt_or_messages, str):
#             messages = [{"role": "user", "content": prompt_or_messages}]
#         else:
#             messages = prompt_or_messages
#
#         # 检查是否是异步方法
#         if hasattr(self.llm, 'async_invoke'):
#             return await self.llm.async_invoke(messages)
#         elif asyncio.iscoroutinefunction(getattr(self.llm, 'invoke', None)):
#             return await self.llm.invoke(messages)
#         elif hasattr(self.llm, 'invoke'):
#             # 同步调用
#             return self.llm.invoke(messages)
#         else:
#             # 尝试通用调用
#             return await self.llm(messages)
