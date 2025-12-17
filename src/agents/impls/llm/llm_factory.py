"""
LLM工厂类
"""

import logging
from typing import Dict, Any, Union

from src.agents.core.base_llm import BaseLLM, LLMConfig
from .deepseek_llm import DeepSeekClient
from .mock_llm import MockLLM
from .openai_llm import OpenAIClient
from ...models.agent_config import AgentConfig
from ...DTO.agent_full_config import AgentFullConfig

logger = logging.getLogger(__name__)


class LLMFactory:
    """LLM工厂类"""

    @staticmethod
    def create_llm(llm_type: str = "openai", config: Union[LLMConfig, Dict, None] = None) -> BaseLLM:
        """创建LLM实例 - 支持LLMConfig对象或字典配置"""

        # 如果config是LLMConfig对象，直接使用
        if isinstance(config, LLMConfig):
            llm_config = config
        else:
            # 如果是字典或None，创建LLMConfig对象
            if config is None:
                config_dict = {}
            elif isinstance(config, dict):
                config_dict = config
            else:
                raise ValueError(f"不支持的配置类型: {type(config)}")

            # 确保有必要的字段
            if 'model_name' not in config_dict:
                config_dict['model_name'] = "deepseek-chat"

            # 创建配置对象
            llm_config = LLMConfig(**config_dict)
            llm_config.llm_type = llm_type  # 确保llm_type设置正确

        # 根据类型创建对应的LLM客户端
        llm_type_lower = llm_config.llm_type.lower() if hasattr(llm_config, 'llm_type') else llm_type.lower()

        if llm_type_lower == "openai":
            return OpenAIClient(llm_config)
        elif llm_type_lower == "deepseek":
            return DeepSeekClient(llm_config)
        elif llm_type_lower == "mock":
            return MockLLM(llm_config)
        else:
            raise ValueError(f"不支持的LLM类型: {llm_type_lower}")

    @staticmethod
    def from_dict(config_dict: Dict[str, Any]) -> BaseLLM:
        """从配置字典创建LLM实例 - 兼容多种字段名"""
        # 从字典中提取llm_type
        llm_type = config_dict.get('llm_type', config_dict.get('type', config_dict.get('provider', 'openai')))

        # 准备配置参数
        llm_config_params = {}

        # 字段名映射（处理不同来源的字段名）
        field_mappings = {
            # 标准字段
            'llm_type': 'llm_type',
            'type': 'llm_type',
            'provider': 'llm_type',
            'model': 'model_name',
            'model_name': 'model_name',
            'api_key': 'api_key',
            'base_url': 'base_url',
            'temperature': 'temperature',
            'max_tokens': 'max_tokens',
            'timeout': 'timeout',
            'max_retries': 'max_retries',
            'extra_params': 'extra_params',
            'description': 'description'
        }

        # 复制配置参数
        for key, value in config_dict.items():
            if key in field_mappings:
                llm_config_params[field_mappings[key]] = value
            else:
                # 保留其他字段
                llm_config_params[key] = value

        # 确保llm_type存在
        if 'llm_type' not in llm_config_params:
            llm_config_params['llm_type'] = llm_type

        # 确保model_name存在
        if 'model_name' not in llm_config_params:
            if 'model' in config_dict:
                llm_config_params['model_name'] = config_dict['model']
            else:
                llm_config_params['model_name'] = f"default-{llm_type}"

        # 温度值处理
        if 'temperature' in llm_config_params and llm_config_params['temperature'] is not None:
            # 确保温度是数字类型
            try:
                temp_value = llm_config_params.get('temperature')
                if isinstance(temp_value, str):
                    llm_config_params['temperature'] = float(temp_value)
                elif hasattr(temp_value, '__float__'):
                    llm_config_params['temperature'] = float(temp_value)
            except (ValueError, TypeError):
                llm_config_params['temperature'] = 0.7

        # 创建LLM实例
        return LLMFactory.create_llm(llm_type, llm_config_params)

    @staticmethod
    def from_config_object(llm_config: LLMConfig) -> BaseLLM:
        """直接从LLMConfig对象创建LLM实例"""
        return LLMFactory.create_llm(llm_config.llm_type, llm_config)

    @staticmethod
    def create_default_llm(llm_type: str = "openai") -> BaseLLM:
        """创建默认配置的LLM实例"""
        default_config = {
            'llm_type': llm_type,
            'model_name': 'gpt-3.5-turbo' if llm_type == 'openai' else 'deepseek-chat',
            'temperature': 0.7,
            'max_tokens': 2048,
            'timeout': 30,
            'max_retries': 3
        }

        return LLMFactory.create_llm(llm_type, default_config)

    async def create_llm_from_config(self, agent_full_config: AgentFullConfig) -> BaseLLM:
        """根据AgentConfig的LLM配置创建LLM实例"""
        try:
            # 1. 检查是否有LLM配置
            if not hasattr(agent_full_config, 'llm_config') or agent_full_config.llm_config is None:
                logger.warning(f"AgentConfig {agent_full_config.agent_config.name} has no llm_config relation loaded")

                # 尝试从extra_params获取
                if agent_full_config.agent_config.extra_params and 'llm_config' in agent_full_config.agent_config.extra_params:
                    return self.from_dict(agent_full_config.agent_config.extra_params['llm_config'])
                else:
                    # 创建默认LLM
                    logger.info(f"Creating default LLM for agent: {agent_full_config.agent_config.name}")
                    return self.create_default_llm()

            # 2. 使用AgentConfig中的LLMConfig
            llm_config = agent_full_config.llm_config

            # 3. 可以直接使用LLMConfig对象
            llm = self.from_config_object(llm_config)

            logger.info(f"Created LLM for agent {agent_full_config.agent_config.name} (type: {llm_config.llm_type})")
            return llm

        except Exception as e:
            logger.error(f"Failed to create LLM for agent {agent_full_config.agent_config.name}: {e}")

            # 兜底：创建MockLLM
            fallback_config = LLMConfig(
                llm_type='mock',
                model_name='mock-llm',
                temperature=0.7,
                max_tokens=2048
            )
            return self.from_config_object(fallback_config)
