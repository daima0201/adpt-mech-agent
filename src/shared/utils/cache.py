"""
缓存工具
提供内存缓存功能，支持LRU策略
"""

import time
from typing import Any, Dict, Optional, Callable
from collections import OrderedDict
import asyncio


class LRUCache:
    """LRU（最近最少使用）缓存实现"""
    
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
        """
        设置缓存值
        
        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），如果为None则使用默认值
        """
        # 如果缓存已满，移除最旧的项
        if len(self._cache) >= self.max_size and key not in self._cache:
            self._evict_oldest()
        
        # 设置缓存值和过期时间
        self._cache[key] = value
        self._cache.move_to_end(key)  # 标记为最近使用
        
        expiry_time = time.time() + (ttl or self.default_ttl)
        self._expiry_times[key] = expiry_time
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        获取缓存值
        
        Args:
            key: 缓存键
            default: 默认值
            
        Returns:
            缓存值，如果不存在或已过期则返回默认值
        """
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
        """
        删除缓存项
        
        Args:
            key: 缓存键
            
        Returns:
            是否成功删除
        """
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


class CacheManager:
    """缓存管理器，管理多个缓存实例"""
    
    def __init__(self):
        self._caches: Dict[str, LRUCache] = {}
        self._default_config = {
            'max_size': 1000,
            'default_ttl': 3600
        }
    
    def get_cache(self, name: str, **kwargs) -> LRUCache:
        """
        获取指定名称的缓存实例
        
        Args:
            name: 缓存名称
            kwargs: 缓存配置参数
            
        Returns:
            LRUCache实例
        """
        if name not in self._caches:
            config = self._default_config.copy()
            config.update(kwargs)
            self._caches[name] = LRUCache(**config)
        
        return self._caches[name]
    
    def set_default_config(self, max_size: int = None, default_ttl: int = None) -> None:
        """设置默认缓存配置"""
        if max_size is not None:
            self._default_config['max_size'] = max_size
        if default_ttl is not None:
            self._default_config['default_ttl'] = default_ttl
    
    def clear_cache(self, name: str = None) -> None:
        """清空缓存"""
        if name:
            if name in self._caches:
                self._caches[name].clear()
        else:
            for cache in self._caches.values():
                cache.clear()
    
    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """获取所有缓存的统计信息"""
        stats = {}
        for name, cache in self._caches.items():
            stats[name] = {
                'size': cache.size(),
                'max_size': cache.max_size,
                'keys': cache.keys()[:10]  # 只显示前10个键
            }
        return stats


def cached(
    max_size: int = 1000, 
    ttl: int = 3600, 
    key_func: Optional[Callable] = None
):
    """
    缓存装饰器，用于缓存函数结果
    
    Args:
        max_size: 缓存大小
        ttl: 过期时间（秒）
        key_func: 自定义缓存键生成函数
    """
    def decorator(func):
        cache = LRUCache(max_size=max_size, default_ttl=ttl)
        
        def make_key(*args, **kwargs):
            """生成缓存键"""
            if key_func:
                return key_func(*args, **kwargs)
            
            # 默认键生成逻辑
            key_parts = [func.__name__]
            
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
                cached_result = cache.get(key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = await func(*args, **kwargs)
                cache.set(key, result, ttl)
                return result
            
            return async_wrapper
        
        else:
            # 同步函数版本
            @functools.wraps(func)
            def sync_wrapper(*args, **kwargs):
                key = make_key(*args, **kwargs)
                
                # 检查缓存
                cached_result = cache.get(key)
                if cached_result is not None:
                    return cached_result
                
                # 执行函数并缓存结果
                result = func(*args, **kwargs)
                cache.set(key, result, ttl)
                return result
            
            return sync_wrapper
    
    return decorator