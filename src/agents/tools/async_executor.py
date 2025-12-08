"""
异步工具执行器
提供高性能的异步工具执行能力
"""

import asyncio
import time
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from dataclasses import dataclass
from enum import Enum
from src.agents.tools.base import Tool, AsyncTool
from src.agents.tools.registry import ToolRegistry


class ExecutionMode(Enum):
    """执行模式"""
    ASYNC = "async"        # 异步执行（默认）
    THREAD = "thread"      # 线程池执行
    PROCESS = "process"    # 进程池执行


@dataclass
class ExecutionConfig:
    """执行配置"""
    mode: ExecutionMode = ExecutionMode.ASYNC
    timeout: Optional[int] = None
    max_workers: int = 10
    retry_count: int = 0
    retry_delay: float = 1.0


@dataclass
class ExecutionResult:
    """执行结果"""
    success: bool
    result: Optional[Any] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    attempts: int = 1
    metadata: Optional[Dict[str, Any]] = None


class AsyncToolExecutor:
    """异步工具执行器"""
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        self.registry = registry or ToolRegistry()
        self._thread_pool = ThreadPoolExecutor(max_workers=10)
        self._process_pool = ProcessPoolExecutor(max_workers=4)
        self._execution_stats: Dict[str, Dict[str, Any]] = {}


    async def execute_tool(self, tool_name: str, parameters: Dict[str, Any],
                          config: Optional[ExecutionConfig] = None) -> ExecutionResult:
        """执行单个工具"""
        
        if config is None:
            config = ExecutionConfig()
        
        start_time = time.time()
        
        # 获取工具
        tool = self.registry.get_tool(tool_name)
        if not tool:
            return ExecutionResult(
                success=False,
                error=f"工具 '{tool_name}' 未找到",
                execution_time=time.time() - start_time
            )
        
        # 执行工具（支持重试）
        for attempt in range(config.retry_count + 1):
            try:
                result = await self._execute_with_mode(tool, parameters, config)
                
                # 记录执行统计
                self._record_execution_stat(tool_name, True, time.time() - start_time)
                
                return ExecutionResult(
                    success=True,
                    result=result,
                    execution_time=time.time() - start_time,
                    attempts=attempt + 1,
                    metadata={'tool_name': tool_name, 'mode': config.mode.value}
                )
            
            except Exception as e:
                if attempt == config.retry_count:
                    # 记录失败统计
                    self._record_execution_stat(tool_name, False, time.time() - start_time)
                    
                    return ExecutionResult(
                        success=False,
                        error=str(e),
                        execution_time=time.time() - start_time,
                        attempts=attempt + 1,
                        metadata={'tool_name': tool_name, 'mode': config.mode.value}
                    )
                
                # 重试前等待
                if config.retry_delay > 0:
                    await asyncio.sleep(config.retry_delay)
    
    async def _execute_with_mode(self, tool: Union[Tool, AsyncTool],
                                parameters: Dict[str, Any],
                                config: ExecutionConfig) -> Any:
        """根据模式执行工具"""
        
        if config.mode == ExecutionMode.ASYNC:
            return await self._execute_async(tool, parameters, config)
        elif config.mode == ExecutionMode.THREAD:
            return await self._execute_thread(tool, parameters, config)
        elif config.mode == ExecutionMode.PROCESS:
            return await self._execute_process(tool, parameters, config)
        else:
            raise ValueError(f"不支持的执行模式: {config.mode}")
    
    async def _execute_async(self, tool: Union[Tool, AsyncTool],
                            parameters: Dict[str, Any],
                            config: ExecutionConfig) -> Any:
        """异步执行"""
        
        if isinstance(tool, AsyncTool):
            # 原生异步工具
            if config.timeout:
                return await asyncio.wait_for(
                    tool.execute(**parameters),
                    timeout=config.timeout
                )
            else:
                return await tool.execute(**parameters)
        else:
            # 同步工具包装为异步
            loop = asyncio.get_event_loop()
            
            if config.timeout:
                return await asyncio.wait_for(
                    loop.run_in_executor(None, lambda: tool.execute(**parameters)),
                    timeout=config.timeout
                )
            else:
                return await loop.run_in_executor(
                    None, lambda: tool.execute(**parameters)
                )
    
    async def _execute_thread(self, tool: Union[Tool, AsyncTool],
                             parameters: Dict[str, Any],
                             config: ExecutionConfig) -> Any:
        """线程池执行"""
        
        loop = asyncio.get_event_loop()
        
        def sync_wrapper():
            if isinstance(tool, AsyncTool):
                # 异步工具在同步环境中执行
                return asyncio.run(tool.execute(**parameters))
            else:
                return tool.execute(**parameters)
        
        if config.timeout:
            return await asyncio.wait_for(
                loop.run_in_executor(self._thread_pool, sync_wrapper),
                timeout=config.timeout
            )
        else:
            return await loop.run_in_executor(
                self._thread_pool, sync_wrapper
            )
    
    async def _execute_process(self, tool: Union[Tool, AsyncTool],
                              parameters: Dict[str, Any],
                              config: ExecutionConfig) -> Any:
        """进程池执行"""
        
        # 注意：进程池执行有序列化限制
        # 工具和参数必须可序列化
        
        loop = asyncio.get_event_loop()
        
        def process_wrapper():
            # 在子进程中重新初始化工具
            # 这里需要确保工具可以在子进程中正确初始化
            if hasattr(tool, '__class__'):
                # 尝试重新实例化工具
                tool_class = tool.__class__
                new_tool = tool_class()
                return new_tool.execute(**parameters)
            else:
                raise RuntimeError("工具无法在子进程中执行")
        
        if config.timeout:
            return await asyncio.wait_for(
                loop.run_in_executor(self._process_pool, process_wrapper),
                timeout=config.timeout
            )
        else:
            return await loop.run_in_executor(
                self._process_pool, process_wrapper
            )
    
    async def execute_batch(self, tasks: List[Dict[str, Any]],
                           config: Optional[ExecutionConfig] = None) -> List[ExecutionResult]:
        """批量执行工具"""
        
        if config is None:
            config = ExecutionConfig()
        
        # 创建任务列表
        async_tasks = []
        for task in tasks:
            tool_name = task.get('tool_name')
            parameters = task.get('parameters', {})
            
            async_tasks.append(
                self.execute_tool(tool_name, parameters, config)
            )
        
        # 并行执行
        results = await asyncio.gather(*async_tasks, return_exceptions=True)
        
        # 处理异常结果
        final_results = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                final_results.append(ExecutionResult(
                    success=False,
                    error=str(result),
                    metadata={'task_index': i}
                ))
            else:
                final_results.append(result)
        
        return final_results
    
    async def execute_stream(self, tool_name: str, parameters: Dict[str, Any],
                            config: Optional[ExecutionConfig] = None) -> AsyncGenerator[Any, None]:
        """流式执行工具"""
        
        if config is None:
            config = ExecutionConfig()
        
        tool = self.registry.get_tool(tool_name)
        if not tool:
            yield ExecutionResult(
                success=False,
                error=f"工具 '{tool_name}' 未找到"
            )
            return
        
        # 检查工具是否支持流式输出
        if hasattr(tool, 'execute_stream') and callable(getattr(tool, 'execute_stream')):
            # 流式执行
            try:
                async for chunk in tool.execute_stream(**parameters):
                    yield chunk
            except Exception as e:
                yield ExecutionResult(
                    success=False,
                    error=str(e)
                )
        else:
            # 普通执行，返回单个结果
            result = await self.execute_tool(tool_name, parameters, config)
            yield result
    
    def _record_execution_stat(self, tool_name: str, success: bool, execution_time: float):
        """记录执行统计"""
        
        if tool_name not in self._execution_stats:
            self._execution_stats[tool_name] = {
                'total_executions': 0,
                'successful_executions': 0,
                'failed_executions': 0,
                'total_execution_time': 0.0,
                'average_execution_time': 0.0
            }
        
        stats = self._execution_stats[tool_name]
        stats['total_executions'] += 1
        stats['total_execution_time'] += execution_time
        
        if success:
            stats['successful_executions'] += 1
        else:
            stats['failed_executions'] += 1
        
        stats['average_execution_time'] = (
            stats['total_execution_time'] / stats['total_executions']
        )
    
    def get_execution_stats(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """获取执行统计"""
        
        if tool_name:
            return self._execution_stats.get(tool_name, {})
        else:
            return self._execution_stats.copy()
    
    def clear_stats(self) -> None:
        """清空统计信息"""
        self._execution_stats.clear()
    
    def optimize_config(self, tool_name: str) -> ExecutionConfig:
        """根据历史数据优化执行配置"""
        
        stats = self._execution_stats.get(tool_name)
        if not stats:
            return ExecutionConfig()
        
        avg_time = stats.get('average_execution_time', 0)
        success_rate = stats.get('successful_executions', 0) / max(stats.get('total_executions', 1), 1)
        
        # 根据平均执行时间设置超时
        timeout = max(int(avg_time * 3), 30)  # 3倍平均时间，最小30秒
        
        # 根据成功率设置重试次数
        if success_rate < 0.8:
            retry_count = 2
        elif success_rate < 0.95:
            retry_count = 1
        else:
            retry_count = 0
        
        return ExecutionConfig(
            timeout=timeout,
            retry_count=retry_count,
            retry_delay=1.0
        )
    
    async def close(self):
        """关闭执行器，释放资源"""
        self._thread_pool.shutdown(wait=True)
        self._process_pool.shutdown(wait=True)


# 全局异步执行器实例
_global_executor = AsyncToolExecutor()


def get_async_executor() -> AsyncToolExecutor:
    """获取全局异步执行器"""
    return _global_executor


async def execute_tool(tool_name: str, parameters: Dict[str, Any],
                      config: Optional[ExecutionConfig] = None) -> ExecutionResult:
    """便捷函数：执行工具"""
    return await _global_executor.execute_tool(tool_name, parameters, config)


async def execute_batch(tasks: List[Dict[str, Any]],
                       config: Optional[ExecutionConfig] = None) -> List[ExecutionResult]:
    """便捷函数：批量执行工具"""
    return await _global_executor.execute_batch(tasks, config)


async def execute_stream(tool_name: str, parameters: Dict[str, Any],
                        config: Optional[ExecutionConfig] = None) -> AsyncGenerator[Any, None]:
    """便捷函数：流式执行工具"""
    async for result in _global_executor.execute_stream(tool_name, parameters, config):
        yield result


def get_execution_stats(tool_name: Optional[str] = None) -> Dict[str, Any]:
    """便捷函数：获取执行统计"""
    return _global_executor.get_execution_stats(tool_name)


async def close_executor():
    """便捷函数：关闭执行器"""
    await _global_executor.close()