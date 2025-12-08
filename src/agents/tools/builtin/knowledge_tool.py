"""
知识检索工具
为智能体提供知识库检索能力，支持语义搜索、相似性搜索等功能
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

from src.agents.tools.base import Tool
from src.knowledge.schema.query import Query
from src.knowledge.schema.chunk import KnowledgeChunk
from src.agents.core import Message
from src.adaptive.knowledge_manager import KnowledgeManager


class KnowledgeRetrievalTool(Tool):
    """知识检索工具 - 为智能体提供知识库访问能力"""
    
    def __init__(self, knowledge_manager: KnowledgeManager = None):
        super().__init__(
            name="knowledge_retrieval",
            description="从知识库中检索相关知识，支持语义搜索、相似性搜索和关键词搜索",
            parameters={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索查询内容"
                    },
                    "search_type": {
                        "type": "string", 
                        "enum": ["semantic", "similarity", "keyword"],
                        "default": "semantic",
                        "description": "搜索类型：semantic(语义搜索)、similarity(相似性搜索)、keyword(关键词搜索)"
                    },
                    "knowledge_bases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "default": ["code_knowledge", "document_knowledge"],
                        "description": "要搜索的知识库列表"
                    },
                    "top_k": {
                        "type": "integer",
                        "minimum": 1,
                        "maximum": 20,
                        "default": 5,
                        "description": "返回结果数量"
                    },
                    "score_threshold": {
                        "type": "number",
                        "minimum": 0.0,
                        "maximum": 1.0,
                        "default": 0.7,
                        "description": "相关性阈值，只返回得分高于此值的结果"
                    }
                },
                "required": ["query"]
            }
        )
        
        self.logger = logging.getLogger(__name__)
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """初始化知识管理器"""
        if self.is_initialized:
            return
        
        await self.knowledge_manager.initialize()
        self.is_initialized = True
        self.logger.info("知识检索工具初始化完成")
    
    async def _execute(
        self, 
        query: str, 
        search_type: str = "semantic",
        knowledge_bases: List[str] = None,
        top_k: int = 5,
        score_threshold: float = 0.7,
        **kwargs
    ) -> Dict[str, Any]:
        """执行知识检索"""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            # 创建查询对象
            query_obj = Query(
                text=query,
                type=search_type,
                top_k=top_k,
                score_threshold=score_threshold
            )
            
            # 执行搜索
            results = await self.knowledge_manager.search(
                query=query_obj,
                knowledge_base_names=knowledge_bases
            )
            
            # 格式化结果
            formatted_results = self._format_results(results)
            
            # 记录检索历史
            await self._record_retrieval_history(query, search_type, len(results))
            
            return {
                "success": True,
                "query": query,
                "search_type": search_type,
                "knowledge_bases": knowledge_bases or ["all"],
                "total_results": len(results),
                "results": formatted_results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"知识检索失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "query": query,
                "timestamp": datetime.now().isoformat()
            }
    
    def _format_results(self, chunks: List[KnowledgeChunk]) -> List[Dict[str, Any]]:
        """格式化检索结果"""
        formatted = []
        
        for i, chunk in enumerate(chunks):
            result = {
                "rank": i + 1,
                "content": chunk.content[:500] + "..." if len(chunk.content) > 500 else chunk.content,
                "score": round(chunk.score, 4),
                "source": chunk.metadata.get('source', 'unknown'),
                "title": chunk.metadata.get('title', 'untitled'),
                "metadata": {
                    k: v for k, v in chunk.metadata.items() 
                    if k not in ['source', 'title'] and not k.startswith('_')
                }
            }
            formatted.append(result)
        
        return formatted
    
    async def _record_retrieval_history(
        self, 
        query: str, 
        search_type: str, 
        result_count: int
    ) -> None:
        """记录检索历史（可选功能）"""
        # 这里可以集成到对话记忆系统或日志系统
        retrieval_log = {
            "query": query,
            "search_type": search_type,
            "result_count": result_count,
            "timestamp": datetime.now().isoformat()
        }
        
        self.logger.info(f"检索记录: {retrieval_log}")
    
    async def get_knowledge_base_info(self) -> Dict[str, Any]:
        """获取知识库信息"""
        if not self.is_initialized:
            await self.initialize()
        
        stats = await self.knowledge_manager.get_statistics()
        return {
            "success": True,
            "knowledge_bases": stats
        }
    
    async def semantic_search(self, query: str, top_k: int = 5) -> Dict[str, Any]:
        """语义搜索快捷方法"""
        return await self._execute(query, "semantic", top_k=top_k)
    
    async def similarity_search(self, content: str, top_k: int = 5) -> Dict[str, Any]:
        """相似性搜索快捷方法"""
        return await self._execute(content, "similarity", top_k=top_k)
    
    async def keyword_search(self, keywords: str, top_k: int = 5) -> Dict[str, Any]:
        """关键词搜索快捷方法"""
        return await self._execute(keywords, "keyword", top_k=top_k)


class KnowledgeUpdateTool(Tool):
    """知识更新工具 - 允许智能体向知识库添加新知识"""
    
    def __init__(self, knowledge_manager: KnowledgeManager = None):
        super().__init__(
            name="knowledge_update",
            description="向知识库添加新的知识内容，支持自动切分和向量化",
            parameters={
                "type": "object",
                "properties": {
                    "content": {
                        "type": "string",
                        "description": "要添加到知识库的内容"
                    },
                    "knowledge_base": {
                        "type": "string",
                        "default": "general_knowledge",
                        "description": "目标知识库名称"
                    },
                    "title": {
                        "type": "string",
                        "description": "知识标题"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "附加元数据"
                    }
                },
                "required": ["content", "knowledge_base"]
            }
        )
        
        self.logger = logging.getLogger(__name__)
        self.knowledge_manager = knowledge_manager or KnowledgeManager()
        self.is_initialized = False
    
    async def initialize(self) -> None:
        """初始化知识管理器"""
        if self.is_initialized:
            return
        
        await self.knowledge_manager.initialize()
        self.is_initialized = True
        self.logger.info("知识更新工具初始化完成")
    
    async def _execute(
        self, 
        content: str, 
        knowledge_base: str = "general_knowledge",
        title: str = None,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """执行知识更新"""
        
        if not self.is_initialized:
            await self.initialize()
        
        try:
            from src.knowledge.schema.document import Document
            
            # 创建文档对象
            document = Document(
                title=title or f"智能体添加的知识_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                content=content,
                source="agent_generated",
                metadata=metadata or {}
            )
            
            # 添加到知识库
            success = await self.knowledge_manager.add_document(knowledge_base, document)
            
            if success:
                return {
                    "success": True,
                    "message": f"知识已成功添加到 '{knowledge_base}' 知识库",
                    "title": document.title,
                    "content_length": len(content),
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "error": "添加知识失败",
                    "knowledge_base": knowledge_base,
                    "timestamp": datetime.now().isoformat()
                }
                
        except Exception as e:
            self.logger.error(f"知识更新失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "knowledge_base": knowledge_base,
                "timestamp": datetime.now().isoformat()
            }


class ConversationKnowledgeExtractor:
    """对话知识提取器 - 从对话中提取有价值的知识并反馈给知识库"""
    
    def __init__(self, knowledge_update_tool: KnowledgeUpdateTool):
        self.knowledge_update_tool = knowledge_update_tool
        self.logger = logging.getLogger(__name__)
    
    async def extract_from_conversation(
        self, 
        conversation_history: List[Message],
        knowledge_base: str = "conversation_knowledge"
    ) -> Dict[str, Any]:
        """从对话历史中提取知识"""
        
        try:
            # 分析对话，提取关键信息
            extracted_knowledge = self._analyze_conversation(conversation_history)
            
            if not extracted_knowledge:
                return {"success": True, "extracted_count": 0, "message": "未发现可提取的知识"}
            
            # 将提取的知识添加到知识库
            added_count = 0
            for knowledge in extracted_knowledge:
                result = await self.knowledge_update_tool._execute(
                    content=knowledge['content'],
                    knowledge_base=knowledge_base,
                    title=knowledge.get('title'),
                    metadata=knowledge.get('metadata', {})
                )
                
                if result.get('success'):
                    added_count += 1
            
            return {
                "success": True,
                "extracted_count": len(extracted_knowledge),
                "added_count": added_count,
                "knowledge_base": knowledge_base,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            self.logger.error(f"对话知识提取失败: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    def _analyze_conversation(self, conversation_history: List[Message]) -> List[Dict[str, Any]]:
        """分析对话，提取有价值的知识点"""
        extracted_knowledge = []
        
        # 简单的启发式规则提取知识
        for i, message in enumerate(conversation_history):
            content = message.content
            
            # 检测可能包含知识的消息
            if self._is_knowledge_rich_message(content):
                knowledge = self._extract_knowledge_from_message(content, message.role)
                if knowledge:
                    extracted_knowledge.append(knowledge)
        
        return extracted_knowledge
    
    def _is_knowledge_rich_message(self, content: str) -> bool:
        """判断消息是否富含知识"""
        # 基于长度和关键词的简单判断
        knowledge_keywords = [
            '如何', '步骤', '方法', '技巧', '建议', '最佳实践',
            '原理', '概念', '定义', '说明', '解释', '示例'
        ]
        
        if len(content) < 50:  # 太短的消息可能不包含完整知识
            return False
        
        # 检查是否包含知识相关关键词
        return any(keyword in content for keyword in knowledge_keywords)
    
    def _extract_knowledge_from_message(self, content: str, role: str) -> Dict[str, Any]:
        """从单条消息中提取知识"""
        # 简单的知识提取逻辑
        # 在实际应用中可以使用更复杂的NLP技术
        
        metadata = {
            'source': 'conversation',
            'role': role,
            'extraction_method': 'heuristic'
        }
        
        # 尝试提取标题（第一句话或前50个字符）
        title = content.split('。')[0] if '。' in content else content[:50]
        
        return {
            'title': title.strip(),
            'content': content,
            'metadata': metadata
        }


# 工具注册函数
def register_knowledge_tools(tool_registry, knowledge_manager=None):
    """注册知识相关工具"""
    
    # 创建工具实例
    retrieval_tool = KnowledgeRetrievalTool(knowledge_manager)
    update_tool = KnowledgeUpdateTool(knowledge_manager)
    
    # 注册到工具注册表
    tool_registry.register_tool(retrieval_tool)
    tool_registry.register_tool(update_tool)
    
    # 创建知识提取器
    knowledge_extractor = ConversationKnowledgeExtractor(update_tool)
    
    return {
        'retrieval_tool': retrieval_tool,
        'update_tool': update_tool,
        'knowledge_extractor': knowledge_extractor
    }