"""
统一日志系统
提供标准化的日志记录功能
"""

import logging
import sys
from pathlib import Path
from typing import Optional, Dict, Any


class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器"""
    
    COLORS = {
        'DEBUG': '\033[36m',     # 青色
        'INFO': '\033[32m',      # 绿色
        'WARNING': '\033[33m',   # 黄色
        'ERROR': '\033[31m',     # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'       # 重置
    }
    
    def format(self, record):
        log_message = super().format(record)
        if record.levelname in self.COLORS:
            return f"{self.COLORS[record.levelname]}{log_message}{self.COLORS['RESET']}"
        return log_message


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    format_str: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    enable_colors: bool = True
) -> None:
    """
    设置日志配置
    
    Args:
        level: 日志级别 (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: 日志文件路径，如果为None则只输出到控制台
        format_str: 日志格式字符串
        enable_colors: 是否启用彩色输出
    """
    # 清除现有的处理器
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # 设置日志级别
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    root_logger.setLevel(numeric_level)
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    if enable_colors:
        formatter = ColoredFormatter(format_str)
    else:
        formatter = logging.Formatter(format_str)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # 创建文件处理器（如果需要）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file, encoding='utf-8')
        file_formatter = logging.Formatter(format_str)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)
    
    # 防止日志传播到父logger
    root_logger.propagate = False


def get_logger(name: str, level: Optional[str] = None) -> logging.Logger:
    """
    获取指定名称的logger
    
    Args:
        name: logger名称
        level: 日志级别，如果为None则使用根logger的级别
        
    Returns:
        logging.Logger实例
    """
    logger = logging.getLogger(name)
    
    if level:
        numeric_level = getattr(logging, level.upper(), logging.INFO)
        logger.setLevel(numeric_level)
    
    return logger


class LoggerMixin:
    """日志混入类，为其他类提供日志功能"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的logger"""
        if not hasattr(self, '_logger'):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger