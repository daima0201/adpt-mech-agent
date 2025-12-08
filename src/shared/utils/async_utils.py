"""
异步工具
提供异步编程相关的工具函数
"""

import asyncio
import inspect
from typing import Any, Callable, Coroutine, Optional, Union
from concurrent.futures import ThreadPoolExecutor
import functools


async def run_async(
    func: Callable, 
    *args, 
    executor: Optional[ThreadPoolExecutor] = None,
    **kwargs
) -> Any:
    """
    在异步环境中运行同步函数
    
    Args:
        func: 要运行的同步函数
        args: 函数参数
        executor: 线程池执行器，如果为None则使用默认执行器
        kwargs: 函数关键字参数
        
    Returns:
        函数的返回值
    """
    loop = asyncio.get_event_loop()
    
    # 使用functools.partial包装函数和参数
    partial_func = functools.partial(func, *args, **kwargs)
    
    return await loop.run_in_executor(executor, partial_func)


def create_task_safely(coro: Coroutine, name: Optional[str] = None) -> asyncio.Task:
    """
    安全地创建异步任务，包含错误处理
    
    Args:
        coro: 协程对象
        name: 任务名称
        
    Returns:
        asyncio.Task对象
    """
    task = asyncio.create_task(coro, name=name)
    
    # 添加错误处理回调
    def handle_exception(future):
        try:
            future.result()  # 这会重新抛出异常
        except Exception as e:
            # 这里可以记录日志或进行其他错误处理
            print(f"异步任务失败: {e}")
    
    task.add_done_callback(handle_exception)
    return task


class AsyncLockManager:
    """异步锁管理器，用于管理多个异步锁"""
    
    def __init__(self):
        self._locks = {}
    
    def get_lock(self, key: str) -> asyncio.Lock:
        """获取指定key的锁"""
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()
        return self._locks[key]
    
    async def acquire(self, key: str) -> None:
        """获取锁"""
        lock = self.get_lock(key)
        await lock.acquire()
    
    def release(self, key: str) -> None:
        """释放锁"""
        if key in self._locks:
            self._locks[key].release()


class RateLimiter:
    """速率限制器，用于控制异步操作的频率"""
    
    def __init__(self, max_calls: int, period: float):
        """
        Args:
            max_calls: 时间段内最大调用次数
            period: 时间段（秒）
        """
        self.max_calls = max_calls
        self.period = period
        self.calls = []
        self.lock = asyncio.Lock()
    
    async def __aenter__(self):
        async with self.lock:
            now = asyncio.get_event_loop().time()
            
            # 移除过期的调用记录
            self.calls = [call_time for call_time in self.calls 
                         if now - call_time < self.period]
            
            # 检查是否超过限制
            if len(self.calls) >= self.max_calls:
                # 计算需要等待的时间
                oldest_call = self.calls[0]
                wait_time = self.period - (now - oldest_call)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
                    # 更新调用记录
                    self.calls = self.calls[1:]
            
            # 记录当前调用
            self.calls.append(asyncio.get_event_loop().time())
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def async_retry(max_attempts: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    异步重试装饰器
    
    Args:
        max_attempts: 最大重试次数
        delay: 初始延迟时间（秒）
        backoff: 退避因子
    """
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt == max_attempts - 1:
                        break  # 最后一次尝试，不等待
                    
                    # 等待一段时间后重试
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            
            raise last_exception
        
        return wrapper
    return decorator


class AsyncBatchProcessor:
    """异步批处理器，用于批量处理异步任务"""
    
    def __init__(self, batch_size: int = 10, max_concurrent: int = 5):
        """
        Args:
            batch_size: 每批处理的任务数量
            max_concurrent: 最大并发批次数量
        """
        self.batch_size = batch_size
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_batch(self, tasks: list, processor: Callable) -> list:
        """
        批量处理任务
        
        Args:
            tasks: 任务列表
            processor: 处理函数（异步）
            
        Returns:
            处理结果列表
        """
        results = []
        
        # 分批处理
        for i in range(0, len(tasks), self.batch_size):
            batch = tasks[i:i + self.batch_size]
            
            async with self.semaphore:
                batch_results = await asyncio.gather(
                    *[processor(task) for task in batch],
                    return_exceptions=True
                )
                results.extend(batch_results)
        
        return results


def to_async(func: Callable) -> Callable:
    """
    将同步函数转换为异步函数
    
    Args:
        func: 同步函数
        
    Returns:
        异步函数
    """
    if inspect.iscoroutinefunction(func):
        return func  # 已经是异步函数
    
    @functools.wraps(func)
    async def async_wrapper(*args, **kwargs):
        return await run_async(func, *args, **kwargs)
    
    return async_wrapper