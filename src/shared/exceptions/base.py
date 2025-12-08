"""
异常基类
定义项目的基础异常类型
"""

from typing import Optional, Dict, Any


class BaseError(Exception):
    """基础异常类"""
    
    def __init__(
        self, 
        message: str, 
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """
        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情
        """
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.code:
            return f"[{self.code}] {self.message}"
        return self.message
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            'error': self.__class__.__name__,
            'message': self.message,
            'code': self.code,
            'details': self.details
        }


class ConfigError(BaseError):
    """配置相关异常"""
    
    def __init__(
        self, 
        message: str, 
        config_key: Optional[str] = None,
        config_file: Optional[str] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if config_key:
            details['config_key'] = config_key
        if config_file:
            details['config_file'] = config_file
        
        super().__init__(message, code="CONFIG_ERROR", details=details, **kwargs)


class ValidationError(BaseError):
    """验证相关异常"""
    
    def __init__(
        self, 
        message: str, 
        field: Optional[str] = None,
        value: Optional[Any] = None,
        **kwargs
    ):
        details = kwargs.pop('details', {})
        if field:
            details['field'] = field
        if value is not None:
            details['value'] = value
        
        super().__init__(message, code="VALIDATION_ERROR", details=details, **kwargs)