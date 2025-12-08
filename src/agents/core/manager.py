"""
智能体管理器 - 统一的多智能体协调系统
基于参考架构优化的智能体管理组件
"""

import logging
import asyncio
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass
from enum import Enum

from src.agents.core.agent import Agent
from src.agents.core.message import Message
from src.agents.tools import ToolRegistry

logger = logging.getLogger(__name__)

class AgentState(Enum):
    """智能体状态枚举"""
    IDLE = "idle"           # 空闲
    THINKING = "thinking"   # 思考中
    EXECUTING = "executing" # 执行中
    ERROR = "error"         # 错误

@dataclass
class AgentProfile:
    """智能体配置文件"""
    name: str                    # 智能体名称
    role: str                    # 角色描述
    personality: str             # 个性特征
    expertise: List[str]         # 专业领域
    thinking_style: str          # 思考风格
    response_template: str       # 响应模板

class AgentManager:
    """智能体管理器 - 统一的多智能体协调系统"""
    
    def __init__(self, tool_registry: Optional[ToolRegistry] = None):
        self.agents: Dict[str, Agent] = {}
        self.active_agent_id: Optional[str] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        self.conversation_sessions: Dict[str, List[Message]] = {}
        self.tool_registry = tool_registry
        
        logger.info("Agent Manager initialized")
    
    def register_agent(self, agent_id: str, agent: Agent) -> bool:
        """注册智能体"""
        if agent_id in self.agents:
            logger.warning(f"Agent {agent_id} already exists")
            return False
        
        self.agents[agent_id] = agent
        
        # 如果没有活跃智能体，设置第一个为活跃
        if not self.active_agent_id:
            self.active_agent_id = agent_id
        
        logger.info(f"Registered agent: {agent_id}")
        return True
    
    def unregister_agent(self, agent_id: str) -> bool:
        """注销智能体"""
        if agent_id not in self.agents:
            logger.warning(f"Agent {agent_id} not found")
            return False
        
        # 如果注销的是活跃智能体，需要重新选择
        if self.active_agent_id == agent_id:
            self.active_agent_id = None
            # 尝试选择另一个智能体作为活跃
            for other_id in self.agents.keys():
                if other_id != agent_id:
                    self.active_agent_id = other_id
                    break
        
        del self.agents[agent_id]
        logger.info(f"Unregistered agent: {agent_id}")
        return True
    
    async def switch_active_agent(self, new_agent_id: str) -> bool:
        """切换活跃智能体"""
        if new_agent_id not in self.agents:
            logger.error(f"Agent {new_agent_id} not found")
            return False
        
        old_agent_id = self.active_agent_id
        self.active_agent_id = new_agent_id
        
        logger.info(f"Switched active agent from {old_agent_id} to {new_agent_id}")
        return True
    
    async def send_message(self, message_content: str, session_id: str = None, **kwargs) -> str:
        """发送消息给当前活跃智能体"""
        if not self.active_agent_id:
            raise ValueError("No active agent selected")
        
        active_agent = self.agents[self.active_agent_id]
        
        # 使用智能体的run方法处理消息
        response = await asyncio.get_event_loop().run_in_executor(
            None, lambda: active_agent.run(message_content, **kwargs)
        )
        
        # 记录会话历史
        if session_id:
            if session_id not in self.conversation_sessions:
                self.conversation_sessions[session_id] = []
            
            # 添加用户消息和智能体响应到会话历史
            user_message = Message(content=message_content, role="user")
            assistant_message = Message(content=response, role="assistant")
            
            self.conversation_sessions[session_id].extend([user_message, assistant_message])
        
        return response
    
    def get_agent_list(self) -> List[Dict[str, Any]]:
        """获取智能体列表信息"""
        agents_info = []
        
        for agent_id, agent in self.agents.items():
            agents_info.append({
                'id': agent_id,
                'name': agent.config.name,
                'is_active': agent_id == self.active_agent_id,
                'conversation_count': len(agent.get_message_history())
            })
        
        return agents_info
    
    def get_active_agent_info(self) -> Optional[Dict[str, Any]]:
        """获取当前活跃智能体信息"""
        if not self.active_agent_id:
            return None
        
        agent = self.agents[self.active_agent_id]
        return {
            'id': self.active_agent_id,
            'name': agent.config.name,
            'system_prompt': agent.config.system_prompt,
            'history_length': len(agent.get_message_history())
        }
    
    def register_tool_to_agent(self, agent_id: str, tool_name: str, tool_function: Callable) -> bool:
        """为指定智能体注册工具"""
        if agent_id not in self.agents:
            logger.error(f"Agent {agent_id} not found")
            return False
        
        # 这里需要根据具体的智能体类型来注册工具
        # 对于支持工具的智能体（如ReActAgent），可以调用其工具注册方法
        agent = self.agents[agent_id]
        
        # 检查智能体是否支持工具注册
        if hasattr(agent, 'register_tool'):
            agent.register_tool(tool_name, tool_function)
            logger.info(f"Registered tool {tool_name} to agent {agent_id}")
            return True
        else:
            logger.warning(f"Agent {agent_id} does not support tool registration")
            return False
    
    async def extract_knowledge_from_session(self, session_id: str) -> List[Dict[str, Any]]:
        """从会话中提取知识"""
        if session_id not in self.conversation_sessions:
            return []
        
        conversation = self.conversation_sessions[session_id]
        knowledge_items = []
        
        for i, message in enumerate(conversation):
            if message.role == "assistant":
                # 简单的知识提取逻辑
                content = message.content
                if len(content) > 100 and '?' not in content:
                    knowledge_item = {
                        'id': f"knowledge_{i}_{hash(content) % 10000}",
                        'content': content,
                        'source_agent': self.active_agent_id,
                        'importance': self._calculate_knowledge_importance(content)
                    }
                    knowledge_items.append(knowledge_item)
        
        return knowledge_items
    
    def _calculate_knowledge_importance(self, content: str) -> float:
        """计算知识重要性"""
        importance_score = 0.0
        
        # 长度因素
        length_factor = min(len(content) / 500, 1.0)
        importance_score += length_factor * 0.3
        
        # 关键词因素
        important_indicators = ['方案', '建议', '策略', '流程', '标准']
        for indicator in important_indicators:
            if indicator in content:
                importance_score += 0.2
                break
        
        # 结构因素
        if any(struct in content for struct in ['第一', '第二', '1.', '2.', '- ', '* ']):
            importance_score += 0.2
        
        return min(importance_score, 1.0)
    
    def clear_session(self, session_id: str) -> bool:
        """清空指定会话"""
        if session_id in self.conversation_sessions:
            del self.conversation_sessions[session_id]
            logger.info(f"Cleared session: {session_id}")
            return True
        return False
    
    def get_session_count(self) -> int:
        """获取会话数量"""
        return len(self.conversation_sessions)

