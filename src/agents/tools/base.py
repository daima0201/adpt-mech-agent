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
                'description': '',
                'required': param.default == param.empty
            }

            # 尝试从类型注解获取类型信息
            if param.annotation != param.empty:
                type_name = str(param.annotation)
                if 'str' in type_name:
                    param_info['type'] = 'string'
                elif 'int' in type_name or 'float' in type_name:
                    param_info['type'] = 'number'
                elif 'bool' in type_name:
                    param_info['type'] = 'boolean'
                elif 'list' in type_name or 'List' in type_name:
                    param_info['type'] = 'array'
                elif 'dict' in type_name or 'Dict' in type_name:
                    param_info['type'] = 'object'

            parameters[param_name] = param_info

        return {
            'name': self.name,
            'description': self.description,
            'parameters': parameters,
            'required': [name for name, info in parameters.items() if info['required']]
        }

    def validate_parameters(self, **kwargs) -> bool:
        """验证参数是否有效"""
        schema = self.get_schema()

        # 检查必需参数
        for required_param in schema['required']:
            if required_param not in kwargs:
                return False

        # 检查参数类型（简化验证）
        for param_name, param_value in kwargs.items():
            if param_name in schema['parameters']:
                param_type = schema['parameters'][param_name]['type']

                if param_type == 'string' and not isinstance(param_value, str):
                    return False
                elif param_type == 'number' and not isinstance(param_value, (int, float)):
                    return False
                elif param_type == 'boolean' and not isinstance(param_value, bool):
                    return False

        return True

    def record_usage(self, success: bool = True) -> None:
        """记录工具使用情况"""
        self._usage_count += 1
        if not success:
            self._error_count += 1

    def get_usage_stats(self) -> Dict[str, Any]:
        """获取使用统计"""
        total_usage = self._usage_count
        error_rate = self._error_count / total_usage if total_usage > 0 else 0

        return {
            'total_usage': total_usage,
            'error_count': self._error_count,
            'error_rate': error_rate,
            'success_rate': 1 - error_rate
        }

    def __call__(self, **kwargs) -> Any:
        """使工具可调用"""
        return self.execute(**kwargs)

    def __str__(self) -> str:
        """字符串表示"""
        return f"Tool(name='{self.name}', description='{self.description}')"


class AsyncTool(Tool):
    """异步工具基类"""

    @abstractmethod
    async def execute_async(self, **kwargs) -> Any:
        """异步执行工具操作"""
        pass

    def execute(self, **kwargs) -> Any:
        """同步执行（默认实现，子类可以重写）"""
        import asyncio
        return asyncio.run(self.execute_async(**kwargs))


class FunctionTool(Tool):
    """函数包装工具"""

    def __init__(self, func: Callable, name: Optional[str] = None,
                 description: Optional[str] = None, **kwargs):

        name = name or func.__name__
        description = description or func.__doc__ or f"Function tool: {func.__name__}"

        super().__init__(name, description, **kwargs)
        self.func = func

    def execute(self, **kwargs) -> Any:
        """执行包装的函数"""
        try:
            result = self.func(**kwargs)
            self.record_usage(success=True)
            return result
        except Exception as e:
            self.record_usage(success=False)
            raise e


class CompositeTool(Tool):
    """组合工具 - 将多个工具组合成一个"""

    def __init__(self, name: str, description: str, tools: List[Tool], **kwargs):
        super().__init__(name, description, **kwargs)
        self.tools = tools
        self.execution_order = []

    def set_execution_order(self, order: List[str]) -> None:
        """设置工具执行顺序"""
        self.execution_order = order

    def execute(self, **kwargs) -> Any:
        """按顺序执行工具"""
        results = {}

        # 确定执行顺序
        execution_list = []
        if self.execution_order:
            # 使用指定的顺序
            for tool_name in self.execution_order:
                tool = next((t for t in self.tools if t.name == tool_name), None)
                if tool:
                    execution_list.append(tool)
            # 添加未指定的工具
            for tool in self.tools:
                if tool not in execution_list:
                    execution_list.append(tool)
        else:
            # 默认顺序
            execution_list = self.tools.copy()

        # 执行工具
        for tool in execution_list:
            try:
                # 传递之前的结果作为参数
                tool_kwargs = {}
                for param_name in tool.get_schema()['parameters'].keys():
                    if param_name in kwargs:
                        tool_kwargs[param_name] = kwargs[param_name]
                    elif param_name in results:
                        tool_kwargs[param_name] = results[param_name]

                result = tool.execute(**tool_kwargs)
                results[tool.name] = result

            except Exception as e:
                results[tool.name] = f"Error: {str(e)}"

        return results

    def get_schema(self) -> Dict[str, Any]:
        """获取组合工具的模式"""

        # 合并所有子工具的参数
        all_parameters = {}
        all_required = []

        for tool in self.tools:
            tool_schema = tool.get_schema()
            all_parameters.update(tool_schema['parameters'])
            all_required.extend(tool_schema['required'])

        # 去重必需参数
        all_required = list(set(all_required))

        return {
            'name': self.name,
            'description': self.description,
            'parameters': all_parameters,
            'required': all_required,
            'sub_tools': [tool.name for tool in self.tools]
        }
