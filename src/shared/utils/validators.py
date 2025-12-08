"""
统一验证器
提供配置和输入数据的验证功能
"""

import re
from typing import Any, Dict, List, Optional, Union
from pathlib import Path


class ValidationError(Exception):
    """验证错误异常"""
    def __init__(self, message: str, field: Optional[str] = None):
        self.message = message
        self.field = field
        super().__init__(f"{field + ': ' if field else ''}{message}")


def validate_config(config: Dict[str, Any], schema: Dict[str, Any]) -> bool:
    """
    验证配置字典是否符合给定的schema
    
    Args:
        config: 要验证的配置字典
        schema: schema定义，包含字段类型、必需性等信息
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    errors = []
    
    # 检查必需字段
    for field, field_schema in schema.items():
        if field_schema.get('required', False) and field not in config:
            errors.append(f"必需字段 '{field}' 缺失")
    
    # 验证字段值
    for field, value in config.items():
        if field not in schema:
            continue  # 忽略不在schema中的字段
            
        field_schema = schema[field]
        
        try:
            _validate_field(value, field_schema, field)
        except ValidationError as e:
            errors.append(str(e))
    
    if errors:
        raise ValidationError("配置验证失败: " + "; ".join(errors))
    
    return True


def validate_input(input_data: Any, rules: Dict[str, Any], field_name: str = "input") -> bool:
    """
    验证输入数据是否符合规则
    
    Args:
        input_data: 要验证的输入数据
        rules: 验证规则字典
        field_name: 字段名称，用于错误消息
        
    Returns:
        bool: 验证是否通过
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    try:
        _validate_field(input_data, rules, field_name)
        return True
    except ValidationError as e:
        raise ValidationError(f"输入验证失败: {str(e)}")


def _validate_field(value: Any, schema: Dict[str, Any], field_name: str) -> None:
    """验证单个字段"""
    # 类型检查
    expected_type = schema.get('type')
    if expected_type and not isinstance(value, expected_type):
        raise ValidationError(f"必须是 {expected_type.__name__} 类型", field_name)
    
    # 枚举值检查
    enum_values = schema.get('enum')
    if enum_values and value not in enum_values:
        raise ValidationError(f"必须是以下值之一: {enum_values}", field_name)
    
    # 范围检查（数值）
    if isinstance(value, (int, float)):
        min_val = schema.get('min')
        max_val = schema.get('max')
        
        if min_val is not None and value < min_val:
            raise ValidationError(f"不能小于 {min_val}", field_name)
        if max_val is not None and value > max_val:
            raise ValidationError(f"不能大于 {max_val}", field_name)
    
    # 长度检查（字符串、列表）
    if isinstance(value, (str, list)):
        min_len = schema.get('min_length')
        max_len = schema.get('max_length')
        
        if min_len is not None and len(value) < min_len:
            raise ValidationError(f"长度不能小于 {min_len}", field_name)
        if max_len is not None and len(value) > max_len:
            raise ValidationError(f"长度不能大于 {max_len}", field_name)
    
    # 正则表达式检查（字符串）
    pattern = schema.get('pattern')
    if isinstance(value, str) and pattern:
        if not re.match(pattern, value):
            raise ValidationError(f"格式不符合要求", field_name)
    
    # 文件路径检查
    file_check = schema.get('file_exists')
    if file_check and isinstance(value, str):
        if file_check == 'required' and not Path(value).exists():
            raise ValidationError(f"文件不存在: {value}", field_name)
        elif file_check == 'optional' and value and not Path(value).exists():
            raise ValidationError(f"文件不存在: {value}", field_name)
    
    # 嵌套验证（字典）
    nested_schema = schema.get('schema')
    if isinstance(value, dict) and nested_schema:
        validate_config(value, nested_schema)
    
    # 列表项验证
    item_schema = schema.get('items')
    if isinstance(value, list) and item_schema:
        for i, item in enumerate(value):
            try:
                _validate_field(item, item_schema, f"{field_name}[{i}]")
            except ValidationError as e:
                raise ValidationError(f"列表项验证失败: {str(e)}", field_name)


# 常用验证schema模板
CONFIG_SCHEMAS = {
    'database': {
        'host': {'type': str, 'required': True},
        'port': {'type': int, 'min': 1, 'max': 65535},
        'username': {'type': str, 'required': True},
        'password': {'type': str},
        'database': {'type': str, 'required': True}
    },
    'llm': {
        'model': {'type': str, 'required': True},
        'api_key': {'type': str, 'required': True},
        'temperature': {'type': float, 'min': 0.0, 'max': 2.0},
        'max_tokens': {'type': int, 'min': 1}
    },
    'knowledge_base': {
        'name': {'type': str, 'required': True},
        'vector_store': {'type': str, 'enum': ['chroma', 'qdrant']},
        'embedder': {'type': str, 'enum': ['openai', 'bge', 'local']}
    }
}