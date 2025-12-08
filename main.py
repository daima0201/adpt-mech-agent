"""
自适应机制智能体系统 - 主应用入口
集成知识管理、工具调用和智能体协调功能
"""

import logging
import asyncio
import argparse
import sys
from pathlib import Path

# 添加项目根目录到Python路径
sys.path.insert(0, str(Path(__file__).parent))

from src.adaptive.knowledge_manager import KnowledgeManager
from src.adaptive import ToolManager
from src.adaptive import AgentOrchestrator, AgentRole

logger = logging.getLogger(__name__)

class AdaptiveMechAgentSystem:
    """自适应机制智能体系统"""
    
    def __init__(self, config_path: str = None):
        self.config = self._load_config(config_path)
        self.knowledge_manager = None
        self.tool_manager = None
        self.agent_orchestrator = None
        
        # 初始化标志
        self.initialized = False
        
        logger.info("Adaptive Mech Agent System created")
    
    async def initialize(self):
        """初始化系统组件"""
        
        try:
            logger.info("Initializing Adaptive Mech Agent System...")
            
            # 1. 初始化知识管理器
            self.knowledge_manager = KnowledgeManager(
                vector_db_path=self.config.get('vector_db_path', './data/vector_db'),
                chunk_size=self.config.get('chunk_size', 500),
                chunk_overlap=self.config.get('chunk_overlap', 50)
            )
            await self.knowledge_manager.initialize()
            
            # 2. 初始化工具管理器
            self.tool_manager = ToolManager()
            
            # 3. 初始化智能体协调器
            self.agent_orchestrator = AgentOrchestrator(
                knowledge_manager=self.knowledge_manager,
                tool_manager=self.tool_manager
            )
            
            self.initialized = True
            logger.info("Adaptive Mech Agent System initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize system: {e}")
            raise
    
    async def process_user_message(self, conversation_id: str, user_message: str, 
                                  current_role: AgentRole = None) -> dict:
        """处理用户消息"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        try:
            # 1. 路由消息到合适的智能体
            collaboration_result = await self.agent_orchestrator.route_message(
                conversation_id, user_message, current_role
            )
            
            # 2. 获取对话摘要
            conversation_summary = self.agent_orchestrator.get_conversation_summary(conversation_id)
            
            # 3. 准备响应数据
            response_data = {
                'success': True,
                'response': collaboration_result.final_response,
                'primary_agent': collaboration_result.primary_agent.value,
                'supporting_agents': [agent.value for agent in collaboration_result.contributing_agents],
                'confidence_score': collaboration_result.confidence_score,
                'reasoning_log': collaboration_result.reasoning_log,
                'conversation_summary': conversation_summary,
                'timestamp': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Processed message for conversation {conversation_id}")
            return response_data
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return {
                'success': False,
                'error': str(e),
                'response': "抱歉，处理消息时出现错误。"
            }
    
    async def switch_agent_role(self, conversation_id: str, new_role: AgentRole) -> dict:
        """切换智能体角色"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        success = self.agent_orchestrator.switch_agent_role(conversation_id, new_role)
        
        return {
            'success': success,
            'new_role': new_role.value if success else None,
            'message': f"切换到 {new_role.value} 角色" if success else "角色切换失败"
        }
    
    async def execute_tool(self, tool_name: str, parameters: dict) -> dict:
        """执行工具"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        try:
            # 这里可以添加权限检查和确认逻辑
            result = await self.tool_manager.execute_tool(tool_name, parameters)
            
            return {
                'success': result.success,
                'output': result.output,
                'error_message': result.error_message,
                'execution_time': result.execution_time,
                'metadata': result.metadata
            }
            
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {
                'success': False,
                'error': str(e),
                'output': ""
            }
    
    async def search_knowledge_base(self, query: str, top_k: int = 5) -> dict:
        """搜索知识库"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        try:
            results = self.knowledge_manager.search(query, top_k=top_k)
            
            return {
                'success': True,
                'query': query,
                'results': results,
                'total_found': len(results)
            }
            
        except Exception as e:
            logger.error(f"Error searching knowledge base: {e}")
            return {
                'success': False,
                'error': str(e),
                'results': []
            }
    
    async def add_document_to_knowledge_base(self, file_path: str, 
                                           metadata: dict = None) -> dict:
        """添加文档到知识库"""
        
        if not self.initialized:
            raise RuntimeError("System not initialized. Call initialize() first.")
        
        try:
            document_id = await self.knowledge_manager.add_document(file_path, metadata)
            
            return {
                'success': True,
                'document_id': document_id,
                'message': f"文档已成功添加到知识库，ID: {document_id}"
            }
            
        except Exception as e:
            logger.error(f"Error adding document to knowledge base: {e}")
            return {
                'success': False,
                'error': str(e),
                'document_id': None
            }
    
    def get_system_status(self) -> dict:
        """获取系统状态"""
        
        status = {
            'initialized': self.initialized,
            'components': {}
        }
        
        if self.initialized:
            # 知识库状态
            kb_stats = self.knowledge_manager.get_statistics()
            status['components']['knowledge_manager'] = {
                'status': 'active',
                'documents_count': kb_stats.get('documents_count', 0),
                'chunks_count': kb_stats.get('chunks_count', 0),
                'vector_db_size': kb_stats.get('vector_db_size', 0)
            }
            
            # 工具管理器状态
            tools_info = self.tool_manager.list_tools_by_category()
            status['components']['tool_manager'] = {
                'status': 'active',
                'total_tools': sum(len(tools) for tools in tools_info.values()),
                'categories': list(tools_info.keys())
            }
            
            # 智能体协调器状态
            agent_stats = self.agent_orchestrator.get_agent_performance_stats()
            status['components']['agent_orchestrator'] = {
                'status': 'active',
                'total_agents': len(agent_stats),
                'recent_tasks': sum(stats['recent_tasks'] for stats in agent_stats.values())
            }
        
        return status
    
    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        
        # 默认配置
        default_config = {
            'vector_db_path': './data/vector_db',
            'chunk_size': 500,
            'chunk_overlap': 50,
            'embedding_model': 'text-embedding-ada-002',
            'llm_model': 'gpt-3.5-turbo',
            'max_conversation_history': 50,
            'log_level': 'INFO'
        }
        
        # 如果提供了配置文件路径，则加载
        if config_path and Path(config_path).exists():
            try:
                import yaml
                with open(config_path, 'r', encoding='utf-8') as f:
                    user_config = yaml.safe_load(f)
                    default_config.update(user_config)
                logger.info(f"Loaded configuration from {config_path}")
            except Exception as e:
                logger.warning(f"Failed to load config from {config_path}: {e}")
        
        return default_config

