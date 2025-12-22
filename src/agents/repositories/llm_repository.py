"""
LLM配置Repository
"""

from typing import Optional, List, Dict, Any

from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.repositories.models.llm_config import LLMConfig
from .base_repository import BaseRepository


class LLMRepository:
    """LLM配置Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.base_repo = BaseRepository(session, LLMConfig)

    def set_session(self, session: AsyncSession):
        """设置数据库会话（兼容工厂模式）"""
        self.session = session
        self.base_repo = BaseRepository(session, LLMConfig)

    async def get_by_name(self, name: str) -> Optional[LLMConfig]:
        """根据名称获取LLM配置"""
        return await self.base_repo.get_by(name=name)

    async def list_usable_llm_configs(self) -> List[LLMConfig]:
        """获取所有可用的LLM配置"""
        return await self.base_repo.list(is_usable=True)

    async def get_by_type(self, llm_type: str) -> List[LLMConfig]:
        """根据类型获取LLM配置"""
        return await self.base_repo.list(llm_type=llm_type, is_active=True)

    async def search_llm_configs(
            self,
            keyword: str = None,
            llm_type: str = None,
            is_usable: bool = True,
            limit: int = 20
    ) -> List[LLMConfig]:
        """搜索LLM配置"""
        query = select(LLMConfig)

        conditions = []
        if keyword:
            conditions.append(
                or_(
                    LLMConfig.name.ilike(f"%{keyword}%"),
                    LLMConfig.model_name.ilike(f"%{keyword}%"),
                    LLMConfig.description.ilike(f"%{keyword}%")
                )
            )

        if llm_type:
            conditions.append(LLMConfig.llm_type == llm_type)

        if is_usable is not None:
            conditions.append(LLMConfig.is_usable == is_usable)

        if conditions:
            query = query.where(*conditions)

        query = query.limit(limit)

        result = await self.session.execute(query)
        return self.base_repo.scalars_to_list(result.scalars())

    async def create_llm_config(
            self,
            name: str,
            llm_type: str,
            model_name: str,
            api_key: str = None,
            base_url: str = None,
            temperature: int = 70,
            max_tokens: int = 2048,
            timeout: int = 30,
            max_retries: int = 3,
            description: str = None,
            **extra_fields
    ) -> LLMConfig:
        """创建LLM配置"""
        data = {
            'name': name,
            'llm_type': llm_type,
            'model_name': model_name,
            'api_key': api_key,
            'base_url': base_url,
            'temperature': temperature,
            'max_tokens': max_tokens,
            'timeout': timeout,
            'max_retries': max_retries,
            'description': description,
            **extra_fields
        }
        return await self.base_repo.create(**data)

    async def update_llm_config(
            self,
            llm_id: int,
            **data
    ) -> Optional[LLMConfig]:
        """更新LLM配置"""
        # 检查是否有敏感信息需要特殊处理
        if 'api_key' in data and data['api_key'] is None:
            # 如果api_key为None，不更新该字段（保持原值）
            del data['api_key']

        return await self.base_repo.update(llm_id, **data)

    # 保留基本的CRUD操作
    async def get(self, id: int) -> Optional[LLMConfig]:
        return await self.base_repo.get(id)

    async def list_all(self) -> List[LLMConfig]:
        return await self.base_repo.list()

    async def update(self, id: int, **data) -> Optional[LLMConfig]:
        return await self.base_repo.update(id, **data)

    async def delete(self, id: int) -> bool:
        return await self.base_repo.delete(id)

    async def paginate_llm_configs(
            self,
            page: int = 1,
            page_size: int = 20,
            **filters
    ) -> Dict[str, Any]:
        """分页查询LLM配置"""
        return await self.base_repo.paginate(page, page_size, **filters)
