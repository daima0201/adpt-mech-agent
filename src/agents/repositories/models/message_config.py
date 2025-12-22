"""
消息配置数据模型
定义消息相关的配置参数
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from src.agents.base.base_config import BaseConfig


class MessageConfig(BaseConfig):
    """消息配置模型"""
    __tablename__ = 'message_configs'
    
    name = Column(String(255), nullable=False, unique=True, comment='配置名称')
    max_history = Column(Integer, default=50, comment='最大历史消息数')
    truncate_length = Column(Integer, default=1000, comment='截断长度')
    enable_summary = Column(Boolean, default=True, comment='是否启用摘要')
    summary_threshold = Column(Integer, default=20, comment='摘要阈值')
    
    def __repr__(self):
        return f"<MessageConfig(name='{self.name}', max_history={self.max_history})>"
    
    def to_dict(self):
        """转换为字典格式"""
        result = super().to_dict()
        result.update({
            'name': self.name,
            'max_history': self.max_history,
            'truncate_length': self.truncate_length,
            'enable_summary': self.enable_summary,
            'summary_threshold': self.summary_threshold
        })
        return result