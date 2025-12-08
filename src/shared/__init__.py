"""
共享模块
提供项目通用的工具函数、配置管理、异常体系等共享功能
"""

__version__ = "1.0.0"

# 导出主要接口
from .utils.logger import get_logger
from .config.manager import ConfigManager
from .exceptions.base import BaseError

__all__ = [
    'get_logger',
    'ConfigManager', 
    'BaseException'
]