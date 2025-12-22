"""
工具系统基础类定义
提供工具接口和抽象基类
"""

import inspect
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, List, Callable


class Tool(ABC):
    """工具基类"""

    def __init__(self, name: str, description: str, **kwargs):
        self.name = name
        self.description = description
        self.config = kwargs
        self._usage_count = 0
        self._error_count = 0

    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """执行工具操作"""
        pass

    def get_schema(self) -> Dict[str, Any]:
        """获取工具模式定义"""

        # 分析execute方法的参数签名
        sig = inspect.signature(self.execute)
        parameters = {}

        for param_name, param in sig.parameters.items():
            if param_name == 'self':
                continue

            param_info = {
                'type': 'string',  # 默认类型
                'description': f"参数 {param_name}"
            }

            # 根据参数默认值推断类型
            if param.default != inspect.Parameter.empty:
                if isinstance(param.default, bool):
                    param_info['type'] = 'boolean'
                elif isinstance(param.default, int):
                    param_info['type'] = 'integer'
                elif isinstance(param.default, float):
                    param_info['type'] = 'number'

            parameters[param_name] = param_info

        return {
            'name': self.name,
            'description': self.description,
            'parameters': parameters
        }

    def record_usage(self, success: bool = True):
        """记录工具使用情况"""
        self._usage_count += 1
        if not success:
            self._error_count += 1

    def get_stats(self) -> Dict[str, int]:
        """获取工具统计信息"""
        return {
            'usage_count': self._usage_count,
            'error_count': self._error_count,
            'success_rate': (self._usage_count - self._error_count) / max(1, self._usage_count)
        }


class AsyncTool(Tool):
    """异步工具基类"""

    @abstractmethod
    async def execute(self, **kwargs) -> Any:
        """异步执行工具操作"""
        pass