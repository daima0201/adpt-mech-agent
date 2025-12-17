"""
智能体管理器 - 简化版本
只负责Agent实例的管理，不负责创建和缓存
"""

import asyncio
import logging
from typing import Dict, Optional, List

from src.agents import BaseAgent, AgentFactory, BaseLLM
from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.impls.llm.llm_factory import LLMFactory
from src.agents.repositories import agent_repository
from src.managers.cache_manager import get_cache_manager

logger = logging.getLogger(__name__)


class AgentManager:
    """Agent实例和配置管理器 - 管理内存中的Agent配置和实例"""

    def __init__(self):
        self.UnifiedCacheManager = get_cache_manager()
        self.llm_factory = LLMFactory()
        self.agent_factory = AgentFactory()
        self.agent_configs: Dict[str, AgentFullConfig] = {}
        self.agents: Dict[str, BaseAgent] = {}  # 使用BaseAgent类型以支持任何Agent实例
        self.active_agent_id: Optional[str] = None
        self._lock = asyncio.Lock()
        self._register_lock = asyncio.Lock()
        self.initialized = False

    async def initialize(self):
        async with self._lock:
            """初始化管理器"""
            if not self.initialized:
                self.agent_configs = await self._load_agent_configs()
                try:
                    for agent_id, agent_full_config in self.agent_configs.items():
                        try:
                            # 2.1 从配置获取LLM实例
                            llm = await self.llm_factory.create_llm_from_config(agent_full_config)

                            # 2.2 创建Agent实例
                            agent = await self._create_agent(agent_id, agent_full_config, llm)
                            await agent.initialize()

                            # 2.3 注册Agent
                            await self.register(agent_id, agent, agent_full_config)

                            logger.info(f"Agent initialized: {agent_id}")

                        except Exception as e:
                            logger.error(f"Failed to initialize agent {agent_id}: {e}")
                            # 可以选择继续初始化其他Agent，而不是直接失败
                            continue
                    self.initialized = True
                except Exception as e:
                    logger.error(f"Failed to initialize AgentManager: {e}")

    async def register(self, agent_id: str, agent: BaseAgent, agent_full_config: AgentFullConfig) -> bool:
        """注册Agent实例"""
        async with self._register_lock:
            # if agent_id in self.agent_configs:
            #     logger.warning(f"Agent {agent_id} already registered")
            #     return False

            self.agent_configs[agent_id] = agent_full_config
            self.agents[agent_id] = agent
            # 将配置存入缓存
            await self.UnifiedCacheManager.set_config("agent", agent_id, agent_full_config.to_dict())

            # 如果没有活跃Agent，设置为活跃
            if self.active_agent_id is None:
                self.active_agent_id = agent_id
                await self.switch_active(agent_id)

            logger.info(f"Agent registered: {agent_id}")
            return True

    async def create_and_register(self, agent_id: str, agent_full_config: AgentFullConfig) -> bool:
        async with self._lock:
            """创建Agent并且注册Agent实例"""
            try:
                # 2.1 从配置获取LLM实例
                llm = await self.llm_factory.create_llm_from_config(agent_full_config)

                # 2.2 创建Agent实例
                agent = await self._create_agent(agent_id, agent_full_config, llm)
                await agent.initialize()

                # 2.3 注册Agent
                await self.register(agent_id, agent, agent_full_config)

                logger.info(f"Agent initialized: {agent_id}")

                return True
            except Exception as e:
                logger.error(f"Failed to initialize agent {agent_id}: {e}")
                return False

    async def unregister(self, agent_id: str) -> bool:
        """注销Agent实例"""
        async with self._lock:
            if agent_id not in self.agent_configs:
                logger.warning(f"Agent {agent_id} not found")
                return False

            # 如果注销的是活跃Agent，重新选择
            if self.active_agent_id == agent_id:
                self.active_agent_id = next(
                    (id_ for id_ in self.agent_configs.keys() if id_ != agent_id),
                    None
                )
                await self.switch_active(agent_id)
            # 关闭Agent
            await self.close_agent(agent_id)

            logger.info(f"Agent unregistered: {agent_id}")
            return True

    async def switch_active(self, agent_id: str) -> bool:
        """切换活跃Agent"""
        if agent_id not in self.agent_configs:
            logger.error(f"Agent {agent_id} not found")
            return False

        old_id = self.active_agent_id
        self.agents[old_id].switch_active(False)
        self.active_agent_id = agent_id
        self.agents[self.active_agent_id].switch_active(True)
        logger.info(f"Active agent switched: {old_id} -> {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> BaseAgent:
        """获取Agent实例"""
        logger.debug(f"Looking for agent: {agent_id}")
        logger.debug(f"Available agents: {list(self.agents.keys())}")
        return self.agents.get(agent_id)

    async def get_active_agent(self) -> BaseAgent | None:
        """获取活跃Agent实例"""
        if self.active_agent_id:
            logger.info(f"Active agent fetched: {self.active_agent_id}")
            return self.agents.get(self.active_agent_id)
        logger.info(f"No active agent : None ")
        return None

    def list_agents(self) -> List[str]:
        """列出所有Agent ID"""
        ids = []
        # 正确的方式 - 通过 agent_config 访问
        for agent_id, full_config in self.agent_configs.items():
            ids.append(agent_id)
        return ids

    async def close_all(self):
        """关闭所有Agent"""
        async with self._lock:
            for agent_id, agent in list(self.agents.items()):
                await self.close_agent(agent_id)

            self.agent_configs.clear()
            self.agents.clear()
            clear_cnt = await self.UnifiedCacheManager.clear_pattern("agent:config:*")
            # logger.info(f"{clear_cnt} agents has been cleared")

            self.active_agent_id = None
            logger.info("All agents closed")

    async def close_agent(self, agent_id: str):
        try:
            agent_instance = self.agents.pop(agent_id, None)
            config = self.agent_configs.pop(agent_id, None)  # 同上
            """关闭单个Agent"""
            if hasattr(agent_instance, 'close') and callable(getattr(agent_instance, 'close')):
                await agent_instance.close()
            elif hasattr(agent_instance, 'shutdown') and callable(getattr(agent_instance, 'shutdown')):
                await agent_instance.shutdown()
            # 从缓存删除配置
            await self.UnifiedCacheManager.delete_config("agent", agent_id)
            logger.info(f"agent:{agent_id} -> agents has been cleared")
        except Exception as e:
            logger.error(f"Failed to close agent {agent_id}: {e}")
            raise

    async def _load_agent_configs(self) -> Dict[str, AgentFullConfig]:
        """从redis和内存加载初始Agent配置（如果有）"""
        agent_configs = {}
        try:
            configs = await self.UnifiedCacheManager.get_all_config("agent", "*")
            logger.info(f"Found {len(configs)} cache entries")

            for cache_key, agent_full_config_data in configs.items():
                logger.debug(f"Processing cache key: {cache_key}")
                # 从完整的缓存键中提取agent_id
                # 缓存键格式: "agent:config:{agent_id}"
                if cache_key.startswith("agent:config:"):
                    agent_id = cache_key.replace("agent:config:", "")
                    try:
                        agent_configs[agent_id] = AgentFullConfig.from_dict(agent_full_config_data)
                        logger.info(f"Successfully loaded agent config: {agent_id}")
                    except Exception as e:
                        logger.error(f"Failed to parse agent config for {agent_id}: {e}")
                else:
                    logger.warning(f"Unexpected cache key format: {cache_key}")
        except Exception as e:
            logger.error(f"Failed to load agent configs from cache: {e}")
            return {}

        logger.info(f"Loaded {len(agent_configs)} agent configs from cache")
        return agent_configs

    def get_all_config(self) -> Dict[str, AgentFullConfig]:
        """从redis和内存加载初始Agent配置（如果有）"""
        return self.agent_configs

    async def _create_agent(self, agent_id: str, agent_full_config: AgentFullConfig, llm: BaseLLM) -> BaseAgent:
        """根据配置创建 LLM 实例"""
        return await self.agent_factory.create_agent(agent_id, agent_full_config, llm)

    async def list_agent_templates(self):
        """列出所有可用的智能体模板"""
        try:
            async with agent_repository() as repo:
                # 1. 获取DTO
                full_config = await repo.list_agent_configs()
        except Exception as e:
            logger.error(f"Failed to list agent templates: {e}")
            return []
        return full_config
