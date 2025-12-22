"""
配置验证器
"""

from typing import Dict, Any, List
import re

class ConfigValidator:
    """配置验证器"""
    
    @staticmethod
    def validate_agent_config(config: Dict[str, Any]) -> List[str]:
        """验证Agent配置"""
        errors = []
        
        # 必需字段检查
        required_fields = ['name', 'agent_type', 'system_prompt']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # Agent类型验证
        valid_types = ['simple', 'react', 'plan_solve', 'reflection']
        if config.get('agent_type') and config['agent_type'] not in valid_types:
            errors.append(f"无效的Agent类型: {config['agent_type']}")
        
        # 名称格式验证
        name = config.get('name', '')
        if name and not re.match(r'^[a-zA-Z0-9_-]{1,50}$', name):
            errors.append("名称只能包含字母、数字、下划线和连字符，长度1-50")
        
        return errors
    
    @staticmethod
    def validate_llm_config(config: Dict[str, Any]) -> List[str]:
        """验证LLM配置"""
        errors = []
        
        # 必需字段检查
        required_fields = ['name', 'provider', 'model_name', 'api_key']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # Provider验证
        valid_providers = ['openai', 'anthropic', 'azure', 'local']
        if config.get('provider') and config['provider'] not in valid_providers:
            errors.append(f"无效的Provider: {config['provider']}")
        
        # 温度值验证
        temperature = config.get('temperature', 0.7)
        if not isinstance(temperature, (int, float)) or not 0 <= temperature <= 2:
            errors.append("温度值必须在0到2之间")
        
        # 超时时间验证
        timeout = config.get('timeout', 30)
        if not isinstance(timeout, int) or timeout <= 0:
            errors.append("超时时间必须为正整数")
        
        return errors
    
    @staticmethod
    def validate_prompt_template(config: Dict[str, Any]) -> List[str]:
        """验证Prompt模板"""
        errors = []
        
        # 必需字段检查
        required_fields = ['name', 'template', 'variables']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # 模板内容验证
        template = config.get('template', '')
        if not template.strip():
            errors.append("模板内容不能为空")
        
        # 变量列表验证
        variables = config.get('variables', [])
        if not isinstance(variables, list):
            errors.append("variables必须是列表")
        
        return errors
    
    @staticmethod
    def validate_database_config(config: Dict[str, Any]) -> List[str]:
        """验证数据库配置"""
        errors = []
        
        # 必需字段检查
        required_fields = ['host', 'port', 'database', 'username']
        for field in required_fields:
            if not config.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # 端口验证
        port = config.get('port')
        if port and (not isinstance(port, int) or not 1 <= port <= 65535):
            errors.append("端口号必须在1-65535之间")
        
        # 连接池大小验证
        pool_size = config.get('pool_size', 10)
        if not isinstance(pool_size, int) or pool_size <= 0:
            errors.append("连接池大小必须为正整数")
        
        return errors