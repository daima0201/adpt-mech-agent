"""
配置管理器
提供统一的配置管理功能
"""

import os
from typing import Any, Dict, Optional, Union
from pathlib import Path
from .schema import ConfigSchema
from ..utils.file_utils import read_yaml, write_yaml, read_json, write_json
from ..utils.validators import validate_config


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """
        Args:
            config_dir: 配置文件目录，如果为None则使用默认目录
        """
        self.config_dir = Path(config_dir) if config_dir else Path("config")
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._schemas: Dict[str, Dict[str, Any]] = {}
    
    def load_config(
        self, 
        name: str, 
        config_file: Optional[str] = None,
        schema: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        加载配置文件
        
        Args:
            name: 配置名称
            config_file: 配置文件路径，如果为None则使用默认路径
            schema: 配置schema，用于验证
            
        Returns:
            配置字典
        """
        if config_file is None:
            # 尝试不同的配置文件格式
            possible_files = [
                self.config_dir / f"{name}.yaml",
                self.config_dir / f"{name}.yml", 
                self.config_dir / f"{name}.json"
            ]
            
            config_file = None
            for file_path in possible_files:
                if file_path.exists():
                    config_file = file_path
                    break
            
            if config_file is None:
                raise FileNotFoundError(f"找不到配置文件: {name}")
        
        # 根据文件扩展名选择读取方法
        file_ext = Path(config_file).suffix.lower()
        
        if file_ext in ['.yaml', '.yml']:
            config_data = read_yaml(config_file)
        elif file_ext == '.json':
            config_data = read_json(config_file)
        else:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
        
        # 验证配置
        if schema:
            validate_config(config_data, schema)
        
        # 缓存配置
        self._configs[name] = config_data
        if schema:
            self._schemas[name] = schema
        
        return config_data
    
    def get_config(self, name: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            name: 配置名称
            key: 配置键，如果为None则返回整个配置
            default: 默认值
            
        Returns:
            配置值
        """
        if name not in self._configs:
            # 自动加载配置
            try:
                self.load_config(name)
            except FileNotFoundError:
                return default
        
        config_data = self._configs[name]
        
        if key is None:
            return config_data
        
        # 支持嵌套键（使用点号分隔）
        keys = key.split('.')
        current = config_data
        
        for k in keys:
            if isinstance(current, dict) and k in current:
                current = current[k]
            else:
                return default
        
        return current
    
    def set_config(self, name: str, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            name: 配置名称
            key: 配置键
            value: 配置值
        """
        if name not in self._configs:
            self._configs[name] = {}
        
        # 支持嵌套键（使用点号分隔）
        keys = key.split('.')
        current = self._configs[name]
        
        # 创建嵌套字典结构
        for k in keys[:-1]:
            if k not in current or not isinstance(current[k], dict):
                current[k] = {}
            current = current[k]
        
        # 设置最终值
        current[keys[-1]] = value
    
    def save_config(self, name: str, config_file: Optional[str] = None) -> None:
        """
        保存配置到文件
        
        Args:
            name: 配置名称
            config_file: 配置文件路径，如果为None则使用默认路径
        """
        if name not in self._configs:
            raise KeyError(f"配置不存在: {name}")
        
        if config_file is None:
            config_file = self.config_dir / f"{name}.yaml"
        
        # 确保目录存在
        Path(config_file).parent.mkdir(parents=True, exist_ok=True)
        
        # 根据文件扩展名选择写入方法
        file_ext = Path(config_file).suffix.lower()
        
        if file_ext in ['.yaml', '.yml']:
            write_yaml(config_file, self._configs[name])
        elif file_ext == '.json':
            write_json(config_file, self._configs[name])
        else:
            raise ValueError(f"不支持的配置文件格式: {file_ext}")
    
    def reload_config(self, name: str) -> Dict[str, Any]:
        """重新加载配置文件"""
        if name in self._configs:
            del self._configs[name]
        
        return self.load_config(name)
    
    def list_configs(self) -> list:
        """列出所有已加载的配置"""
        return list(self._configs.keys())
    
    def validate_config(self, name: str) -> bool:
        """验证配置是否符合schema"""
        if name not in self._configs:
            raise KeyError(f"配置不存在: {name}")
        
        if name not in self._schemas:
            return True  # 没有schema，认为验证通过
        
        return validate_config(self._configs[name], self._schemas[name])
    
    def register_schema(self, name: str, schema: Dict[str, Any]) -> None:
        """注册配置schema"""
        self._schemas[name] = schema
    
    def get_env_config(self, prefix: str = "APP_") -> Dict[str, Any]:
        """
        从环境变量获取配置
        
        Args:
            prefix: 环境变量前缀
            
        Returns:
            环境变量配置字典
        """
        env_config = {}
        
        for key, value in os.environ.items():
            if key.startswith(prefix):
                # 移除前缀并转换为小写
                config_key = key[len(prefix):].lower()
                
                # 尝试解析值类型
                try:
                    # 布尔值
                    if value.lower() in ['true', 'false']:
                        env_config[config_key] = value.lower() == 'true'
                    # 整数
                    elif value.isdigit():
                        env_config[config_key] = int(value)
                    # 浮点数
                    elif value.replace('.', '').isdigit():
                        env_config[config_key] = float(value)
                    # 字符串
                    else:
                        env_config[config_key] = value
                except (ValueError, AttributeError):
                    env_config[config_key] = value
        
        return env_config