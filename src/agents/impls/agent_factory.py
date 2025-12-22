# """
# Agent工厂类 - 最简化版本
# 只做一件事：根据AgentConfig和LLM创建Agent实例
# """
#
# from typing import Dict, Any, Type
# from src.agents.base.base_agent import BaseAgent, AgentConfig
# from src.agents.base.base_llm import BaseLLM
# from src.agents.enum.agent_type import AgentType
# from .plan_solve_agent import PlanAndSolveAgent
# from .react_agent import ReActAgent
# from .reflection_agent import ReflectionAgent
# from .simple_agent import SimpleAgent
#
#
# class AgentFactory:
#     """Agent工厂 - 使用AgentFullConfig创建Agent
#         最简单的Agent工厂
#         1. 不接受LLM创建 - 必须外部传入
#         2. 直接验证agent_type字符串
#         3. 映射到对应Agent类
#         4. 创建实例并返回
#     """
#
#     # Agent类型映射表
#     _AGENT_CLASSES = {
#         AgentType.SIMPLE: SimpleAgent,
#         AgentType.REACT: ReActAgent,
#         AgentType.PLAN_SOLVE: PlanAndSolveAgent,
#         AgentType.REFLECTION: ReflectionAgent,
#     }
#
#     @classmethod
#     def create_agent(cls, agent_config: AgentConfig, llm: BaseLLM) -> BaseAgent:
#         """
#         创建Agent实例 - 最简实现
#         """
#         # 1. 基础验证
#         if not isinstance(agent_config, AgentConfig):
#             raise TypeError("需要AgentConfig对象")
#
#         if not isinstance(llm, BaseLLM):
#             raise TypeError("需要BaseLLM实例")
#
#         if not agent_config.agent_type:
#             raise ValueError("AgentConfig缺少agent_type")
#
#         # 2. 解析agent_type
#         agent_type_str = agent_config.agent_type.lower()
#
#         # 简单的类型映射
#         agent_type = None
#         try:
#             # 直接尝试枚举转换
#             agent_type = AgentType(agent_type_str)
#         except ValueError:
#             # 简单的兼容处理
#             if "plan" in agent_type_str:
#                 agent_type = AgentType.PLAN_SOLVE
#             elif agent_type_str in ["react", "reaction"]:
#                 agent_type = AgentType.REACT
#             elif "reflect" in agent_type_str:
#                 agent_type = AgentType.REFLECTION
#             else:
#                 agent_type = AgentType.SIMPLE  # 默认
#
#         # 3. 获取Agent类
#         if agent_type not in cls._AGENT_CLASSES:
#             raise ValueError(f"不支持的Agent类型: {agent_type}")
#
#         agent_class = cls._AGENT_CLASSES[agent_type]
#
#         # 4. 创建实例
#         try:
#             return agent_class(config=agent_config, llm=llm)
#         except Exception as e:
#             raise ValueError(f"创建Agent失败: {e}")
#
#
# # 使用示例
# def create_agent_from_config(agent_config: AgentConfig, llm: BaseLLM) -> BaseAgent:
#     """便捷函数"""
#     return AgentFactory.create_agent(agent_config, llm)

"""
Agent工厂 - 负责创建Agent并加载完整配置
"""

import logging
from typing import Optional

from src.agents.DTO.agent_full_config import AgentFullConfig
from src.agents.base.base_agent import BaseAgent
from src.agents.base.base_llm import BaseLLM
from src.agents.impls.plan_solve_agent import PlanAndSolveAgent
from src.agents.impls.react_agent import ReActAgent
from src.agents.impls.reflection_agent import ReflectionAgent
from src.agents.impls.simple_agent import SimpleAgent
from src.infrastructure.llm.impls.llm_factory import LLMFactory

logger = logging.getLogger(__name__)


class AgentFactory:
    """Agent工厂 - 使用AgentFullConfig创建Agent"""

    def __init__(self):
        self.llm_factory = LLMFactory()

    async def create_agent(
            self,
            agent_id: str,
            agent_full_config: AgentFullConfig,
            llm: Optional[BaseLLM] = None
    ) -> BaseAgent:
        """
        创建Agent实例（传统方式，兼容性）

        Args:
            agent_id: Agent ID
            agent_full_config: Agent配置
            llm: LLM实例（可选，不提供则从配置创建）

        Returns:
            AgentFullConfig: Agent实例
        """
        # 1. 如果没有提供LLM，从配置创建
        if llm is None:
            llm = await self.llm_factory.create_llm_from_config(agent_full_config)

        # 2. 创建具体的Agent
        agent_type = agent_full_config.agent_type
        if agent_type == "simple":
            return SimpleAgent(agent_id, agent_full_config, llm)
        elif agent_type == "react":
            return ReActAgent(agent_id, agent_full_config, llm)
        elif agent_type == "plan_solve":
            return PlanAndSolveAgent(agent_id, agent_full_config, llm)
        elif agent_type == "reflection":
            return ReflectionAgent(agent_id, agent_full_config, llm)
        else:
            raise ValueError(f"不支持的Agent类型: {agent_type}")


async def create_agent(agent_id: str, agent_full_config: AgentFullConfig, llm: Optional[BaseLLM] = None) -> BaseAgent:
    """便捷函数 - 创建Agent实例"""
    factory = AgentFactory()
    return await factory.create_agent(agent_id, agent_full_config, llm)


async def create_agent_from_config(agent_full_config: AgentFullConfig, llm: Optional[BaseLLM] = None) -> BaseAgent:
    """便捷函数 - 从配置创建Agent"""
    factory = AgentFactory()
    return await factory.create_agent("default_agent", agent_full_config, llm)
