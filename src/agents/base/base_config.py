"""
基础数据模型
定义所有模型的公共字段和方法
"""

from datetime import datetime
from typing import Optional
from sqlalchemy import Column, Integer, DateTime, String, text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class BaseConfig(Base):
    """基础模型类"""
    __abstract__ = True
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    created_by = Column(String(100), nullable=True)
    updated_by = Column(String(100), nullable=True)
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {}
        for column in self.__table__.columns:
            value = getattr(self, column.name)
            if isinstance(value, datetime):
                value = value.isoformat()
            result[column.name] = value
        return result
    
    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        instance = cls()
        for key, value in data.items():
            if hasattr(instance, key):
                setattr(instance, key, value)
        return instance