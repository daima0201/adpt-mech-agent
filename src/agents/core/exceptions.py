"""
异常体系定义
提供统一的错误处理和异常分类
"""

from typing import Optional, Dict, Any


class AgentError(Exception):
    """Agent基础异常类"""
    
    def __init__(self, message: str, agent_name: Optional[str] = None, 
                 error_code: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.agent_name = agent_name
        self.error_code = error_code
        self.details = details or {}
        super().__init__(self._format_message())
    
    def _format_message(self) -> str:
        """格式化错误消息"""
        parts = []
        if self.agent_name:
            parts.append(f"Agent '{self.agent_name}'")
        if self.error_code:
            parts.append(f"[{self.error_code}]")
        parts.append(self.message)
        return " ".join(parts)


class ToolExecutionError(AgentError):
    """工具执行异常"""
    
    def __init__(self, tool_name: str, error_msg: str, **kwargs):
        message = f"工具 '{tool_name}' 执行失败: {error_msg}"
        super().__init__(message, **kwargs)
        self.tool_name = tool_name


class LLMError(AgentError):
    """LLM调用异常"""
    
    def __init__(self, model_name: str, error_msg: str, **kwargs):
        message = f"LLM模型 '{model_name}' 调用失败: {error_msg}"
        super().__init__(message, **kwargs)
        self.model_name = model_name


class ConfigurationError(AgentError):
    """配置异常"""
    
    def __init__(self, config_key: str, error_msg: str, **kwargs):
        message = f"配置项 '{config_key}' 错误: {error_msg}"
        super().__init__(message, **kwargs)
        self.config_key = config_key


class ValidationError(AgentError):
    """数据验证异常"""
    
    def __init__(self, field_name: str, value: Any, constraint: str, **kwargs):
        message = f"字段 '{field_name}' 的值 '{value}' 不满足约束: {constraint}"
        super().__init__(message, **kwargs)
        self.field_name = field_name
        self.value = value
        self.constraint = constraint


class TimeoutError(AgentError):
    """超时异常"""
    
    def __init__(self, operation: str, timeout_seconds: int, **kwargs):
        message = f"操作 '{operation}' 在 {timeout_seconds} 秒后超时"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.timeout_seconds = timeout_seconds


class ResourceNotFoundError(AgentError):
    """资源未找到异常"""
    
    def __init__(self, resource_type: str, resource_id: str, **kwargs):
        message = f"{resource_type} '{resource_id}' 未找到"
        super().__init__(message, **kwargs)
        self.resource_type = resource_type
        self.resource_id = resource_id


class PermissionError(AgentError):
    """权限异常"""
    
    def __init__(self, operation: str, required_permission: str, **kwargs):
        message = f"操作 '{operation}' 需要权限: {required_permission}"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.required_permission = required_permission


class RetryExhaustedError(AgentError):
    """重试耗尽异常"""
    
    def __init__(self, operation: str, max_retries: int, last_error: Exception, **kwargs):
        message = f"操作 '{operation}' 在 {max_retries} 次重试后仍然失败，最后错误: {str(last_error)}"
        super().__init__(message, **kwargs)
        self.operation = operation
        self.max_retries = max_retries
        self.last_error = last_error


class InvalidStateError(AgentError):
    """无效状态异常"""
    
    def __init__(self, current_state: str, expected_states: list, **kwargs):
        message = f"当前状态 '{current_state}' 无效，期望状态: {', '.join(expected_states)}"
        super().__init__(message, **kwargs)
        self.current_state = current_state
        self.expected_states = expected_states


class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_error(error: Exception, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理异常并返回结构化信息"""
        
        error_info = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context or {},
            'timestamp': None  # 可以添加时间戳
        }
        
        # 添加特定异常的额外信息
        if isinstance(error, AgentError):
            error_info.update({
                'agent_name': getattr(error, 'agent_name', None),
                'error_code': getattr(error, 'error_code', None),
                'details': getattr(error, 'details', {})
            })
        
        return error_info
    
    @staticmethod
    def should_retry(error: Exception, retry_count: int, max_retries: int) -> bool:
        """判断是否应该重试"""
        
        if retry_count >= max_retries:
            return False
        
        # 不应该重试的异常类型
        non_retryable_errors = [
            ValidationError,
            PermissionError,
            ResourceNotFoundError,
            InvalidStateError
        ]
        
        for error_type in non_retryable_errors:
            if isinstance(error, error_type):
                return False
        
        # 其他异常可以重试
        return True
    
    @staticmethod
    def get_safe_error_message(error: Exception) -> str:
        """获取安全的错误消息（避免泄露敏感信息）"""
        
        if isinstance(error, AgentError):
            # AgentError已经包含了安全的消息格式
            return str(error)
        else:
            # 对于其他异常，返回通用错误消息
            return f"系统内部错误: {type(error).__name__}"


# 错误代码定义
ERROR_CODES = {
    # Agent相关错误
    'AGENT_INIT_FAILED': 'A001',
    'AGENT_RUN_FAILED': 'A002',
    'AGENT_CONFIG_ERROR': 'A003',
    
    # LLM相关错误
    'LLM_CONNECTION_ERROR': 'L001',
    'LLM_RATE_LIMIT': 'L002',
    'LLM_AUTH_ERROR': 'L003',
    'LLM_MODEL_NOT_FOUND': 'L004',
    
    # 工具相关错误
    'TOOL_EXECUTION_ERROR': 'T001',
    'TOOL_NOT_FOUND': 'T002',
    'TOOL_VALIDATION_ERROR': 'T003',
    'TOOL_TIMEOUT': 'T004',
    
    # 配置相关错误
    'CONFIG_FILE_NOT_FOUND': 'C001',
    'CONFIG_VALIDATION_ERROR': 'C002',
    'CONFIG_FORMAT_ERROR': 'C003',
    
    # 数据相关错误
    'DATA_VALIDATION_ERROR': 'D001',
    'DATA_FORMAT_ERROR': 'D002',
    'DATA_NOT_FOUND': 'D003'
}