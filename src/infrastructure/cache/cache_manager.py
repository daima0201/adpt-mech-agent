"""
统一缓存管理器
结合内存缓存和Redis持久化，支持多级缓存策略
"""

import asyncio
import fnmatch
import json
import logging
import time
from collections import OrderedDict
from decimal import Decimal
from typing import Any, Optional, Dict, Callable

from src.shared.utils.redis_utils import get_redis_client

logger = logging.getLogger(__name__)


class CustomJSONEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理Decimal等特殊类型"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            # 将Decimal转换为float进行序列化
            return float(obj)
        elif hasattr(obj, '__dict__'):
            # 处理对象序列化
            return obj.__dict__
        elif isinstance(obj, (set, frozenset)):
            # 将集合转换为列表
            return list(obj)

        # 让基类处理其他类型
        return super().default(obj)


class LRUCacheManager:
    """LRU（最近最少使用）内存缓存实现"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 3600):
        """
        Args:
            max_size: 最大缓存项数量
            default_ttl: 默认过期时间（秒）
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache = OrderedDict()
        self._expiry_times = {}

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """设置缓存值"""
        # 如果缓存已满，移除最旧的项
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_oldest()

        # 设置缓存值和过期时间
        self._cache[key] = value
        self._cache.move_to_end(key)  # 标记为最近使用

        expiry_time = time.time() + (ttl or self.default_ttl)
        self._expiry_times[key] = expiry_time

    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        # 检查是否存在
        if key not in self._cache:
            return default

        # 检查是否过期
        if self._is_expired(key):
            self.delete(key)
            return default

        # 标记为最近使用
        self._cache.move_to_end(key)
        return self._cache[key]

    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
            del self._expiry_times[key]
            return True
        return False

    def exists(self, key: str) -> bool:
        """检查缓存项是否存在且未过期"""
        if key not in self._cache:
            return False

        if self._is_expired(key):
            self.delete(key)
            return False

        return True

    def clear(self) -> None:
        """清空所有缓存"""
        self._cache.clear()
        self._expiry_times.clear()

    def size(self) -> int:
        """获取当前缓存大小"""
        # 清理过期项
        self._clean_expired()
        return len(self._cache)

    def keys(self) -> list:
        """获取所有有效的缓存键"""
        self._clean_expired()
        return list(self._cache.keys())

    def _is_expired(self, key: str) -> bool:
        """检查缓存项是否过期"""
        if key not in self._expiry_times:
            return True

        return time.time() > self._expiry_times[key]

    def _evict_oldest(self) -> None:
        """移除最旧的缓存项"""
        if self._cache:
            oldest_key = next(iter(self._cache))
            self.delete(oldest_key)

    def _clean_expired(self) -> None:
        """清理所有过期的缓存项"""
        expired_keys = [key for key in self._cache if self._is_expired(key)]
        for key in expired_keys:
            self.delete(key)

    def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存项"""
        # 获取所有有效的键
        valid_keys = self.keys()

        # 使用fnmatch进行模式匹配
        matched_keys = [key for key in valid_keys if fnmatch.fnmatch(key, pattern)]

        # 删除匹配的键
        deleted_count = 0
        for key in matched_keys:
            if self.delete(key):
                deleted_count += 1

        return deleted_count

    def get_pattern(self, pattern) -> Dict[str, Any]:
        """获得匹配模式的缓存项"""
        # 获取所有有效的键
        valid_keys = self.keys()
        get_obj = OrderedDict()

        # 使用fnmatch进行模式匹配
        matched_keys = [key for key in valid_keys if fnmatch.fnmatch(key, pattern)]
        for key in matched_keys:
            get_obj[key] = self.get(key)
            get_obj.move_to_end(key)
        return get_obj


class RedisCacheManager:
    """Redis持久化缓存实现"""

    def __init__(self, redis_client):
        self.redis = redis_client

    async def set(self, key: str, value: Any, ttl: int = 300) -> bool:
        """设置缓存值"""
        try:
            serialized = json.dumps(value, ensure_ascii=False, cls=CustomJSONEncoder)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            print(f"❌ Redis缓存设置失败: {e}")
            return False

    async def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
        except Exception:
            pass
        return None

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        try:
            await self.redis.delete(key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        try:
            return await self.redis.exists(key) > 0
        except Exception:
            return False

    async def keys(self, pattern: str = '*') -> list:
        """获取匹配模式的缓存键列表"""
        try:
            return await self.redis.keys(pattern)
        except Exception:
            return []

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存"""
        try:
            keys = await self.redis.keys(pattern)
            if keys:
                await self.redis.delete(*keys)
                return len(keys)
        except Exception:
            pass
        return 0

    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """获取匹配模式的缓存项"""
        try:
            # 确保模式包含通配符
            if '*' not in pattern and '?' not in pattern:
                pattern = f"{pattern}*"

            keys = await self.redis.keys(pattern)
            result = {}
            for key in keys:
                value = await self.get(key)
                if value is not None:
                    result[key.decode('utf-8') if isinstance(key, bytes) else key] = value
            return result
        except Exception:
            return {}


