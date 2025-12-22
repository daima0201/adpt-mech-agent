"""
Repository工厂模块
提供统一的Repository创建和管理
"""

from contextlib import asynccontextmanager
from typing import AsyncGenerator, Type, TypeVar, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession

from ...shared.utils.db_utils import get_async_session

T = TypeVar('T')


class RepositoryFactory:
    """Repository工厂类"""

    def __init__(self):
        self._repositories: Dict[Type, Any] = {}

    @asynccontextmanager
    async def create(
            self,
            repo_class: Type[T],
            *args,
            with_transaction: bool = True,
            **kwargs
    ) -> AsyncGenerator[T, None]:
        """创建Repository实例（使用上下文管理器）

        Args:
            repo_class: Repository类
            with_transaction: 是否自动管理事务
            *args, **kwargs: 传递给Repository的参数
        """
        async with self.session_manager.get_session(with_transaction) as session:
            # 检查Repository是否接受session参数
            repo = self._instantiate_repository(repo_class, session, *args, **kwargs)

            try:
                yield repo
            finally:
                # 清理Repository持有的session引用
                self._cleanup_repository(repo)

    def _instantiate_repository(self, repo_class: Type[T], session: AsyncSession, *args, **kwargs) -> T:
        """实例化Repository"""
        import inspect

        # 检查构造函数参数
        sig = inspect.signature(repo_class.__init__)
        params = sig.parameters

        if 'session' in params:
            # 如果构造函数接受session参数
            return repo_class(session=session, *args, **kwargs)
        else:
            # 尝试使用set_session方法
            repo = repo_class(*args, **kwargs)
            if hasattr(repo, 'set_session'):
                repo.set_session(session)
                return repo
            else:
                # 尝试将session作为第一个位置参数
                try:
                    return repo_class(session, *args, **kwargs)
                except:
                    raise ValueError(f"Repository {repo_class.__name__} 无法接受session参数")

    def _cleanup_repository(self, repo: T) -> None:
        """清理Repository资源"""
        # 清除session引用
        if hasattr(repo, 'session'):
            repo.session = None

        # 清除子Repository的引用
        for attr_name in dir(repo):
            if attr_name.endswith('_repo'):
                attr = getattr(repo, attr_name)
                if hasattr(attr, 'session'):
                    attr.session = None

    def register_repository(self, repo_type: Type, factory_func: callable):
        """注册Repository工厂函数"""
        self._repositories[repo_type] = factory_func

    async def get_registered(self, repo_type: Type, *args, **kwargs):
        """获取已注册的Repository"""
        if repo_type not in self._repositories:
            raise KeyError(f"Repository类型 {repo_type.__name__} 未注册")

        factory_func = self._repositories[repo_type]
        return await factory_func(*args, **kwargs)


# 全局工厂实例
_factory = RepositoryFactory()


def get_repository_factory() -> RepositoryFactory:
    """获取Repository工厂实例"""
    return _factory


# 特定Repository的工厂函数
@asynccontextmanager
async def agent_repository(*args, **kwargs) -> AsyncGenerator:
    """AgentRepository工厂函数"""
    from .agent_repository import AgentRepository

    factory = get_repository_factory()
    async with factory.create(AgentRepository, *args, **kwargs) as repo:
        yield repo


@asynccontextmanager
async def llm_repository(*args, **kwargs) -> AsyncGenerator:
    """LLMRepository工厂函数"""
    from .llm_repository import LLMRepository

    factory = get_repository_factory()
    async with factory.create(LLMRepository, *args, **kwargs) as repo:
        yield repo


# 快捷函数
async def create_repository(repo_class: Type[T], *args, **kwargs) -> T:
    """创建Repository（需要手动管理会话）"""
    async with get_async_session() as session:
        factory = get_repository_factory()
        return factory._instantiate_repository(repo_class, session, *args, **kwargs)


# 导出常用工厂函数
__all__ = [
    'get_repository_factory',
    'agent_repository',
    'llm_repository',
    'create_repository',
]
