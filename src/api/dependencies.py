"""
依赖注入模块 - FastAPI依赖管理
提供各管理器的单例模式依赖注入
"""

import logging
from fastapi import Depends

from src.infrastructure.cache.cache_manager import UnifiedCacheManager
from src.services.agent_service import AgentService
from src.core.session.session_manager import SessionManager
from src.api.websocket.connection_manager import ConnectionManager

logger = logging.getLogger(__name__)

# 全局单例实例
_cache_manager: UnifiedCacheManager | None = None
_agent_service: AgentService | None = None
_session_manager: SessionManager | None = None
_connection_manager: ConnectionManager | None = None


def get_cache_manager() -> UnifiedCacheManager:
    """获取缓存管理器单例"""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = UnifiedCacheManager()
        logger.info("Cache manager initialized")
    return _cache_manager


async def get_agent_service() -> AgentService:
    """获取Agent服务单例"""
    global _agent_service
    if _agent_service is None:
        _agent_service = AgentService()
        await _agent_service.initialize()
        logger.info("Agent service initialized")
    return _agent_service


def get_session_manager(
    cache_manager: UnifiedCacheManager = Depends(get_cache_manager)
) -> SessionManager:
    """获取会话管理器单例"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(cache_manager)
        logger.info("Session manager initialized")
    return _session_manager


def get_connection_manager() -> ConnectionManager:
    """获取WebSocket连接管理器单例"""
    global _connection_manager
    if _connection_manager is None:
        _connection_manager = ConnectionManager()
        logger.info("Connection manager initialized")
    return _connection_manager