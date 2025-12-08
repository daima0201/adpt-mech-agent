"""
智能体相关异常
定义智能体执行过程中的异常类型
"""

from typing import Optional, Dict, Any
from .base import BaseError


class AgentError(BaseError):
    """智能体基础异常"""
    
    def __init__(
        self, 
        message: str, 
        agent_name: Optional[str] = None,
        agent_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if agent_name:
            details['agent_name'] = agent_name
        if agent_type:
            details['agent_type'] = agent_type
        
        super().__init__(message, code="AGENT_ERROR", details=details, **kwargs)


class AgentExecutionError(AgentError):
    """智能体执行异常"""
    
    def __init__(
        self, 
        message: str, 
        step: Optional[str] = None,
        input_data: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if step:
            details['step'] = step
        if input_data is not None:
            details['input_data'] = input_data
        
        super().__init__(message, code="AGENT_EXECUTION_ERROR", details=details, **kwargs)


class AgentInitializationError(AgentError):
    """智能体初始化异常"""
    
    def __init__(
        self, 
        message: str, 
        config: Optional[Dict[str, Any]] = None,
        dependencies: Optional[list] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if config:
            details['config'] = config
        if dependencies:
            details['dependencies'] = dependencies
        
        super().__init__(message, code="AGENT_INITIALIZATION_ERROR", details=details, **kwargs)


class ToolNotFoundError(AgentError):
    """工具未找到异常"""
    
    def __init__(
        self, 
        tool_name: str, 
        available_tools: Optional[list] = None,
        **kwargs
    ):
        message = f"工具 '{tool_name}' 未找到"
        details = kwargs.pop('details', {})
        details['tool_name'] = tool_name
        if available_tools:
            details['available_tools'] = available_tools
        
        super().__init__(message, code="TOOL_NOT_FOUND", details=details, **kwargs)


class ToolExecutionError(AgentError):
    """工具执行异常"""
    
    def __init__(
        self, 
        message: str, 
        tool_name: Optional[str] = None,
        tool_args: Optional[Dict[str, Any]] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if tool_name:
            details['tool_name'] = tool_name
        if tool_args:
            details['tool_args'] = tool_args
        
        super().__init__(message, code="TOOL_EXECUTION_ERROR", details=details, **kwargs)