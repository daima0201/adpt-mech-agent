"""
Agent服务 - 适配API架构的简化版本
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Optional, List, Any, AsyncGenerator

from pydantic import BaseModel

from src.agents import BaseAgent
from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.models.agent_config import AgentConfig
from src.agents.repositories import AgentRepository, agent_repository
from src.managers.agent_manager import AgentManager
from src.managers.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class ChatResponse(BaseModel):
    """聊天响应模型"""
    response: str
    session_id: str
    tokens_used: int = 0
    processing_time: float = 0.0


class AgentService:
    """Agent服务层 - 提供业务逻辑和API适配"""

    def __init__(self, agent_manager: AgentManager = None):
        self.agent_repo: Optional[AgentRepository] = None  # ✅ 初始化为None
        self.cache_manager = get_cache_manager()
        self.agent_manager = agent_manager or AgentManager()
        self._initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """初始化服务"""
        async with self._lock:
            if not self._initialized:
                await self.agent_manager.initialize()
                # async_session_gen = get_async_session()
                # async_session = await async_session_gen.__anext__()
                # self.agent_repo = AgentRepository(async_session)
                self._initialized = True
                logger.info("AgentService initialized")

    async def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """获取Agent实例"""
        if not self._initialized:
            await self.initialize()

        return self.agent_manager.get_agent(agent_id)

    async def get_active_agent(self) -> Optional[BaseAgent]:
        """获取当前活跃的Agent"""
        if not self._initialized:
            await self.initialize()

        return await self.agent_manager.get_active_agent()

    async def create_agent_from_db(self, agent_config_id: int) -> str:
        """使用DTO创建Agent"""
        try:
            async with agent_repository() as repo:
                # 1. 获取DTO
                full_config = await repo.get_full_agent_config(agent_config_id)
            if not full_config:
                raise ValueError(f"数据库配置不存在: {agent_config_id}")

            if not full_config.is_valid:
                errors = ", ".join(full_config.validation_errors)
                raise ValueError(f"配置无效: {errors}")

            # # 3. 将模板数据存入extra_params（用于Agent初始化）
            # if full_config.prompt_templates:
            #     if full_config.agent_config.extra_params is None:
            #         full_config.agent_config.extra_params = {}
            #     # 转换模板为字典
            #     template_dicts = {
            #         key: template.to_dict() if hasattr(template, 'to_dict') else str(template)
            #         for key, template in full_config.prompt_templates.items()
            #     }
            #     full_config.agent_config.extra_params["prompt_templates"] = template_dicts

            # 4. 创建Agent实例
            instance_id = f"agent_{full_config.agent_config.agent_type}_{full_config.agent_config.name}_{int(datetime.now().timestamp())}"
            success = await self.agent_manager.create_and_register(instance_id, full_config)
            # await self.agent_manager.agents[instance_id].initialize()
            if not success & self.agent_manager.agents[instance_id].is_initialized:
                raise RuntimeError("创建Agent失败")

            return instance_id

        except Exception as e:
            logger.error(f"从数据库创建Agent失败 {agent_config_id}: {e}")
            raise

    async def create_agent(self, agent_full_config: AgentFullConfig, auto_activate: bool = False) -> str:
        """
        创建新的Agent

        Args:
            agent_full_config: Agent配置
            auto_activate: 是否自动设置为活跃Agent

        Returns:
            agent_id: 创建的Agent ID
        """
        if not self._initialized:
            await self.initialize()

        # 检查配置是否有效
        if not agent_full_config.agent_config.id:
            raise ValueError("Agent配置缺少模板ID（agent_config.id）")
        # 生成唯一ID（如果配置中没有）
        agent_id = self._gen_agent_id(agent_full_config.agent_config)
        # 检查是否已存在
        if agent_id in self.agent_manager.list_agents():
            raise ValueError(f"Agent {agent_id} already exists")
        try:
            # 创建并注册Agent
            success = await self.agent_manager.create_and_register(agent_id, agent_full_config)
            if not success:
                raise RuntimeError(f"Failed to create agent {agent_id}")

            # 如果需要，设置为活跃Agent
            if auto_activate or not self.agent_manager.active_agent_id:
                await self.agent_manager.switch_active(agent_id)

            logger.info(f"Agent created successfully: {agent_id}")
            return agent_id

        except Exception as e:
            logger.error(f"Failed to create agent {agent_id}: {e}")
            # 清理可能已创建的资源
            if agent_id in self.agent_manager.list_agents():
                await self.agent_manager.unregister(agent_id)
            raise

    async def update_agent(self, agent_id: str, **kwargs) -> bool:
        """
        更新Agent配置

        Args:
            agent_id: Agent ID
            **kwargs: 要更新的配置字段

        Returns:
            bool: 是否更新成功
        """
        if not self._initialized:
            await self.initialize()

        agent = self.agent_manager.get_agent(agent_id)
        if not agent:
            logger.warning(f"Agent {agent_id} not found")
            return False

        try:
            # 获取当前配置
            current_config = self.agent_manager.agent_configs[agent_id]

            # 更新配置
            for key, value in kwargs.items():
                if hasattr(current_config, key):
                    setattr(current_config, key, value)
                else:
                    # 如果是extra_params中的字段
                    if current_config.extra_params is None:
                        current_config.extra_params = {}
                    current_config.extra_params[key] = value

            # 重新创建Agent（因为配置已更改）
            await self.agent_manager.unregister(agent_id)
            is_success = await self.agent_manager.create_and_register(agent_id, current_config)

            return is_success

        except Exception as e:
            logger.error(f"Failed to update agent {agent_id}: {e}")
            return False

    async def delete_agent(self, agent_id: str) -> bool:
        """删除Agent"""
        if not self._initialized:
            await self.initialize()
        try:
            is_success = await self.agent_manager.unregister(agent_id)
            if is_success:
                logger.info(f"Agent deleted: {agent_id}")
            return is_success
        except Exception as e:
            logger.error(f"Failed to delete agent {agent_id}: {e}")
            return False

    async def switch_active_agent(self, agent_id: str) -> bool:
        """切换活跃Agent"""
        if not self._initialized:
            await self.initialize()

        is_success = await self.agent_manager.switch_active(agent_id)
        if is_success:
            logger.info(f"Active agent switched to: {agent_id}")
        return is_success

    def list_agents(self) -> List[str]:
        """列出所有Agent ID"""
        return self.agent_manager.list_agents()

    def get_agent_config(self, agent_id: str) -> Optional[AgentFullConfig]:
        """获取Agent配置"""
        return self.agent_manager.agent_configs.get(agent_id)

    def get_all_agent_configs(self) -> Dict[str, AgentFullConfig]:
        """获取所有Agent配置"""
        return self.agent_manager.agent_configs

    async def execute_with_agent(
            self,
            agent_id: str,
            input_data: Any,
            **kwargs
    ) -> Any:
        """
        使用指定Agent执行任务
        
        Args:
            agent_id: 要使用的Agent ID
            input_data: 输入数据
            **kwargs: 传递给Agent的额外参数
        
        Returns:
            Agent执行结果
        """
        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"Agent {agent_id} not found")

        try:
            if hasattr(agent, 'process'):
                result = await agent.process(input_data, **kwargs)
            else:
                raise ValueError("Agent不支持处理接口")
            return result
        except Exception as e:
            logger.error(f"Agent {agent_id} execution failed: {e}")
            raise

    async def execute_with_active_agent(
            self,
            input_data: Any,
            **kwargs
    ) -> Any:
        """使用当前活跃Agent执行任务"""
        agent = await self.get_active_agent()
        if not agent:
            raise ValueError("No active agent available")

        return await self.execute_with_agent(agent.config.id, input_data, **kwargs)

    async def close_all(self):
        """关闭所有Agent"""
        await self.agent_manager.close_all()
        self._initialized = False
        logger.info("AgentService closed")

    @staticmethod
    def _gen_agent_id(agent_config: AgentConfig) -> str:
        return f"agent_{agent_config.agent_type}_{agent_config.name}_{int(datetime.now().timestamp())}"

    async def process_message(
            self,
            agent_id: str,
            message: str,
            session_id: str = None
    ) -> ChatResponse:
        """
        处理用户消息（非流式）
        
        Args:
            agent_id: 智能体ID
            message: 用户消息
            session_id: 会话ID
        
        Returns:
            ChatResponse: 聊天响应
        """
        if not self._initialized:
            await self.initialize()

        agent = await self.get_agent(agent_id)
        if not agent:
            raise ValueError(f"智能体 {agent_id} 不存在")

        start_time = datetime.now()

        try:
            # 执行对话
            if hasattr(agent, 'process'):
                result = await agent.process(message, session_id=session_id)
            else:
                raise ValueError("智能体不支持处理接口")

            # 计算处理时间
            processing_time = (datetime.now() - start_time).total_seconds()

            return ChatResponse(
                response=str(result),
                session_id=session_id or f"session_{int(datetime.now().timestamp())}",
                processing_time=processing_time
            )

        except Exception as e:
            logger.error(f"处理消息失败: {e}")
            raise

    async def process_message_stream(
            self,
            agent_id: str,
            message: str,
            session_id: str = None
    ) -> AsyncGenerator[str, None]:
        """
        流式处理用户消息
        
        Args:
            agent_id: 智能体ID
            message: 用户消息
            session_id: 会话ID
        
        Yields:
            str: 流式响应块
        """
        if not self._initialized:
            await self.initialize()

        logger.debug(f"Looking for agent: {agent_id}")
        agent = await self.get_agent(agent_id)
        if not agent:
            logger.error(f"Agent {agent_id} not found in agent_manager")
            logger.error(f"Available agents in service: {list(self.agent_manager.agents.keys())}")
            raise ValueError(f"智能体 {agent_id} 不存在")

        try:
            # 检查智能体是否支持流式输出
            if hasattr(agent, 'process_stream'):
                # 使用智能体的流式接口 - 不需要await，直接使用异步生成器
                async for chunk in agent.process_stream(message, session_id=session_id):
                    yield chunk
            elif hasattr(agent, 'process'):
                # 备用方案：模拟流式输出
                result = await agent.process(message, session_id=session_id)
                response_text = str(result)

                # 将响应拆分为小块进行流式输出
                chunk_size = 10
                for i in range(0, len(response_text), chunk_size):
                    chunk = response_text[i:i + chunk_size]
                    yield chunk
                    await asyncio.sleep(0.05)  # 模拟流式延迟
            else:
                raise ValueError("智能体不支持流式处理")

        except Exception as e:
            logger.error(f"流式处理消息失败: {e}")
            yield f"处理失败: {str(e)}"

    async def get_conversation_history(self, session_id: str) -> List[Dict[str, Any]]:
        """
        获取对话历史
        
        Args:
            session_id: 会话ID
            
        Returns:
            List[Dict]: 对话历史记录
        """
        # TODO: 实现对话历史存储和检索
        # 目前返回空列表，后续可以集成数据库存储
        return []

    async def list_available_templates(self):
        """列出所有可用的智能体模板"""
        return await self.agent_manager.list_agent_templates()

    def list_available_agents(self):
        """列出所有可用的智能体实例"""
        return self.agent_manager.agents


# 全局AgentService实例
_agent_service_instance = None


async def get_agent_service() -> AgentService:
    """获取全局AgentService实例"""
    global _agent_service_instance
    if _agent_service_instance is None:
        _agent_service_instance = AgentService()
        await _agent_service_instance.initialize()
    return _agent_service_instance
