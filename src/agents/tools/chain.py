"""
工具链管理系统
提供工具组合、编排和执行功能
"""

import asyncio
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from enum import Enum
from src.agents.tools.base import Tool, AsyncTool
from src.agents.tools.registry import ToolRegistry


class ChainExecutionMode(Enum):
    """工具链执行模式"""
    SEQUENTIAL = "sequential"  # 顺序执行
    PARALLEL = "parallel"      # 并行执行
    CONDITIONAL = "conditional" # 条件执行


@dataclass
class ChainStep:
    """工具链步骤定义"""
    tool_name: str
    parameters: Dict[str, Any]
    condition: Optional[Callable[[Dict[str, Any]], bool]] = None
    timeout: Optional[int] = None
    retry_count: int = 0
    
    def __post_init__(self):
        if self.timeout is not None and self.timeout <= 0:
            raise ValueError("超时时间必须大于0")
        if self.retry_count < 0:
            raise ValueError("重试次数不能为负数")


@dataclass
class ChainResult:
    """工具链执行结果"""
    step_results: List[Dict[str, Any]]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class ToolChain:
    """工具链管理器"""
    
    def __init__(self, name: str, registry: Optional[ToolRegistry] = None):
        self.name = name
        self.registry = registry or ToolRegistry()
        self.steps: List[ChainStep] = []
        self.mode: ChainExecutionMode = ChainExecutionMode.SEQUENTIAL
        self.max_parallel: int = 5
        self._execution_history: List[ChainResult] = []
    
    def add_step(self, tool_name: str, parameters: Dict[str, Any],
                 condition: Optional[Callable[[Dict[str, Any]], bool]] = None,
                 timeout: Optional[int] = None, retry_count: int = 0) -> 'ToolChain':
        """添加工具步骤"""
        
        # 验证工具是否存在
        if not self.registry.get_tool(tool_name):
            raise ValueError(f"工具 '{tool_name}' 未注册")
        
        step = ChainStep(
            tool_name=tool_name,
            parameters=parameters,
            condition=condition,
            timeout=timeout,
            retry_count=retry_count
        )
        
        self.steps.append(step)
        return self
    
    def set_mode(self, mode: ChainExecutionMode, max_parallel: int = 5) -> 'ToolChain':
        """设置执行模式"""
        self.mode = mode
        self.max_parallel = max_parallel
        return self
    
    async def execute(self, context: Optional[Dict[str, Any]] = None) -> ChainResult:
        """执行工具链"""
        
        import time
        start_time = time.time()
        
        if context is None:
            context = {}
        
        step_results = []
        execution_success = True
        error_message = None
        
        try:
            if self.mode == ChainExecutionMode.SEQUENTIAL:
                await self._execute_sequential(context, step_results)
            elif self.mode == ChainExecutionMode.PARALLEL:
                await self._execute_parallel(context, step_results)
            elif self.mode == ChainExecutionMode.CONDITIONAL:
                await self._execute_conditional(context, step_results)
            else:
                raise ValueError(f"不支持的执行模式: {self.mode}")
        
        except Exception as e:
            execution_success = False
            error_message = str(e)
        
        execution_time = time.time() - start_time
        
        result = ChainResult(
            step_results=step_results,
            execution_time=execution_time,
            success=execution_success,
            error_message=error_message,
            metadata={
                'chain_name': self.name,
                'mode': self.mode.value,
                'total_steps': len(self.steps),
                'executed_steps': len(step_results)
            }
        )
        
        self._execution_history.append(result)
        return result
    
    async def _execute_sequential(self, context: Dict[str, Any],
                                 step_results: List[Dict[str, Any]]) -> None:
        """顺序执行工具链"""
        
        for i, step in enumerate(self.steps):
            # 检查执行条件
            if step.condition and not step.condition(context):
                step_results.append({
                    'step_index': i,
                    'tool_name': step.tool_name,
                    'skipped': True,
                    'reason': '条件不满足'
                })
                continue
            
            # 执行工具
            result = await self._execute_step(step, context, i)
            step_results.append(result)
            
            # 更新上下文
            if result['success'] and 'result' in result:
                context[f'{step.tool_name}_result'] = result['result']
    
    async def _execute_parallel(self, context: Dict[str, Any],
                               step_results: List[Dict[str, Any]]) -> None:
        """并行执行工具链"""
        
        import asyncio

        # 分组并行执行
        semaphore = asyncio.Semaphore(self.max_parallel)
        
        async def execute_with_semaphore(step: ChainStep, index: int):
            async with semaphore:
                return await self._execute_step(step, context, index)
        
        tasks = [
            execute_with_semaphore(step, i)
            for i, step in enumerate(self.steps)
            if not step.condition or step.condition(context)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                step_results.append({
                    'step_index': i,
                    'tool_name': self.steps[i].tool_name,
                    'success': False,
                    'error': str(result)
                })
            else:
                step_results.append(result)
    
    async def _execute_conditional(self, context: Dict[str, Any],
                                  step_results: List[Dict[str, Any]]) -> None:
        """条件执行工具链"""
        
        for i, step in enumerate(self.steps):
            # 检查执行条件
            if step.condition and not step.condition(context):
                step_results.append({
                    'step_index': i,
                    'tool_name': step.tool_name,
                    'skipped': True,
                    'reason': '条件不满足'
                })
                continue
            
            # 执行工具
            result = await self._execute_step(step, context, i)
            step_results.append(result)
            
            # 如果执行失败且不是最后一个步骤，可以决定是否继续
            if not result['success'] and i < len(self.steps) - 1:
                # 这里可以根据策略决定是否继续执行后续步骤
                # 当前实现是继续执行
                pass
    
    async def _execute_step(self, step: ChainStep, context: Dict[str, Any],
                           step_index: int) -> Dict[str, Any]:
        """执行单个工具步骤"""
        
        tool = self.registry.get_tool(step.tool_name)
        if not tool:
            return {
                'step_index': step_index,
                'tool_name': step.tool_name,
                'success': False,
                'error': f"工具 '{step.tool_name}' 未找到"
            }
        
        # 合并参数和上下文
        parameters = self._merge_parameters(step.parameters, context)
        
        # 执行工具（支持重试）
        for attempt in range(step.retry_count + 1):
            try:
                if isinstance(tool, AsyncTool):
                    result = await tool.execute(**parameters)
                else:
                    # 同步工具转换为异步执行
                    loop = asyncio.get_event_loop()
                    result = await loop.run_in_executor(
                        None, lambda: tool.execute(**parameters)
                    )
                
                return {
                    'step_index': step_index,
                    'tool_name': step.tool_name,
                    'success': True,
                    'result': result,
                    'attempts': attempt + 1
                }
            
            except Exception as e:
                if attempt == step.retry_count:
                    return {
                        'step_index': step_index,
                        'tool_name': step.tool_name,
                        'success': False,
                        'error': str(e),
                        'attempts': attempt + 1
                    }
        
        # 理论上不会执行到这里
        return {
            'step_index': step_index,
            'tool_name': step.tool_name,
            'success': False,
            'error': '未知错误',
            'attempts': step.retry_count + 1
        }
    
    def _merge_parameters(self, parameters: Dict[str, Any],
                         context: Dict[str, Any]) -> Dict[str, Any]:
        """合并参数和上下文"""
        
        merged = parameters.copy()
        
        # 支持参数中的变量替换
        for key, value in merged.items():
            if isinstance(value, str) and value.startswith('{{') and value.endswith('}}'):
                var_name = value[2:-2].strip()
                if var_name in context:
                    merged[key] = context[var_name]
        
        return merged
    
    def get_execution_history(self) -> List[ChainResult]:
        """获取执行历史"""
        return self._execution_history.copy()
    
    def clear_history(self) -> None:
        """清空执行历史"""
        self._execution_history.clear()
    
    def validate_chain(self) -> Dict[str, Any]:
        """验证工具链"""
        
        validation_result = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'steps_validation': []
        }
        
        if not self.steps:
            validation_result['warnings'].append("工具链为空")
        
        for i, step in enumerate(self.steps):
            step_validation = {
                'step_index': i,
                'tool_name': step.tool_name,
                'valid': True,
                'warnings': [],
                'errors': []
            }
            
            # 检查工具是否存在
            tool = self.registry.get_tool(step.tool_name)
            if not tool:
                step_validation['valid'] = False
                step_validation['errors'].append(f"工具 '{step.tool_name}' 未注册")
                validation_result['valid'] = False
            else:
                # 验证参数
                schema = tool.get_schema()
                required_params = schema.get('parameters', {}).get('required', [])
                
                for param in required_params:
                    if param not in step.parameters:
                        step_validation['warnings'].append(f"缺少必需参数: {param}")
            
            validation_result['steps_validation'].append(step_validation)
        
        return validation_result


