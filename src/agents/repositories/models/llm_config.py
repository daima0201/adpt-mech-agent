"""
LLM配置模型
对应 llm_configs 表
"""

from sqlalchemy import Column, String, Text, Integer, Boolean, JSON
from sqlalchemy.dialects.mysql import DECIMAL

from src.agents.base.base_config import BaseConfig


class LLMConfig(BaseConfig):
    """LLM配置模型"""
    __tablename__ = 'llm_configs'

    name = Column(String(100), nullable=False, unique=True)
    llm_type = Column(String(50), nullable=False)  # openai, azure, anthropic, etc.
    api_key = Column(String(255), nullable=True)
    base_url = Column(String(500), nullable=True)
    model_name = Column(String(100), nullable=False)
    temperature = Column(DECIMAL, default=0.7)  # 0-2 scale
    max_tokens = Column(Integer, default=2048)
    timeout = Column(Integer, default=30)
    max_retries = Column(Integer, default=3)
    extra_params = Column(JSON, nullable=True)
    description = Column(Text, nullable=True)
    is_usable = Column(Boolean, server_default='true', comment="是否可用")

    def __repr__(self):
        return f"<LLMConfig(id={self.id}, name='{self.name}', type='{self.llm_type}')>"