# 示例：创建预配置的智能体管理器
class PreconfiguredAgentManager(AgentManager):
    """预配置的智能体管理器"""
    
    def __init__(self, llm, tool_registry: Optional[ToolRegistry] = None):
        super().__init__(tool_registry)
        self.llm = llm
        self._initialize_default_agents()
    
    def _initialize_default_agents(self):
        """初始化默认智能体"""
        from src.agents.core.agent import AgentConfig
        from src.agents.impls.simple_agent import SimpleAgent
        from src.agents.impls.react_agent import ReActAgent
        from src.agents.impls.reflection_agent import ReflectionAgent
        from src.agents.impls.plan_solve_agent import PlanAndSolveAgent
        
        # 创建简单助手
        simple_config = AgentConfig(
            name="简单助手",
            description="一个简单的对话助手",
            system_prompt="你是一个乐于助人的AI助手。"
        )
        simple_agent = SimpleAgent(simple_config, self.llm)
        self.register_agent("simple_assistant", simple_agent)
        
        # 创建推理助手
        react_config = AgentConfig(
            name="推理助手",
            description="一个善于推理的助手",
            system_prompt="你是一个善于推理和解决问题的AI助手。"
        )
        react_agent = ReActAgent(react_config, self.llm)
        self.register_agent("reasoning_assistant", react_agent)
        
        # 创建反思助手
        reflection_config = AgentConfig(
            name="反思助手",
            description="一个善于反思的助手",
            system_prompt="你是一个严谨、善于自我反思的AI助手。"
        )
        reflection_agent = ReflectionAgent(reflection_config, self.llm)
        self.register_agent("reflective_assistant", reflection_agent)
        
        # 创建规划助手
        plan_config = AgentConfig(
            name="规划助手",
            description="一个善于规划的助手",
            system_prompt="你是一个擅长制定计划和解决问题的AI助手。"
        )
        plan_agent = PlanAndSolveAgent(plan_config, self.llm)
        self.register_agent("planning_assistant", plan_agent)
        
        logger.info("Initialized default impls")

# 演示函数
async def demo_agent_manager():
    """演示智能体管理器功能"""
    
    from src.agents.core.llm import HelloAgentsLLM
    
    # 创建LLM实例
    llm = HelloAgentsLLM()
    
    # 创建预配置的管理器
    manager = PreconfiguredAgentManager(llm)
    
    # 显示可用智能体
    print("可用智能体:")
    for agent in manager.get_agent_list():
        print(f"- {agent['name']} ({agent['id']}) - {'活跃' if agent['is_active'] else '非活跃'}")
    
    # 发送测试消息
    response = await manager.send_message("你好，请介绍一下你自己", "demo_session")
    print(f"\n智能体响应: {response}")
    
    # 切换到推理助手
    await manager.switch_active_agent("reasoning_assistant")
    
    # 再次发送消息
    response2 = await manager.send_message("请帮我分析一个复杂问题", "demo_session")
    print(f"\n推理助手响应: {response2}")
    
    # 提取知识
    knowledge = await manager.extract_knowledge_from_session("demo_session")
    print(f"\n提取的知识项: {len(knowledge)}")

if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 运行演示
    asyncio.run(demo_agent_manager())