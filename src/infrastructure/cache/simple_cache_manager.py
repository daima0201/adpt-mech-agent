"""
简化缓存管理器
为API架构提供基础的缓存功能
"""

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


class SimpleCacheManager:
    """简化缓存管理器"""

    def __init__(self):
        self._cache: dict[str, dict] = {}
        self._ttl_cache: dict[str, datetime] = {}

    async def get_config(self, namespace: str, key: str) -> Optional[dict]:
        """获取配置"""
        cache_key = f"{namespace}:{key}"

        # 检查TTL
        if cache_key in self._ttl_cache:
            if datetime.now() > self._ttl_cache[cache_key]:
                del self._cache[cache_key]
                del self._ttl_cache[cache_key]
                return None

        return self._cache.get(cache_key)

    async def set_config(
            self,
            namespace: str,
            key: str,
            value: dict,
            ttl: Optional[int] = None
    ) -> bool:
        """设置配置"""
        try:
            cache_key = f"{namespace}:{key}"
            self._cache[cache_key] = value

            if ttl:
                expire_time = datetime.now() + timedelta(seconds=ttl)
                self._ttl_cache[cache_key] = expire_time

            logger.debug(f"Config cached: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Error setting config {namespace}:{key}: {e}")
            return False

    async def delete_config(self, namespace: str, key: str) -> bool:
        """删除配置"""
        try:
            cache_key = f"{namespace}:{key}"
            if cache_key in self._cache:
                del self._cache[cache_key]
            if cache_key in self._ttl_cache:
                del self._ttl_cache[cache_key]

            logger.debug(f"Config deleted: {cache_key}")
            return True

        except Exception as e:
            logger.error(f"Error deleting config {namespace}:{key}: {e}")
            return False

    async def clear_namespace(self, namespace: str) -> bool:
        """清除命名空间下的所有配置"""
        try:
            keys_to_delete = []
            for key in self._cache.keys():
                if key.startswith(f"{namespace}:"):
                    keys_to_delete.append(key)

            for key in keys_to_delete:
                del self._cache[key]
                if key in self._ttl_cache:
                    del self._ttl_cache[key]

            logger.info(f"Namespace cleared: {namespace}")
            return True

        except Exception as e:
            logger.error(f"Error clearing namespace {namespace}: {e}")
            return False


# 全局单例
_simple_cache_manager: Optional[SimpleCacheManager] = None


def get_simple_cache_manager() -> SimpleCacheManager:
    """获取简化缓存管理器单例"""
    global _simple_cache_manager
    if _simple_cache_manager is None:
        _simple_cache_manager = SimpleCacheManager()
    return _simple_cache_manager
