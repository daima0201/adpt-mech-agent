"""
工具管理器 - 管理知识检索工具
扩展现有工具系统以支持知识检索功能
"""

import logging
from typing import Dict, Any, List, Optional
from src.agents.tools.registry import ToolRegistry
from src.agents.tools.builtin.knowledge_tool import KnowledgeRetrievalTool


class KnowledgeToolManager:
    """知识工具管理器"""
    
    def __init__(self, tool_registry: ToolRegistry):
        self.tool_registry = tool_registry
        self.logger = logging.getLogger(__name__)
        self.knowledge_tools: Dict[str, KnowledgeRetrievalTool] = {}
    
    async def register_knowledge_tools(self, knowledge_bases: Dict[str, Any]) -> None:
        """注册知识检索工具"""
        for kb_name, kb_instance in knowledge_bases.items():
            tool_name = f"retrieve_from_{kb_name}"
            
            # 创建知识检索工具
            knowledge_tool = KnowledgeRetrievalTool(
                name=tool_name,
                description=f"从{kb_name}知识库中检索相关知识",
                knowledge_base=kb_instance
            )
            
            # 注册到工具注册表
            await self.tool_registry.register_tool(knowledge_tool)
            self.knowledge_tools[tool_name] = knowledge_tool
            
            self.logger.info(f"已注册知识检索工具: {tool_name}")
    
    async def unregister_knowledge_tools(self) -> None:
        """注销所有知识检索工具"""
        for tool_name in list(self.knowledge_tools.keys()):
            await self.tool_registry.unregister_tool(tool_name)
            del self.knowledge_tools[tool_name]
            self.logger.info(f"已注销知识检索工具: {tool_name}")
    
    def get_available_knowledge_tools(self) -> List[str]:
        """获取可用的知识检索工具列表"""
        return list(self.knowledge_tools.keys())
    
    async def execute_knowledge_query(
        self, 
        tool_name: str, 
        query: str, 
        **kwargs
    ) -> Optional[Dict[str, Any]]:
        """执行知识查询"""
        if tool_name not in self.knowledge_tools:
            self.logger.error(f"知识检索工具不存在: {tool_name}")
            return None
        
        try:
            tool = self.knowledge_tools[tool_name]
            result = await tool.execute(query, **kwargs)
            return result
        except Exception as e:
            self.logger.error(f"知识查询执行失败: {str(e)}")
            return None