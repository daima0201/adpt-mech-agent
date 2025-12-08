"""
知识感知智能体基类
扩展基础Agent，集成知识库检索和更新能力
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional

from src.agents.core.agent import Agent
from src.agents.core import Message
from src.agents.tools.builtin.knowledge_tool import (
    KnowledgeRetrievalTool, 
    KnowledgeUpdateTool,
    ConversationKnowledgeExtractor
)
from src.adaptive.knowledge_manager import KnowledgeManager


class KnowledgeAwareAgent(Agent):
    """知识感知智能体基类 - 集成知识库能力的智能体"""
    
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        
        # 知识相关组件
        self.knowledge_manager: Optional[KnowledgeManager] = None
        self.knowledge_retrieval_tool: Optional[KnowledgeRetrievalTool] = None
        self.knowledge_update_tool: Optional[KnowledgeUpdateTool] = None
        self.knowledge_extractor: Optional[ConversationKnowledgeExtractor] = None
        
        # 知识感知配置
        self.knowledge_config = {
            'auto_retrieve': True,           # 自动检索相关知识
            'auto_extract': False,           # 自动提取对话知识
            'knowledge_bases': ['general_knowledge'],  # 默认知识库
            'retrieval_threshold': 0.7,      # 检索阈值
            'max_retrieval_results': 5       # 最大检索结果数
        }
        
        # 更新配置
        if config and 'knowledge' in config:
            self.knowledge_config.update(config['knowledge'])
        
        self.logger = logging.getLogger(f"{__name__}.{name}")
        self.is_knowledge_initialized = False
    
    async def initialize(self) -> None:
        """初始化知识感知组件"""
        await super().initialize()
        
        if not self.is_knowledge_initialized:
            await self._initialize_knowledge_system()
            self.is_knowledge_initialized = True
    
    async def _initialize_knowledge_system(self) -> None:
        """初始化知识系统"""
        try:
            # 初始化知识管理器
            self.knowledge_manager = KnowledgeManager()
            await self.knowledge_manager.initialize()
            
            # 初始化知识工具
            self.knowledge_retrieval_tool = KnowledgeRetrievalTool(self.knowledge_manager)
            self.knowledge_update_tool = KnowledgeUpdateTool(self.knowledge_manager)
            self.knowledge_extractor = ConversationKnowledgeExtractor(self.knowledge_update_tool)
            
            # 注册知识工具到工具系统
            if hasattr(self, 'tool_registry') and self.tool_registry:
                from src.agents.tools.builtin.knowledge_tool import register_knowledge_tools
                register_knowledge_tools(self.tool_registry, self.knowledge_manager)
            
            self.logger.info(f"知识感知系统初始化完成 - 自动检索: {self.knowledge_config['auto_retrieve']}")
            
        except Exception as e:
            self.logger.error(f"知识系统初始化失败: {str(e)}")
            raise
    
    async def process_message(self, message: Message) -> Message:
        """处理消息，集成知识检索功能"""
        
        # 确保知识系统已初始化
        if not self.is_knowledge_initialized:
            await self.initialize()
        
        # 自动检索相关知识（如果启用）
        knowledge_context = None
        if self.knowledge_config['auto_retrieve']:
            knowledge_context = await self._retrieve_relevant_knowledge(message.content)
        
        # 将知识上下文添加到消息中
        if knowledge_context:
            message.knowledge_context = knowledge_context
            self.logger.info(f"检索到 {len(knowledge_context)} 条相关知识")
        
        # 调用父类处理逻辑
        response = await super().process_message(message)
        
        # 自动提取对话知识（如果启用）
        if self.knowledge_config['auto_extract']:
            await self._extract_conversation_knowledge([message, response])
        
        return response
    
    async def _retrieve_relevant_knowledge(self, query: str) -> List[Dict[str, Any]]:
        """检索相关知识"""
        if not self.knowledge_retrieval_tool:
            return []
        
        try:
            result = await self.knowledge_retrieval_tool.semantic_search(
                query=query,
                top_k=self.knowledge_config['max_retrieval_results'],
                score_threshold=self.knowledge_config['retrieval_threshold']
            )
            
            if result.get('success') and result.get('results'):
                return result['results']
            else:
                return []
                
        except Exception as e:
            self.logger.error(f"知识检索失败: {str(e)}")
            return []
    
    async def _extract_conversation_knowledge(self, conversation: List[Message]) -> None:
        """从对话中提取知识"""
        if not self.knowledge_extractor:
            return
        
        try:
            result = await self.knowledge_extractor.extract_from_conversation(
                conversation_history=conversation,
                knowledge_base="conversation_knowledge"
            )
            
            if result.get('success') and result.get('added_count', 0) > 0:
                self.logger.info(f"从对话中提取了 {result['added_count']} 条知识")
                
        except Exception as e:
            self.logger.error(f"知识提取失败: {str(e)}")
    
    async def search_knowledge(
        self, 
        query: str, 
        search_type: str = "semantic",
        knowledge_bases: List[str] = None,
        top_k: int = None
    ) -> Dict[str, Any]:
        """主动搜索知识库"""
        if not self.knowledge_retrieval_tool:
            return {"success": False, "error": "知识检索工具未初始化"}
        
        if knowledge_bases is None:
            knowledge_bases = self.knowledge_config['knowledge_bases']
        
        if top_k is None:
            top_k = self.knowledge_config['max_retrieval_results']
        
        return await self.knowledge_retrieval_tool._execute(
            query=query,
            search_type=search_type,
            knowledge_bases=knowledge_bases,
            top_k=top_k
        )
    
    async def add_knowledge(
        self, 
        content: str, 
        knowledge_base: str = "general_knowledge",
        title: str = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """向知识库添加新知识"""
        if not self.knowledge_update_tool:
            return {"success": False, "error": "知识更新工具未初始化"}
        
        return await self.knowledge_update_tool._execute(
            content=content,
            knowledge_base=knowledge_base,
            title=title,
            metadata=metadata
        )
    
    async def get_knowledge_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        if not self.knowledge_manager:
            return {"success": False, "error": "知识管理器未初始化"}
        
        return await self.knowledge_manager.get_statistics()
    
    def enable_auto_retrieval(self, enabled: bool = True) -> None:
        """启用/禁用自动知识检索"""
        self.knowledge_config['auto_retrieve'] = enabled
        self.logger.info(f"自动知识检索 {'启用' if enabled else '禁用'}")
    
    def enable_auto_extraction(self, enabled: bool = True) -> None:
        """启用/禁用自动知识提取"""
        self.knowledge_config['auto_extract'] = enabled
        self.logger.info(f"自动知识提取 {'启用' if enabled else '禁用'}")
    
    def set_knowledge_bases(self, knowledge_bases: List[str]) -> None:
        """设置使用的知识库"""
        self.knowledge_config['knowledge_bases'] = knowledge_bases
        self.logger.info(f"知识库设置为: {knowledge_bases}")
    
    async def close(self) -> None:
        """关闭知识系统"""
        if self.knowledge_manager:
            await self.knowledge_manager.close()
        
        await super().close()


class KnowledgeEnhancedReActAgent(KnowledgeAwareAgent):
    """知识增强的ReAct智能体 - 在思考过程中集成知识检索"""
    def __init__(self, name: str, config: Dict[str, Any] = None):
        super().__init__(name, config)
        
        # ReAct特定的知识增强配置
        self.react_knowledge_config = {
            'use_knowledge_in_thought': True,     # 在思考中使用知识
            'knowledge_retrieval_steps': ['think', 'action'],  # 在哪些步骤检索知识
            'dynamic_retrieval': True,            # 动态检索（根据思考内容）
            'confidence_threshold': 0.8           # 知识置信度阈值
        }
        
        if config and 'react_knowledge' in config:
            self.react_knowledge_config.update(config['react_knowledge'])
    
    async def _generate_thought_with_knowledge(
        self, 
        observation: str, 
        previous_thought: str = None
    ) -> str:
        """生成包含知识的思考"""
        
        # 如果需要动态检索知识
        knowledge_context = ""
        if self.react_knowledge_config['dynamic_retrieval'] and previous_thought:
            # 基于之前的思考内容检索相关知识
            retrieval_result = await self._retrieve_relevant_knowledge(previous_thought)
            if retrieval_result:
                knowledge_context = self._format_knowledge_for_thought(retrieval_result)
        
        # 构建包含知识的思考提示
        thought_prompt = self._build_knowledge_enhanced_prompt(
            observation=observation,
            previous_thought=previous_thought,
            knowledge_context=knowledge_context
        )
        
        # 调用LLM生成思考
        thought = await self.llm.generate(thought_prompt)
        
        return thought.strip()
    
    def _format_knowledge_for_thought(self, knowledge_results: List[Dict[str, Any]]) -> str:
        """格式化知识结果用于思考过程"""
        if not knowledge_results:
            return ""
        
        formatted = "\n相关背景知识:\n"
        for i, result in enumerate(knowledge_results[:3], 1):  # 最多使用
            formatted += f"{i}. {result.get('content', '')} (相关性: {result.get('score', 0):.2f})\n"
        
        return formatted
    
    def _build_knowledge_enhanced_prompt(
        self, 
        observation: str, 
        previous_thought: str = None,
        knowledge_context: str = ""
    ) -> str:
        """构建知识增强的提示词"""
        
        base_prompt = f"""