class ChainManager:
    """工具链管理器（管理多个工具链）"""
    
    def __init__(self):
        self.chains: Dict[str, ToolChain] = {}
        self.registry = ToolRegistry()
    
    def create_chain(self, name: str) -> ToolChain:
        """创建新的工具链"""
        
        if name in self.chains:
            raise ValueError(f"工具链 '{name}' 已存在")
        
        chain = ToolChain(name, self.registry)
        self.chains[name] = chain
        return chain
    
    def get_chain(self, name: str) -> Optional[ToolChain]:
        """获取工具链"""
        return self.chains.get(name)
    
    def delete_chain(self, name: str) -> bool:
        """删除工具链"""
        
        if name not in self.chains:
            return False
        
        del self.chains[name]
        return True
    
    def list_chains(self) -> List[str]:
        """列出所有工具链"""
        return list(self.chains.keys())
    
    def export_chains(self) -> Dict[str, Any]:
        """导出所有工具链配置"""
        
        export_data = {
            'chains': {},
            'metadata': {
                'export_time': self._get_timestamp(),
                'total_chains': len(self.chains)
            }
        }
        
        for name, chain in self.chains.items():
            chain_config = {
                'steps': [
                    {
                        'tool_name': step.tool_name,
                        'parameters': step.parameters,
                        'timeout': step.timeout,
                        'retry_count': step.retry_count
                    }
                    for step in chain.steps
                ],
                'mode': chain.mode.value,
                'max_parallel': chain.max_parallel
            }
            export_data['chains'][name] = chain_config
        
        return export_data
    
    def import_chains(self, data: Dict[str, Any]) -> bool:
        """导入工具链配置"""
        
        try:
            if 'chains' not in data:
                return False
            
            for name, config in data['chains'].items():
                chain = self.create_chain(name)
                
                # 设置模式
                mode = ChainExecutionMode(config.get('mode', 'sequential'))
                max_parallel = config.get('max_parallel', 5)
                chain.set_mode(mode, max_parallel)
                
                # 添加步骤
                for step_config in config.get('steps', []):
                    chain.add_step(
                        tool_name=step_config['tool_name'],
                        parameters=step_config['parameters'],
                        timeout=step_config.get('timeout'),
                        retry_count=step_config.get('retry_count', 0)
                    )
            
            return True
            
        except Exception as e:
            print(f"导入工具链失败: {str(e)}")
            return False
    
    def _get_timestamp(self) -> str:
        """获取时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


# 全局工具链管理器实例
_global_chain_manager = ChainManager()


def create_chain(name: str) -> ToolChain:
    """便捷函数：创建工具链"""
    return _global_chain_manager.create_chain(name)


def get_chain(name: str) -> Optional[ToolChain]:
    """便捷函数：获取工具链"""
    return _global_chain_manager.get_chain(name)


def execute_chain(name: str, context: Optional[Dict[str, Any]] = None) -> ChainResult:
    """便捷函数：执行工具链"""
    
    chain = _global_chain_manager.get_chain(name)
    if not chain:
        raise ValueError(f"工具链 '{name}' 不存在")
    
    return asyncio.run(chain.execute(context))


def list_chains() -> List[str]:
    """便捷函数：列出所有工具链"""
    return _global_chain_manager.list_chains()


class ToolChain:
    """工具链 - 管理工具的执行顺序和数据流"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: List[Dict[str, Any]] = []
        self.input_mapping: Dict[str, str] = {}
        self.output_mapping: Dict[str, str] = {}
        self.conditions: Dict[int, Callable] = {}
    
    def add_step(self, tool: Tool, step_name: Optional[str] = None, 
                input_map: Optional[Dict[str, str]] = None,
                condition: Optional[Callable] = None) -> 'ToolChain':
        """添加工具步骤"""
        
        step_info = {
            'step_number': len(self.steps) + 1,
            'step_name': step_name or f"step_{len(self.steps) + 1}",
            'tool': tool,
            'input_map': input_map or {},
            'condition': condition
        }
        
        self.steps.append(step_info)
        
        if condition:
            self.conditions[len(self.steps) - 1] = condition
        
        return self
    
    def set_input_mapping(self, mapping: Dict[str, str]) -> 'ToolChain':
        """设置输入映射"""
        self.input_mapping = mapping
        return self
    
    def set_output_mapping(self, mapping: Dict[str, str]) -> 'ToolChain':
        """设置输出映射"""
        self.output_mapping = mapping
        return self
    
    def execute(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具链"""
        
        current_context = initial_inputs.copy()
        execution_results = {}
        
        for i, step in enumerate(self.steps):
            # 检查条件
            if i in self.conditions:
                condition_func = self.conditions[i]
                if not condition_func(current_context):
                    execution_results[step['step_name']] = {
                        'status': 'skipped',
                        'reason': 'condition_not_met'
                    }
                    continue
            
            # 准备工具输入
            tool_inputs = self._prepare_tool_inputs(step, current_context)
            
            try:
                # 执行工具
                result = step['tool'].execute(**tool_inputs)
                
                # 更新上下文
                step_result_key = f"{step['step_name']}_result"
                current_context[step_result_key] = result
                execution_results[step['step_name']] = {
                    'status': 'success',
                    'inputs': tool_inputs,
                    'output': result
                }
                
            except Exception as e:
                execution_results[step['step_name']] = {
                    'status': 'error',
                    'inputs': tool_inputs,
                    'error': str(e)
                }
                
                # 根据配置决定是否继续执行
                if not self._should_continue_on_error():
                    break
        
        # 应用输出映射
        final_output = self._apply_output_mapping(current_context)
        
        return {
            'final_output': final_output,
            'execution_results': execution_results,
            'context': current_context
        }
    
    def _prepare_tool_inputs(self, step: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """准备工具输入参数"""
        
        tool_inputs = {}
        
        # 应用输入映射
        for param_name, source_key in step['input_map'].items():
            if source_key in context:
                tool_inputs[param_name] = context[source_key]
        
        # 如果没有映射，尝试从上下文中匹配参数名
        if not tool_inputs:
            tool_schema = step['tool'].get_schema()
            for param_name in tool_schema['parameters'].keys():
                if param_name in context:
                    tool_inputs[param_name] = context[param_name]
        
        return tool_inputs
    
    def _apply_output_mapping(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """应用输出映射"""
        
        if not self.output_mapping:
            return context
        
        output = {}
        for output_key, source_key in self.output_mapping.items():
            if source_key in context:
                output[output_key] = context[source_key]
        
        return output
    
    def _should_continue_on_error(self) -> bool:
        """判断出错时是否继续执行"""
        # 默认行为：遇到错误停止执行
        # 子类可以重写这个方法来改变行为
        return False
    
    def validate(self) -> Dict[str, Any]:
        """验证工具链配置"""
        
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # 检查步骤
        if not self.steps:
            validation_result['valid'] = False
            validation_result['errors'].append("工具链没有定义任何步骤")
        
        # 检查工具可用性
        for i, step in enumerate(self.steps):
            tool = step['tool']
            
            # 验证工具模式
            try:
                schema = tool.get_schema()
                if not schema.get('parameters'):
                    validation_result['warnings'].append(
                        f"步骤 {i+1} 的工具 '{tool.name}' 没有定义参数"
                    )
            except Exception as e:
                validation_result['errors'].append(
                    f"步骤 {i+1} 的工具 '{tool.name}' 模式获取失败: {str(e)}"
                )
        
        # 检查输入映射
        for step in self.steps:
            for source_key in step['input_map'].values():
                # 这里可以添加更复杂的依赖关系检查
                pass
        
        return validation_result
    
    def get_execution_plan(self) -> List[Dict[str, Any]]:
        """获取执行计划"""
        
        plan = []
        for step in self.steps:
            step_info = {
                'step_number': step['step_number'],
                'step_name': step['step_name'],
                'tool_name': step['tool'].name,
                'tool_description': step['tool'].description,
                'input_mapping': step['input_map'],
                'has_condition': step['condition'] is not None
            }
            plan.append(step_info)
        
        return plan
    
    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        
        return {
            'name': self.name,
            'description': self.description,
            'steps': [
                {
                    'step_name': step['step_name'],
                    'tool_name': step['tool'].name,
                    'input_map': step['input_map']
                }
                for step in self.steps
            ],
            'input_mapping': self.input_mapping,
            'output_mapping': self.output_mapping
        }


class ParallelToolChain(ToolChain):
    """并行工具链 - 支持工具并行执行"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__(name, description)
        self.parallel_groups: List[List[int]] = []
    
    def add_parallel_group(self, step_indices: List[int]) -> 'ParallelToolChain':
        """添加并行执行组"""
        self.parallel_groups.append(step_indices)
        return self
    
    def execute(self, initial_inputs: Dict[str, Any]) -> Dict[str, Any]:
        """执行并行工具链"""
        
        import asyncio
        
        current_context = initial_inputs.copy()
        execution_results = {}
        
        # 如果没有定义并行组，按顺序执行
        if not self.parallel_groups:
            return super().execute(initial_inputs)
        
        # 按组执行
        for group_indices in self.parallel_groups:
            # 收集本组需要执行的步骤
            group_steps = [self.steps[i] for i in group_indices if i < len(self.steps)]
            
            # 并行执行组内步骤
            async def execute_group():
                tasks = []
                for step in group_steps:
                    # 准备工具输入
                    tool_inputs = self._prepare_tool_inputs(step, current_context)
                    
                    # 创建异步任务
                    if hasattr(step['tool'], 'execute_async'):
                        task = step['tool'].execute_async(**tool_inputs)
                    else:
                        # 同步工具包装为异步
                        async def sync_wrapper():
                            return step['tool'].execute(**tool_inputs)
                        task = sync_wrapper()
                    
                    tasks.append((step, task))
                
                # 等待所有任务完成
                results = await asyncio.gather(*[task for _, task in tasks], 
                                             return_exceptions=True)
                
                # 处理结果
                group_results = {}
                for (step, _), result in zip(tasks, results):
                    step_name = step['step_name']
                    
                    if isinstance(result, Exception):
                        group_results[step_name] = {
                            'status': 'error',
                            'error': str(result)
                        }
                    else:
                        step_result_key = f"{step_name}_result"
                        current_context[step_result_key] = result
                        group_results[step_name] = {
                            'status': 'success',
                            'output': result
                        }
                
                return group_results
            
            # 执行当前组
            group_results = asyncio.run(execute_group())
            execution_results.update(group_results)
        
        # 应用输出映射
        final_output = self._apply_output_mapping(current_context)
        
        return {
            'final_output': final_output,
            'execution_results': execution_results,
            'context': current_context
        }


class ToolChainBuilder:
    """工具链构建器 - 提供流畅的API"""
    
    def __init__(self, name: str):
        self.chain = ToolChain(name)
    
    def with_description(self, description: str) -> 'ToolChainBuilder':
        """设置描述"""
        self.chain.description = description
        return self
    
    def add_tool(self, tool: Tool, step_name: Optional[str] = None,
                input_map: Optional[Dict[str, str]] = None,
                condition: Optional[Callable] = None) -> 'ToolChainBuilder':
        """添加工具"""
        self.chain.add_step(tool, step_name, input_map, condition)
        return self
    
    def with_input_mapping(self, mapping: Dict[str, str]) -> 'ToolChainBuilder':
        """设置输入映射"""
        self.chain.set_input_mapping(mapping)
        return self
    
    def with_output_mapping(self, mapping: Dict[str, str]) -> 'ToolChainBuilder':
        """设置输出映射"""
        self.chain.set_output_mapping(mapping)
        return self
    
    def build(self) -> ToolChain:
        """构建工具链"""
        return self.chain