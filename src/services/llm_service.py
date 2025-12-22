"""
LLM服务 - 负责LLM的完整生命周期
"""

import logging
from typing import Dict, Optional

from src.agents.base.base_llm import BaseLLM
from src.infrastructure.cache.cache_manager import UnifiedCacheManager

logger = logging.getLogger(__name__)


class LLMService:
    """LLM服务 - 集成创建、管理、缓存"""
    
    def __init__(self, cache_manager: UnifiedCacheManager):
        self.cache_manager = cache_manager
        self._llm_instances: Dict[str, BaseLLM] = {}
    
    async def get_or_create_llm(
        self,
        llm_config_id: int,
        llm_id: Optional[str] = None
    ) -> BaseLLM:
        """
        获取或创建LLM实例
        
        Args:
            llm_config_id: LLM配置ID
            llm_id: LLM实例ID，如果为None则使用配置ID
            
        Returns:
            BaseLLM实例
        """
        if llm_id is None:
            llm_id = f"llm_{llm_config_id}"
        
        # 1. 检查是否已存在该实例
        if llm_id in self._llm_instances:
            logger.info(f"Using existing LLM instance: {llm_id}")
            return self._llm_instances[llm_id]
        
        # 2. 从数据库获取配置
        config = await self._get_llm_config(llm_config_id)
        
        # 3. 创建LLM实例
        llm_instance = await self._create_llm_instance(config)
        
        # 4. 存储实例
        self._llm_instances[llm_id] = llm_instance
        
        logger.info(f"LLM instance created: {llm_id} ({config.llm_type})")
        return llm_instance
    
    async def _get_llm_config(self, llm_config_id: int):
        """从数据库获取LLM配置"""
        try:
            from src.shared.utils.db_utils import get_async_session
            from src.agents.repositories.llm_repository import LLMRepository
            
            session_gen = get_async_session()
            session = await session_gen.__anext__()
            
            llm_repo = LLMRepository(session)
            db_config = await llm_repo.get(llm_config_id)
            
            if not db_config:
                raise ValueError(f"数据库中未找到LLM配置: {llm_config_id}")
            
            # 验证和调整配置参数
            self._validate_and_adjust_config(db_config)
            
            return db_config
            
        except Exception as e:
            logger.error(f"Failed to get LLM config from database: {e}")
            raise
    
    async def _create_llm_instance(self, config) -> BaseLLM:
        """创建LLM实例"""
        try:
            from src.infrastructure.llm.impls.llm_factory import LLMFactory
            
            # 使用LLMFactory创建LLM实例
            llm_instance = LLMFactory.create_llm(config.llm_type, config)
            return llm_instance
            
        except Exception as e:
            logger.error(f"Failed to create LLM instance: {e}")
            raise
    
    @staticmethod
    def _validate_and_adjust_config(config):
        """验证和调整配置参数"""
        # 检查温度值是否在有效范围内，并转换为float
        try:
            temp_value = float(config.temperature)
            if temp_value > 2 or temp_value < 0:
                logger.warning(f"Temperature value {temp_value} out of range [0,2], adjusting to 0.7")
                config.temperature = 0.7
            else:
                config.temperature = temp_value
        except (ValueError, TypeError):
            logger.warning("Temperature value format error, adjusting to 0.7")
            config.temperature = 0.7

        # 检查API key是否存在
        if not config.api_key and config.llm_type != "mock":
            logger.warning(f"{config.name} configuration missing API key, will use Mock mode")
            config.llm_type = "mock"
    
    def get_llm(self, name: str) -> Optional[BaseLLM]:
        """获取LLM实例"""
        return self._llm_instances.get(name)

    def list_llms(self) -> Dict[str, str]:
        """列出所有LLM实例"""
        return {
            name: type(llm).__name__
            for name, llm in self._llm_instances.items()
        }

    async def remove_llm(self, name: str):
        """移除LLM实例"""
        if name in self._llm_instances:
            llm_instance = self._llm_instances.pop(name)
            try:
                # 如果LLM有close方法，调用它
                if hasattr(llm_instance, 'close') and callable(getattr(llm_instance, 'close')):
                    await llm_instance.close()
            except Exception as e:
                logger.error(f"Failed to close LLM instance {name}: {e}")
            logger.info(f"LLM instance removed: {name}")

    async def close(self):
        """关闭服务"""
        for llm_id, llm_instance in list(self._llm_instances.items()):
            try:
                # 如果LLM有close方法，调用它
                if hasattr(llm_instance, 'close') and callable(getattr(llm_instance, 'close')):
                    await llm_instance.close()
            except Exception as e:
                logger.error(f"Failed to close LLM instance {llm_id}: {e}")
        
        self._llm_instances.clear()
        logger.info("All LLM instances closed")