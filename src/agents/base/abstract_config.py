"""
配置管理类 - 支持多层级配置源（数据库、文件、环境变量）
"""

import os
import yaml
import json
from typing import Any, Dict, Optional
from pathlib import Path


class MultiSourceConfigManager:
    """多源配置管理器 - 支持多层级配置源"""
    
    def __init__(self, config_type: str, config_name: str = "default",
                 db_repository=None, config_dir: str = "./configs"):
        self.config_type = config_type  # agent, llm, knowledge, etc.
        self.config_name = config_name
        self.db_repository = db_repository
        self.config_dir = Path(config_dir)
        self._config_cache = {}
    
    async def get_config(self) -> Dict[str, Any]:
        """获取配置 - 优先级：数据库 > 配置文件 > 默认配置"""
        cache_key = f"{self.config_type}:{self.config_name}"
        
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]
        
        # 1. 尝试从数据库获取
        config = await self._get_from_database()
        if config:
            self._config_cache[cache_key] = config
            return config
        
        # 2. 尝试从配置文件获取
        config = self._get_from_file()
        if config:
            self._config_cache[cache_key] = config
            return config
        
        # 3. 使用默认配置
        config = self._get_default_config()
        self._config_cache[cache_key] = config
        return config
    
    async def _get_from_database(self) -> Optional[Dict[str, Any]]:
        """从数据库获取配置"""
        if not self.db_repository:
            return None
        
        try:
            if self.config_type == "agent":
                # 通过名称查找智能体配置
                agent = await self.db_repository.get_by_name(self.config_name)
                if agent:
                    return await self.db_repository.get_full_agent_config(agent.id)
            elif self.config_type == "llm":
                # 通过名称查找LLM配置
                llm_configs = await self.db_repository.list_active_llms()
                for llm in llm_configs:
                    if llm.name == self.config_name:
                        return llm.to_dict()
            return None
        except Exception as e:
            print(f"从数据库获取配置失败: {e}")
            return None
    
    def _get_from_file(self) -> Optional[Dict[str, Any]]:
        """从配置文件获取配置"""
        file_paths = [
            self.config_dir / f"{self.config_name}.yaml",
            self.config_dir / f"{self.config_name}.yml",
            self.config_dir / f"{self.config_name}.json",
            self.config_dir / "default.yaml"
        ]
        
        for file_path in file_paths:
            if file_path.exists():
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        if file_path.suffix in ['.yaml', '.yml']:
                            config = yaml.safe_load(f) or {}
                        elif file_path.suffix == '.json':
                            config = json.load(f) or {}
                        else:
                            continue
                    
                    # 提取对应类型的配置
                    if self.config_type in config:
                        return config[self.config_type]
                    elif self.config_type == "global":
                        return config
                    else:
                        return None
                except Exception as e:
                    print(f"读取配置文件失败 {file_path}: {e}")
                    continue
        
        return None
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置 - 根据配置类型返回不同的默认值"""
        defaults = {
            "agent": {
                "type": "react",
                "max_iterations": 5,
                "timeout": 30,
                "enable_knowledge": True,
                "enable_tools": True
            },
            "llm": {
                "provider": "openai",
                "model": "gpt-3.5-turbo",
                "temperature": 0.1,
                "max_tokens": 2000,
                "timeout": 30
            },
            "knowledge": {
                "vector_store": {
                    "type": "chroma",
                    "persist_directory": "./data/vector_stores/chroma"
                },
                "embedder": {
                    "type": "local",
                    "model_name": "BAAI/bge-small-zh-v1.5"
                },
                "retriever": {
                    "type": "hybrid",
                    "top_k": 5
                }
            },
            "tools": {
                "builtin": {
                    "calculator": True,
                    "search": True,
                    "knowledge_query": True
                }
            }
        }
        
        return defaults.get(self.config_type, {})
    
    def clear_cache(self):
        """清除配置缓存"""
        self._config_cache.clear()


class EnvironmentConfig:
    """环境变量配置类"""
    
    def __init__(self, prefix: str = "AGENT_"):
        self.prefix = prefix
        self._config = {}
        self._load_env_vars()
    
    def _load_env_vars(self):
        """从环境变量加载配置"""
        for key, value in os.environ.items():
            if key.startswith(self.prefix):
                config_key = key[len(self.prefix):].lower()
                
                # 尝试转换类型
                if value.lower() in ('true', 'false'):
                    value = value.lower() == 'true'
                elif value.isdigit():
                    value = int(value)
                elif value.replace('.', '').isdigit():
                    value = float(value)
                
                self._config[config_key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        return self._config.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self._config.copy()


# 兼容性函数
def get_global_config() -> Dict[str, Any]:
    """获取全局配置"""
    manager = MultiSourceConfigManager("global")
    return manager._get_from_file() or {}


def load_config_from_file(filepath: str) -> Dict[str, Any]:
    """从文件加载配置"""
    manager = MultiSourceConfigManager("global")
    return manager._get_from_file() or {}