async def interactive_demo():
    """交互式演示"""
    
    print("=== 自适应机制智能体系统演示 ===")
    
    # 创建系统实例
    system = AdaptiveMechAgentSystem()
    
    # 初始化系统
    print("正在初始化系统...")
    await system.initialize()
    
    # 显示系统状态
    status = system.get_system_status()
    print(f"\n系统状态: {'已初始化' if status['initialized'] else '未初始化'}")
    
    if status['initialized']:
        print("组件状态:")
        for component, info in status['components'].items():
            print(f"  - {component}: {info['status']}")
    
    # 交互循环
    conversation_id = "demo_conversation"
    current_role = None
    
    while True:
        print("\n" + "="*50)
        print("请输入您的消息 (输入 'quit' 退出，'switch' 切换角色):")
        user_input = input("> ").strip()
        
        if user_input.lower() == 'quit':
            break
        elif user_input.lower() == 'switch':
            print("\n可用角色:")
            for role in AgentRole:
                print(f"  - {role.value}: {system.agent_orchestrator.agents_capabilities[role].description}")
            
            print("\n请输入要切换的角色名称:")
            role_input = input("> ").strip()
            
            try:
                new_role = AgentRole(role_input)
                result = await system.switch_agent_role(conversation_id, new_role)
                
                if result['success']:
                    current_role = new_role
                    print(f"✓ {result['message']}")
                else:
                    print(f"✗ {result['message']}")
                    
            except ValueError:
                print("✗ 无效的角色名称")
            
            continue
        
        # 处理用户消息
        print("\n处理中...")
        result = await system.process_user_message(conversation_id, user_input, current_role)
        
        if result['success']:
            print(f"\n🤖 {result['primary_agent']}:")
            print(result['response'])
            
            if result['supporting_agents']:
                print(f"\n辅助智能体: {', '.join(result['supporting_agents'])}")
            
            print(f"\n置信度: {result['confidence_score']:.2f}")
            
            # 更新当前角色
            current_role = AgentRole(result['primary_agent'])
            
        else:
            print(f"\n❌ 错误: {result.get('error', '未知错误')}")
    
    print("\n感谢使用自适应机制智能体系统！")

def main():
    """主函数"""
    
    parser = argparse.ArgumentParser(description='自适应机制智能体系统')
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--demo', '-d', action='store_true', help='运行交互式演示')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'], 
                       default='INFO', help='日志级别')
    
    args = parser.parse_args()
    
    # 配置日志
    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    if args.demo:
        # 运行交互式演示
        asyncio.run(interactive_demo())
    else:
        # 启动服务模式（未来扩展）
        print("服务模式尚未实现，请使用 --demo 参数运行演示")
        sys.exit(1)

if __name__ == "__main__":
    main()