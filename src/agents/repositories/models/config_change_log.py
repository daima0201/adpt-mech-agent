"""
配置变更日志模型
对应 config_change_logs 表
"""

from sqlalchemy import Column, String, Text, Integer, JSON
from src.agents.base.base_config import BaseConfig

class ConfigChangeLog(BaseConfig):
    """配置变更日志模型"""
    __tablename__ = 'config_change_logs'
    
    config_type = Column(String(50), nullable=False)  # agent, llm, prompt, etc.
    config_id = Column(Integer, nullable=False)
    operation = Column(String(20), nullable=False)  # create, update, delete
    old_values = Column(JSON, nullable=True)
    new_values = Column(JSON, nullable=True)
    change_reason = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    
    def __repr__(self):
        return f"<ConfigChangeLog(id={self.id}, config_type='{self.config_type}', operation='{self.operation}')>"
    
    @property
    def summary(self) -> str:
        """变更摘要"""
        return f"{self.config_type} #{self.config_id} {self.operation}"
    
    def get_changed_fields(self) -> list:
        """获取变更的字段列表"""
        if not self.old_values or not self.new_values:
            return []
        
        changed = []
        for key in set(self.old_values.keys()) | set(self.new_values.keys()):
            old_val = self.old_values.get(key)
            new_val = self.new_values.get(key)
            if old_val != new_val:
                changed.append(key)
        return changed