"""
知识管理器
统一管理多个知识库，提供智能体间的知识协调和共享
"""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from src.knowledge import KnowledgeBase
from src.knowledge.schema.document import Document
from src.knowledge.schema.query import Query
from src.knowledge.schema.chunk import KnowledgeChunk
from src.agents.core import KnowledgeConfig


class KnowledgeManager:
    """知识管理器 - 统一管理多个知识库"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or "config/knowledge_config.yaml"
        self.knowledge_bases: Dict[str, KnowledgeBase] = {}
        self.is_initialized = False
        self.logger = logging.getLogger(__name__)
        
        # 默认知识库配置
        self.default_knowledge_bases = {
            'code_knowledge': {
                'description': '代码知识库',
                'vector_store': {'type': 'chroma'},
                'embedding': {'model': 'bge-m3'},
                'processing': {'chunk_size': 800, 'chunk_overlap': 100}
            },
            'document_knowledge': {
                'description': '文档知识库', 
                'vector_store': {'type': 'chroma'},
                'embedding': {'model': 'bge-m3'},
                'processing': {'chunk_size': 1000, 'chunk_overlap': 150}
            },
            'conversation_knowledge': {
                'description': '对话知识库',
                'vector_store': {'type': 'chroma'},
                'embedding': {'model': 'bge-m3'},
                'processing': {'chunk_size': 500, 'chunk_overlap': 50}
            }
        }
    
    async def initialize(self) -> None:
        """初始化知识管理器"""
        if self.is_initialized:
            return
        
        try:
            # 加载配置
            await self._load_config()
            
            # 初始化默认知识库
            for name, config_data in self.default_knowledge_bases.items():
                await self._create_knowledge_base(name, config_data)
            
            self.is_initialized = True
            self.logger.info(f"知识管理器初始化完成，已创建 {len(self.knowledge_bases)} 个知识库")
            
        except Exception as e:
            self.logger.error(f"知识管理器初始化失败: {str(e)}")
            raise
    
    async def _load_config(self) -> None:
        """加载配置文件"""
        try:
            config_file = Path(self.config_path)
            if config_file.exists():
                # 这里可以添加YAML配置加载逻辑
                self.logger.info(f"从 {self.config_path} 加载配置")
            else:
                self.logger.warning(f"配置文件 {self.config_path} 不存在，使用默认配置")
                
        except Exception as e:
            self.logger.warning(f"配置加载失败，使用默认配置: {str(e)}")
    
    async def _create_knowledge_base(self, name: str, config_data: Dict[str, Any]) -> None:
        """创建知识库实例"""
        try:
            config = KnowledgeConfig(**config_data)
            knowledge_base = KnowledgeBase(name=name, config=config)
            await knowledge_base.initialize()
            
            self.knowledge_bases[name] = knowledge_base
            self.logger.info(f"知识库 '{name}' 创建成功")
            
        except Exception as e:
            self.logger.error(f"创建知识库 '{name}' 失败: {str(e)}")
            raise
    
    async def search(
        self, 
        query: Query, 
        knowledge_base_names: List[str] = None
    ) -> List[KnowledgeChunk]:
        """在多个知识库中搜索"""
        
        if not self.is_initialized:
            await self.initialize()
        
        if knowledge_base_names is None:
            knowledge_base_names = list(self.knowledge_bases.keys())
        
        all_results = []
        
        for base_name in knowledge_base_names:
            if base_name not in self.knowledge_bases:
                self.logger.warning(f"知识库 '{base_name}' 不存在")
                continue
            
            try:
                knowledge_base = self.knowledge_bases[base_name]
                results = await knowledge_base.retrieve(
                    query=query.text,
                    top_k=query.top_k,
                    score_threshold=query.score_threshold
                )
                
                # 标记结果来源
                for result in results:
                    result.metadata['knowledge_base'] = base_name
                
                all_results.extend(results)
                
            except Exception as e:
                self.logger.error(f"在知识库 '{base_name}' 中搜索失败: {str(e)}")
        
        # 合并和重排序结果
        merged_results = self._merge_and_rank_results(all_results)
        
        return merged_results[:query.top_k]
    
    async def add_document(
        self, 
        knowledge_base_name: str, 
        document: Document
    ) -> bool:
        """向指定知识库添加文档"""
        
        if not self.is_initialized:
            await self.initialize()
        
        if knowledge_base_name not in self.knowledge_bases:
            self.logger.error(f"知识库 '{knowledge_base_name}' 不存在")
            return False
        
        try:
            knowledge_base = self.knowledge_bases[knowledge_base_name]
            await knowledge_base.add_documents([document])
            
            self.logger.info(f"文档 '{document.title}' 已添加到知识库 '{knowledge_base_name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"添加文档到知识库 '{knowledge_base_name}' 失败: {str(e)}")
            return False
    
    async def get_statistics(self) -> Dict[str, Any]:
        """获取知识库统计信息"""
        
        if not self.is_initialized:
            await self.initialize()
        
        stats = {}
        total_chunks = 0
        
        for name, knowledge_base in self.knowledge_bases.items():
            try:
                # 这里可以添加获取知识库统计信息的逻辑
                base_stats = {
                    'description': knowledge_base.config.description,
                    'chunk_count': '待实现',  # 需要向量存储支持
                    'last_updated': '待实现'
                }
                stats[name] = base_stats
                
            except Exception as e:
                self.logger.error(f"获取知识库 '{name}' 统计信息失败: {str(e)}")
                stats[name] = {'error': str(e)}
        
        return {
            'total_knowledge_bases': len(self.knowledge_bases),
            'knowledge_bases': stats,
            'total_chunks': total_chunks
        }
    
    async def create_knowledge_base(
        self, 
        name: str, 
        config: Dict[str, Any]
    ) -> bool:
        """创建新的知识库"""
        
        if name in self.knowledge_bases:
            self.logger.warning(f"知识库 '{name}' 已存在")
            return False
        
        try:
            await self._create_knowledge_base(name, config)
            return True
            
        except Exception as e:
            self.logger.error(f"创建知识库 '{name}' 失败: {str(e)}")
            return False
    
    async def delete_knowledge_base(self, name: str) -> bool:
        """删除知识库"""
        
        if name not in self.knowledge_bases:
            self.logger.warning(f"知识库 '{name}' 不存在")
            return False
        
        try:
            knowledge_base = self.knowledge_bases.pop(name)
            await knowledge_base.close()
            
            self.logger.info(f"知识库 '{name}' 已删除")
            return True
            
        except Exception as e:
            self.logger.error(f"删除知识库 '{name}' 失败: {str(e)}")
            return False
    
    def _merge_and_rank_results(self, results: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """合并和重排序来自不同知识库的结果"""
        
        # 去重（基于内容相似性）
        unique_results = self._deduplicate_results(results)
        
        # 按相关性排序
        unique_results.sort(key=lambda x: x.score, reverse=True)
        
        return unique_results
    
    def _deduplicate_results(self, results: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        """去重结果（基于内容和语义相似性）"""
        
        seen_contents = set()
        deduplicated = []
        
        for result in results:
            # 简单的基于内容的去重
            content_hash = hash(result.content[:200])  # 取前200字符的哈希
            
            if content_hash not in seen_contents:
                seen_contents.add(content_hash)
                deduplicated.append(result)
        
        return deduplicated
    
    async def close(self) -> None:
        """关闭所有知识库"""
        for name, knowledge_base in self.knowledge_bases.items():
            try:
                await knowledge_base.close()
                self.logger.info(f"知识库 '{name}' 已关闭")
            except Exception as e:
                self.logger.error(f"关闭知识库 '{name}' 失败: {str(e)}")
        
        self.is_initialized = False
    
    def list_knowledge_bases(self) -> List[str]:
        """列出所有知识库"""
        return list(self.knowledge_bases.keys())
    
    def get_knowledge_base(self, name: str) -> Optional[KnowledgeBase]:
        """获取指定知识库"""
        return self.knowledge_bases.get(name)
    
    async def backup_knowledge_base(self, name: str, backup_path: str) -> bool:
        """备份知识库"""
        
        if name not in self.knowledge_bases:
            self.logger.error(f"知识库 '{name}' 不存在")
            return False
        
        try:
            knowledge_base = self.knowledge_bases[name]
            # 这里可以实现备份逻辑
            self.logger.info(f"知识库 '{name}' 备份到 {backup_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"备份知识库 '{name}' 失败: {str(e)}")
            return False
    
    async def restore_knowledge_base(self, name: str, backup_path: str) -> bool:
        """恢复知识库"""
        
        try:
            # 这里可以实现恢复逻辑
            self.logger.info(f"从 {backup_path} 恢复知识库 '{name}'")
            return True
            
        except Exception as e:
            self.logger.error(f"恢复知识库 '{name}' 失败: {str(e)}")
            return False


class KnowledgeCoordinator:
    """知识协调器 - 管理智能体间的知识共享和协作"""
    
    def __init__(self, knowledge_manager: KnowledgeManager):
        self.knowledge_manager = knowledge_manager
        self.agent_knowledge_mappings: Dict[str, List[str]] = {}  # 智能体-知识库映射
        self.shared_knowledge_base = "shared_knowledge"
        self.logger = logging.getLogger(__name__)
    
    async def initialize(self) -> None:
        """初始化协调器"""
        await self.knowledge_manager.initialize()
        
        # 确保共享知识库存在
        if self.shared_knowledge_base not in self.knowledge_manager.list_knowledge_bases():
            shared_config = {
                'description': '智能体共享知识库',
                'vector_store': {'type': 'chroma'},
                'embedding': {'model': 'bge-m3'},
                'processing': {'chunk_size': 800, 'chunk_overlap': 100}
            }
            await self.knowledge_manager.create_knowledge_base(
                self.shared_knowledge_base, shared_config
            )
    
    def register_agent(self, agent_id: str, knowledge_bases: List[str]) -> None:
        """注册智能体及其可访问的知识库"""
        self.agent_knowledge_mappings[agent_id] = knowledge_bases
        self.logger.info(f"智能体 '{agent_id}' 注册，可访问知识库: {knowledge_bases}")
    
    async def share_knowledge(
        self, 
        source_agent: str, 
        knowledge_content: str,
        target_agents: List[str] = None,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """在智能体间共享知识"""
        
        try:
            from src.knowledge.schema.document import Document
            
            # 创建共享文档
            document = Document(
                title=f"来自 {source_agent} 的共享知识",
                content=knowledge_content,
                source=f"agent_{source_agent}",
                metadata={
                    'shared_by': source_agent,
                    'priority': priority,
                    'shared_timestamp': asyncio.get_event_loop().time()
                }
            )
            
            # 添加到共享知识库
            success = await self.knowledge_manager.add_document(
                self.shared_knowledge_base, document
            )
            
            if success:
                # 通知目标智能体
                notified_agents = []
                if target_agents:
                    for agent_id in target_agents:
                        if agent_id in self.agent_knowledge_mappings:
                            notified_agents.append(agent_id)
                
                return {
                    'success': True,
                    'shared_to_knowledge_base': self.shared_knowledge_base,
                    'notified_agents': notified_agents,
                    'document_title': document.title
                }
            else:
                return {'success': False, 'error': '添加到知识库失败'}
                
        except Exception as e:
            self.logger.error(f"知识共享失败: {str(e)}")
            return {'success': False, 'error': str(e)}
    
    async def get_agent_knowledge_context(
        self, 
        agent_id: str, 
        query: str
    ) -> List[KnowledgeChunk]:
        """获取智能体的知识上下文"""
        
        if agent_id not in self.agent_knowledge_mappings:
            self.logger.warning(f"智能体 '{agent_id}' 未注册")
            return []
        
        # 获取智能体可访问的知识库
        accessible_bases = self.agent_knowledge_mappings[agent_id]
        
        # 总是包含共享知识库
        if self.shared_knowledge_base not in accessible_bases:
            accessible_bases.append(self.shared_knowledge_base)
        
        # 执行搜索
        search_query = Query(text=query, top_k=5)
        results = await self.knowledge_manager.search(search_query, accessible_bases)
        
        return results
    
    async def update_agent_knowledge_access(
        self, 
        agent_id: str, 
        knowledge_bases: List[str]
    ) -> bool:
        """更新智能体的知识库访问权限"""
        
        if agent_id not in self.agent_knowledge_mappings:
            self.logger.warning(f"智能体 '{agent_id}' 未注册")
            return False
        
        self.agent_knowledge_mappings[agent_id] = knowledge_bases
        self.logger.info(f"智能体 '{agent_id}' 知识库权限更新为: {knowledge_bases}")
        return True
    
    def get_agent_knowledge_access(self, agent_id: str) -> List[str]:
        """获取智能体的知识库访问权限"""
        return self.agent_knowledge_mappings.get(agent_id, [])
    
    async def cleanup_orphaned_knowledge(self) -> Dict[str, Any]:
        """清理孤儿知识（无智能体访问的知识）"""
        
        # 获取所有活跃的知识库
        active_bases = set()
        for bases in self.agent_knowledge_mappings.values():
            active_bases.update(bases)
        
        # 找出孤儿知识库
        all_bases = set(self.knowledge_manager.list_knowledge_bases())
        orphaned_bases = all_bases - active_bases - {self.shared_knowledge_base}
        
        cleanup_report = {
            'orphaned_bases': list(orphaned_bases),
            'cleaned_bases': []
        }
        
        # 清理孤儿知识库
        for base_name in orphaned_bases:
            success = await self.knowledge_manager.delete_knowledge_base(base_name)
            if success:
                cleanup_report['cleaned_bases'].append(base_name)
        
        return cleanup_report