观察: {observation}

{knowledge_context}

请基于以上观察和相关知识进行思考。"""
        
        if previous_thought:
            base_prompt += f"\n之前的思考: {previous_thought}"
        
        base_prompt += "\n\n当前思考:"
        
        return base_prompt


class MultiAgentKnowledgeCoordinator:
    """多智能体知识协调器 - 管理多个智能体间的知识共享"""
    
    def __init__(self, agents: List[KnowledgeAwareAgent] = None):
        self.agents = agents or []
        self.shared_knowledge_base = "multi_agent_shared"
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """初始化所有智能体的知识系统"""
        for agent in self.agents:
            await agent.initialize()
    
    async def share_knowledge_across_agents(
        self, 
        knowledge_content: str, 
        source_agent: str,
        target_agents: List[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """在智能体间共享知识"""
        
        try:
            # 添加到共享知识库
            target_agents = target_agents or [agent.name for agent in self.agents]
            
            shared_count = 0
            for agent_name in target_agents:
                agent = self._get_agent_by_name(agent_name)
                if agent:
                    result = await agent.add_knowledge(
                        content=knowledge_content,
                        knowledge_base=self.shared_knowledge_base,
                        title=f"来自 {source_agent} 的共享知识",
                        metadata={
                            'source_agent': source_agent,
                            'priority': priority,
                            'shared_timestamp': asyncio.get_event_loop().time()
                        }
                    )
                    
                    if result.get('success'):
                        shared_count += 1
            
            return {
                "success": True,
                "shared_count": shared_count,
                "total_targets": len(target_agents),
                "source_agent": source_agent
            }
            
        except Exception as e:
            self.logger.error(f"知识共享失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "source_agent": source_agent
            }
    
    async def coordinate_knowledge_retrieval(
        self, 
        query: str, 
        agent_roles: List[str] = None
    ) -> Dict[str, Any]:
        """协调多个智能体的知识检索"""
        
        aggregated_results = {}
        
        for agent in self.agents:
            if agent_roles and agent.role not in agent_roles:
                continue
            
            try:
                # 每个智能体从自己的知识库检索
                result = await agent.search_knowledge(query)
                if result.get('success') and result.get('results'):
                    aggregated_results[agent.name] = {
                        'role': agent.role,
                        'results': result['results'],
                        'count': len(result['results'])
                    }
                    
            except Exception as e:
                self.logger.error(f"智能体 {agent.name} 知识检索失败: {str(e)}")
        
        # 合并和重排序结果
        merged_results = self._merge_and_rank_results(aggregated_results)
        
        return {
            "success": True,
            "query": query,
            "participating_agents": list(aggregated_results.keys()),
            "merged_results": merged_results,
            "detailed_results": aggregated_results
        }
    
    def _merge_and_rank_results(self, agent_results: Dict[str, Any]) -> List[Dict[str, Any]]:
        """合并和重排序来自不同智能体的结果"""
        all_results = []
        
        for agent_name, data in agent_results.items():
            for result in data.get('results', []):
                # 添加智能体信息
                result['source_agent'] = agent_name
                result['agent_role'] = data.get('role', 'unknown')
                all_results.append(result)
        
        # 按相关性排序
        all_results.sort(key=lambda x: x.get('score', 0), reverse=True)
        
        return all_results
    
    def _get_agent_by_name(self, name: str) -> Optional[KnowledgeAwareAgent]:
        """根据名称获取智能体"""
        for agent in self.agents:
            if agent.name == name:
                return agent
        return None
    
    def add_agent(self, agent: KnowledgeAwareAgent) -> None:
        """添加智能体到协调器"""
        if agent not in self.agents:
            self.agents.append(agent)
            self.logger.info(f"智能体 '{agent.name}' 已添加到知识协调器")
    
    def remove_agent(self, agent_name: str) -> bool:
        """从协调器移除智能体"""
        for i, agent in enumerate(self.agents):
            if agent.name == agent_name:
                self.agents.pop(i)
                self.logger.info(f"智能体 '{agent_name}' 已移除")
                return True
        return False