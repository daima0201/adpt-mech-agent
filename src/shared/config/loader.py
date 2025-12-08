"""
配置加载器
提供配置文件的加载和保存功能
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path
from .schema import ConfigSchema
from ..utils.file_utils import read_yaml, write_yaml, read_json, write_json


def load_config(
    config_path: str, 
    config_type: str = "yaml",
    env_prefix: str = "APP_"
) -> ConfigSchema:
    """
    加载配置文件
    
    Args:
        config_path: 配置文件路径
        config_type: 配置文件类型 (yaml/json)
        env_prefix: 环境变量前缀
        
    Returns:
        ConfigSchema实例
    """
    path = Path(config_path)
    
    if not path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")
    
    # 根据文件类型选择读取方法
    if config_type.lower() == "yaml":
        config_data = read_yaml(path)
    elif config_type.lower() == "json":
        config_data = read_json(path)
    else:
        raise ValueError(f"不支持的配置文件类型: {config_type}")
    
    # 合并环境变量配置
    env_config = _load_env_config(env_prefix)
    config_data = _merge_configs(config_data, env_config)
    
    return ConfigSchema.from_dict(config_data)


def save_config(
    config: ConfigSchema, 
    config_path: str, 
    config_type: str = "yaml"
) -> None:
    """
    保存配置到文件
    
    Args:
        config: ConfigSchema实例
        config_path: 配置文件路径
        config_type: 配置文件类型 (yaml/json)
    """
    config_data = config.to_dict()
    path = Path(config_path)
    
    # 确保目录存在
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # 根据文件类型选择写入方法
    if config_type.lower() == "yaml":
        write_yaml(path, config_data)
    elif config_type.lower() == "json":
        write_json(path, config_data)
    else:
        raise ValueError(f"不支持的配置文件类型: {config_type}")


def _load_env_config(prefix: str = "APP_") -> Dict[str, Any]:
    """
    从环境变量加载配置
    
    Args:
        prefix: 环境变量前缀
        
    Returns:
        环境变量配置字典
    """
    env_config = {}
    
    for key, value in os.environ.items():
        if key.startswith(prefix):
            # 移除前缀并转换为嵌套字典结构
            config_key = key[len(prefix):].lower()
            
            # 支持嵌套配置（使用下划线分隔）
            keys = config_key.split('_')
            current_dict = env_config
            
            # 创建嵌套字典结构
            for k in keys[:-1]:
                if k not in current_dict:
                    current_dict[k] = {}
                current_dict = current_dict[k]
            
            # 设置最终值
            current_dict[keys[-1]] = _parse_env_value(value)
    
    return env_config


def _parse_env_value(value: str) -> Any:
    """
    解析环境变量值
    
    Args:
        value: 环境变量值
        
    Returns:
        解析后的值
    """
    # 布尔值
    if value.lower() in ['true', 'false']:
        return value.lower() == 'true'
    
    # 整数
    if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
        return int(value)
    
    # 浮点数
    try:
        return float(value)
    except ValueError:
        pass
    
    # 列表（逗号分隔）
    if ',' in value:
        return [_parse_env_value(v.strip()) for v in value.split(',')]
    
    # 字符串
    return value


def _merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    合并配置字典，override_config会覆盖base_config中的值
    
    Args:
        base_config: 基础配置
        override_config: 覆盖配置
        
    Returns:
        合并后的配置
    """
    result = base_config.copy()
    
    for key, value in override_config.items():
        if isinstance(value, dict) and key in result and isinstance(result[key], dict):
            # 递归合并嵌套字典
            result[key] = _merge_configs(result[key], value)
        else:
            # 直接覆盖
            result[key] = value
    
    return result


def find_config_files(config_dir: str = "config") -> Dict[str, str]:
    """
    查找配置文件
    
    Args:
        config_dir: 配置目录
        
    Returns:
        配置文件路径字典 {配置名: 文件路径}
    """
    config_files = {}
    config_path = Path(config_dir)
    
    if not config_path.exists():
        return config_files
    
    # 查找所有配置文件
    for file_path in config_path.glob("*"):
        if file_path.is_file():
            name = file_path.stem  # 去掉扩展名
            ext = file_path.suffix.lower()
            
            if ext in ['.yaml', '.yml', '.json']:
                config_files[name] = str(file_path)
    
    return config_files


def validate_config_file(config_path: str, schema: Optional[Dict[str, Any]] = None) -> bool:
    """
    验证配置文件
    
    Args:
        config_path: 配置文件路径
        schema: 验证schema
        
    Returns:
        是否验证通过
    """
    try:
        config = load_config(config_path)
        
        # 如果有schema，进行验证
        if schema:
            from ..utils.validators import validate_config
            validate_config(config.to_dict(), schema)
        
        return True
    except Exception as e:
        print(f"配置文件验证失败: {e}")
        return False