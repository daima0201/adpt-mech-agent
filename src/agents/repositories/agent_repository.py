"""
智能体配置Repository - 合并相关操作
"""

import logging
from typing import Dict, Any, Optional, List

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.models.agent_config import AgentConfig
from src.agents.models.agent_profile import AgentProfile
from src.agents.models.llm_config import LLMConfig
from src.agents.prompts.prompt_template import PromptTemplate
from .base_repository import BaseRepository
from ..DTO.agent_full_config import AgentFullConfig

logger = logging.getLogger(__name__)


class AgentRepository:
    """智能体配置Repository - 一个类管理所有相关表"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.agent_repo = BaseRepository(session, AgentConfig)
        self.profile_repo = BaseRepository(session, AgentProfile)

    def set_session(self, session: AsyncSession):
        """设置数据库会话（兼容工厂模式）"""
        self.session = session
        self.agent_repo = BaseRepository(session, AgentConfig)
        self.profile_repo = BaseRepository(session, AgentProfile)

    async def get_full_agent_config(self, agent_config_id: int) -> Optional[AgentFullConfig]:
        """获取完整的Agent配置（返回DTO）"""
        try:
            # 1. 获取原始数据
            agent = await self.agent_repo.get(agent_config_id)
            if not agent:
                logger.debug(f"未找到Agent配置: {agent_config_id}")
                return None

            profile = await self.profile_repo.get_by(agent_config_id=agent_config_id)

            llm_config = None
            if agent.llm_config_id:
                llm_stmt = select(LLMConfig).where(LLMConfig.id == agent.llm_config_id)
                llm_result = await self.session.execute(llm_stmt)
                llm_config = llm_result.scalar_one_or_none()

            # 2. 获取所有模板
            prompt_templates = {}
            template_fields = [
                ("role_definition_id", "role_definition"),
                ("reasoning_framework_id", "reasoning_framework"),
                ("retrieval_strategy_id", "retrieval_strategy"),
                ("safety_policy_id", "safety_policy"),
                ("process_guide_id", "process_guide"),
            ]

            for field_id, template_key in template_fields:
                if hasattr(agent, field_id):
                    template_id = getattr(agent, field_id)
                    if template_id:
                        stmt = select(PromptTemplate).where(PromptTemplate.id == template_id)
                        result = await self.session.execute(stmt)
                        template = result.scalar_one_or_none()
                        if template:
                            prompt_templates[template_key] = template

            # 3. 创建并返回DTO
            full_config = AgentFullConfig(
                agent_config=agent,
                agent_profile=profile,
                llm_config=llm_config,
                prompt_templates=prompt_templates,
                source_db_id=agent_config_id
            )

            # 4. 验证
            full_config.validate()

            logger.debug(f"成功创建AgentFullConfig: {agent_config_id}")
            return full_config

        except Exception as e:
            logger.error(f"创建AgentFullConfig失败 {agent_config_id}: {e}", exc_info=True)
            return None

    async def create_agent_with_dependencies(
            self,
            agent_data: Dict[str, Any],
            profile_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """创建智能体及所有依赖"""
        # 1. 创建Agent配置
        agent = await self.agent_repo.create(**agent_data)

        # 2. 创建Profile
        profile_data['agent_config_id'] = agent.id
        profile = await self.profile_repo.create(**profile_data)

        logger.info(f"成功创建智能体及依赖: agent_id={agent.id}")
        return {
            "agent": agent,
            "profile": profile
        }

    async def get_by_name(self, name: str) -> Optional[AgentFullConfig]:
        """根据名称获取智能体"""
        return await self.agent_repo.get_by(name=name)

    async def get_by_type(self, agent_type: str) -> List[AgentFullConfig]:
        """根据类型获取智能体"""
        return await self.agent_repo.list(agent_type=agent_type, is_active=True)

    async def search_agent_configs(
            self,
            keyword: str = None,
            agent_type: str = None,
            is_usable: bool = True,
            limit: int = 20
    ) -> List[AgentFullConfig]:
        """搜索智能体"""
        query = select(AgentConfig)

        conditions = []
        if keyword:
            conditions.append(
                or_(
                    AgentConfig.name.ilike(f"%{keyword}%"),
                    AgentConfig.description.ilike(f"%{keyword}%")
                )
            )

        if agent_type:
            conditions.append(AgentConfig.agent_type == agent_type)

        if is_usable is not None:
            conditions.append(AgentConfig.is_usable == is_usable)

        if conditions:
            query = query.where(*conditions)

        query = query.limit(limit)

        result = await self.session.execute(query)
        return self.agent_repo.scalars_to_list(result.scalars())

    # 保留基本的CRUD操作
    async def get_agent(self, agent_id: int) -> Optional[AgentFullConfig]:
        return await self.agent_repo.get(agent_id)

    async def list_agent_configs(self, **filters) -> List[AgentConfig]:
        return await self.agent_repo.list(**filters)

    async def update_agent(self, agent_id: int, **data) -> Optional[AgentFullConfig]:
        return await self.agent_repo.update(agent_id, **data)

    async def delete_agent(self, agent_id: int) -> bool:
        return await self.agent_repo.delete(agent_id)

    async def update_agent_profile(self, agent_id: int, profile_data: Dict[str, Any]) -> Optional[AgentProfile]:
        """更新智能体profile"""
        # 查找现有的profile
        existing_profile = await self.profile_repo.get_by(agent_config_id=agent_id)
        if existing_profile:
            # 更新现有profile
            logger.debug(f"更新现有Profile: agent_id={agent_id}")
            return await self.profile_repo.update(existing_profile.id, **profile_data)
        else:
            # 创建新的profile
            logger.debug(f"创建新Profile: agent_id={agent_id}")
            profile_data['agent_config_id'] = agent_id
            return await self.profile_repo.create(**profile_data)

    async def get_agent_with_profile(self, agent_id: int) -> Dict[str, Any] | None:
        """获取智能体及其profile"""
        agent = await self.agent_repo.get(agent_id)
        if not agent:
            return None

        profile = await self.profile_repo.get_by(agent_config_id=agent_id)

        return {
            "agent": agent,
            "profile": profile
        }

    async def paginate_agent_configs(
            self,
            page: int = 1,
            page_size: int = 20,
            **filters
    ) -> Dict[str, Any]:
        """分页查询智能体"""
        return await self.agent_repo.paginate(page, page_size, **filters)

# """
# Repository使用示例
# """
#
# import asyncio
# from src.agents.repositories import (
#     agent_repository,
#     llm_repository,
#     create_repository,
#     AgentRepository,
#     LLMRepository
# )
#
#
# async def example_agent_operations():
#     """智能体操作示例"""
#
#     # 方式1：使用工厂函数（推荐）
#     async with agent_repository() as repo:
#         # 获取完整配置
#         full_config = await repo.get_full_agent_config(1)
#         print(f"智能体: {full_config.agent_config.name}")
#
#         # 搜索智能体
#         agents = await repo.search_agents(keyword="助手", agent_type="assistant")
#         print(f"找到 {len(agents)} 个助手智能体")
#
#         # 分页查询
#         result = await repo.paginate_agents(page=1, page_size=10, is_active=True)
#         print(f"第1页，共{result['total_pages']}页")
#
#     # 方式2：手动创建Repository
#     from database.db_tools import get_async_session
#
#     async with get_async_session() as session:
#         repo = AgentRepository(session)
#         agent = await repo.get_agent(1)
#         print(f"手动获取: {agent.name if agent else '未找到'}")
#
#
# async def example_llm_operations():
#     """LLM配置操作示例"""
#
#     async with llm_repository() as repo:
#         # 创建LLM配置
#         llm = await repo.create_llm_config(
#             name="GPT-4测试",
#             llm_type="openai",
#             model_name="gpt-4",
#             api_key="sk-...",
#             description="测试用GPT-4配置"
#         )
#         print(f"创建LLM配置: {llm.id}")
#
#         # 搜索LLM配置
#         llms = await repo.search_llms(keyword="GPT", llm_type="openai")
#         print(f"找到 {len(llms)} 个OpenAI配置")
#
#         # 更新配置
#         updated = await repo.update_llm_config(
#             llm.id,
#             temperature=80,
#             max_tokens=4096
#         )
#         print(f"更新后温度: {updated.temperature}")
#
#
# async def example_custom_transaction():
#     """自定义事务管理示例"""
#
#     # 手动管理事务
#     from database.db_tools import get_async_session
#
#     async with get_async_session(with_transaction=False) as session:
#         try:
#             # 开始事务
#             await session.begin()
#
#             # 创建多个Repository
#             agent_repo = AgentRepository(session)
#             llm_repo = LLMRepository(session)
#
#             # 创建LLM配置
#             llm = await llm_repo.create_llm_config(
#                 name="事务测试LLM",
#                 llm_type="openai",
#                 model_name="gpt-3.5-turbo"
#             )
#
#             # 创建智能体（关联LLM）
#             result = await agent_repo.create_agent_with_dependencies(
#                 agent_data={
#                     "name": "事务测试智能体",
#                     "agent_type": "assistant",
#                     "llm_config_id": llm.id
#                 },
#                 profile_data={
#                     "bio": "事务测试"
#                 }
#             )
#
#             # 提交事务
#             await session.commit()
#             print(f"事务提交成功，Agent ID: {result['agent'].id}")
#
#         except Exception as e:
#             # 回滚事务
#             await session.rollback()
#             print(f"事务回滚: {e}")
#             raise
#
#
# async def main():
#     """主函数"""
#     print("=== Repository架构演示 ===")
#
#     print("\n1. 智能体操作:")
#     await example_agent_operations()
#
#     print("\n2. LLM配置操作:")
#     await example_llm_operations()
#
#     print("\n3. 自定义事务:")
#     await example_custom_transaction()
#
#     print("\n=== 演示完成 ===")
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