class UnifiedCacheManager:
    """统一缓存管理器 - 支持多级缓存策略"""

    def __init__(self, enable_redis: bool = True):
        """
        Args:
            enable_redis: 是否启用Redis持久化缓存
        """
        self.enable_redis = enable_redis
        self.memory_cache = LRUCacheManager(max_size=1000, default_ttl=3600)
        self._redis_initialized = asyncio.Event()  # 新增：Redis初始化完成标志

        if enable_redis:
            # 这里只是标记需要初始化，但不立即执行
            self._need_redis_init = True
        else:
            self._need_redis_init = False
            self._redis_initialized.set()  # 如果不需要Redis，直接标记为已初始化
            self.redis_cache = None

    async def ensure_redis_initialized(self):
        """确保Redis已初始化"""
        if not self._need_redis_init:
            return

        if not self._redis_initialized.is_set():
            await self._async_init_redis()

    async def _async_init_redis(self):
        """异步初始化Redis"""
        try:
            redis_client = await get_redis_client()
            self.redis_cache = RedisCacheManager(redis_client)
            print("✅ Redis缓存初始化成功")
            self._redis_initialized.set()  # 设置初始化完成标志
            self._need_redis_init = False
        except Exception as e:
            print(f"❌ Redis缓存初始化失败: {e}")
            self.enable_redis = False
            self._redis_initialized.set()  # 即使失败也要设置，防止无限等待

    async def set(self, key: str, value: Any, ttl: int = 3600,
                  persist_to_redis: bool = True) -> bool:
        """
        设置缓存值
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒）
            persist_to_redis: 是否持久化到Redis
        """
        # 先设置内存缓存
        self.memory_cache.set(key, value, ttl)

        # 如果需要持久化且Redis可用，则设置Redis缓存
        if persist_to_redis and self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            return await self.redis_cache.set(key, value, ttl)

        return True

    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值 - 多级缓存策略
        1. 先检查内存缓存
        2. 如果内存缓存不存在且Redis可用，检查Redis缓存
        3. 如果Redis中存在，将其加载到内存缓存中
        """
        # 先检查内存缓存
        result = self.memory_cache.get(key)
        if result is not None:
            return result

        # 如果内存缓存不存在且Redis可用，检查Redis缓存
        if self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            redis_result = await self.redis_cache.get(key)
            if redis_result is not None:
                # 将Redis中的结果加载到内存缓存
                self.memory_cache.set(key, redis_result, ttl=3600)
                return redis_result

        return default

    async def delete(self, key: str) -> bool:
        """删除缓存值"""
        # 删除内存缓存
        memory_result = self.memory_cache.delete(key)

        # 删除Redis缓存
        redis_result = True
        if self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            redis_result = await self.redis_cache.delete(key)

        return memory_result and redis_result

    async def exists(self, key: str) -> bool:
        """检查键是否存在"""
        # 检查内存缓存
        if self.memory_cache.exists(key):
            return True

        # 检查Redis缓存
        if self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            return await self.redis_cache.exists(key)

        return False

    def get_memory_stats(self) -> Dict[str, Any]:
        """获取内存缓存统计信息"""
        return {
            'size': self.memory_cache.size(),
            'max_size': self.memory_cache.max_size,
            'keys_count': len(self.memory_cache.keys()),
            'keys_sample': self.memory_cache.keys()[:5]  # 显示前5个键作为示例
        }

    async def clear_memory_cache(self) -> None:
        """清空内存缓存"""
        self.memory_cache.clear()

    async def clear_redis_cache(self, pattern: str = '*') -> int:
        """清空Redis缓存"""
        if self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            return await self.redis_cache.clear_pattern(pattern)
        return 0

    async def clear_pattern(self, pattern: str) -> int:
        """清除匹配模式的缓存（多级缓存）"""
        total_deleted = 0

        # 清理内存缓存中的匹配项
        memory_deleted = self.memory_cache.clear_pattern(pattern)
        total_deleted += memory_deleted

        # 清理Redis缓存中的匹配项
        redis_deleted = await self.clear_redis_cache(pattern)
        total_deleted += redis_deleted

        return total_deleted

    async def get_pattern(self, pattern: str) -> Dict[str, Any]:
        """获取匹配模式的缓存（多级缓存）"""
        result = {}

        # 获取内存缓存中的匹配项
        memory_result = self.memory_cache.get_pattern(pattern)
        result.update(memory_result)

        # 获取Redis缓存中的匹配项
        if self.enable_redis:
            if self._need_redis_init:
                await self.ensure_redis_initialized()  # 确保Redis已初始化
            redis_result = await self.redis_cache.get_pattern(pattern)
            result.update(redis_result)

        return result

    async def clear_all(self) -> None:
        """清空所有缓存"""
        await self.clear_memory_cache()
        await self.clear_redis_cache()

    # 新增：专门用于缓存配置的方法
    async def set_config(self, config_type: str, key: str, config_data: Any, ttl: int = 3600):
        """缓存配置数据"""
        cache_key = f"{config_type}:config:{key}"
        return await self.set(cache_key, config_data, ttl)

    async def get_config(self, config_type: str, key: str):
        """获取缓存的配置数据"""
        cache_key = f"{config_type}:config:{key}"
        return await self.get(cache_key)

    async def delete_config(self, config_type: str, key: str):
        """删除缓存的配置数据"""
        cache_key = f"{config_type}:config:{key}"
        await self.delete(cache_key)

    async def get_all_config(self, config_type: str, key: str) -> Dict[str, Any]:
        """获取全部缓存的配置数据"""
        # 如果key是通配符，直接使用；否则添加通配符
        if '*' not in key and '?' not in key:
            cache_key = f"{config_type}:config:{key}*"
        else:
            cache_key = f"{config_type}:config:{key}"

        logger.debug(f"Searching for cache keys with pattern: {cache_key}")
        result = await self.get_pattern(cache_key)
        logger.debug(f"Found {len(result)} cache entries")
        return result


# 全局缓存管理器实例
_global_cache_manager = UnifiedCacheManager(True)


def get_cache_manager() -> UnifiedCacheManager:
    """获取全局缓存管理器实例"""
    return _global_cache_manager


def cached(
        max_size: int = 1000,
        ttl: int = 3600,
        key_func: Optional[Callable] = None,
        use_redis: bool = True
):
    """
    缓存装饰器，支持多级缓存
    
    Args:
        max_size: 内存缓存大小
        ttl: 过期时间（秒）
        key_func: 自定义缓存键生成函数
        use_redis: 是否使用Redis持久化
    """
    import functools

    def decorator(func):
        cache_manager = get_cache_manager()

        def make_key(*args, **kwargs):
            """生成缓存键"""
            if key_func:
                return key_func(*args, **kwargs)

            # 默认键生成逻辑
            key_parts = [func.__module__, func.__name__]

            # 处理位置参数
            for arg in args:
                key_parts.append(str(arg))

            # 处理关键字参数
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}={v}")

            return "|".join(key_parts)

        if asyncio.iscoroutinefunction(func):
            # 异步函数版本
            @functools.wraps(func)
            async def async_wrapper(*args, **kwargs):
                key = make_key(*args, **kwargs)

                # 检查缓存
                cached_result = await cache_manager.get(key)
                if cached_result is not None:
                    return cached_result

                # 执行函数并缓存结果
                result = await func(*args, **kwargs)
                await cache_manager.set(key, result, ttl, persist_to_redis=use_redis)
                return result

            return async_wrapper

        else:
            # 同步函数版本
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = make_key(*args, **kwargs)

                # 检查缓存
                cached_result = cache_manager.memory_cache.get(key)
                if cached_result is not None:
                    return cached_result

                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                cache_manager.memory_cache.set(key, result, ttl)

                # 异步持久化到Redis
                if use_redis and cache_manager.enable_redis:
                    asyncio.create_task(
                        cache_manager.set(key, result, ttl, persist_to_redis=True)
                    )

                return result

            return sync_wrapper

    return decorator
