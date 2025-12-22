"""
Agent协调器 - 协调知识感知Agent的执行
管理多个Agent之间的协作和知识共享
"""

import logging
from typing import Dict, Any, List
from src.agents.base.base_agent import BaseAgent
from src.agents.impls.agent.knowledge_aware_agent import KnowledgeAwareAgent
from src.knowledge.knowledge_base import KnowledgeManager


class AgentOrchestrator:
    """Agent协调器"""
    
    def __init__(self, knowledge_manager: KnowledgeManager):
        self.knowledge_manager = knowledge_manager
        self.logger = logging.getLogger(__name__)
        self.agents: Dict[str, BaseAgent] = {}
        self.conversation_history: List[Dict[str, Any]] = []
    
    async def register_agent(self, agent_id: str, agent: BaseAgent) -> None:
        """注册Agent"""
        self.agents[agent_id] = agent
        
        # 如果Agent是知识感知的，注入知识管理器
        if isinstance(agent, KnowledgeAwareAgent):
            await agent.set_knowledge_manager(self.knowledge_manager)
        
        self.logger.info(f"已注册Agent: {agent_id}")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """注销Agent"""
        if agent_id in self.agents:
            del self.agents[agent_id]
            self.logger.info(f"已注销Agent: {agent_id}")
    
    async def orchestrate_conversation(
        self, 
        user_input: str, 
        context: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """协调多Agent对话"""
        
        # 1. 分析用户输入，确定需要哪些Agent参与
        required_agents = await self._analyze_user_input(user_input, context)
        
        # 2. 检索相关知识
        knowledge_context = await self.knowledge_manager.retrieve_relevant_knowledge(
            query=user_input,
            context=context
        )
        
        # 3. 按顺序执行Agent
        responses = {}
        for agent_id in required_agents:
            if agent_id in self.agents:
                agent = self.agents[agent_id]
                
                # 准备Agent输入
                agent_input = {
                    'user_message': user_input,
                    'knowledge_context': knowledge_context,
                    'previous_responses': responses,
                    'conversation_history': self.conversation_history[-10:]  # 最近10轮对话
                }
                
                # 执行Agent
                response = await agent.process(agent_input)
                responses[agent_id] = response
                
                # 记录对话历史
                self.conversation_history.append({
                    'agent_id': agent_id,
                    'input': agent_input,
                    'response': response,
                    'timestamp': self._get_current_timestamp()
                })
        
        # 4. 整合结果
        final_response = await self._integrate_responses(responses, knowledge_context)
        
        return {
            'final_response': final_response,
            'agent_responses': responses,
            'knowledge_context': knowledge_context
        }
    
    async def _analyze_user_input(
        self, 
        user_input: str, 
        context: Dict[str, Any] = None
    ) -> List[str]:
        """分析用户输入，确定需要的Agent"""
        # 简单的基于关键词的分析
        # TODO: 可以替换为更智能的意图识别
        
        input_lower = user_input.lower()
        required_agents = []
        
        # 检查是否需要规划Agent
        if any(word in input_lower for word in ['计划', '规划', '步骤', '流程']):
            required_agents.append('plan_solve_agent')
        
        # 检查是否需要反思Agent
        if any(word in input_lower for word in ['分析', '评估', '反思', '总结']):
            required_agents.append('reflection_agent')
        
        # 默认使用简单Agent
        if not required_agents:
            required_agents.append('simple_agent')
        
        return required_agents
    
    async def _integrate_responses(
        self, 
        responses: Dict[str, Any], 
        knowledge_context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """整合多个Agent的响应"""
        
        if len(responses) == 1:
            # 单个Agent直接返回
            return list(responses.values())[0]
        
        # 多个Agent响应整合逻辑
        integrated_response = {
            'content': '',
            'sources': [],
            'confidence': 0.0
        }
        
        # 合并内容
        for agent_id, response in responses.items():
            if response.get('content'):
                integrated_response['content'] += f"【{agent_id}】\n{response['content']}\n\n"
            
            # 合并来源
            if response.get('sources'):
                integrated_response['sources'].extend(response['sources'])
            
            # 计算平均置信度
            if response.get('confidence'):
                integrated_response['confidence'] += response['confidence']
        
        if responses:
            integrated_response['confidence'] /= len(responses)
        
        # 去重来源
        integrated_response['sources'] = list(set(integrated_response['sources']))
        
        return integrated_response
    
    def _get_current_timestamp(self) -> str:
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """获取对话摘要"""
        return {
            'total_conversations': len(self.conversation_history),
            'active_agents': list(self.agents.keys()),
            'recent_activity': self.conversation_history[-5:] if self.conversation_history else []
        }