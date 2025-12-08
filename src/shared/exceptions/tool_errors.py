"""
工具相关异常
定义工具操作过程中的异常类型
"""

from typing import Optional, Dict, Any
from .base import BaseError


class ToolError(BaseError):
    """工具基础异常"""
    
    def __init__(
        self, 
        message: str, 
        tool_name: Optional[str] = None,
        tool_type: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if tool_name:
            details['tool_name'] = tool_name
        if tool_type:
            details['tool_type'] = tool_type
        
        super().__init__(message, code="TOOL_ERROR", details=details, **kwargs)


class ToolValidationError(ToolError):
    """工具验证异常"""
    
    def __init__(
        self, 
        message: str, 
        validation_rules: Optional[Dict[str, Any]] = None,
        invalid_value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if validation_rules:
            details['validation_rules'] = validation_rules
        if invalid_value is not None:
            details['invalid_value'] = invalid_value
        
        super().__init__(message, code="TOOL_VALIDATION_ERROR", details=details, **kwargs)


class ToolTimeoutError(ToolError):
    """工具超时异常"""
    
    def __init__(
        self, 
        message: str, 
        timeout_seconds: Optional[float] = None,
        elapsed_time: Optional[float] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if timeout_seconds is not None:
            details['timeout_seconds'] = timeout_seconds
        if elapsed_time is not None:
            details['elapsed_time'] = elapsed_time
        
        super().__init__(message, code="TOOL_TIMEOUT_ERROR", details=details, **kwargs)


class ToolPermissionError(ToolError):
    """工具权限异常"""
    
    def __init__(
        self, 
        message: str, 
        required_permissions: Optional[list] = None,
        actual_permissions: Optional[list] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if required_permissions:
            details['required_permissions'] = required_permissions
        if actual_permissions:
            details['actual_permissions'] = actual_permissions
        
        super().__init__(message, code="TOOL_PERMISSION_ERROR", details=details, **kwargs)