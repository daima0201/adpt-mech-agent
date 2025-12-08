"""
ReAct Agent实现
基于BaseAgent的支持推理和工具调用的智能体
"""

from typing import List, Dict, Any, Optional, Iterator
from src.agents.core.agent import Agent, AgentConfig
from src.agents.core.message import Message, MessageBuilder
from src.agents.core import HelloAgentsLLM
from src.agents.tools import Tool
from src.agents.tools import ToolRegistry


class ReActAgent(Agent):
    """ReAct (Reasoning + Acting) Agent - 支持推理和工具调用"""
    
    def __init__(self, config: AgentConfig, llm: Optional[HelloAgentsLLM] = None,
                 tool_registry: Optional[ToolRegistry] = None):
        super().__init__(config, llm)
        self.tool_registry = tool_registry
        self.max_iterations = config.max_iterations if hasattr(config, 'max_iterations') else 5
        self.thoughts_history = []
    
    async def process_message(self, message: Message) -> Message:
        """处理消息的核心方法（异步）"""
        self.set_state(self.state.THINKING)
        
        try:
            result = await self._run_react_async(message.content)
            response_message = MessageBuilder.create_assistant_message(result)
            
            # 保存到历史记录
            self.add_message_to_history(message)
            self.add_message_to_history(response_message)
            
            self.logger.info(f"ReAct处理完成，迭代次数: {len(self.thoughts_history)}")
            return response_message
            
        except Exception as e:
            self.set_state(self.state.ERROR)
            self.logger.error(f"ReAct处理失败: {str(e)}")
            error_message = MessageBuilder.create_error_message(f"ReAct处理失败: {str(e)}")
            return error_message
        finally:
            self.set_state(self.state.IDLE)
    
    def run(self, input_text: str, **kwargs) -> str:
        """同步运行方法"""
        import asyncio
        
        user_message = MessageBuilder.create_user_message(input_text)
        response_message = asyncio.run(self.process_message(user_message))
        
        return response_message.content
    
    def stream_run(self, input_text: str, **kwargs) -> Iterator[str]:
        """ReAct流式处理（简化版）"""
        # 对于复杂的ReAct流程，流式处理较复杂，这里返回完整响应
        result = self.run(input_text, **kwargs)
        for char in result:
            yield char
    
    async def _run_react_async(self, input_text: str) -> str:
        """异步ReAct推理循环"""
        thoughts = []
        current_iteration = 0
        
        while current_iteration < self.max_iterations:
            prompt = self._build_react_prompt(input_text, thoughts)
            response = await self.llm.invoke([{"role": "user", "content": prompt}])
            
            thought, action, observation = self._parse_react_response(response)
            thoughts.append((thought, action, observation))
            
            if not action or action == "FINISH":
                break
            
            if action and self.tool_registry:
                observation = await self._execute_action_async(action, {})
                thoughts[-1] = (thought, action, observation)
            
            current_iteration += 1
        
        # 保存思考历史
        self.thoughts_history.extend(thoughts)
        
        return self._extract_final_answer(thoughts)
    
    async def _execute_action_async(self, action: str, params: Dict) -> str:
        """异步执行动作（工具调用）"""
        if not self.tool_registry:
            return "错误：未配置工具注册表"
        
        try:
            if ':' in action:
                tool_name, tool_params = action.split(':', 1)
                result = await self.tool_registry.execute_tool_async(tool_name.strip(), tool_params.strip())
                return str(result)
            else:
                return f"无效的动作格式：{action}"
        except Exception as e:
            return f"执行动作失败：{str(e)}"
    
    def _build_react_prompt(self, query: str, thoughts: List) -> str:
        """构建ReAct提示词"""
        prompt = f"问题：{query}\n\n"
        
        if thoughts:
            prompt += "思考过程：\n"
            for i, (thought, action, observation) in enumerate(thoughts):
                prompt += f"{i+1}. 思考：{thought}\n"
                if action:
                    prompt += f"   行动：{action}\n"
                if observation:
                    prompt += f"   观察：{observation}\n"
            prompt += "\n请继续思考：\n"
        else:
            prompt += "请开始思考这个问题：\n"
        
        return prompt
    
    def _parse_react_response(self, response: str) -> tuple:
        """解析ReAct响应"""
        # 简化的解析逻辑，实际应该更复杂
        lines = response.split('\n')
        thought = ""
        action = ""
        observation = ""
        
        for line in lines:
            if line.startswith('思考：'):
                thought = line[3:].strip()
            elif line.startswith('行动：'):
                action = line[3:].strip()
            elif line.startswith('观察：'):
                observation = line[3:].strip()
        
        return thought, action, observation
    
    def _extract_final_answer(self, thoughts: List) -> str:
        """从思考过程中提取最终答案"""
        if not thoughts:
            return "未能生成有效回答"
        
        # 返回最后一次思考的内容作为答案
        last_thought, last_action, last_observation = thoughts[-1]
        
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