"""
配置管理系统
支持多种配置源和动态配置更新
"""

import os
import yaml
import json
from typing import Dict, Any, Optional, Union
from pathlib import Path


class Config:
    """配置管理类"""
    
    def __init__(self, config_dict: Optional[Dict[str, Any]] = None):
        self._config = config_dict or {}
        self._defaults = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            'max_history_length': 100,
            'timeout': 30,
            'temperature': 0.7,
            'max_tokens': 2048,
            'model_name': 'gpt-3.5-turbo',
            'log_level': 'INFO',
            'enable_streaming': True,
            'max_iterations': 5,
            'reflection_threshold': 0.7,
            'tool_timeout': 60
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 首先检查用户配置
        if key in self._config:
            return self._config[key]
        
        # 然后检查默认配置
        if key in self._defaults:
            return self._defaults[key]
        
        # 最后返回提供的默认值
        return default
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值"""
        self._config[key] = value
    
    def update(self, config_dict: Dict[str, Any]) -> None:
        """批量更新配置"""
        self._config.update(config_dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        # 合并默认配置和用户配置
        result = self._defaults.copy()
        result.update(self._config)
        return result
    
    def save_to_file(self, filepath: str, format: str = 'yaml') -> None:
        """保存配置到文件"""
        config_dict = self.to_dict()
        
        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        
        if format.lower() == 'yaml':
            with open(filepath, 'w', encoding='utf-8') as f:
                yaml.dump(config_dict, f, allow_unicode=True, indent=2)
        elif format.lower() == 'json':
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, ensure_ascii=False, indent=2)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    @classmethod
    def from_file(cls, filepath: str) -> 'Config':
        """从文件加载配置"""
        filepath = Path(filepath)
        
        if not filepath.exists():
            raise FileNotFoundError(f"配置文件不存在: {filepath}")
        
        if filepath.suffix.lower() in ['.yaml', '.yml']:
            with open(filepath, 'r', encoding='utf-8') as f:
                config_dict = yaml.safe_load(f) or {}
        elif filepath.suffix.lower() == '.json':
            with open(filepath, 'r', encoding='utf-8') as f:
                config_dict = json.load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {filepath.suffix}")
        
        return cls(config_dict)
    
    @classmethod
    def from_env_vars(cls, prefix: str = "HELLOAGENTS_") -> 'Config':
        """从环境变量加载配置"""
        config_dict = {}
        
        for env_key, env_value in os.environ.items():
            if env_key.startswith(prefix):
                # 移除前缀并转换为小写
                config_key = env_key[len(prefix):].lower()
                
                # 尝试解析为适当的数据类型
                try:
                    # 尝试解析为数字
                    if env_value.isdigit():
                        config_dict[config_key] = int(env_value)
                    elif env_value.replace('.', '', 1).isdigit():
                        config_dict[config_key] = float(env_value)
                    elif env_value.lower() in ['true', 'false']:
                        config_dict[config_key] = env_value.lower() == 'true'
                    else:
                        config_dict[config_key] = env_value
                except:
                    config_dict[config_key] = env_value
        
        return cls(config_dict)
    
    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)
    
    def __setitem__(self, key: str, value: Any) -> None:
        """支持字典式设置"""
        self.set(key, value)
    
    def __contains__(self, key: str) -> bool:
        """检查配置键是否存在"""
        return key in self._config or key in self._defaults
    
    def keys(self):
        """获取所有配置键"""
        all_keys = set(self._defaults.keys()) | set(self._config.keys())
        return list(all_keys)


class ConfigManager:
    """配置管理器 - 支持多源配置合并"""
    
    def __init__(self):
        self._config_sources = []
        self._config = Config()
    
    def add_source(self, source_type: str, **kwargs) -> None:
        """添加配置源"""
        self._config_sources.append({
            'type': source_type,
            'params': kwargs
        })
    
    def load_config(self) -> Config:
        """加载并合并所有配置源"""
        merged_config = {}
        
        for source in self._config_sources:
            source_type = source['type']
            params = source['params']
            
            if source_type == 'file':
                file_config = Config.from_file(params['filepath'])
                merged_config.update(file_config.to_dict())
            elif source_type == 'env':
                prefix = params.get('prefix', 'HELLOAGENTS_')
                env_config = Config.from_env_vars(prefix)
                merged_config.update(env_config.to_dict())
            elif source_type == 'dict':
                merged_config.update(params.get('config_dict', {}))
            else:
                raise ValueError(f"不支持的配置源类型: {source_type}")
        
        self._config = Config(merged_config)
        return self._config
    
    def get_config(self) -> Config:
        """获取当前配置"""
        return self._config
    
    def reload(self) -> Config:
        """重新加载配置"""
        return self.load_config()


# 全局配置实例
_global_config = None


def get_global_config() -> Config:
    """获取全局配置实例"""
    global _global_config
    if _global_config is None:
        _global_config = Config()
    return _global_config


def set_global_config(config: Config) -> None:
    """设置全局配置实例"""
    global _global_config
    _global_config = config


def load_config_from_file(filepath: str) -> Config:
    """从文件加载配置并设置为全局配置"""
    config = Config.from_file(filepath)
    set_global_config(config)
    return config